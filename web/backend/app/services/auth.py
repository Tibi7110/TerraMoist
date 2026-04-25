"""Simple local authentication service for TerraMoist."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from pathlib import Path


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


class AuthError(Exception):
    """Raised for invalid credentials or malformed tokens."""


class UserAlreadyExistsError(Exception):
    """Raised when trying to register an already-used email."""


class AuthService:
    """Persist users locally, hash passwords, and issue signed tokens."""

    def __init__(
        self,
        db_path: Path,
        secret_key: str,
        token_ttl_seconds: int,
    ) -> None:
        self._db_path = db_path
        self._secret_key = secret_key.encode("utf-8")
        self._token_ttl_seconds = token_ttl_seconds
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def register_user(self, name: str, email: str, password: str) -> dict:
        """Create a user and return its public shape."""
        password_hash = self._hash_password(password)
        with self._connect() as conn:
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (name.strip(), email.strip().lower(), password_hash),
                )
            except sqlite3.IntegrityError as exc:
                raise UserAlreadyExistsError from exc

            conn.commit()
            user_id = int(cursor.lastrowid)
            return {
                "id": user_id,
                "name": name.strip(),
                "email": email.strip().lower(),
            }

    def authenticate(self, email: str, password: str) -> dict:
        """Return the public user if credentials are valid."""
        user = self._get_user_by_email(email)
        if not user or not self._verify_password(password, user["password_hash"]):
            raise AuthError("Invalid email or password")
        return self._public_user(user)

    def issue_token(self, user: dict) -> str:
        """Create a signed token with a simple HMAC-protected payload."""
        payload = {
            "sub": user["id"],
            "exp": int(time.time()) + self._token_ttl_seconds,
        }
        payload_bytes = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        payload_b64 = _b64url_encode(payload_bytes)
        signature = hmac.new(
            self._secret_key,
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{payload_b64}.{_b64url_encode(signature)}"

    def get_user_from_token(self, token: str) -> dict:
        """Validate a bearer token and return the fresh user record."""
        try:
            payload_b64, signature_b64 = token.split(".", 1)
        except ValueError as exc:
            raise AuthError("Malformed token") from exc

        expected_sig = hmac.new(
            self._secret_key,
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise AuthError("Invalid token signature")

        payload = json.loads(_b64url_decode(payload_b64))
        if int(payload["exp"]) <= int(time.time()):
            raise AuthError("Token expired")

        user = self._get_user_by_id(int(payload["sub"]))
        if not user:
            raise AuthError("User no longer exists")
        return self._public_user(user)

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            310_000,
        )
        return f"{_b64url_encode(salt)}:{_b64url_encode(derived)}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            salt_b64, digest_b64 = stored_hash.split(":", 1)
        except ValueError:
            return False

        salt = _b64url_decode(salt_b64)
        expected = _b64url_decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            310_000,
        )
        return hmac.compare_digest(expected, actual)

    def _public_user(self, user: sqlite3.Row | dict) -> dict:
        return {
            "id": int(user["id"]),
            "name": str(user["name"]),
            "email": str(user["email"]),
        }

    def _get_user_by_email(self, email: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT id, name, email, password_hash
                FROM users
                WHERE email = ?
                """,
                (email.strip().lower(),),
            ).fetchone()

    def _get_user_by_id(self, user_id: int) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT id, name, email, password_hash
                FROM users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
