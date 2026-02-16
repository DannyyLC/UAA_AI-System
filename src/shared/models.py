"""
Modelos Pydantic compartidos entre servicios.

Estos modelos se usan para validación en el Gateway (REST)
y como representación interna entre capas.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============================================================
# Enums
# ============================================================
class UserRole(str, Enum):
    """Roles del sistema."""

    USER = "user"
    ADMIN = "admin"


class MessageRole(str, Enum):
    """Roles de los mensajes en una conversación."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class JobStatus(str, Enum):
    """Estados de un trabajo de indexación."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================
# Auth
# ============================================================
class UserCreate(BaseModel):
    """Request para crear un usuario."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Request para login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Representación pública de un usuario."""

    id: UUID
    email: str
    name: str
    role: UserRole
    created_at: datetime


class TokenResponse(BaseModel):
    """Respuesta de login/refresh con tokens."""

    user: UserResponse
    access_token: str
    refresh_token: str
    expires_in: int


# ============================================================
# Chat
# ============================================================
class ConversationCreate(BaseModel):
    """Request para crear una conversación."""

    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """Representación de una conversación."""

    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional["MessageResponse"] = None


class MessageResponse(BaseModel):
    """Representación de un mensaje."""

    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    used_rag: bool = False
    sources: list[str] = Field(default_factory=list)
    created_at: datetime


class SendMessageRequest(BaseModel):
    """Request para enviar un mensaje."""

    content: str = Field(min_length=1, max_length=10000)


# ============================================================
# Indexing / Documents
# ============================================================
class SubmitDocumentRequest(BaseModel):
    """Metadata para subir un documento (el archivo va como Form/File)."""

    topic: str = Field(min_length=1, max_length=255)
    metadata: Optional[dict[str, str]] = None


class JobStatusResponse(BaseModel):
    """Estado de un trabajo de indexación."""

    job_id: UUID
    filename: str
    topic: str
    status: JobStatus
    chunks_created: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SourceInfo(BaseModel):
    """Información de un documento indexado."""

    source: str
    topic: str
    chunks_count: int
    indexed_at: Optional[datetime] = None


# ============================================================
# RAG
# ============================================================
class SearchResultItem(BaseModel):
    """Un resultado de búsqueda semántica."""

    document_id: str
    chunk_id: str
    content: str
    score: float
    source: str
    topic: str
    page: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Respuesta de búsqueda RAG."""

    results: list[SearchResultItem]
    context: str
    total: int


# ============================================================
# Paginación
# ============================================================
class PaginationParams(BaseModel):
    """Parámetros de paginación para requests."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Wrapper genérico para respuestas paginadas."""

    page: int
    page_size: int
    total: int
    total_pages: int
    items: list[Any]


# ============================================================
# Errores
# ============================================================
class ErrorResponse(BaseModel):
    """Respuesta de error estándar."""

    code: int
    message: str
    detail: Optional[str] = None


# Resolver forward references
ConversationResponse.model_rebuild()
