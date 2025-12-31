import requests
from app.database import SessionLocal
from app.models import Investment, CryptoWallet, PlatformCash

BASE_URL = "http://localhost:8000"
TOKEN = "dev-token-123"

def test_platform_delete():
    db = SessionLocal()
    platform_name = "DeleteMePlatform_v4"
    
    # 1. Create Platform Cash
    cash = PlatformCash(user_id=1, platform=platform_name, cash_balance=100)
    db.add(cash)
    
    # 2. Create Investment
    inv = Investment(
        user_id=1,
        platform=platform_name,
        name="DeleteMeInv",
        symbol="BTC",
        holdings=1,
        current_price=100
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    
    # 3. Create CryptoWallet
    wallet = CryptoWallet(investment_id=inv.id, xpub="xpubTest", status="active")
    db.add(wallet)
    db.commit()
    
    # 4. Create CryptoBalanceSnapshot (The likely new blocker)
    from app.models import CryptoBalanceSnapshot
    snapshot = CryptoBalanceSnapshot(wallet_id=wallet.id, balance=1.5, currency="BTC")
    db.add(snapshot)
    db.commit()
    
    print(f"Created Platform '{platform_name}' with Investment {inv.id}, Wallet {wallet.id}, and Snapshot {snapshot.id}")
    db.close()
    
    # 5. Try DELETE Platform
    try:
        print(f"Attempting DELETE /holdings/platform/{platform_name}...")
        headers = {"Authorization": f"Bearer {TOKEN}"}
        resp = requests.delete(f"{BASE_URL}/holdings/platform/{platform_name}", headers=headers)
        print(f"Response: {resp.status_code}")
        print(f"Body: {resp.text}")
        
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_platform_delete()
