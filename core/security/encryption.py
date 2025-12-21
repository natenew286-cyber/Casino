from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib


class DataEncryption:
    """
    Utility for encrypting sensitive data
    """
    def __init__(self):
        self.cipher_suite = Fernet(self._get_encryption_key())
    
    def _get_encryption_key(self):
        # Generate key from Django secret key
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return base64.urlsafe_b64encode(key[:32])
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        encrypted = self.cipher_suite.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data"""
        decrypted = self.cipher_suite.decrypt(encrypted_data.encode())
        return decrypted.decode()