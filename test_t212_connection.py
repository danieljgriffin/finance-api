"""
Debug script to test Trading212 API connection.
Run this to verify your credentials work before using the app.

Usage:
  .venv/bin/python test_t212_connection.py
"""
import requests
import base64
import sys

def test_connection(api_key: str, api_secret: str):
    """Test Trading212 API connection with provided credentials"""
    
    # Build Basic Auth header
    credentials = f"{api_key}:{api_secret}"
    encoded_creds = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    auth_header = f"Basic {encoded_creds}"
    
    print(f"\n{'='*50}")
    print("Trading212 API Connection Test")
    print(f"{'='*50}")
    print(f"API Key length: {len(api_key)} chars")
    print(f"API Secret length: {len(api_secret)} chars")
    print(f"Auth header prefix: {auth_header[:30]}...")
    
    # Try live endpoint
    urls = [
        ("Live", "https://live.trading212.com/api/v0/equity/portfolio"),
        ("Demo", "https://demo.trading212.com/api/v0/equity/portfolio"),
    ]
    
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for name, url in urls:
        print(f"\n🔄 Testing {name} endpoint...")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS! Connected to {name}")
                print(f"   Found {len(data)} positions in portfolio:")
                for pos in data[:5]:  # Show first 5
                    print(f"   - {pos.get('ticker')}: {pos.get('quantity')} units")
                if len(data) > 5:
                    print(f"   ... and {len(data)-5} more")
                return True
            else:
                print(f"❌ FAILED: Status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    return False

if __name__ == "__main__":
    print("\nEnter your Trading212 API credentials:")
    print("(You can find these in Trading212 -> Settings -> API)")
    print("")
    
    api_key = input("API Key: ").strip()
    api_secret = input("API Secret: ").strip()
    
    if not api_key or not api_secret:
        print("\n❌ Both API Key and API Secret are required!")
        print("\nNote: When you generate an API key in Trading212, you get TWO values:")
        print("  1. API Key (a long alphanumeric string)")
        print("  2. API Secret (another long string, shown only ONCE)")
        print("\nIf you only see ONE value, that might be an older key format.")
        sys.exit(1)
    
    success = test_connection(api_key, api_secret)
    
    if success:
        print("\n✅ Your credentials work! You can now use them in the app.")
    else:
        print("\n❌ Connection failed. Please check:")
        print("   1. Did you copy BOTH the API Key AND Secret correctly?")
        print("   2. Is the API key enabled in Trading212?")
        print("   3. Did you select 'Portfolio' permission when generating the key?")
        print("   4. Are you using a Live (not Demo) account key with the Live URL?")
