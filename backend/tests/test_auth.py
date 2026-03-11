"""Tests for POST /auth/register and POST /auth/login routes."""
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """A new user can register and receives a 201 response with an access token."""
    payload = {"email": "alice@example.com", "password": "StrongPass1!"}
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Registering with an already-used email returns 400."""
    payload = {"email": "bob@example.com", "password": "StrongPass1!"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """A registered user can log in and receives a 200 response with a token."""
    email = "carol@example.com"
    password = "MyPassword99!"
    await client.post("/auth/register", json={"email": email, "password": password})

    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert isinstance(body["access_token"], str)


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Logging in with the wrong password returns 401."""
    email = "dave@example.com"
    await client.post("/auth/register", json={"email": email, "password": "CorrectHorse1!"})

    response = await client.post("/auth/login", json={"email": email, "password": "WrongPass!"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    """Logging in with an email that was never registered returns 401."""
    response = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "SomePassword1!"},
    )
    assert response.status_code == 401
