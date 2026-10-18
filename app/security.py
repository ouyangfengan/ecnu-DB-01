import hashlib
import secrets
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError


password_hasher = PasswordHasher()


def utc_now():
    return datetime.now(timezone.utc)


def new_token():
    return secrets.token_urlsafe(32)


def token_hash(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_password(encoded: str, password: str):
    try:
        return password_hasher.verify(encoded, password)
    except VerificationError:
        return False
