from app.database import SessionLocal
from app.models import Investment, CryptoWallet

def check_btc_status():
    db = SessionLocal()
    print("--- Investments ---")
    investments = db.query(Investment).filter(Investment.symbol == "BTC").all()
    for inv in investments:
        print(f"ID: {inv.id}, Name: {inv.name}, Platform: {inv.platform}")
        print(f"  Holdings: {inv.holdings}")
        print(f"  Current Price: {inv.current_price}")
        print(f"  Value: {inv.holdings * inv.current_price if inv.holdings and inv.current_price else 0}")
        
        # Check associated wallet status
        # inv.crypto_wallet is likely a list
        if inv.crypto_wallet:
             for wallet in inv.crypto_wallet:
                 print(f"  Wallet ID: {wallet.id}, XPUB: {wallet.xpub[:15]}..., Status: {wallet.status}")
                 print(f"  Last Synced: {wallet.last_synced_at}")
        else:
             print("  [No generic crypto_wallet link found]")

    db.close()

if __name__ == "__main__":
    check_btc_status()
