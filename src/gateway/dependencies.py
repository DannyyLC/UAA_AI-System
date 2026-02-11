"""Dependencies para FastAPI."""

from fastapi import Cookie, HTTPException, status
from typing import Optional
import grpc
from src.gateway.grpc_clients.auth_client import auth_client
from src.gateway.models import UserResponse
from src.gateway.utils import proto_user_to_response
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


async def get_current_user(
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> UserResponse:
    """
    Dependency para obtener el usuario actual desde la cookie JWT.
    
    Args:
        access_token: Token JWT desde la cookie httpOnly
        
    Returns:
        UserResponse con información del usuario autenticado
        
    Raises:
        HTTPException 401: Si el token no existe o es inválido
    """
    if not access_token:
        logger.warning("Intento de acceso sin token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado. Token no encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Validar token con Auth Service
        response = await auth_client.validate_token(access_token)
        
        if not response.valid:
            logger.warning(f"Token inválido: {response.error.message if response.error else 'unknown'}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Convertir protobuf User a UserResponse
        user_response = proto_user_to_response(response.user)
        logger.debug(f"Token validado para usuario: {user_response.email}")
        return user_response
        
    except grpc.RpcError as e:
        logger.error(f"Error gRPC validando token: {e.code()} - {e.details()}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de autenticación no disponible"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado validando token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


async def get_optional_user(
    access_token: Optional[str] = Cookie(None, alias="access_token")
) -> Optional[UserResponse]:
    """
    Dependency opcional para obtener el usuario actual.
    Retorna None si no hay token o es inválido, en lugar de lanzar excepción.
    
    Args:
        access_token: Token JWT desde la cookie httpOnly
        
    Returns:
        UserResponse si el token es válido, None en caso contrario
    """
    if not access_token:
        return None
    
    try:
        response = await auth_client.validate_token(access_token)
        
        if not response.valid:
            return None
        
        return proto_user_to_response(response.user)
        
    except Exception as e:
        logger.debug(f"Token opcional inválido: {e}")
        return None
