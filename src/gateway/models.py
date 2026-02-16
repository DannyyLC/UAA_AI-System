"""Modelos Pydantic para validación de requests y responses."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# ============================================================
# Auth Models
# ============================================================


class RegisterRequest(BaseModel):
    """Request para registro de usuario."""

    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., min_length=8, description="Contraseña (mínimo 8 caracteres)")
    full_name: str = Field(..., min_length=2, description="Nombre completo del usuario")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "usuario@uaa.edu.mx",
                "password": "password123",
                "full_name": "Juan Pérez",
            }
        }
    }


class LoginRequest(BaseModel):
    """Request para login de usuario."""

    email: EmailStr = Field(..., description="Email del usuario")
    password: str = Field(..., description="Contraseña del usuario")

    model_config = {
        "json_schema_extra": {"example": {"email": "usuario@uaa.edu.mx", "password": "password123"}}
    }


class UserResponse(BaseModel):
    """Response con información del usuario."""

    user_id: str = Field(..., description="ID único del usuario")
    email: str = Field(..., description="Email del usuario")
    full_name: str = Field(..., description="Nombre completo del usuario")
    created_at: str = Field(..., description="Fecha de creación")
    role: str = Field(default="user", description="Rol del usuario")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "usuario@uaa.edu.mx",
                "full_name": "Juan Pérez",
                "created_at": "2026-02-11T10:30:00Z",
                "role": "user",
            }
        }
    }


class AuthResponse(BaseModel):
    """Response para operaciones de autenticación exitosas."""

    message: str = Field(..., description="Mensaje de confirmación")
    user: UserResponse = Field(..., description="Información del usuario")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Login exitoso",
                "user": {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "usuario@uaa.edu.mx",
                    "full_name": "Juan Pérez",
                    "created_at": "2026-02-11T10:30:00Z",
                    "is_active": True,
                },
            }
        }
    }


class LogoutResponse(BaseModel):
    """Response para logout."""

    message: str = Field(..., description="Mensaje de confirmación")

    model_config = {"json_schema_extra": {"example": {"message": "Sesión cerrada exitosamente"}}}


class ErrorResponse(BaseModel):
    """Response para errores."""

    error: str = Field(..., description="Tipo de error")
    message: str = Field(..., description="Mensaje descriptivo del error")
    detail: Optional[str] = Field(None, description="Detalles adicionales del error")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "UNAUTHORIZED",
                "message": "Credenciales inválidas",
                "detail": "El email o contraseña son incorrectos",
            }
        }
    }


# ============================================================
# Health Check Models
# ============================================================


class HealthResponse(BaseModel):
    """Response para health check."""

    status: str = Field(..., description="Estado del servicio")
    timestamp: str = Field(..., description="Timestamp del check")
    version: str = Field(default="1.0.0", description="Versión del API")
    services: dict = Field(default_factory=dict, description="Estado de servicios dependientes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2026-02-11T10:30:00Z",
                "version": "1.0.0",
                "services": {"auth_service": "connected", "database": "connected"},
            }
        }
    }
