"""Supabase Auth: verify the access token (JWT) the SPA sends as a Bearer token.

We verify locally against the project's JWKS endpoint (asymmetric ES256/RS256
signing keys) rather than calling the Auth server per request — fast, and
revocation-aware via key rotation. This requires the project to have migrated off
the legacy HS256 shared secret; see the README "Supabase Auth setup" checklist.

Only verified top-level claims are trusted for identity (``sub`` = user UUID,
``email``). Never read ``user_metadata`` for authorization — it is user-editable.
"""

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import settings

# Caches fetched signing keys across requests (refetches only on cache miss /
# key rotation), so we don't hit the JWKS endpoint on every call.
_jwks_client = PyJWKClient(settings.jwks_url)

# auto_error=False so a missing header yields our 401 below, not HTTPBearer's 403.
_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="invalid or missing authentication token",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class CurrentUser:
    id: str  # JWT `sub` — the Supabase user UUID; matches graphs.user_id
    email: str | None


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if creds is None:
        raise _UNAUTHORIZED
    token = creds.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError:
        raise _UNAUTHORIZED from None

    sub = claims.get("sub")
    if not sub:
        raise _UNAUTHORIZED
    return CurrentUser(id=sub, email=claims.get("email"))
