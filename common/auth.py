"""
auth.py - create and verify JWTs.

  * The FastAPI backend calls create_token() when a user logs in.
  * The MCP server calls decode_token() on every request to find out
    WHO is calling (user_id) and WHAT they are allowed to do (scopes).
"""

from datetime import datetime, timedelta, timezone

import jwt  # PyJWT

from common.config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_EXPIRY_MINUTES, JWT_ISSUER, JWT_SECRET


def create_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "scope": " ".join(user["scopes"]),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["exp", "iss", "aud", "sub", "scope"]},
    )