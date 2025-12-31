from hdwallet.hds import BIP32HD
from hdwallet import HDWallet
from hdwallet.addresses import P2WPKHAddress
from hdwallet.cryptocurrencies import Bitcoin as BTC
import base58

def test_robust():
    # Valid XPUB (Standard)
    xpub = "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8"
    
    # 1. Depth Hack
    try:
        raw = base58.b58decode_check(xpub)
        data = list(raw)
        data[0:4] = [0x04, 0x88, 0xB2, 0x1E] # Force XPUB version
        data[4] = 0 # Depth 0
        data[5:9] = [0, 0, 0, 0]
        data[9:13] = [0, 0, 0, 0]
        hacked_key = base58.b58encode_check(bytes(data)).decode()
        print(f"Hacked Key: {hacked_key[:15]}...")
    except Exception as e:
        print(f"Hack failed: {e}")
        return

    # 2. Use HDWallet Wrapper with BIP32HD and Explicit Address Class
    try:
        print("Using HDWallet(hd=BIP32HD, address=P2WPKHAddress)...")
        hd = HDWallet(cryptocurrency=BTC, hd=BIP32HD, address=P2WPKHAddress)
        hd.from_xpublic_key(hacked_key)
        
        # 3. Derive 0/0 using protected _hd to bypass wrapper
        hd._hd.drive(0)
        hd._hd.drive(0)
        
        addr = hd.address()
        print(f"Direct Address Check: {addr}")
        if addr.startswith("bc1"):
             print("SUCCESS: Got Bech32 address")
             
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_robust()
