from hdwallet import HDWallet
from hdwallet.cryptocurrencies import Bitcoin as BTC

def inspect_hdwallet():
    # VALID TEST VECTORS 
    valid_xpub = "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqZL4h..." # Shortened
    valid_xpub = "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8"

    hd = HDWallet(cryptocurrency=BTC)
    hd.from_xpublic_key(valid_xpub)
    
    print("\n--- Methods ---")
    # print([x for x in dir(hd) if 'address' in x])

    print("\n--- Dumps ---")
    try:
        data = hd.dumps()
        print("Keys in dump:", data.keys())
        if 'addresses' in data:
            print("Addresses keys:", data['addresses'].keys())
    except Exception as e:
        print(f"Dump failed: {e}")
        
    print("\n--- Test Access ---")
    try:
        print(f"P2WPKH via property? {hd.p2wpkh_address}")
    except:
        pass
        
    try:
        print(f"P2WPKH via method? {hd.p2wpkh_address()}")
    except Exception as e:
        print(f"Method call failed: {e}")

if __name__ == "__main__":
    inspect_hdwallet()
