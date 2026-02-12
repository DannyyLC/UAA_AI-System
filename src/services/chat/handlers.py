"""
Chat Service Handlers - Lógica de negocio para gestión de conversaciones y chat con LLM.

Orquesta:
- Gestión de conversaciones y mensajes
- Integración con LiteLLM (function calling)
- Búsqueda RAG cuando el LLM lo requiera
- Streaming de respuestas
- Eventos de auditoría
"""

import json
from typing import AsyncGenerator, Optional
import grpc

from src.generated import chat_pb2, chat_pb2_grpc, common_pb2
from src.services.chat.database import ChatRepository
from src.services.chat.litellm_client import LiteLLMClient
from src.services.chat.tools import get_rag_tools, create_system_message_with_topics, format_tool_call_result
from src.services.chat.rag.qdrant_client import QdrantManager
from src.services.chat.rag.retrieval import RAGRetriever
from src.kafka.audit import AuditProducer
from src.shared.utils import generate_id, datetime_to_proto_timestamp
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class ChatServiceHandler(chat_pb2_grpc.ChatServiceServicer):
    """
    Implementación del servicio gRPC de Chat.
    
    Maneja todas las operaciones relacionadas con conversaciones,
    mensajes e interacción con el LLM.
    """
    
    def __init__(
        self,
        repo: ChatRepository,
        llm_client: LiteLLMClient,
        rag_retriever: RAGRetriever,
        audit: AuditProducer
    ):
        """
        Inicializa el handler.
        
        Args:
            repo: Repositorio de base de datos
            llm_client: Cliente de LiteLLM
            rag_retriever: Cliente de RAG
            audit: Producer de eventos de auditoría
        """
        self.repo = repo
        self.llm = llm_client
        self.rag = rag_retriever
        self.audit = audit
    
    # ============================================================
    # CreateConversation
    # ============================================================
    
    async def CreateConversation(
        self, request: chat_pb2.CreateConversationRequest, context: grpc.aio.ServicerContext
    ) -> chat_pb2.CreateConversationResponse:
        """Crea una nueva conversación para un usuario."""
        try:
            logger.info(f"Creando conversación para user_id={request.user_id}")
            
            # Crear conversación en DB
            title = request.title if request.title else "Nueva conversación"
            conversation = await self.repo.create_conversation(
                user_id=request.user_id,
                title=title
            )
            
            if not conversation:
                return chat_pb2.CreateConversationResponse(
                    success=False,
                    error=common_pb2.Error(
                        code="CREATION_FAILED",
                        message="No se pudo crear la conversación"
                    )
                )
            
            # Auditoría
            await self.audit.send_event(
                action="conversation.created",
                service="chat",
                user_id=request.user_id,
                detail={"conversation_id": conversation["id"]}
            )
            
            # Construir response
            conv_proto = chat_pb2.Conversation(
                id=conversation["id"],
                user_id=conversation["user_id"],
                title=conversation["title"],
                created_at=datetime_to_proto_timestamp(conversation["created_at"]),
                updated_at=datetime_to_proto_timestamp(conversation["updated_at"])
            )
            
            logger.info(f"Conversación creada: {conversation['id']}")
            
            return chat_pb2.CreateConversationResponse(
                success=True,
                conversation=conv_proto
            )
            
        except Exception as e:
            logger.error(f"Error creando conversación: {e}", exc_info=True)
            return chat_pb2.CreateConversationResponse(
                success=False,
                error=common_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )
    
    # ============================================================
    # ListConversations
    # ============================================================
    
    async def ListConversations(
        self, request: chat_pb2.ListConversationsRequest, context: grpc.aio.ServicerContext
    ) -> chat_pb2.ListConversationsResponse:
        """Lista las conversaciones de un usuario."""
        try:
            logger.info(f"Listando conversaciones para user_id={request.user_id}")
            
            # Paginación
            page = request.pagination.page if request.pagination.page > 0 else 1
            page_size = request.pagination.page_size if request.pagination.page_size > 0 else 50
            offset = (page - 1) * page_size
            
            # Obtener conversaciones y total
            conversations = await self.repo.list_conversations(
                user_id=request.user_id,
                limit=page_size,
                offset=offset
            )
            
            total = await self.repo.count_conversations(request.user_id)
            total_pages = (total + page_size - 1) // page_size
            
            # Construir response
            conv_list = []
            for conv in conversations:
                conv_proto = chat_pb2.Conversation(
                    id=conv["id"],
                    user_id=conv["user_id"],
                    title=conv["title"],
                    created_at=datetime_to_proto_timestamp(conv["created_at"]),
                    updated_at=datetime_to_proto_timestamp(conv["updated_at"])
                )
                conv_list.append(conv_proto)
            
            pagination_response = common_pb2.PaginationResponse(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages
            )
            
            logger.info(f"Listadas {len(conv_list)} conversaciones (total={total})")
            
            return chat_pb2.ListConversationsResponse(
                success=True,
                conversations=conv_list,
                pagination=pagination_response
            )
            
        except Exception as e:
            logger.error(f"Error listando conversaciones: {e}", exc_info=True)
            return chat_pb2.ListConversationsResponse(
                success=False,
                error=common_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )
    
    # ============================================================
    # GetConversation
    # ============================================================
    
    async def GetConversation(
        self, request: chat_pb2.GetConversationRequest, context: grpc.aio.ServicerContext
    ) -> chat_pb2.GetConversationResponse:
        """Obtiene una conversación con todos sus mensajes."""
        try:
            logger.info(f"Obteniendo conversación {request.conversation_id}")
            
            # Verificar ownership
            if not await self.repo.conversation_belongs_to_user(
                request.conversation_id, request.user_id
            ):
                return chat_pb2.GetConversationResponse(
                    success=False,
                    error=common_pb2.Error(
                        code="NOT_FOUND",
                        message="Conversación no encontrada o no pertenece al usuario"
                    )
                )
            
            # Obtener conversación
            conversation = await self.repo.get_conversation(request.conversation_id)
            
            if not conversation:
                return chat_pb2.GetConversationResponse(
                    success=False,
                    error=common_pb2.Error(
                        code="NOT_FOUND",
                        message="Conversación no encontrada"
                    )
                )
            
            # Obtener mensajes
            messages = await self.repo.get_messages(request.conversation_id)
            
            # Construir response
            conv_proto = chat_pb2.Conversation(
                id=conversation["id"],
                user_id=conversation["user_id"],
                title=conversation["title"],
                created_at=datetime_to_proto_timestamp(conversation["created_at"]),
                updated_at=datetime_to_proto_timestamp(conversation["updated_at"])
            )
            
            messages_proto = []
            for msg in messages:
                msg_proto = chat_pb2.Message(
                    id=msg["id"],
                    conversation_id=msg["conversation_id"],
                    role=self._string_to_message_role(msg["role"]),
                    content=msg["content"],
                    used_rag=msg["used_rag"],
                    sources=msg["sources"] or [],
                    created_at=datetime_to_proto_timestamp(msg["created_at"])
                )
                messages_proto.append(msg_proto)
            
            logger.info(f"Conversación obtenida: {len(messages_proto)} mensajes")
            
            return chat_pb2.GetConversationResponse(
                success=True,
                conversation=conv_proto,
                messages=messages_proto
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo conversación: {e}", exc_info=True)
            return chat_pb2.GetConversationResponse(
                success=False,
                error=common_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )
    
    # ============================================================
    # DeleteConversation
    # ============================================================
    
    async def DeleteConversation(
        self, request: chat_pb2.DeleteConversationRequest, context: grpc.aio.ServicerContext
    ) -> chat_pb2.DeleteConversationResponse:
        """Elimina una conversación y todos sus mensajes."""
        try:
            logger.info(f"Eliminando conversación {request.conversation_id}")
            
            # Verificar ownership
            if not await self.repo.conversation_belongs_to_user(
                request.conversation_id, request.user_id
            ):
                return chat_pb2.DeleteConversationResponse(
                    success=False,
                    error=common_pb2.Error(
                        code="NOT_FOUND",
                        message="Conversación no encontrada o no pertenece al usuario"
                    )
                )
            
            # Eliminar
            deleted = await self.repo.delete_conversation(request.conversation_id)
            
            if not deleted:
                return chat_pb2.DeleteConversationResponse(
                    success=False,
                    error=common_pb2.Error(
                        code="NOT_FOUND",
                        message="Conversación no encontrada"
                    )
                )
            
            # Auditoría
            await self.audit.send_event(
                action="conversation.deleted",
                service="chat",
                user_id=request.user_id,
                detail={"conversation_id": request.conversation_id}
            )
            
            logger.info(f"Conversación eliminada: {request.conversation_id}")
            
            return chat_pb2.DeleteConversationResponse(
                success=True,
                message="Conversación eliminada exitosamente"
            )
            
        except Exception as e:
            logger.error(f"Error eliminando conversación: {e}", exc_info=True)
            return chat_pb2.DeleteConversationResponse(
                success=False,
                error=common_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )
    
    # ============================================================
    # SendMessage (STREAMING)
    # ============================================================
    
    async def SendMessage(
        self, request: chat_pb2.SendMessageRequest, context: grpc.aio.ServicerContext
    ) -> AsyncGenerator[chat_pb2.SendMessageResponse, None]:
        """
        Envía un mensaje y genera respuesta del LLM con streaming.
        
        Flujo:
        1. Valida que la conversación pertenezca al usuario
        2. Obtiene temas disponibles del usuario
        3. Crea system message con temas
        4. Obtiene historial de la conversación
        5. Llama al LLM (con function calling habilitado)
        6. Si el LLM llama a RAG tool, ejecuta búsqueda
        7. Streamea la respuesta al cliente
        8. Guarda mensajes en DB
        """
        try:
            logger.info(
                f"SendMessage: conversation_id={request.conversation_id}, "
                f"user_id={request.user_id}"
            )
            
            # Verificar ownership
            if not await self.repo.conversation_belongs_to_user(
                request.conversation_id, request.user_id
            ):
                yield chat_pb2.SendMessageResponse(
                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_ERROR,
                    error=common_pb2.Error(
                        code="NOT_FOUND",
                        message="Conversación no encontrada o no pertenece al usuario"
                    )
                )
                return
            
            # 1. Guardar mensaje del usuario
            user_message = await self.repo.create_message(
                conversation_id=request.conversation_id,
                role="user",
                content=request.content
            )
            
            # 2. Obtener temas disponibles del usuario
            logger.info("Obteniendo temas disponibles del usuario...")
            topics = await self.repo.get_user_topics(request.user_id)
            logger.info(f"Temas disponibles: {topics}")
            
            # 3. Crear system message con temas
            system_message = create_system_message_with_topics(topics)
            
            # 4. Obtener historial de mensajes
            history = await self.repo.get_conversation_history(
                request.conversation_id,
                limit=10  # Últimos 10 mensajes
            )
            
            # 5. Formatear mensajes para el LLM
            messages = self.llm.format_messages(
                system_message=system_message,
                conversation_history=history[:-1],  # Excluir el último (es el que acabamos de agregar)
                user_message=request.content
            )
            
            # 6. Obtener tools
            tools = get_rag_tools()
            
            # Variables para tracking
            full_response = ""
            used_rag = False
            sources = []
            tool_calls_pending = []
            
            # 7. Primera llamada al LLM (puede decidir usar RAG)
            logger.info("Llamando al LLM (primera iteración)...")
            
            async for chunk in self.llm.chat_completion_stream(
                messages=messages,
                tools=tools,
                tool_choice="auto"
            ):
                # Contenido de texto
                if chunk["type"] == "content":
                    full_response += chunk["delta"]
                    
                    # Enviar chunk al cliente
                    yield chat_pb2.SendMessageResponse(
                        chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_TOKEN,
                        token=chunk["delta"]
                    )
                
                # Tool call detectado
                elif chunk["type"] == "tool_call":
                    logger.info("LLM decidió usar RAG tool")
                    used_rag = True
                    
                    # Notificar al cliente
                    yield chat_pb2.SendMessageResponse(
                        chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_RAG_START
                    )
                    
                    tool_calls_pending = chunk["tool_calls"]
                
                # Finalización
                elif chunk["type"] == "done":
                    finish_reason = chunk["finish_reason"]
                    logger.info(f"Primera iteración completada: finish_reason={finish_reason}")
                    
                    # Si hay tool calls, ejecutarlos
                    if finish_reason == "tool_calls" and tool_calls_pending:
                        # Ejecutar cada tool call
                        for tool_call in tool_calls_pending:
                            function_name = tool_call["function"]["name"]
                            arguments = json.loads(tool_call["function"]["arguments"])
                            
                            logger.info(f"Ejecutando tool: {function_name} con args: {arguments}")
                            
                            # Ejecutar RAG
                            if function_name == "search_knowledge_base":
                                query = arguments.get("query")
                                topic = arguments.get("topic")
                                
                                rag_result = await self.rag.search(
                                    query=query,
                                    user_id=request.user_id,
                                    topic=topic,
                                    limit=5
                                )
                                
                                sources = rag_result["sources"]
                                context = rag_result["context"]
                                
                                logger.info(f"RAG completado: {len(sources)} fuentes encontradas")
                                
                                # Notificar al cliente
                                yield chat_pb2.SendMessageResponse(
                                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_RAG_DONE
                                )
                                
                                # Agregar tool result a mensajes
                                messages.append({
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [{
                                        "id": tool_call["id"],
                                        "type": "function",
                                        "function": {
                                            "name": function_name,
                                            "arguments": tool_call["function"]["arguments"]
                                        }
                                    }]
                                })
                                
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "name": function_name,
                                    "content": format_tool_call_result(function_name, rag_result)
                                })
                        
                        # Segunda llamada al LLM con el contexto de RAG
                        logger.info("Llamando al LLM (segunda iteración con contexto RAG)...")
                        full_response = ""  # Reset
                        
                        async for chunk2 in self.llm.chat_completion_stream(
                            messages=messages,
                            tools=None,  # No más tools en esta iteración
                            tool_choice="none"
                        ):
                            if chunk2["type"] == "content":
                                full_response += chunk2["delta"]
                                
                                # Enviar chunk al cliente
                                yield chat_pb2.SendMessageResponse(
                                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_TOKEN,
                                    token=chunk2["delta"]
                                )
                            
                            elif chunk2["type"] == "done":
                                logger.info("Segunda iteración completada")
            
            # 8. Guardar respuesta del asistente en DB
            assistant_message = await self.repo.create_message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=full_response,
                used_rag=used_rag,
                sources=sources
            )
            
            # Auditoría
            await self.audit.send_event(
                action="message.sent",
                service="chat",
                user_id=request.user_id,
                detail={
                    "conversation_id": request.conversation_id,
                    "used_rag": used_rag,
                    "sources_count": len(sources)
                }
            )
            
            # 9. Enviar mensaje de finalización con metadata
            yield chat_pb2.SendMessageResponse(
                chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_DONE,
                message=chat_pb2.Message(
                    id=assistant_message["id"],
                    conversation_id=request.conversation_id,
                    role=chat_pb2.MESSAGE_ROLE_ASSISTANT,
                    content=full_response,
                    used_rag=used_rag,
                    sources=sources,
                    created_at=datetime_to_proto_timestamp(assistant_message["created_at"])
                ),
                used_rag=used_rag
            )
            
            logger.info(f"Mensaje completado (used_rag={used_rag}, sources={len(sources)})")
            
        except Exception as e:
            logger.error(f"Error en SendMessage: {e}", exc_info=True)
            yield chat_pb2.SendMessageResponse(
                chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_ERROR,
                error=common_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )
    
    # ============================================================
    # GetMessages
    # ============================================================
    
    async def GetMessages(
        self, request: chat_pb2.GetMessagesRequest, context: grpc.aio.ServicerContext
    ) -> chat_pb2.GetMessagesResponse:
        """Obtiene los mensajes de una conversación (paginados)."""
        try:
            logger.info(f"Obteniendo mensajes de conversación {request.conversation_id}")
            
            # Verificar ownership
            if not await self.repo.conversation_belongs_to_user(
                request.conversation_id, request.user_id
            ):
                return chat_pb2.GetMessagesResponse(
                    success=False,
                    error=common_pb2.Error(
                        code="NOT_FOUND",
                        message="Conversación no encontrada o no pertenece al usuario"
                    )
                )
            
            # Paginación
            page = request.pagination.page if request.pagination.page > 0 else 1
            page_size = request.pagination.page_size if request.pagination.page_size > 0 else 100
            offset = (page - 1) * page_size
            
            # Obtener mensajes y total
            messages = await self.repo.get_messages(
                conversation_id=request.conversation_id,
                limit=page_size,
                offset=offset
            )
            
            total = await self.repo.count_messages(request.conversation_id)
            total_pages = (total + page_size - 1) // page_size
            
            # Construir response
            messages_proto = []
            for msg in messages:
                msg_proto = chat_pb2.Message(
                    id=msg["id"],
                    conversation_id=msg["conversation_id"],
                    role=self._string_to_message_role(msg["role"]),
                    content=msg["content"],
                    used_rag=msg["used_rag"],
                    sources=msg["sources"] or [],
                    created_at=datetime_to_proto_timestamp(msg["created_at"])
                )
                messages_proto.append(msg_proto)
            
            pagination_response = common_pb2.PaginationResponse(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages
            )
            
            logger.info(f"Obtenidos {len(messages_proto)} mensajes (total={total})")
            
            return chat_pb2.GetMessagesResponse(
                success=True,
                messages=messages_proto,
                pagination=pagination_response
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}", exc_info=True)
            return chat_pb2.GetMessagesResponse(
                success=False,
                error=common_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )
    
    # ============================================================
    # GetUserTopics
    # ============================================================
    
    async def GetUserTopics(
        self, request: chat_pb2.GetUserTopicsRequest, context: grpc.aio.ServicerContext
    ) -> chat_pb2.GetUserTopicsResponse:
        """Obtiene los temas únicos disponibles para un usuario."""
        try:
            logger.info(f"Obteniendo temas para user_id={request.user_id}")
            
            topics = await self.repo.get_user_topics(request.user_id)
            
            logger.info(f"Temas encontrados: {topics}")
            
            return chat_pb2.GetUserTopicsResponse(
                success=True,
                topics=topics
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo temas: {e}", exc_info=True)
            return chat_pb2.GetUserTopicsResponse(
                success=False,
                error=common_pb2.Error(
                    code="INTERNAL_ERROR",
                    message=str(e)
                )
            )
    
    # ============================================================
    # Utilidades
    # ============================================================
    
    def _string_to_message_role(self, role: str) -> int:
        """Convierte string de rol a enum proto."""
        role_map = {
            "user": chat_pb2.MESSAGE_ROLE_USER,
            "assistant": chat_pb2.MESSAGE_ROLE_ASSISTANT,
            "system": chat_pb2.MESSAGE_ROLE_SYSTEM,
            "tool": chat_pb2.MESSAGE_ROLE_TOOL
        }
        return role_map.get(role.lower(), chat_pb2.MESSAGE_ROLE_UNSPECIFIED)
