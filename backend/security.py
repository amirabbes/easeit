from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher

from config import settings


ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except Exception:
        return False


def create_token(subject: str, role: str, department: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': subject,
        'role': role,
        'department': department,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=settings.jwt_expire_minutes)).timestamp()),
        'jti': f'{subject}-{int(now.timestamp())}'
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
