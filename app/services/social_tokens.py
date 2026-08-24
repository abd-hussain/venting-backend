"""Verify Google / Apple ID tokens from native mobile SDKs."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jwt import PyJWKClient

from app.core.config import Settings
from app.models.enums import AuthProvider

logger = logging.getLogger(__name__)

GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
JWT_LEEWAY_SECONDS = 60

_apple_jwks_client: PyJWKClient | None = None


class SocialTokenVerificationError(Exception):
    """Base error for provider token verification."""


class InvalidSocialTokenError(SocialTokenVerificationError):
    """Token invalid, expired, wrong audience/issuer, or bad signature."""


class NonceMismatchError(SocialTokenVerificationError):
    """Apple nonce does not match token claim."""


class ProviderUnavailableError(SocialTokenVerificationError):
    """JWKS / upstream verification unavailable."""


@dataclass(frozen=True)
class VerifiedSocialToken:
    provider: AuthProvider
    provider_user_id: str
    email: str | None
    email_verified: bool
    raw_claims: dict[str, Any]


def _get_apple_jwks_client() -> PyJWKClient:
    global _apple_jwks_client
    if _apple_jwks_client is None:
        _apple_jwks_client = PyJWKClient(APPLE_JWKS_URL, cache_keys=True)
    return _apple_jwks_client


def _normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _verify_google_token(token: str, settings: Settings) -> VerifiedSocialToken:
    audiences = settings.google_client_id_list
    if not audiences:
        raise ProviderUnavailableError("Google client IDs are not configured")

    request = google_requests.Request()
    last_error: Exception | None = None
    claims: dict[str, Any] | None = None

    for audience in audiences:
        try:
            claims = google_id_token.verify_oauth2_token(token, request, audience)
            break
        except ValueError as exc:
            last_error = exc
            continue

    if claims is None:
        raise InvalidSocialTokenError("Invalid Google ID token") from last_error

    issuer = claims.get("iss")
    if issuer not in GOOGLE_ISSUERS:
        raise InvalidSocialTokenError("Invalid Google token issuer")

    provider_user_id = claims.get("sub")
    if not provider_user_id:
        raise InvalidSocialTokenError("Google token missing subject")

    email = _normalize_email(claims.get("email"))
    email_verified = bool(claims.get("email_verified", False))

    return VerifiedSocialToken(
        provider=AuthProvider.google,
        provider_user_id=str(provider_user_id),
        email=email if email_verified else None,
        email_verified=email_verified,
        raw_claims=claims,
    )


def _verify_apple_token(
    token: str,
    settings: Settings,
    *,
    nonce: str | None,
) -> VerifiedSocialToken:
    audiences = settings.apple_audience_list
    if not audiences:
        raise ProviderUnavailableError("Apple audiences are not configured")

    try:
        jwks_client = _get_apple_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
    except Exception as exc:
        logger.warning("Apple JWKS fetch failed: %s", exc)
        raise ProviderUnavailableError("Apple verification unavailable") from exc

    claims: dict[str, Any] | None = None
    last_error: Exception | None = None

    for audience in audiences:
        try:
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=audience,
                issuer=APPLE_ISSUER,
                leeway=JWT_LEEWAY_SECONDS,
            )
            break
        except jwt.InvalidAudienceError as exc:
            last_error = exc
            continue
        except jwt.PyJWTError as exc:
            raise InvalidSocialTokenError("Invalid Apple identity token") from exc

    if claims is None:
        raise InvalidSocialTokenError("Invalid Apple token audience") from last_error

    if nonce is not None:
        expected_nonce = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        token_nonce = claims.get("nonce")
        if token_nonce != expected_nonce:
            raise NonceMismatchError("Apple nonce mismatch")

    provider_user_id = claims.get("sub")
    if not provider_user_id:
        raise InvalidSocialTokenError("Apple token missing subject")

    email = _normalize_email(claims.get("email"))
    # Apple does not expose email_verified; treat relay/private emails as usable.
    email_verified = email is not None

    return VerifiedSocialToken(
        provider=AuthProvider.apple,
        provider_user_id=str(provider_user_id),
        email=email,
        email_verified=email_verified,
        raw_claims=claims,
    )


def verify_social_id_token(
    *,
    provider: AuthProvider,
    id_token: str,
    settings: Settings,
    nonce: str | None = None,
) -> VerifiedSocialToken:
    try:
        if provider == AuthProvider.google:
            return _verify_google_token(id_token, settings)
        if provider == AuthProvider.apple:
            return _verify_apple_token(id_token, settings, nonce=nonce)
        raise InvalidSocialTokenError(f"Unsupported provider: {provider.value}")
    except (InvalidSocialTokenError, NonceMismatchError):
        raise
    except ProviderUnavailableError:
        raise
    except Exception as exc:
        logger.warning("Social token verification failed for %s: %s", provider.value, exc)
        raise InvalidSocialTokenError("Invalid social ID token") from exc
