"""
AES-256-GCM encryption/decryption for PII reverse mappings.

Key is loaded from PII_ENCRYPTION_KEY env var (32-byte, base64-encoded).
Output format: base64(12-byte nonce || ciphertext || 16-byte tag)
"""
from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.exceptions import PIIDecryptionError, PIIMaskingError


def _decode_key(b64_key: str) -> bytes:
    try:
        key = base64.b64decode(b64_key)
    except Exception as exc:
        raise PIIMaskingError(f"PII_ENCRYPTION_KEY is not valid base64: {exc}") from exc
    if len(key) != 32:
        raise PIIMaskingError(
            f"PII_ENCRYPTION_KEY must decode to exactly 32 bytes, got {len(key)}"
        )
    return key


def encrypt_mapping(plaintext: str, b64_key: str) -> str:
    """Encrypt a JSON string and return base64(nonce || ciphertext || tag)."""
    key = _decode_key(b64_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode(), None)
    blob = nonce + ciphertext_with_tag
    return base64.b64encode(blob).decode()


def decrypt_mapping(b64_blob: str, b64_key: str) -> str:
    """Decrypt and return the original JSON string."""
    key = _decode_key(b64_key)
    try:
        blob = base64.b64decode(b64_blob)
        nonce = blob[:12]
        ciphertext_with_tag = blob[12:]
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext.decode()
    except Exception as exc:
        raise PIIDecryptionError(f"Failed to decrypt PII mapping: {exc}") from exc
