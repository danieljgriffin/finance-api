from app.services.crypto_service import CryptoService
from app.database import SessionLocal
from hdwallet import HDWallet
from hdwallet.symbols import BTC

def test_validation():
    # Mock DB
    db = SessionLocal()
    service = CryptoService(db)
    
    # Test Cases
    cases = [
        ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", True), # Genesis (Legacy)
        ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", True), # Nested Segwit
        ("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq", True), # Native Segwit
        ("xpub6CUGRUonZSQ4CCyTouCKTq1gYq8s8tfrfyb2P6Fh... (invalid)", False), 
        ("invalid", False)
    ]
    
    print("Testing CryptoService Validation:")
    for key, expected in cases:
        result = service.validate_xpub(key)
        status = "PASS" if result == expected else "FAIL"
        print(f"[{status}] Key: {key[:20]}... Result: {result}, Expected: {expected}")
        
    db.close()

if __name__ == "__main__":
    test_validation()
