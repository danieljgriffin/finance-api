from hdwallet import HDWallet
from hdwallet.symbols import BTC

def test_formats():
    print("Testing HDWallet formats...")
    
    # Try positional 
    try:
        hd = HDWallet(BTC)
        print("Initialized with positional arg")
    except Exception as e:
        print(f"Positional init failed: {e}")
        try:
             # Try kwarg
             hd = HDWallet(cryptocurrency=BTC)
             print("Initialized with cryptocurrency=")
        except Exception as e:
             print(f"d init failed: {e}")
             return

    print(f"Has from_zpublic_key? {hasattr(hd, 'from_zpublic_key')}")
    print(f"Has from_ypublic_key? {hasattr(hd, 'from_ypublic_key')}")
    print(f"Has from_xpublic_key? {hasattr(hd, 'from_xpublic_key')}")

if __name__ == "__main__":
    test_formats()
