"""Encryption service for sensitive data."""

import base64
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize encryption service.

        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()

        # Generate key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"t-tasker-salt",  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.settings.session_secret.get_secret_value().encode())
        )

        self.cipher = Fernet(key)
        logger.info("Encryption service initialized")

    def encrypt(self, data: str) -> str:
        """Encrypt string data.

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data as base64 string
        """
        if not data:
            return ""

        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt data") from e

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data.

        Args:
            encrypted_data: Encrypted data as base64 string

        Returns:
            Decrypted data
        """
        if not encrypted_data:
            return ""

        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt data") from e


# Global encryption service instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get encryption service instance.

    Returns:
        Encryption service instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
