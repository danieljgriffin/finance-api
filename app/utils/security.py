from cryptography.fernet import Fernet
import base64
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_cipher_suite():
    """
    Create a Fernet cipher suite from the SECRET_KEY.
    Fernet requires a 32-byte base64-encoded key.
    We derive this from our SECRET_KEY to ensure consistency.
    """
    key = settings.SECRET_KEY
    if not key:
        raise ValueError("SECRET_KEY is missing in configuration")
    
    # Pad or truncate to 32 chars to make it compatible (simple derivation)
    # In production, a proper KDF (Key Derivation Function) is better, 
    # but for this scale, padding/hashing to 32 bytes is sufficient.
    # We'll use SHA256 to get exactly 32 bytes, then urlsafe b64 encode it.
    import hashlib
    digest = hashlib.sha256(key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    
    return Fernet(fernet_key)

def encrypt_value(value: str) -> str:
    """Encrypt a string value"""
    if not value: return None
    try:
        cipher = get_cipher_suite()
        encrypted_bytes = cipher.encrypt(value.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise e

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value"""
    if not encrypted_value: return None
    try:
        cipher = get_cipher_suite()
        decrypted_bytes = cipher.decrypt(encrypted_value.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise e
