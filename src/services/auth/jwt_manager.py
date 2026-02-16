"""
JWT Manager — Creación y validación de tokens JWT.

Tokens:
  - Access Token: corta duración, contiene user_id, email, role
  - Refresh Token: larga duración, solo contiene user_id + jti (unique ID)

Ambos firmados con HS256 y el mismo secret (configurable).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from src.shared.configuration import settings
from src.shared.logging_utils import get_logger
from src.shared.utils import generate_id

logger = get_logger(__name__)


class JWTManager:
    """Gestiona la creación y validación de tokens JWT."""

    def __init__(self) -> None:
        self.secret = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.access_expiry = timedelta(minutes=settings.jwt_expiration_minutes)
        self.refresh_expiry = timedelta(days=settings.jwt_refresh_expiration_days)

    # ----------------------------------------------------------------
    # Creación de tokens
    # ----------------------------------------------------------------

    def create_access_token(self, user_id: str, email: str, role: str) -> tuple[str, int]:
        """
        Crea un access token JWT.

        Returns:
            (token_string, expires_in_seconds)
        """
        now = datetime.now(timezone.utc)
        expires = now + self.access_expiry

        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "jti": generate_id(),
            "iat": now,
            "exp": expires,
        }

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, int(self.access_expiry.total_seconds())

    def create_refresh_token(self, user_id: str) -> tuple[str, datetime]:
        """
        Crea un refresh token JWT.

        Returns:
            (token_string, expires_at_datetime)
        """
        now = datetime.now(timezone.utc)
        expires = now + self.refresh_expiry

        payload = {
            "sub": user_id,
            "type": "refresh",
            "jti": generate_id(),
            "iat": now,
            "exp": expires,
        }

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, expires

    # ----------------------------------------------------------------
    # Decodificación y validación
    # ----------------------------------------------------------------

    def decode_token(self, token: str) -> Optional[dict]:
        """
        Decodifica y valida un token JWT genérico.
        Retorna el payload o None si es inválido/expirado.
        """
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except jwt.ExpiredSignatureError:
            logger.debug("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"Token inválido: {e}")
            return None

    def decode_access_token(self, token: str) -> Optional[dict]:
        """Decodifica un access token. Retorna None si no es tipo 'access'."""
        payload = self.decode_token(token)
        if payload and payload.get("type") == "access":
            return payload
        return None

    def decode_refresh_token(self, token: str) -> Optional[dict]:
        """Decodifica un refresh token. Retorna None si no es tipo 'refresh'."""
        payload = self.decode_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None
