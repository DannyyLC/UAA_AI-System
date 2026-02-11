"""Routes de autenticación."""

import os
import grpc
from fastapi import APIRouter, HTTPException, status, Response, Depends, Cookie
from typing import Annotated, Optional
from src.gateway.models import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    LogoutResponse,
    UserResponse,
    ErrorResponse
)
from src.gateway.grpc_clients.auth_client import auth_client
from src.gateway.dependencies import get_current_user
from src.gateway.utils import proto_user_to_response
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# Configuración de cookies
COOKIE_NAME = "access_token"
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # true en producción
COOKIE_SAMESITE = "lax"  # 'lax' o 'strict' en producción
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", None)  # None para desarrollo local
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))


def set_auth_cookie(response: Response, token: str):
    """
    Configura la cookie httpOnly con el token JWT.
    
    Args:
        response: Response de FastAPI
        token: Token JWT a guardar en la cookie
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,  # No accesible desde JavaScript
        secure=COOKIE_SECURE,  # Solo HTTPS en producción
        samesite=COOKIE_SAMESITE,  # Protección CSRF
        max_age=JWT_EXPIRATION_MINUTES * 60,  # Segundos
        domain=COOKIE_DOMAIN,
        path="/"
    )


def clear_auth_cookie(response: Response):
    """
    Elimina la cookie de autenticación.
    
    Args:
        response: Response de FastAPI
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        domain=COOKIE_DOMAIN
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Usuario registrado exitosamente"},
        400: {"model": ErrorResponse, "description": "Email ya registrado"},
        422: {"model": ErrorResponse, "description": "Datos de entrada inválidos"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"}
    },
    summary="Registrar nuevo usuario",
    description="Crea una nueva cuenta de usuario y retorna un token JWT en una cookie httpOnly"
)
async def register(request: RegisterRequest, response: Response):
    """
    Registra un nuevo usuario en el sistema.
    
    - **email**: Email del usuario (debe ser único)
    - **password**: Contraseña (mínimo 8 caracteres)
    - **full_name**: Nombre completo del usuario
    
    Retorna información del usuario y establece una cookie httpOnly con el token JWT.
    """
    try:
        # Llamar a Auth Service
        grpc_response = await auth_client.register(
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )
        
        # Verificar éxito
        if not grpc_response.success:
            error_msg = grpc_response.error.message if grpc_response.error else "Error desconocido"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
        # Nota: RegisterResponse NO incluye token, solo crea el usuario
        # El cliente debe hacer login después del registro para obtener el token
        
        # Construir response
        user_response = proto_user_to_response(grpc_response.user)
        
        logger.info(f"Usuario registrado exitosamente: {request.email}")
        
        return AuthResponse(
            message="Usuario registrado exitosamente. Por favor inicia sesión.",
            user=user_response
        )
        
    except grpc.RpcError as e:
        logger.error(f"Error gRPC en registro: {e.code()} - {e.details()}")
        
        # Mapear errores gRPC a HTTP
        if e.code() == grpc.StatusCode.ALREADY_EXISTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        elif e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.details() or "Datos de entrada inválidos"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Servicio de autenticación no disponible"
            )
    
    except Exception as e:
        logger.error(f"Error inesperado en registro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Login exitoso"},
        401: {"model": ErrorResponse, "description": "Credenciales inválidas"},
        422: {"model": ErrorResponse, "description": "Datos de entrada inválidos"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"}
    },
    summary="Iniciar sesión",
    description="Autentica un usuario y retorna un token JWT en una cookie httpOnly"
)
async def login(request: LoginRequest, response: Response):
    """
    Autentica un usuario existente.
    
    - **email**: Email del usuario
    - **password**: Contraseña del usuario
    
    Retorna información del usuario y establece una cookie httpOnly con el token JWT.
    """
    try:
        # Llamar a Auth Service
        grpc_response = await auth_client.login(
            email=request.email,
            password=request.password
        )
        
        # Verificar éxito
        if not grpc_response.success:
            error_msg = grpc_response.error.message if grpc_response.error else "Credenciales inválidas"
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error_msg
            )
        
        # Configurar cookie con el token
        set_auth_cookie(response, grpc_response.access_token)
        
        # Construir response
        user_response = proto_user_to_response(grpc_response.user)
        
        logger.info(f"Usuario autenticado exitosamente: {request.email}")
        
        return AuthResponse(
            message="Login exitoso",
            user=user_response
        )
        
    except grpc.RpcError as e:
        logger.error(f"Error gRPC en login: {e.code()} - {e.details()}")
        
        # Mapear errores gRPC a HTTP
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        elif e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.details() or "Datos de entrada inválidos"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Servicio de autenticación no disponible"
            )
    
    except Exception as e:
        logger.error(f"Error inesperado en login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Sesión cerrada exitosamente"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"}
    },
    summary="Cerrar sesión",
    description="Cierra la sesión del usuario actual y elimina la cookie JWT"
)
async def logout(
    response: Response,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    access_token: Optional[str] = Cookie(None, alias="access_token")
):
    """
    Cierra la sesión del usuario autenticado.
    
    Requiere estar autenticado (cookie httpOnly con token JWT válido).
    Invalida el token en el servidor y elimina la cookie.
    """
    try:
        # Si tenemos el token, invalidar la sesión en Auth Service
        if access_token:
            try:
                await auth_client.logout(access_token)
                logger.info(f"Sesión invalidada en Auth Service para: {current_user.email}")
            except grpc.RpcError as e:
                # Si falla la invalidación, continuamos igual limpiando la cookie
                logger.warning(f"Error invalidando sesión en Auth Service: {e.details()}")
        
        # Limpiar cookie en el cliente
        clear_auth_cookie(response)
        
        logger.info(f"Usuario desconectado: {current_user.email}")
        
        return LogoutResponse(
            message="Sesión cerrada exitosamente"
        )
        
    except Exception as e:
        logger.error(f"Error en logout: {e}")
        # Aunque falle, limpiamos la cookie del cliente
        clear_auth_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cerrando sesión, pero cookie eliminada"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Información del usuario actual"},
        401: {"model": ErrorResponse, "description": "No autenticado"}
    },
    summary="Obtener usuario actual",
    description="Retorna la información del usuario autenticado"
)
async def get_me(current_user: Annotated[UserResponse, Depends(get_current_user)]):
    """
    Obtiene la información del usuario actualmente autenticado.
    
    Requiere estar autenticado (cookie httpOnly con token JWT válido).
    """
    return current_user
