"""Secret storage backed by the operating system keychain."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Protocol

SERVICE_NAME = "lego-element-lookup"
ACCOUNT_NAME = "rebrickable-api-key"


class SecretStoreError(RuntimeError):
    """Raised when the system keychain cannot be used."""


class KeyringBackend(Protocol):
    def get_password(self, service: str, username: str) -> str | None: ...
    def set_password(self, service: str, username: str, password: str) -> None: ...
    def delete_password(self, service: str, username: str) -> None: ...


def _default_backend() -> KeyringBackend:
    try:
        import keyring
    except ImportError as exc:
        raise SecretStoreError("Secure keychain support is unavailable.") from exc
    return keyring


@dataclass
class SecretStore:
    backend: KeyringBackend | None = None
    _session_key: str | None = field(default=None, init=False, repr=False)
    _retrieval_attempted: bool = field(default=False, init=False, repr=False)
    _access_error: bool = field(default=False, init=False, repr=False)

    def _keyring(self) -> KeyringBackend:
        return self.backend or _default_backend()

    def get(self) -> str | None:
        if self._retrieval_attempted:
            return self._session_key
        try:
            value = self._keyring().get_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception as exc:
            self._retrieval_attempted = True
            self._access_error = True
            raise SecretStoreError("Secure keychain access was not allowed. Enter the API key again to use it for this session.") from exc
        self._retrieval_attempted = True
        self._session_key = value.strip() if value else None
        return self._session_key

    @property
    def access_denied(self) -> bool:
        return self._access_error

    def save(self, api_key: str) -> None:
        value = api_key.strip()
        if not value:
            raise SecretStoreError("The API key cannot be blank.")
        try:
            self._keyring().set_password(SERVICE_NAME, ACCOUNT_NAME, value)
        except Exception as exc:
            raise SecretStoreError("The API key could not be saved to the operating system keychain.") from exc
        self._session_key = value
        self._retrieval_attempted = True
        self._access_error = False

    def save_for_session(self, api_key: str) -> None:
        value = api_key.strip()
        if not value:
            raise SecretStoreError("The API key cannot be blank.")
        self._session_key = value
        self._retrieval_attempted = True
        self._access_error = False

    def clear_session(self) -> None:
        self._session_key = None
        self._retrieval_attempted = False
        self._access_error = False

    def delete(self) -> None:
        self._session_key = None
        self._retrieval_attempted = True
        self._access_error = False
        try:
            self._keyring().delete_password(SERVICE_NAME, ACCOUNT_NAME)
        except Exception as exc:
            if exc.__class__.__name__ != "PasswordDeleteError":
                raise SecretStoreError("The API key could not be removed from the operating system keychain.") from exc


def resolve_api_key(
    store: SecretStore,
    legacy_key: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str | None:
    values = os.environ if env is None else env
    environment_key = values.get("REBRICKABLE_API_KEY")
    if environment_key:
        return environment_key.strip()
    try:
        stored = store.get()
    except SecretStoreError:
        stored = None
    return stored or (legacy_key.strip() if legacy_key else None)
