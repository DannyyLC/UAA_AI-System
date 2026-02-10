"""
Auth Service gRPC Handlers — Implementación del AuthServiceServicer.

Cada método corresponde a un RPC definido en auth.proto:
  - Register: Crea usuario nuevo (siempre rol USER)
  - Login: Autentica y genera tokens
  - Logout: Revoca todas las sesiones del usuario
  - ValidateToken: Valida access token (usado por Gateway en cada request)
  - RefreshToken: Rota tokens (revoca anterior, genera nuevos)
  - GetProfile: Retorna perfil público del usuario
"""

import bcrypt
import grpc

from src.generated import auth_pb2, auth_pb2_grpc, common_pb2
from src.services.auth.jwt_manager import JWTManager
from src.services.auth.database import AuthRepository
from src.kafka.audit import AuditProducer
from src.shared.utils import datetime_to_proto_timestamp
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


# ================================================================
# Helpers
# ================================================================


def _hash_password(password: str) -> str:
    """Genera un hash bcrypt de la contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verifica una contraseña contra su hash bcrypt."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def _user_to_proto(user: dict) -> common_pb2.User:
    """Convierte un dict de usuario (de DB) a un mensaje proto User."""
    role_map = {
        "user": common_pb2.USER_ROLE_USER,
        "admin": common_pb2.USER_ROLE_ADMIN,
    }
    ts = datetime_to_proto_timestamp(user["created_at"])
    return common_pb2.User(
        id=str(user["id"]),
        email=user["email"],
        name=user["name"],
        role=role_map.get(user["role"], common_pb2.USER_ROLE_USER),
        created_at=common_pb2.Timestamp(**ts),
    )


# ================================================================
# gRPC Servicer
# ================================================================


class AuthServiceHandler(auth_pb2_grpc.AuthServiceServicer):
    """Implementación del servicio gRPC AuthService."""

    def __init__(
        self,
        repo: AuthRepository,
        jwt_manager: JWTManager,
        audit: AuditProducer,
    ) -> None:
        self.repo = repo
        self.jwt = jwt_manager
        self.audit = audit

    # ----------------------------------------------------------------
    # Register
    # ----------------------------------------------------------------

    async def Register(self, request, context):
        """Registra un nuevo usuario con rol USER."""
        try:
            # Validaciones básicas
            if not request.email or not request.password or not request.name:
                return auth_pb2.RegisterResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=400, message="Todos los campos son obligatorios"
                    ),
                )

            if len(request.password) < 8:
                return auth_pb2.RegisterResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=400,
                        message="La contraseña debe tener al menos 8 caracteres",
                    ),
                )

            # Verificar email duplicado
            if await self.repo.email_exists(request.email):
                return auth_pb2.RegisterResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=409, message="El email ya está registrado"
                    ),
                )

            # Crear usuario
            password_hash = _hash_password(request.password)
            user = await self.repo.create_user(
                request.email, request.name, password_hash
            )

            if not user:
                return auth_pb2.RegisterResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=500, message="Error interno al crear usuario"
                    ),
                )

            # Evento de auditoría
            await self.audit.send_event(
                action="user.register",
                service="auth",
                user_id=str(user["id"]),
                detail={"email": request.email},
            )

            logger.info(f"Usuario registrado: {request.email}")
            return auth_pb2.RegisterResponse(
                success=True,
                user=_user_to_proto(user),
            )

        except Exception as e:
            logger.error(f"Error en Register: {e}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, "Error interno del servidor")

    # ----------------------------------------------------------------
    # Login
    # ----------------------------------------------------------------

    async def Login(self, request, context):
        """Autentica usuario y genera access + refresh tokens."""
        try:
            # Buscar usuario
            user = await self.repo.get_user_by_email(request.email)
            if not user:
                return auth_pb2.LoginResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=401, message="Credenciales inválidas"
                    ),
                )

            # Verificar contraseña
            if not _verify_password(request.password, user["password_hash"]):
                return auth_pb2.LoginResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=401, message="Credenciales inválidas"
                    ),
                )

            # Generar tokens
            user_id = str(user["id"])
            access_token, expires_in = self.jwt.create_access_token(
                user_id, user["email"], user["role"]
            )
            refresh_token, refresh_expires = self.jwt.create_refresh_token(user_id)

            # Persistir sesión (refresh token)
            await self.repo.create_session(user_id, refresh_token, refresh_expires)

            # Auditoría
            await self.audit.send_event(
                action="user.login",
                service="auth",
                user_id=user_id,
            )

            logger.info(f"Login exitoso: {request.email}")
            return auth_pb2.LoginResponse(
                success=True,
                user=_user_to_proto(user),
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in,
            )

        except Exception as e:
            logger.error(f"Error en Login: {e}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, "Error interno del servidor")

    # ----------------------------------------------------------------
    # Logout
    # ----------------------------------------------------------------

    async def Logout(self, request, context):
        """Revoca todas las sesiones del usuario (logout global)."""
        try:
            payload = self.jwt.decode_access_token(request.access_token)
            if not payload:
                return auth_pb2.LogoutResponse(
                    success=False,
                    message="Token inválido",
                    error=common_pb2.Error(
                        code=401, message="Token inválido o expirado"
                    ),
                )

            user_id = payload["sub"]
            await self.repo.revoke_all_user_sessions(user_id)

            await self.audit.send_event(
                action="user.logout",
                service="auth",
                user_id=user_id,
            )

            logger.info(f"Logout: user_id={user_id}")
            return auth_pb2.LogoutResponse(
                success=True,
                message="Sesión cerrada correctamente",
            )

        except Exception as e:
            logger.error(f"Error en Logout: {e}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, "Error interno del servidor")

    # ----------------------------------------------------------------
    # ValidateToken
    # ----------------------------------------------------------------

    async def ValidateToken(self, request, context):
        """
        Valida un access token JWT.
        El Gateway llama este RPC en cada request autenticado.
        """
        try:
            payload = self.jwt.decode_access_token(request.access_token)
            if not payload:
                return auth_pb2.ValidateTokenResponse(
                    valid=False,
                    error=common_pb2.Error(
                        code=401, message="Token inválido o expirado"
                    ),
                )

            # Verificar que el usuario sigue existiendo
            user = await self.repo.get_user_by_id(payload["sub"])
            if not user:
                return auth_pb2.ValidateTokenResponse(
                    valid=False,
                    error=common_pb2.Error(
                        code=404, message="Usuario no encontrado"
                    ),
                )

            return auth_pb2.ValidateTokenResponse(
                valid=True,
                user=_user_to_proto(user),
            )

        except Exception as e:
            logger.error(f"Error en ValidateToken: {e}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, "Error interno del servidor")

    # ----------------------------------------------------------------
    # RefreshToken
    # ----------------------------------------------------------------

    async def RefreshToken(self, request, context):
        """
        Rota tokens: revoca el refresh token actual y genera nuevos.
        Implementa refresh token rotation para mayor seguridad.
        """
        try:
            # Validar el refresh token JWT
            payload = self.jwt.decode_refresh_token(request.refresh_token)
            if not payload:
                return auth_pb2.RefreshTokenResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=401, message="Refresh token inválido o expirado"
                    ),
                )

            # Verificar que la sesión existe y no está revocada
            session = await self.repo.get_session_by_refresh_token(
                request.refresh_token
            )
            if not session:
                return auth_pb2.RefreshTokenResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=401, message="Sesión no encontrada o revocada"
                    ),
                )

            # Revocar la sesión anterior (token rotation)
            await self.repo.revoke_session(str(session["id"]))

            # Obtener usuario actualizado
            user_id = payload["sub"]
            user = await self.repo.get_user_by_id(user_id)
            if not user:
                return auth_pb2.RefreshTokenResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=404, message="Usuario no encontrado"
                    ),
                )

            # Generar nuevos tokens
            new_access, expires_in = self.jwt.create_access_token(
                user_id, user["email"], user["role"]
            )
            new_refresh, refresh_expires = self.jwt.create_refresh_token(user_id)

            # Crear nueva sesión
            await self.repo.create_session(user_id, new_refresh, refresh_expires)

            await self.audit.send_event(
                action="user.refresh_token",
                service="auth",
                user_id=user_id,
            )

            return auth_pb2.RefreshTokenResponse(
                success=True,
                access_token=new_access,
                refresh_token=new_refresh,
                expires_in=expires_in,
            )

        except Exception as e:
            logger.error(f"Error en RefreshToken: {e}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, "Error interno del servidor")

    # ----------------------------------------------------------------
    # GetProfile
    # ----------------------------------------------------------------

    async def GetProfile(self, request, context):
        """Retorna el perfil público de un usuario por ID."""
        try:
            if not request.user_id:
                return auth_pb2.GetProfileResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=400, message="user_id es obligatorio"
                    ),
                )

            user = await self.repo.get_user_by_id(request.user_id)
            if not user:
                return auth_pb2.GetProfileResponse(
                    success=False,
                    error=common_pb2.Error(
                        code=404, message="Usuario no encontrado"
                    ),
                )

            return auth_pb2.GetProfileResponse(
                success=True,
                user=_user_to_proto(user),
            )

        except Exception as e:
            logger.error(f"Error en GetProfile: {e}", exc_info=True)
            context.abort(grpc.StatusCode.INTERNAL, "Error interno del servidor")
