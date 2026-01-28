# Quick diagnostic to check T212 credential status
import sys
sys.path.insert(0, '/Users/danielgriffin/Documents/Apps/WealthTrackerStack/finance-api')

from app.database import SessionLocal
from app.models import User
import json

db = SessionLocal()
user = db.query(User).filter(User.id == 1).first()

print("=" * 50)
print("Trading212 Credential Diagnostic")
print("=" * 50)

if user:
    print(f"\n✅ User found (ID: {user.id}, Email: {user.email})")
    
    if user.preferences:
        prefs = user.preferences
        print(f"\n📋 Preferences keys: {list(prefs.keys())}")
        
        t212_config = prefs.get('trading212_sync')
        if t212_config:
            print("\n✅ trading212_sync config found:")
            print(f"   enabled: {t212_config.get('enabled')}")
            print(f"   updated_at: {t212_config.get('updated_at')}")
            print(f"   has api_key_id_enc: {bool(t212_config.get('api_key_id_enc'))}")
            print(f"   has api_secret_key_enc: {bool(t212_config.get('api_secret_key_enc'))}")
            
            if not t212_config.get('enabled'):
                print("\n⚠️  ISSUE: enabled is False - auto-sync is disabled!")
            elif not t212_config.get('api_key_id_enc'):
                print("\n⚠️  ISSUE: No encrypted API Key ID found!")
            elif not t212_config.get('api_secret_key_enc'):
                print("\n⚠️  ISSUE: No encrypted API Secret Key found!")
            else:
                print("\n✅ Credentials appear to be configured correctly")
                # Try to decrypt
                try:
                    from app.utils.security import decrypt_value
                    key_id = decrypt_value(t212_config.get('api_key_id_enc'))
                    secret = decrypt_value(t212_config.get('api_secret_key_enc'))
                    print(f"✅ Decryption successful (key_id length: {len(key_id)}, secret length: {len(secret)})")
                except Exception as e:
                    print(f"\n❌ ISSUE: Decryption FAILED: {e}")
        else:
            print("\n❌ No trading212_sync config in preferences")
    else:
        print("\n❌ User has no preferences set")
else:
    print("\n❌ User ID 1 not found in database")

db.close()
print("\n" + "=" * 50)
