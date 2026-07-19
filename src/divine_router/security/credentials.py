"""Credential resolution without SQLite or configuration-file secret storage."""

from __future__ import annotations

import json
import os
from pathlib import Path

import keyring
from cryptography.fernet import Fernet, InvalidToken

from divine_router.config.models import CredentialReference
from divine_router.constants import SERVICE_NAME


class CredentialUnavailable(RuntimeError):
    pass


class CredentialStore:
    def __init__(self, encrypted_file: Path | None = None) -> None:
        self.encrypted_file = encrypted_file

    def resolve(self, reference: CredentialReference) -> str:
        if reference.keyring_name:
            try:
                value = keyring.get_password(SERVICE_NAME, reference.keyring_name)
            except keyring.errors.KeyringError:
                value = None
            if value:
                return value
        if reference.environment:
            value = os.environ.get(reference.environment)
            if value:
                return value
        if reference.encrypted_file_name:
            value = self._from_encrypted_file(reference.encrypted_file_name)
            if value:
                return value
        raise CredentialUnavailable("configured credential is unavailable")

    def _from_encrypted_file(self, name: str) -> str | None:
        if self.encrypted_file is None or not self.encrypted_file.exists():
            return None
        master_key = os.environ.get("DIVINE_MASTER_KEY")
        if not master_key:
            raise CredentialUnavailable("DIVINE_MASTER_KEY is required for encrypted credentials")
        try:
            decrypted = Fernet(master_key.encode()).decrypt(self.encrypted_file.read_bytes())
            payload = json.loads(decrypted)
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise CredentialUnavailable("encrypted credential file could not be decrypted") from exc
        value = payload.get(name)
        return value if isinstance(value, str) and value else None
