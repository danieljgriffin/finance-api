from app.services.crypto_service import CryptoService
from app.database import SessionLocal
from hdwallet import HDWallet
# CORRECT IMPORT:
from hdwallet.cryptocurrencies import Bitcoin as BTC

def test_keys():
    # Mock DB
    db = SessionLocal()
    service = CryptoService(db)
    
    # VALID TEST VECTORS 
    valid_xpub = "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8"
    
    print("\n--- Testing Valid XPUB with Correct Import ---")
    try:
        # Pass the CLASS, not the string symbol
        hd = HDWallet(cryptocurrency=BTC)
        hd.from_xpublic_key(valid_xpub)
        print("SUCCESS: Standard XPUB loaded via from_xpublic_key")
    except Exception as e:
        print(f"FAILED: Standard XPUB: {e}")

    print("\n--- Testing Valid ZPUB with Correct Import ---")
    valid_zpub = "zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xXY7WLNCcecLcu3295J2818rJm5Xg6kP2p59J3498r593285"
    try:
        hd = HDWallet(cryptocurrency=BTC)
        hd.from_xpublic_key(valid_zpub)
        print("SUCCESS: ZPUB loaded via from_xpublic_key")
    except Exception as e:
        print(f"FAILED: ZPUB: {e}")
        
    print(f"\nHas from_zpublic_key? {hasattr(HDWallet, 'from_zpublic_key')}")

    db.close()

if __name__ == "__main__":
    test_keys()
