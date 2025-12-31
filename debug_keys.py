from app.services.crypto_service import CryptoService
from app.database import SessionLocal
from hdwallet import HDWallet
from hdwallet.symbols import BTC

def test_keys():
    # Mock DB
    db = SessionLocal()
    service = CryptoService(db)
    
    # VALID TEST VECTORS (from BIP32/BIP84/BIP49 specs or public test vectors)
    valid_xpub = "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8"
    valid_zpub = "zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xXY7WLNCcecLcu3295J2818rJm5Xg6kP2p59J3498r593285" # Note: This might be invalid, need real vector
    # Real BIP84 zpub vector
    real_zpub = "zpub6jftahH18ngVxma5zL3mhLqD1QnVpyV5C42FpuvS5y5y3D5e5q595555555555555555555555555555555555" # Placeholder
    # Actually, let's use a known good/bad to just inspect library.
    # We will try to load them and see EXACT error if any.
    
    print("\n--- Testing Valid XPUB ---")
    try:
        hd = HDWallet(cryptocurrency=BTC)
        hd.from_xpublic_key(valid_xpub)
        print("SUCCESS: Standard XPUB loaded via from_xpublic_key")
    except Exception as e:
        print(f"FAILED: Standard XPUB: {e}")

    # Checking Method Existence
    hd = HDWallet(cryptocurrency=BTC)
    print(f"\nHas from_zpublic_key? {hasattr(hd, 'from_zpublic_key')}")
    print(f"Has from_ypublic_key? {hasattr(hd, 'from_ypublic_key')}")

    # Simulate validate_xpub
    print(f"\nvalidate_xpub('{valid_xpub[:10]}...'): {service.validate_xpub(valid_xpub)}")

    db.close()

if __name__ == "__main__":
    test_keys()
