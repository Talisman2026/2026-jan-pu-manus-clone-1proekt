import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

# ---------------------------------------------------------------------------
# Log sanitization
# ---------------------------------------------------------------------------

REDACT_PATTERNS: list[str] = [
    r"sk-[a-zA-Z0-9\-_]{20,}",   # OpenAI API key
    r"e2b_[a-zA-Z0-9]{20,}",      # E2B API key
    r"fc-[a-zA-Z0-9]{20,}",       # Firecrawl API key
]


def sanitize(text: str) -> str:
    """Redact sensitive API keys from log messages and error strings."""
    for pattern in REDACT_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text


class SanitizingFilter(logging.Filter):
    """Logging filter that redacts sensitive patterns from every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize(str(record.msg))
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize(str(v)) for k, v in record.args.items()
                }
            else:
                record.args = tuple(sanitize(str(a)) for a in record.args)
        return True


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token for *subject* (user id)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    """Decode *token* and return the subject (user id), or None on failure."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        sub: Optional[str] = payload.get("sub")
        return sub
    except JWTError:
        return None
