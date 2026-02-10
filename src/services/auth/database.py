"""
Auth Repository — Queries de base de datos específicas de autenticación.

Todas las operaciones usan el DatabaseManager compartido (asyncpg pool).
"""

from datetime import datetime
from typing import Optional

from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class AuthRepository:
    """Repositorio de datos para el servicio de autenticación."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ================================================================
    # USERS
    # ================================================================

    async def create_user(
        self, email: str, name: str, password_hash: str
    ) -> Optional[dict]:
        """Crea un usuario con rol 'user'. Retorna el registro creado."""
        row = await self.db.fetchone(
            """
            INSERT INTO users (email, name, password_hash, role)
            VALUES ($1, $2, $3, 'user')
            RETURNING id, email, name, role, created_at, updated_at
            """,
            email,
            name,
            password_hash,
        )
        return dict(row) if row else None

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Busca un usuario por email (incluye password_hash para login)."""
        row = await self.db.fetchone(
            """
            SELECT id, email, name, password_hash, role, created_at, updated_at
            FROM users WHERE email = $1
            """,
            email,
        )
        return dict(row) if row else None

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Busca un usuario por ID (sin password_hash, para respuestas públicas)."""
        row = await self.db.fetchone(
            """
            SELECT id, email, name, role, created_at, updated_at
            FROM users WHERE id = $1::uuid
            """,
            user_id,
        )
        return dict(row) if row else None

    async def email_exists(self, email: str) -> bool:
        """Verifica si un email ya está registrado."""
        count = await self.db.fetchval(
            "SELECT COUNT(*) FROM users WHERE email = $1",
            email,
        )
        return count > 0

    # ================================================================
    # SESSIONS (refresh tokens)
    # ================================================================

    async def create_session(
        self, user_id: str, refresh_token: str, expires_at: datetime
    ) -> Optional[dict]:
        """Crea una sesión con el refresh token."""
        row = await self.db.fetchone(
            """
            INSERT INTO sessions (user_id, refresh_token, expires_at)
            VALUES ($1::uuid, $2, $3)
            RETURNING id, user_id, refresh_token, expires_at, created_at
            """,
            user_id,
            refresh_token,
            expires_at,
        )
        return dict(row) if row else None

    async def get_session_by_refresh_token(
        self, refresh_token: str
    ) -> Optional[dict]:
        """Busca una sesión activa (no revocada) por refresh token."""
        row = await self.db.fetchone(
            """
            SELECT id, user_id, refresh_token, expires_at, is_revoked, created_at
            FROM sessions
            WHERE refresh_token = $1 AND is_revoked = FALSE
            """,
            refresh_token,
        )
        return dict(row) if row else None

    async def revoke_session(self, session_id: str) -> None:
        """Revoca una sesión específica."""
        await self.db.execute(
            "UPDATE sessions SET is_revoked = TRUE WHERE id = $1::uuid",
            session_id,
        )

    async def revoke_all_user_sessions(self, user_id: str) -> None:
        """Revoca todas las sesiones activas de un usuario (logout global)."""
        await self.db.execute(
            "UPDATE sessions SET is_revoked = TRUE WHERE user_id = $1::uuid AND is_revoked = FALSE",
            user_id,
        )

    async def cleanup_expired_sessions(self) -> int:
        """Elimina sesiones expiradas o revocadas. Retorna cantidad eliminada."""
        result = await self.db.execute(
            "DELETE FROM sessions WHERE expires_at < NOW() OR is_revoked = TRUE"
        )
        try:
            return int(result.split()[-1])
        except (IndexError, ValueError):
            return 0
