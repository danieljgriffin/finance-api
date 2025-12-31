import requests
from app.database import SessionLocal
from app.models import Investment

BASE_URL = "http://localhost:8000"

def test_delete():
    # 1. Create a dummy investment with CryptoWallet directly in DB
    db = SessionLocal()
    dummy = Investment(
        user_id=1,
        platform="TestPlatform",
        name="DeleteMeCrypto",
        symbol="BTC",
        holdings=1,
        current_price=100
    )
    db.add(dummy)
    db.commit()
    db.refresh(dummy)
    
    # Add linked wallet
    from app.models import CryptoWallet
    wallet = CryptoWallet(investment_id=dummy.id, xpub="xpubTest...", status="active")
    db.add(wallet)
    db.commit()
    
    dummy_id = dummy.id
    print(f"Created dummy investment with wallet ID: {dummy_id}")
    db.close()
    
    # 2. Try to delete it via API
    try:
        print(f"Attempting DELETE /holdings/{dummy_id}...")
        headers = {"Authorization": "Bearer dev-token-123"}
        resp = requests.delete(f"{BASE_URL}/holdings/{dummy_id}", headers=headers)
        print(f"Response: {resp.status_code}")
        print(f"Body: {resp.text}")
        
        if resp.status_code == 200:
            print("DELETE SUCCESS matches API expectation.")
        else:
            print("DELETE FAILED.")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_delete()
