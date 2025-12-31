from hdwallet import HDWallet
from hdwallet.cryptocurrencies import Bitcoin as BTC

def inspect_init():
    try:
        help(HDWallet.__init__)
    except:
        pass
    
    # Try creating without derivation? 
    # Usually standard usage is:
    # hd = HDWallet(symbol="BTC")
    # hd.from_xpublic_key(xpub)
    
if __name__ == "__main__":
    inspect_init()
