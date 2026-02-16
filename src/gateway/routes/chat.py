"""Routes de chat y conversaciones."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.gateway.dependencies import get_current_user
from src.gateway.grpc_clients.chat_client import chat_client
from src.gateway.models import ErrorResponse, UserResponse
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ============================================================
# Models
# ============================================================


class CreateConversationRequest(BaseModel):
    """Request para crear conversación."""

    title: str = Field(default="Nueva conversación", max_length=500)


class CreateConversationResponse(BaseModel):
    """Response de creación de conversación."""

    message: str
    conversation: dict


class ConversationsListResponse(BaseModel):
    """Response de lista de conversaciones."""

    conversations: list[dict]
    pagination: dict


class ConversationResponse(BaseModel):
    """Response de conversación con mensajes."""

    conversation: dict
    messages: list[dict]


class SendMessageRequest(BaseModel):
    """Request para enviar mensaje."""

    content: str = Field(min_length=1, max_length=10000)


class DeleteConversationResponse(BaseModel):
    """Response de eliminación de conversación."""

    message: str


class TopicsResponse(BaseModel):
    """Response con temas disponibles."""

    topics: list[str]


# ============================================================
# Endpoints
# ============================================================


@router.post(
    "/conversations",
    response_model=CreateConversationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Conversación creada exitosamente"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"},
    },
    summary="Crear nueva conversación",
    description="Crea una nueva conversación para el usuario autenticado",
)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Crea una nueva conversación."""
    try:
        result = await chat_client.create_conversation(
            user_id=current_user.user_id, title=request.title
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"]["message"]
            )

        return CreateConversationResponse(
            message="Conversación creada exitosamente", conversation=result["conversation"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor"
        )


@router.get(
    "/conversations",
    response_model=ConversationsListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Lista de conversaciones"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"},
    },
    summary="Listar conversaciones",
    description="Lista todas las conversaciones del usuario autenticado",
)
async def list_conversations(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    page: int = 1,
    page_size: int = 50,
):
    """Lista las conversaciones del usuario."""
    try:
        result = await chat_client.list_conversations(
            user_id=current_user.user_id, page=page, page_size=page_size
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"]["message"]
            )

        return ConversationsListResponse(
            conversations=result["conversations"], pagination=result["pagination"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando conversaciones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor"
        )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Conversación con mensajes"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        404: {"model": ErrorResponse, "description": "Conversación no encontrada"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"},
    },
    summary="Obtener conversación",
    description="Obtiene una conversación específica con todos sus mensajes",
)
async def get_conversation(
    conversation_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]
):
    """Obtiene una conversación con sus mensajes."""
    try:
        result = await chat_client.get_conversation(
            conversation_id=conversation_id, user_id=current_user.user_id
        )

        if not result["success"]:
            error = result["error"]
            if error["code"] == "NOT_FOUND":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error["message"])
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error["message"]
            )

        return ConversationResponse(
            conversation=result["conversation"], messages=result["messages"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor"
        )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=DeleteConversationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Conversación eliminada"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        404: {"model": ErrorResponse, "description": "Conversación no encontrada"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"},
    },
    summary="Eliminar conversación",
    description="Elimina una conversación y todos sus mensajes",
)
async def delete_conversation(
    conversation_id: str, current_user: Annotated[UserResponse, Depends(get_current_user)]
):
    """Elimina una conversación."""
    try:
        result = await chat_client.delete_conversation(
            conversation_id=conversation_id, user_id=current_user.user_id
        )

        if not result["success"]:
            error = result["error"]
            if error["code"] == "NOT_FOUND":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error["message"])
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=error["message"]
            )

        return DeleteConversationResponse(message=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando conversación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor"
        )


@router.post(
    "/conversations/{conversation_id}/messages",
    responses={
        200: {
            "description": "Streaming de respuesta del LLM",
            "content": {"text/event-stream": {}},
        },
        401: {"model": ErrorResponse, "description": "No autenticado"},
        404: {"model": ErrorResponse, "description": "Conversación no encontrada"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"},
    },
    summary="Enviar mensaje (SSE)",
    description="""
Envía un mensaje a una conversación y recibe la respuesta del LLM en streaming usando Server-Sent Events (SSE).

Tipos de eventos:
- `token`: Fragmento de texto de la respuesta
- `rag_start`: El LLM decidió usar RAG
- `rag_done`: RAG completado
- `done`: Respuesta completada con metadata
- `error`: Error durante el procesamiento
    """,
)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """
    Envía un mensaje y recibe respuesta en streaming (SSE).
    """

    async def event_generator():
        """Generador de eventos SSE."""
        try:
            async for chunk in chat_client.send_message_stream(
                conversation_id=conversation_id,
                user_id=current_user.user_id,
                content=request.content,
            ):
                # Formatear como SSE
                event_type = chunk["type"]

                if event_type == "token":
                    # Enviar token de texto
                    yield f"event: token\ndata: {chunk['token']}\n\n"

                elif event_type == "rag_start":
                    yield f"event: rag_start\ndata: {{}}\n\n"

                elif event_type == "rag_done":
                    yield f"event: rag_done\ndata: {{}}\n\n"

                elif event_type == "done":
                    # Enviar metadata final
                    import json

                    data = json.dumps({"message": chunk["message"], "used_rag": chunk["used_rag"]})
                    yield f"event: done\ndata: {data}\n\n"

                elif event_type == "error":
                    import json

                    data = json.dumps(chunk["error"])
                    yield f"event: error\ndata: {data}\n\n"

        except Exception as e:
            logger.error(f"Error en streaming: {e}")
            import json

            error_data = json.dumps({"code": "INTERNAL_ERROR", "message": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desactivar buffer de nginx
        },
    )


@router.get(
    "/topics",
    response_model=TopicsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Lista de temas disponibles"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"},
    },
    summary="Obtener temas disponibles",
    description="Obtiene la lista de temas únicos de documentos indexados por el usuario",
)
async def get_user_topics(current_user: Annotated[UserResponse, Depends(get_current_user)]):
    """Obtiene los temas disponibles del usuario."""
    try:
        result = await chat_client.get_user_topics(current_user.user_id)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result["error"]["message"]
            )

        return TopicsResponse(topics=result["topics"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo temas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno del servidor"
        )
