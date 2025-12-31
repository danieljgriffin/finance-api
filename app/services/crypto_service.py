from sqlalchemy.orm import Session
from app.models import CryptoWallet, CryptoBalanceSnapshot, Investment
from datetime import datetime
import httpx
from hdwallet import HDWallet
from hdwallet.cryptocurrencies import Bitcoin as BTC
from typing import List, Dict, Optional

class CryptoService:
    def __init__(self, db: Session):
        self.db = db
        self.MEMPOOL_API = "https://mempool.space/api"

    def validate_xpub(self, xpub: str) -> bool:
        try:
            hdwallet = HDWallet(cryptocurrency=BTC)
            # Try loading as xpub, zpub, or ypub
            # The library has specific methods but from_xpublic_key usually handles standard xpubs
            # For zpub/ypub we might need specific calls or the library auto-detects if we use the right one.
            # Let's try from_xpublic_key first, it often handles the base BIP32 serialization.
            # If that fails, we can't easily check zpub without knowing method existence (which we checked).
            # Based on library docs/behavior, let's try generic load or just xpub.
            # Try generic load first
            hdwallet.from_xpublic_key(xpub)
            return True
        except Exception:
            # If standard xpub load fails, check if it is a valid single address
            # 1. Single Address Check (Legacy, Nested Segwit, Native Segwit)
            if xpub.startswith("1") or xpub.startswith("3") or xpub.startswith("bc1"):
                # Basic length checks
                if 25 <= len(xpub) <= 90:
                    return True
            
            # 2. Extended Public Key Check (xpub, ypub, zpub, etc.)
            # These are Base58 strings usually starting with xpub, ypub, zpub, tpub, upub, vpub...
            # Length is constant 111 chars usually, but better to just check prefix and length range
            valid_prefixes = ["xpub", "ypub", "zpub", "tpub", "upub", "vpub"]
            if any(xpub.startswith(p) for p in valid_prefixes):
                 if 100 <= len(xpub) <= 120:
                     return True
                     
            return False

        return addresses

    def derive_addresses(self, xpub: str, count: int = 20) -> List[str]:
        """Derive addresses or return single address if input is not an xpub"""
        # If it looks like a single address, return it directly
        if xpub.startswith("1") or xpub.startswith("3") or xpub.startswith("bc1"):
            return [xpub]

        addresses = []
        try:
            import base58
            
            import base58
            
            # Transform key for library compatibility (Force Root + XPUB Header)
            try:
                raw = base58.b58decode_check(xpub)
                data = list(raw)
                
                # 1. Header Fix: Convert ZPUB/YPUB to XPUB (0x0488B21E)
                # This ensures the library recognizes the key format
                if xpub.startswith("zpub") or xpub.startswith("ypub"):
                    data[0:4] = [0x04, 0x88, 0xB2, 0x1E]
                
                # 2. Depth Fix: Reset Depth, Parent Fingerprint, and Child Index to 0
                # This tricks the library into thinking this is a Root key (m/)
                # preventing "Hardened derivation path is invalid" errors when loading Account-level keys
                data[4] = 0 # Depth
                data[5:9] = [0, 0, 0, 0] # Parent Fingerprint
                data[9:13] = [0, 0, 0, 0] # Child Number
                
                key_to_load = base58.b58encode_check(bytes(data)).decode()
            except Exception as e:
                print(f"Key transformation failed: {e}")
                key_to_load = xpub

            # Use verified imports for robust derivation
            from hdwallet.hds import BIP32HD
            from hdwallet.addresses import P2WPKHAddress
            
            # Use HDWallet with BIP32HD + P2WPKHAddress explicitly
            # This configures the instance to handle keys without strict BIP44 path checking (BIP32HD)
            # and to generate Native Segwit addresses (P2WPKHAddress)
            hdwallet = HDWallet(cryptocurrency=BTC, hd=BIP32HD, address=P2WPKHAddress)
            hdwallet.from_xpublic_key(key_to_load)
            
            # Deriving external chain (receive) addresses: m/0/i
            for i in range(count):
                hdwallet.from_xpublic_key(key_to_load) # Reset to root
                # Manual derivation using protected _hd to bypass wrapper checks
                hdwallet._hd.drive(0) # External
                hdwallet._hd.drive(i) # Index
                addresses.append(hdwallet.address())
                
            # Change addresses: m/1/i
            for i in range(5):
                hdwallet.from_xpublic_key(key_to_load)
                hdwallet._hd.drive(1) # Change
                hdwallet._hd.drive(i) # Index
                addresses.append(hdwallet.address())
                
        except Exception as e:
            print(f"Derivation error: {e}")
            return []
            
        return addresses

    async def fetch_balance(self, addresses: List[str]) -> float:
        """Fetch balance for multiple addresses using mempool.space"""
        total_sats = 0
        
        # mempool.space doesn't have a bulk address endpoint in free tier easily?
        # Actually it does not. We might need to loop or use their "address" endpoint.
        # Rate limit might be an issue. 
        # Better approach: check xpub summary if supported? No, mempool.space doesn't support xpub natively in public API.
        # We must check addresses. Limit to first 20 for MVP.
        
        async with httpx.AsyncClient() as client:
            # Parallelize?
            for addr in addresses:
                try:
                    resp = await client.get(f"{self.MEMPOOL_API}/address/{addr}")
                    if resp.status_code == 200:
                        data = resp.json()
                        chain_stats = data.get('chain_stats', {})
                        mempool_stats = data.get('mempool_stats', {})
                        
                        funded = chain_stats.get('funded_txo_sum', 0)
                        spent = chain_stats.get('spent_txo_sum', 0)
                        
                        # Add unconfirmed? Optional. Let's stick to confirmed for safety + mempool if desired.
                        # User usually wants to see what's "there" so confirmed + unconfirmed is best.
                        funded += mempool_stats.get('funded_txo_sum', 0)
                        spent += mempool_stats.get('spent_txo_sum', 0)
                        
                        total_sats += (funded - spent)
                except Exception as e:
                    print(f"Error fetching {addr}: {e}")
                    
        return total_sats / 100_000_000.0 # Convert Sats to BTC

    async def sync_wallet(self, wallet: CryptoWallet):
        """Syncs a single wallet"""
        if not wallet or not wallet.xpub:
            return

        wallet.status = 'syncing'
        self.db.commit()

        addresses = self.derive_addresses(wallet.xpub)
        if not addresses:
            wallet.status = 'error'
            self.db.commit()
            return

        balance_btc = await self.fetch_balance(addresses)
        
        # Update snapshot
        snapshot = CryptoBalanceSnapshot(
            wallet_id=wallet.id,
            balance=balance_btc,
            currency='BTC'
        )
        self.db.add(snapshot)
        
        # Update Wallet Info
        wallet.last_synced_at = datetime.utcnow()
        wallet.status = 'active'
        
        # Update Investment Holdings
        # If user has set "shares" manually, this will overwrite it. 
        if wallet.investment:
            wallet.investment.holdings = balance_btc
            wallet.investment.last_updated = datetime.utcnow()
            
        self.db.commit()
        return balance_btc

    def create_wallet_for_investment(self, investment_id: int, xpub: str):
        # Validate first
        if not self.validate_xpub(xpub):
            raise ValueError("Invalid XPUB format")
            
        wallet = CryptoWallet(
            investment_id=investment_id,
            xpub=xpub,
            status='active'
        )
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)
        return wallet
