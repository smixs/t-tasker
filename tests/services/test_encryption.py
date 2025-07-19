"""Tests for encryption service."""

import pytest

from src.services.encryption import EncryptionService


class TestEncryptionService:
    """Test encryption service."""

    @pytest.fixture
    def encryption_service(self):
        """Create encryption service instance."""
        return EncryptionService()

    def test_encrypt_decrypt(self, encryption_service):
        """Test encryption and decryption."""
        original = "test_token_123456789"
        
        # Encrypt
        encrypted = encryption_service.encrypt(original)
        assert encrypted != original
        assert len(encrypted) > 0
        
        # Decrypt
        decrypted = encryption_service.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_empty_string(self, encryption_service):
        """Test encrypting empty string."""
        encrypted = encryption_service.encrypt("")
        assert encrypted == ""

    def test_decrypt_empty_string(self, encryption_service):
        """Test decrypting empty string."""
        decrypted = encryption_service.decrypt("")
        assert decrypted == ""

    def test_encrypt_unicode(self, encryption_service):
        """Test encrypting unicode string."""
        original = "Привет мир! 🚀"
        
        encrypted = encryption_service.encrypt(original)
        decrypted = encryption_service.decrypt(encrypted)
        
        assert decrypted == original

    def test_decrypt_invalid_data(self, encryption_service):
        """Test decrypting invalid data."""
        with pytest.raises(ValueError, match="Failed to decrypt data"):
            encryption_service.decrypt("invalid_base64_data")

    def test_different_encryptions(self, encryption_service):
        """Test that same data encrypts differently each time."""
        original = "test_data"
        
        encrypted1 = encryption_service.encrypt(original)
        encrypted2 = encryption_service.encrypt(original)
        
        # Should be different due to random IV
        assert encrypted1 != encrypted2
        
        # But decrypt to same value
        assert encryption_service.decrypt(encrypted1) == original
        assert encryption_service.decrypt(encrypted2) == original