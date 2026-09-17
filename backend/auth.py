"""NexTrace AI parola doğrulama ve sunucu tarafı oturum yönetimi."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from storage import ProjectStore


PASSWORD_ITERATIONS = 600_000
SESSION_HOURS = 12
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class AuthenticationError(ValueError):
    pass


class AuthService:
    def __init__(self, store: ProjectStore):
        self.store = store

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _hash_password(password: str, salt: bytes, iterations: int) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations, dklen=32
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_email(email: str) -> str:
        normalized = email.strip().lower()
        if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
            raise AuthenticationError("Geçerli bir e-posta adresi girilmelidir.")
        return normalized

    @staticmethod
    def _validate_new_password(password: str) -> None:
        if len(password) < 12:
            raise AuthenticationError("Parola en az 12 karakter olmalıdır.")
        if len(password) > 128:
            raise AuthenticationError("Parola en fazla 128 karakter olmalıdır.")
        if not any(character.isalpha() for character in password):
            raise AuthenticationError("Parola en az bir harf içermelidir.")
        if not any(character.isdigit() for character in password):
            raise AuthenticationError("Parola en az bir rakam içermelidir.")

    def setup(self, email: str, password: str) -> tuple[str, dict, str]:
        normalized_email = self._validate_email(email)
        self._validate_new_password(password)
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt, PASSWORD_ITERATIONS)
        user = self.store.create_first_user(
            normalized_email,
            password_hash,
            salt,
            PASSWORD_ITERATIONS,
        )
        return self._create_session(user)

    def create_user(self, email: str, password: str, role: str = "analyst") -> dict:
        normalized_email = self._validate_email(email)
        self._validate_new_password(password)
        if role not in {"admin", "analyst"}:
            raise AuthenticationError("Geçersiz kullanıcı rolü.")
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt, PASSWORD_ITERATIONS)
        return self.store.create_user(
            normalized_email,
            password_hash,
            salt,
            PASSWORD_ITERATIONS,
            role,
        )

    @staticmethod
    def _public_user(user: dict) -> dict:
        return {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "active": bool(user["active"]),
            "must_change_password": bool(user["must_change_password"]),
        }

    def login(self, email: str, password: str) -> tuple[str, dict, str]:
        normalized_email = self._validate_email(email)
        user = self.store.get_user_by_email(normalized_email)
        if user:
            expected = user["password_hash"]
            actual = self._hash_password(
                password, user["password_salt"], user["password_iterations"]
            )
        else:
            expected = bytes(32)
            actual = self._hash_password(password, bytes(16), PASSWORD_ITERATIONS)
        if (
            not user
            or not hmac.compare_digest(actual, expected)
            or not user["active"]
        ):
            raise AuthenticationError("E-posta veya parola hatalı.")
        return self._create_session(self._public_user(user))

    def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> tuple[str, dict, str]:
        self._validate_new_password(new_password)
        user = self.store.get_user_by_id(user_id)
        if not user or not user["active"]:
            raise AuthenticationError("Oturum açılması gerekiyor.")
        current_hash = self._hash_password(
            current_password, user["password_salt"], user["password_iterations"]
        )
        if not hmac.compare_digest(current_hash, user["password_hash"]):
            raise AuthenticationError("Mevcut parola hatalı.")
        new_hash = self._hash_password(
            new_password, user["password_salt"], user["password_iterations"]
        )
        if hmac.compare_digest(new_hash, user["password_hash"]):
            raise AuthenticationError("Yeni parola mevcut paroladan farklı olmalıdır.")
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(new_password, salt, PASSWORD_ITERATIONS)
        updated = self.store.update_user_password(
            user_id,
            password_hash,
            salt,
            PASSWORD_ITERATIONS,
            must_change_password=False,
        )
        return self._create_session(self._public_user(updated))

    def admin_reset_password(self, user_id: str, new_password: str) -> dict:
        self._validate_new_password(new_password)
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(new_password, salt, PASSWORD_ITERATIONS)
        updated = self.store.update_user_password(
            user_id,
            password_hash,
            salt,
            PASSWORD_ITERATIONS,
            must_change_password=True,
        )
        return self._public_user(updated)

    def set_user_active(self, user_id: str, active: bool) -> dict:
        return self._public_user(self.store.set_user_active(user_id, active))

    def _create_session(self, user: dict) -> tuple[str, dict, str]:
        token = secrets.token_urlsafe(32)
        created = self._now()
        expires = created + timedelta(hours=SESSION_HOURS)
        expires_at = expires.isoformat(timespec="seconds")
        self.store.save_session(
            self._token_hash(token),
            user["id"],
            created.isoformat(timespec="seconds"),
            expires_at,
        )
        return token, user, expires_at

    def authenticate(self, token: str | None) -> dict | None:
        if not token:
            return None
        now = self._now().isoformat(timespec="seconds")
        return self.store.get_session_user(self._token_hash(token), now)

    def logout(self, token: str | None) -> None:
        if token:
            self.store.delete_session(self._token_hash(token))
