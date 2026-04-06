"""
Chat Service Handlers - Lógica de negocio para gestión de conversaciones y chat con LLM.

Orquesta:
- Gestión de conversaciones y mensajes
- Clasificación de preguntas (en colección o general)
- Búsqueda RAG cuando la pregunta cae en una colección
- Streaming de respuestas
- Eventos de auditoría
"""

import time
from typing import AsyncGenerator, Optional

import grpc

from src.generated import chat_pb2, chat_pb2_grpc, common_pb2
from src.kafka.audit import AuditProducer
from src.services.chat.database import ChatRepository
from src.services.chat.litellm_client import LiteLLMClient
from src.services.chat.rag.retrieval import RAGRetriever
from src.services.chat.tools import (
    create_classification_prompt,
    create_general_system_message,
    create_rag_system_message,
    create_research_plan_prompt,
    parse_classification_result,
    parse_research_plan,
)
from src.shared.logging_utils import get_logger
from src.shared.utils import datetime_to_proto_timestamp, generate_id

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
        audit: AuditProducer,
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
            conversation = await self.repo.create_conversation(user_id=request.user_id, title=title)

            if not conversation:
                return chat_pb2.CreateConversationResponse(
                    success=False,
                    error=common_pb2.Error(
                        code="CREATION_FAILED", message="No se pudo crear la conversación"
                    ),
                )

            # Auditoría
            await self.audit.send_event(
                action="conversation.created",
                service="chat",
                user_id=request.user_id,
                detail={"conversation_id": conversation["id"]},
            )

            # Construir response
            conv_proto = chat_pb2.Conversation(
                id=str(conversation["id"]),
                user_id=str(conversation["user_id"]),
                title=conversation["title"],
                created_at=datetime_to_proto_timestamp(conversation["created_at"]),
                updated_at=datetime_to_proto_timestamp(conversation["updated_at"]),
            )

            logger.info(f"Conversación creada: {conversation['id']}")

            return chat_pb2.CreateConversationResponse(success=True, conversation=conv_proto)

        except Exception as e:
            logger.error(f"Error creando conversación: {e}", exc_info=True)
            return chat_pb2.CreateConversationResponse(
                success=False, error=common_pb2.Error(code="INTERNAL_ERROR", message=str(e))
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
                user_id=request.user_id, limit=page_size, offset=offset
            )

            total = await self.repo.count_conversations(request.user_id)
            total_pages = (total + page_size - 1) // page_size

            # Construir response
            conv_list = []
            for conv in conversations:
                conv_proto = chat_pb2.Conversation(
                    id=str(conv["id"]),
                    user_id=str(conv["user_id"]),
                    title=conv["title"],
                    created_at=datetime_to_proto_timestamp(conv["created_at"]),
                    updated_at=datetime_to_proto_timestamp(conv["updated_at"]),
                )
                conv_list.append(conv_proto)

            pagination_response = common_pb2.PaginationResponse(
                page=page, page_size=page_size, total=total, total_pages=total_pages
            )

            logger.info(f"Listadas {len(conv_list)} conversaciones (total={total})")

            return chat_pb2.ListConversationsResponse(
                success=True, conversations=conv_list, pagination=pagination_response
            )

        except Exception as e:
            logger.error(f"Error listando conversaciones: {e}", exc_info=True)
            return chat_pb2.ListConversationsResponse(
                success=False, error=common_pb2.Error(code="INTERNAL_ERROR", message=str(e))
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
                        message="Conversación no encontrada o no pertenece al usuario",
                    ),
                )

            # Obtener conversación
            conversation = await self.repo.get_conversation(request.conversation_id)

            if not conversation:
                return chat_pb2.GetConversationResponse(
                    success=False,
                    error=common_pb2.Error(code="NOT_FOUND", message="Conversación no encontrada"),
                )

            # Obtener mensajes
            messages = await self.repo.get_messages(request.conversation_id)

            # Construir response
            conv_proto = chat_pb2.Conversation(
                id=str(conversation["id"]),
                user_id=str(conversation["user_id"]),
                title=conversation["title"],
                created_at=datetime_to_proto_timestamp(conversation["created_at"]),
                updated_at=datetime_to_proto_timestamp(conversation["updated_at"]),
            )

            messages_proto = []
            for msg in messages:
                msg_proto = chat_pb2.Message(
                    id=str(msg["id"]),
                    conversation_id=str(msg["conversation_id"]),
                    role=self._string_to_message_role(msg["role"]),
                    content=msg["content"],
                    used_rag=msg["used_rag"],
                    sources=msg["sources"] or [],
                    created_at=datetime_to_proto_timestamp(msg["created_at"]),
                )
                messages_proto.append(msg_proto)

            logger.info(f"Conversación obtenida: {len(messages_proto)} mensajes")

            return chat_pb2.GetConversationResponse(
                success=True, conversation=conv_proto, messages=messages_proto
            )

        except Exception as e:
            logger.error(f"Error obteniendo conversación: {e}", exc_info=True)
            return chat_pb2.GetConversationResponse(
                success=False, error=common_pb2.Error(code="INTERNAL_ERROR", message=str(e))
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
                        message="Conversación no encontrada o no pertenece al usuario",
                    ),
                )

            # Eliminar
            deleted = await self.repo.delete_conversation(request.conversation_id)

            if not deleted:
                return chat_pb2.DeleteConversationResponse(
                    success=False,
                    error=common_pb2.Error(code="NOT_FOUND", message="Conversación no encontrada"),
                )

            # Auditoría
            await self.audit.send_event(
                action="conversation.deleted",
                service="chat",
                user_id=request.user_id,
                detail={"conversation_id": request.conversation_id},
            )

            logger.info(f"Conversación eliminada: {request.conversation_id}")

            return chat_pb2.DeleteConversationResponse(
                success=True, message="Conversación eliminada exitosamente"
            )

        except Exception as e:
            logger.error(f"Error eliminando conversación: {e}", exc_info=True)
            return chat_pb2.DeleteConversationResponse(
                success=False, error=common_pb2.Error(code="INTERNAL_ERROR", message=str(e))
            )

    # ============================================================
    # SendMessage (STREAMING)
    # ============================================================

    async def SendMessage(
        self, request: chat_pb2.SendMessageRequest, context: grpc.aio.ServicerContext
    ) -> AsyncGenerator[chat_pb2.SendMessageResponse, None]:
        """
        Envía un mensaje y genera respuesta del LLM con streaming.

        Flujo fijo (sin function calling):
        1. Valida que la conversación pertenezca al usuario
        2. Obtiene temas disponibles del usuario
        3. Si hay temas: clasifica la pregunta en una colección o "general"
        4. Si la clasificación es una colección: busca contexto con RAG
        5. Streamea la respuesta del LLM (con o sin contexto)
        6. Guarda mensajes en DB
        """
        try:
            logger.info(
                f"{'='*60}\n"
                f"  NUEVA CONSULTA\n"
                f"  conversation_id={request.conversation_id}\n"
                f"  user_id={request.user_id}\n"
                f"  modelo={request.model or 'default'}\n"
                f"  pregunta={request.content[:100]}{'...' if len(request.content) > 100 else ''}\n"
                f"{'='*60}"
            )

            # Verificar ownership
            if not await self.repo.conversation_belongs_to_user(
                request.conversation_id, request.user_id
            ):
                yield chat_pb2.SendMessageResponse(
                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_ERROR,
                    error=common_pb2.Error(
                        code="NOT_FOUND",
                        message="Conversación no encontrada o no pertenece al usuario",
                    ),
                )
                return

            # Iniciar timer de rendimiento
            perf_start = time.perf_counter()

            # 1. Guardar mensaje del usuario
            user_message = await self.repo.create_message(
                conversation_id=request.conversation_id, role="user", content=request.content
            )
            logger.info("[ETAPA 1/7] Mensaje del usuario guardado en DB")

            # 2. Obtener temas disponibles del usuario
            topics = await self.repo.get_user_topics(request.user_id)
            logger.info(f"[ETAPA 2/7] Temas disponibles del usuario: {topics if topics else '(ninguno)'}")

            # 3. Obtener historial de mensajes
            history = await self.repo.get_conversation_history(
                request.conversation_id, limit=10
            )
            logger.info(f"[ETAPA 3/7] Historial recuperado: {len(history)} mensajes")

            # Determinar modelo a usar (override del request o default)
            model_override = request.model if request.model else None
            if model_override:
                logger.info(f"  → Modelo override: {model_override}")

            # Variables para tracking
            full_response = ""
            used_rag = False
            sources = []
            classification = "general"

            # 4. Clasificación: si hay temas disponibles, clasificar la pregunta
            if topics:
                # Notificar al cliente que estamos clasificando
                logger.info("[ETAPA 4/7] CLASIFICACIÓN — Enviando evento CLASSIFYING al cliente")
                yield chat_pb2.SendMessageResponse(
                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_CLASSIFYING,
                )

                classification_messages = create_classification_prompt(topics, request.content)
                logger.info(f"  → Prompt de clasificación enviado al LLM...")

                classification_response = await self.llm.chat_completion(
                    messages=classification_messages,
                    temperature=0.1,
                    max_tokens=50,
                    model=model_override,
                )

                raw_classification = classification_response.get("content", "general")
                classification = parse_classification_result(raw_classification, topics)
                logger.info(
                    f"  → Resultado clasificación: raw='{raw_classification}' → parsed='{classification}'"
                )
            else:
                logger.info("[ETAPA 4/7] CLASIFICACIÓN — Sin temas, clasificado como 'general'")

            # 5. Construir mensajes para el LLM según la clasificación
            if classification != "general":
                # === FLUJO RAG ===
                used_rag = True

                # Notificar al cliente que estamos generando plan de investigación
                logger.info(f"[ETAPA 5/7] RAG — Generando plan de investigación")
                yield chat_pb2.SendMessageResponse(
                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_RESEARCHING,
                )

                # Generar plan de investigación (3 sub-preguntas)
                research_plan_messages = create_research_plan_prompt(
                    request.content, classification
                )
                logger.info(f"  → Solicitando plan de investigación al LLM...")

                research_plan_response = await self.llm.chat_completion(
                    messages=research_plan_messages,
                    temperature=0.3,
                    max_tokens=300,
                    model=model_override,
                )

                raw_plan = research_plan_response.get("content", "")
                research_questions = parse_research_plan(raw_plan)

                # Fallback: si no se pudieron parsear las preguntas, usar la pregunta original
                if not research_questions:
                    logger.warning("  → No se pudo parsear el plan, usando pregunta original")
                    research_questions = [request.content]

                logger.info(
                    f"  → Plan de investigación ({len(research_questions)} preguntas): "
                    f"{research_questions}"
                )

                # Notificar al cliente que estamos buscando en documentos
                logger.info(f"  → Enviando evento RAG_START al cliente")
                yield chat_pb2.SendMessageResponse(
                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_RAG_START,
                )

                # Buscar contexto para cada sub-pregunta
                import asyncio

                async def search_question(question: str):
                    return await self.rag.search(
                        query=question,
                        user_id=request.user_id,
                        topic=classification,
                        limit=5,
                    )

                rag_results = await asyncio.gather(
                    *[search_question(q) for q in research_questions]
                )

                # Combinar contextos y fuentes de todas las búsquedas
                all_contexts = []
                all_sources = []
                seen_chunks = set()

                for result in rag_results:
                    for chunk in result.get("chunks", []):
                        # Deduplicar por contenido
                        chunk_key = chunk["content"][:100]
                        if chunk_key not in seen_chunks:
                            seen_chunks.add(chunk_key)
                            source = chunk["filename"]
                            if chunk.get("page"):
                                source += f" (p.{chunk['page']})"
                            all_sources.append(source)
                            all_contexts.append(
                                f"[Documento {len(all_contexts) + 1}: {source}]\n"
                                f"{chunk['content']}\n"
                            )

                sources = list(dict.fromkeys(all_sources))
                rag_context = "\n".join(all_contexts)

                logger.info(
                    f"  → RAG completado: {len(sources)} fuentes, "
                    f"{len(all_contexts)} chunks únicos, {len(rag_context)} chars de contexto"
                )
                if sources:
                    logger.info(f"  → Fuentes: {sources}")

                # Notificar al cliente que RAG terminó
                logger.info(f"  → Enviando evento RAG_DONE al cliente")
                yield chat_pb2.SendMessageResponse(
                    chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_RAG_DONE,
                )

                # Si no se encontró contexto, tratar como general
                if not rag_context:
                    logger.info("  → Sin contexto encontrado, respondiendo como general")
                    used_rag = False
                    system_message = create_general_system_message()
                else:
                    system_message = create_rag_system_message(rag_context, sources)
            else:
                # === FLUJO GENERAL (sin RAG) ===
                logger.info("[ETAPA 5/7] RAG — Omitido (clasificación: general)")
                system_message = create_general_system_message()

            # 6. Formatear mensajes para el LLM
            messages = self.llm.format_messages(
                system_message=system_message,
                conversation_history=history[:-1],
                user_message=request.content,
            )
            logger.info(f"[ETAPA 6/7] STREAMING — Iniciando streaming de respuesta ({len(messages)} mensajes en contexto)")

            # 7. Streamear respuesta del LLM
            token_count = 0
            async for chunk in self.llm.chat_completion_stream(
                messages=messages,
                model=model_override,
            ):
                if chunk["type"] == "content":
                    full_response += chunk["delta"]
                    token_count += 1
                    yield chat_pb2.SendMessageResponse(
                        chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_TOKEN,
                        token=chunk["delta"],
                    )
                elif chunk["type"] == "done":
                    logger.info(f"  → Streaming completado: ~{token_count} chunks enviados, {len(full_response)} chars")

            # Calcular tiempo de respuesta
            perf_end = time.perf_counter()
            response_time_ms = (perf_end - perf_start) * 1000

            # 8. Guardar respuesta del asistente en DB
            logger.info("[ETAPA 7/7] GUARDADO — Guardando respuesta en DB")
            assistant_message = await self.repo.create_message(
                conversation_id=request.conversation_id,
                role="assistant",
                content=full_response,
                used_rag=used_rag,
                sources=sources,
            )

            # Guardar log de rendimiento
            resolved_model = model_override or self.llm.model or "unknown"
            try:
                await self.repo.insert_performance_log(
                    question=request.content,
                    answer=full_response,
                    collection_name=classification if classification != "general" else None,
                    model=resolved_model,
                    response_time_ms=response_time_ms,
                    user_id=request.user_id,
                    conversation_id=request.conversation_id,
                    expected_answer=None,
                )
                logger.info(f"  → Performance log guardado: modelo={resolved_model}, tiempo={response_time_ms:.1f}ms")
            except Exception as perf_err:
                logger.warning(f"No se pudo guardar performance log: {perf_err}")

            # Auditoría
            await self.audit.send_event(
                action="message.sent",
                service="chat",
                user_id=request.user_id,
                detail={
                    "conversation_id": request.conversation_id,
                    "used_rag": used_rag,
                    "classification": classification,
                    "sources_count": len(sources),
                },
            )

            # 9. Enviar mensaje de finalización con metadata
            yield chat_pb2.SendMessageResponse(
                chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_DONE,
                message=chat_pb2.Message(
                    id=str(assistant_message["id"]),
                    conversation_id=request.conversation_id,
                    role=chat_pb2.MESSAGE_ROLE_ASSISTANT,
                    content=full_response,
                    used_rag=used_rag,
                    sources=sources,
                    created_at=datetime_to_proto_timestamp(assistant_message["created_at"]),
                ),
                used_rag=used_rag,
            )

            logger.info(
                f"{'='*60}\n"
                f"  CONSULTA COMPLETADA\n"
                f"  clasificación={classification}\n"
                f"  used_rag={used_rag}\n"
                f"  fuentes={len(sources)}\n"
                f"  respuesta={len(full_response)} chars\n"
                f"{'='*60}"
            )

        except Exception as e:
            logger.error(f"Error en SendMessage: {e}", exc_info=True)
            yield chat_pb2.SendMessageResponse(
                chunk_type=chat_pb2.SendMessageResponse.CHUNK_TYPE_ERROR,
                error=common_pb2.Error(code="INTERNAL_ERROR", message=str(e)),
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
                        message="Conversación no encontrada o no pertenece al usuario",
                    ),
                )

            # Paginación
            page = request.pagination.page if request.pagination.page > 0 else 1
            page_size = request.pagination.page_size if request.pagination.page_size > 0 else 100
            offset = (page - 1) * page_size

            # Obtener mensajes y total
            messages = await self.repo.get_messages(
                conversation_id=request.conversation_id, limit=page_size, offset=offset
            )

            total = await self.repo.count_messages(request.conversation_id)
            total_pages = (total + page_size - 1) // page_size

            # Construir response
            messages_proto = []
            for msg in messages:
                msg_proto = chat_pb2.Message(
                    id=str(msg["id"]),
                    conversation_id=str(msg["conversation_id"]),
                    role=self._string_to_message_role(msg["role"]),
                    content=msg["content"],
                    used_rag=msg["used_rag"],
                    sources=msg["sources"] or [],
                    created_at=datetime_to_proto_timestamp(msg["created_at"]),
                )
                messages_proto.append(msg_proto)

            pagination_response = common_pb2.PaginationResponse(
                page=page, page_size=page_size, total=total, total_pages=total_pages
            )

            logger.info(f"Obtenidos {len(messages_proto)} mensajes (total={total})")

            return chat_pb2.GetMessagesResponse(
                success=True, messages=messages_proto, pagination=pagination_response
            )

        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}", exc_info=True)
            return chat_pb2.GetMessagesResponse(
                success=False, error=common_pb2.Error(code="INTERNAL_ERROR", message=str(e))
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

            return chat_pb2.GetUserTopicsResponse(success=True, topics=topics)

        except Exception as e:
            logger.error(f"Error obteniendo temas: {e}", exc_info=True)
            return chat_pb2.GetUserTopicsResponse(
                success=False, error=common_pb2.Error(code="INTERNAL_ERROR", message=str(e))
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
            "tool": chat_pb2.MESSAGE_ROLE_TOOL,
        }
        return role_map.get(role.lower(), chat_pb2.MESSAGE_ROLE_UNSPECIFIED)
