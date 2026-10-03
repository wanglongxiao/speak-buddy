import base64
import hashlib
import hmac
import re
import secrets
import time

from fastapi import Request
from sqlmodel import Session, select

from app.config import get_settings
from app.models import User

SESSION_COOKIE = "speakbuddy_session"
SESSION_SECONDS = 60 * 60 * 24 * 30
PBKDF2_ROUNDS = 210_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,30}$")


def normalize_username(value: str) -> str:
    return value.strip().lower()


def valid_username(value: str) -> bool:
    return bool(USERNAME_PATTERN.fullmatch(normalize_username(value)))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return (
        f"pbkdf2_sha256${PBKDF2_ROUNDS}$"
        f"{base64.urlsafe_b64encode(salt).decode()}$"
        f"{base64.urlsafe_b64encode(digest).decode()}"
    )


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, rounds, salt_text, expected_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text)
        expected = base64.urlsafe_b64decode(expected_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _signature(payload: str) -> str:
    secret = get_settings().session_secret.encode()
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def signed_token(scope: str, user_id: int, ttl: int = SESSION_SECONDS) -> str:
    payload = f"{scope}:{user_id}:{int(time.time()) + ttl}"
    return f"{payload}.{_signature(payload)}"


def token_user_id(token: str | None, scope: str) -> int | None:
    if not token:
        return None
    try:
        payload, signature = token.rsplit(".", 1)
        token_scope, user_id, expires = payload.split(":", 2)
        if token_scope != scope or int(expires) < int(time.time()):
            return None
        if not hmac.compare_digest(signature, _signature(payload)):
            return None
        return int(user_id)
    except (ValueError, TypeError):
        return None


def guest_user(session: Session) -> User:
    guest = session.exec(select(User).where(User.username.is_(None))).first()
    if guest is None:
        guest = User(nickname="Guest")
        session.add(guest)
        session.commit()
        session.refresh(guest)
    return guest


def request_user(request: Request, session: Session) -> User:
    user_id = token_user_id(request.cookies.get(SESSION_COOKIE), "session")
    user = session.get(User, user_id) if user_id else None
    if user and user.username:
        return user
    return guest_user(session)


def parent_share_user(token: str | None, session: Session) -> User | None:
    user_id = token_user_id(token, "parent")
    return session.get(User, user_id) if user_id else None
