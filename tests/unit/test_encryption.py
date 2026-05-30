import pytest
import os
from unittest.mock import patch
from imbalance.core.encryption import (
	derive_key,
	get_encryption_key,
	is_encryption_enabled,
	encrypt_database,
	decrypt_database,
)


def test_derive_key_generates_salt():
	key, salt = derive_key('password')
	assert len(key) == 32
	assert len(salt) == 16


def test_derive_key_with_salt():
	salt = b'0123456789abcdef'
	key, returned_salt = derive_key('password', salt)
	assert len(key) == 32
	assert returned_salt == salt


def test_derive_key_same_password_same_salt():
	salt = b'0123456789abcdef'
	key1, _ = derive_key('password', salt)
	key2, _ = derive_key('password', salt)
	assert key1 == key2


def test_derive_key_different_passwords():
	salt = b'0123456789abcdef'
	key1, _ = derive_key('password1', salt)
	key2, _ = derive_key('password2', salt)
	assert key1 != key2


def test_get_encryption_key_not_set():
	with patch.dict(os.environ, {}, clear=True):
		assert get_encryption_key() is None


def test_get_encryption_key_set():
	with patch.dict(os.environ, {'IMBALANCE_ENCRYPTION_KEY': 'test-key'}):
		assert get_encryption_key() == 'test-key'


def test_is_encryption_enabled_false():
	with patch.dict(os.environ, {}, clear=True):
		assert is_encryption_enabled() is False


def test_is_encryption_enabled_true():
	with patch.dict(os.environ, {'IMBALANCE_ENCRYPTION_KEY': 'test-key'}):
		assert is_encryption_enabled() is True


def test_encrypt_database_placeholder(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test')
	# Should not raise
	encrypt_database(db_path, 'password')


def test_decrypt_database_placeholder(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test')
	# Should not raise
	decrypt_database(db_path, 'password')
