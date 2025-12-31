from hdwallet import HDWallet
from hdwallet.cryptocurrencies import Bitcoin as BTC
import base58

def test_repro():
    zpub = "zpub6rFR7y4Q2AijBEqTUquhVz398htDFrtymD9xXY7WLNCcecLcu3295J2818rJm5Xg6kP2p59J3498r593285"
    print(f"Testing ZPUB: {zpub[:15]}...")
    
    # 1. Convert to XPUB header
    try:
        data = base58.b58decode_check(zpub)
        # 1. Version Fix (ZPUB -> XPUB)
        xpub_version = bytes.fromhex("0488B21E")
        data = xpub_version + data[4:]
        
        # 2. Depth Fix (Set depth to 0 to prevent library from checking parent paths)
        # Depth is byte offset 4 (after version 0-3). Wait, version is 4 bytes.
        # Structure: Version(4) | Depth(1) | Fingerprint(4) | Index(4) | Chain(32) | Key(33)
        # Offset 4 is Depth.
        data_list = list(data)
        data_list[4] = 0 # Set depth to 0
        # Optional: Clear fingerprint (5-9) and Child Index (9-13)? 
        # Usually depth 0 implies root, so fingerprint 00000000 and index 00000000.
        # Let's set them to 0 just in case strict validation checks consistency.
        data_list[5:9] = [0, 0, 0, 0] # Fingerprint
        data_list[9:13] = [0, 0, 0, 0] # Child Index
        data = bytes(data_list)
        
        key_to_load = base58.b58encode_check(data).decode()
        print(f"Hacked XPUB: {key_to_load[:15]}...")
    except Exception as e:
        print(f"Conversion failed: {e}")
        return

    # 2. Test Derivation
    try:
        hd = HDWallet(cryptocurrency=BTC)
        hd.from_xpublic_key(key_to_load)
        
        # Proposed Fix: Manual Path m/0/0 (External Chain, Index 0)
        # Note: XPUB is at account level (m/84'/0'/0'), so "m/0/0" relative to it implies m/84'/0'/0'/0/0
        # However, hdwallet.from_path might reset or append?
        # If I use `from_xpublic_key`, I am at the root of THAT key.
        # So I should use .from_path("m/0/0")? No, .from_path is usually absolute if starting with m?
        # Actually standard practice is .from_key().clean_derivation().from_path("0/0")?
        # Let's try .from_index(0).from_index(0)? (Change=0, Index=0)
        
        print("\n--- Attempting Manual Path (0/0) ---")
        hd.clean_derivation()
        hd.from_xpublic_key(key_to_load)
        
        # Derive Change (0) -> Index (0)
        # Assuming we are at Account level
        hd.from_index(0, hardened=False) # External/Receive
        hd.from_index(0, hardened=False) # Index 0
        
        addr = hd.p2wpkh_address() # Get address property/method
        print(f"Derived Address: {addr}")
        print("SUCCESS! Manual derivation worked.")
        
    except Exception as e:
        print(f"FAILED Manual Derivation: {e}")

if __name__ == "__main__":
    test_repro()
