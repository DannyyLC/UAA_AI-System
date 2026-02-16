"""
Cliente gRPC para Chat Service.

Maneja la comunicación entre el Gateway y el Chat Service.
"""

from typing import Any, AsyncGenerator, Dict, Optional

import grpc
from grpc import aio as grpc_aio

from src.generated import chat_pb2, chat_pb2_grpc, common_pb2
from src.shared.configuration import settings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class ChatClient:
    """
    Cliente para comunicarse con el Chat Service vía gRPC.

    Gestiona la conexión y proporciona métodos para todas las operaciones
    disponibles en el servicio de chat.
    """

    def __init__(self):
        """Inicializa el cliente (sin conectar todavía)."""
        self.channel: Optional[grpc_aio.Channel] = None
        self.stub: Optional[chat_pb2_grpc.ChatServiceStub] = None
        self.host = "localhost"  # TODO: Obtener de settings o service discovery
        self.port = settings.chat_grpc_port

    async def connect(self):
        """Establece la conexión con el servicio."""
        try:
            address = f"{self.host}:{self.port}"
            self.channel = grpc_aio.insecure_channel(address)
            self.stub = chat_pb2_grpc.ChatServiceStub(self.channel)

            # Verificar conexión
            await self.channel.channel_ready()

            logger.info(f"Conectado a Chat Service: {address}")
        except Exception as e:
            logger.error(f"Error conectando a Chat Service: {e}")
            raise

    async def close(self):
        """Cierra la conexión."""
        if self.channel:
            await self.channel.close()
            logger.info("Conexión con Chat Service cerrada")

    # ============================================================
    # Conversaciones
    # ============================================================

    async def create_conversation(self, user_id: str, title: str = "Nueva conversación") -> dict:
        """
        Crea una nueva conversación.

        Args:
            user_id: ID del usuario
            title: Título de la conversación

        Returns:
            Diccionario con la conversación creada o error
        """
        try:
            request = chat_pb2.CreateConversationRequest(user_id=user_id, title=title)

            response = await self.stub.CreateConversation(request)

            if not response.success:
                return {
                    "success": False,
                    "error": {"code": response.error.code, "message": response.error.message},
                }

            return {
                "success": True,
                "conversation": {
                    "id": response.conversation.id,
                    "user_id": response.conversation.user_id,
                    "title": response.conversation.title,
                    "created_at": self._proto_timestamp_to_str(response.conversation.created_at),
                    "updated_at": self._proto_timestamp_to_str(response.conversation.updated_at),
                },
            }

        except grpc.RpcError as e:
            logger.error(f"Error gRPC en create_conversation: {e.code()} - {e.details()}")
            return {"success": False, "error": {"code": str(e.code()), "message": e.details()}}

    async def list_conversations(self, user_id: str, page: int = 1, page_size: int = 50) -> dict:
        """
        Lista las conversaciones de un usuario.

        Args:
            user_id: ID del usuario
            page: Página a obtener
            page_size: Tamaño de página

        Returns:
            Diccionario con lista de conversaciones y paginación
        """
        try:
            request = chat_pb2.ListConversationsRequest(
                user_id=user_id,
                pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
            )

            response = await self.stub.ListConversations(request)

            if not response.success:
                return {
                    "success": False,
                    "error": {"code": response.error.code, "message": response.error.message},
                }

            conversations = []
            for conv in response.conversations:
                conversations.append(
                    {
                        "id": conv.id,
                        "user_id": conv.user_id,
                        "title": conv.title,
                        "created_at": self._proto_timestamp_to_str(conv.created_at),
                        "updated_at": self._proto_timestamp_to_str(conv.updated_at),
                    }
                )

            return {
                "success": True,
                "conversations": conversations,
                "pagination": {
                    "page": response.pagination.page,
                    "page_size": response.pagination.page_size,
                    "total": response.pagination.total,
                    "total_pages": response.pagination.total_pages,
                },
            }

        except grpc.RpcError as e:
            logger.error(f"Error gRPC en list_conversations: {e.code()} - {e.details()}")
            return {"success": False, "error": {"code": str(e.code()), "message": e.details()}}

    async def get_conversation(self, conversation_id: str, user_id: str) -> dict:
        """
        Obtiene una conversación con sus mensajes.

        Args:
            conversation_id: ID de la conversación
            user_id: ID del usuario (para validar ownership)

        Returns:
            Diccionario con la conversación y mensajes
        """
        try:
            request = chat_pb2.GetConversationRequest(
                conversation_id=conversation_id, user_id=user_id
            )

            response = await self.stub.GetConversation(request)

            if not response.success:
                return {
                    "success": False,
                    "error": {"code": response.error.code, "message": response.error.message},
                }

            messages = []
            for msg in response.messages:
                messages.append(
                    {
                        "id": msg.id,
                        "conversation_id": msg.conversation_id,
                        "role": self._message_role_to_str(msg.role),
                        "content": msg.content,
                        "used_rag": msg.used_rag,
                        "sources": list(msg.sources),
                        "created_at": self._proto_timestamp_to_str(msg.created_at),
                    }
                )

            return {
                "success": True,
                "conversation": {
                    "id": response.conversation.id,
                    "user_id": response.conversation.user_id,
                    "title": response.conversation.title,
                    "created_at": self._proto_timestamp_to_str(response.conversation.created_at),
                    "updated_at": self._proto_timestamp_to_str(response.conversation.updated_at),
                },
                "messages": messages,
            }

        except grpc.RpcError as e:
            logger.error(f"Error gRPC en get_conversation: {e.code()} - {e.details()}")
            return {"success": False, "error": {"code": str(e.code()), "message": e.details()}}

    async def delete_conversation(self, conversation_id: str, user_id: str) -> dict:
        """
        Elimina una conversación.

        Args:
            conversation_id: ID de la conversación
            user_id: ID del usuario (para validar ownership)

        Returns:
            Diccionario con resultado de la operación
        """
        try:
            request = chat_pb2.DeleteConversationRequest(
                conversation_id=conversation_id, user_id=user_id
            )

            response = await self.stub.DeleteConversation(request)

            if not response.success:
                return {
                    "success": False,
                    "error": {"code": response.error.code, "message": response.error.message},
                }

            return {"success": True, "message": response.message}

        except grpc.RpcError as e:
            logger.error(f"Error gRPC en delete_conversation: {e.code()} - {e.details()}")
            return {"success": False, "error": {"code": str(e.code()), "message": e.details()}}

    # ============================================================
    # Mensajes
    # ============================================================

    async def send_message_stream(
        self, conversation_id: str, user_id: str, content: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Envía un mensaje y recibe respuesta en streaming.

        Args:
            conversation_id: ID de la conversación
            user_id: ID del usuario
            content: Contenido del mensaje

        Yields:
            Diccionarios con chunks de la respuesta:
            {
                "type": "token" | "rag_start" | "rag_done" | "done" | "error",
                "token": "...", (si type=token)
                "message": {...}, (si type=done)
                "used_rag": bool, (si type=done)
                "error": {...} (si type=error)
            }
        """
        try:
            request = chat_pb2.SendMessageRequest(
                conversation_id=conversation_id, user_id=user_id, content=content
            )

            stream = self.stub.SendMessage(request)

            async for response in stream:
                # Token de texto
                if response.chunk_type == chat_pb2.SendMessageResponse.CHUNK_TYPE_TOKEN:
                    yield {"type": "token", "token": response.token}

                # RAG iniciado
                elif response.chunk_type == chat_pb2.SendMessageResponse.CHUNK_TYPE_RAG_START:
                    yield {"type": "rag_start"}

                # RAG completado
                elif response.chunk_type == chat_pb2.SendMessageResponse.CHUNK_TYPE_RAG_DONE:
                    yield {"type": "rag_done"}

                # Completado
                elif response.chunk_type == chat_pb2.SendMessageResponse.CHUNK_TYPE_DONE:
                    yield {
                        "type": "done",
                        "message": {
                            "id": response.message.id,
                            "conversation_id": response.message.conversation_id,
                            "role": self._message_role_to_str(response.message.role),
                            "content": response.message.content,
                            "used_rag": response.message.used_rag,
                            "sources": list(response.message.sources),
                            "created_at": self._proto_timestamp_to_str(response.message.created_at),
                        },
                        "used_rag": response.used_rag,
                    }

                # Error
                elif response.chunk_type == chat_pb2.SendMessageResponse.CHUNK_TYPE_ERROR:
                    yield {
                        "type": "error",
                        "error": {"code": response.error.code, "message": response.error.message},
                    }

        except grpc.RpcError as e:
            logger.error(f"Error gRPC en send_message_stream: {e.code()} - {e.details()}")
            yield {"type": "error", "error": {"code": str(e.code()), "message": e.details()}}

    async def get_user_topics(self, user_id: str) -> dict:
        """
        Obtiene los temas disponibles para un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con lista de temas
        """
        try:
            request = chat_pb2.GetUserTopicsRequest(user_id=user_id)

            response = await self.stub.GetUserTopics(request)

            if not response.success:
                return {
                    "success": False,
                    "error": {"code": response.error.code, "message": response.error.message},
                }

            return {"success": True, "topics": list(response.topics)}

        except grpc.RpcError as e:
            logger.error(f"Error gRPC en get_user_topics: {e.code()} - {e.details()}")
            return {"success": False, "error": {"code": str(e.code()), "message": e.details()}}

    # ============================================================
    # Utilidades
    # ============================================================

    def _proto_timestamp_to_str(self, timestamp: common_pb2.Timestamp) -> str:
        """Convierte timestamp proto a string ISO."""
        from datetime import datetime, timezone

        dt = datetime.fromtimestamp(timestamp.seconds, tz=timezone.utc)
        return dt.isoformat()

    def _message_role_to_str(self, role: int) -> str:
        """Convierte enum de rol a string."""
        role_map = {
            chat_pb2.MESSAGE_ROLE_USER: "user",
            chat_pb2.MESSAGE_ROLE_ASSISTANT: "assistant",
            chat_pb2.MESSAGE_ROLE_SYSTEM: "system",
            chat_pb2.MESSAGE_ROLE_TOOL: "tool",
        }
        return role_map.get(role, "unknown")


# Instancia global
chat_client = ChatClient()
