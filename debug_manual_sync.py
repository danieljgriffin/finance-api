import asyncio
from app.database import SessionLocal
from app.services.crypto_service import CryptoService
from app.models import CryptoWallet

async def test_sync():
    db = SessionLocal()
    service = CryptoService(db)
    
    # Get all active crypto wallets
    wallets = db.query(CryptoWallet).all()
    print(f"Found {len(wallets)} wallets.")
    
    for wallet in wallets:
        print(f"Syncing Wallet ID: {wallet.id}, Type: {wallet.xpub[:4]}...")
        try:
            await service.sync_wallet(wallet)
            print(f"  [SUCCESS] Synced wallet {wallet.id}. Status: {wallet.status}, Last Synced: {wallet.last_synced_at}")
        except Exception as e:
            print(f"  [ERROR] Failed to sync wallet {wallet.id}: {e}")
            import traceback
            traceback.print_exc()

    db.close()

if __name__ == "__main__":
    asyncio.run(test_sync())
