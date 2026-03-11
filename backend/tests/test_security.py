"""Tests for backend/security.py — sanitization, password hashing, JWT."""
from datetime import timedelta

import pytest

from security import (
    create_access_token,
    hash_password,
    sanitize,
    verify_password,
    verify_token,
)


# ---------------------------------------------------------------------------
# sanitize()
# ---------------------------------------------------------------------------


def test_sanitize_openai_key():
    """An OpenAI API key (sk-...) is replaced with [REDACTED]."""
    text = "Using key sk-abcdefghijklmnopqrstuvwxyz1234 in request"
    result = sanitize(text)
    assert "[REDACTED]" in result
    assert "sk-" not in result


def test_sanitize_e2b_key():
    """An E2B API key (e2b_...) is replaced with [REDACTED]."""
    text = "e2b_abcdefghijklmnopqrstuvwxyz1234567890"
    result = sanitize(text)
    assert "[REDACTED]" in result
    assert "e2b_" not in result


def test_sanitize_firecrawl_key():
    """A Firecrawl API key (fc-...) is replaced with [REDACTED]."""
    text = "Firecrawl key: fc-abcdefghijklmnopqrstuvwxyz1234"
    result = sanitize(text)
    assert "[REDACTED]" in result
    assert "fc-" not in result


def test_sanitize_no_change():
    """Plain text without any API key pattern passes through unchanged."""
    text = "Hello world, this is a normal log message."
    result = sanitize(text)
    assert result == text


# ---------------------------------------------------------------------------
# hash_password() / verify_password()
# ---------------------------------------------------------------------------


def test_hash_and_verify_password():
    """hash_password produces a hash that verify_password accepts."""
    plain = "super-secret-password-123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True


def test_wrong_password():
    """verify_password returns False when the wrong password is supplied."""
    hashed = hash_password("correct-password")
    assert verify_password("wrong-password", hashed) is False


# ---------------------------------------------------------------------------
# create_access_token() / verify_token()
# ---------------------------------------------------------------------------


def test_create_and_verify_token():
    """A freshly created token can be decoded to retrieve the subject."""
    subject = "user-id-abc123"
    token = create_access_token(subject=subject)
    recovered = verify_token(token)
    assert recovered == subject


def test_expired_token():
    """verify_token returns None for a token whose expiry is in the past."""
    token = create_access_token(subject="user-xyz", expires_delta=timedelta(seconds=-1))
    result = verify_token(token)
    assert result is None
