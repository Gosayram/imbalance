from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def derive_key(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
	"""Derive encryption key from password.

	Args:
		password: Password to derive key from
		salt: Salt for key derivation (generated if None)

	Returns:
		Tuple of (key, salt)
	"""
	if salt is None:
		salt = os.urandom(16)

	key = hashlib.pbkdf2_hmac(
		'sha256',
		password.encode('utf-8'),
		salt,
		iterations=100_000,
	)
	return key, salt


def get_encryption_key() -> str | None:
	"""Get encryption key from environment.

	Returns:
		Encryption key or None if not configured
	"""
	return os.environ.get('IMBALANCE_ENCRYPTION_KEY')


def is_encryption_enabled() -> bool:
	"""Check if encryption is enabled.

	Returns:
		True if encryption key is configured
	"""
	return get_encryption_key() is not None


def encrypt_database(db_path: Path, password: str) -> None:
	"""Encrypt SQLite database.

	Args:
		db_path: Path to database file
		password: Encryption password

	Note:
		Requires sqlcipher to be installed.
		This is a placeholder for the actual implementation.
	"""
	logger.info(f'Encryption requested for {db_path}')
	logger.warning('SQLCipher not available - encryption not implemented')


def decrypt_database(db_path: Path, password: str) -> None:
	"""Decrypt SQLite database.

	Args:
		db_path: Path to encrypted database file
		password: Decryption password

	Note:
		Requires sqlcipher to be installed.
		This is a placeholder for the actual implementation.
	"""
	logger.info(f'Decryption requested for {db_path}')
	logger.warning('SQLCipher not available - decryption not implemented')
