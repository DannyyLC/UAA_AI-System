"""
Chat Service gRPC Server - Entry point.

Levanta el servidor gRPC en el puerto configurado (default: 50052).
Inicializa las dependencias:
- PostgreSQL
- Qdrant
- LiteLLM
- Kafka
- RAG Retriever

Ejecución:
    python -m src.services.chat.server
"""

import asyncio
import signal

import grpc
from grpc import aio as grpc_aio

from src.generated import chat_pb2_grpc
from src.services.chat.handlers import ChatServiceHandler
from src.services.chat.database import ChatRepository
from src.services.chat.litellm_client import LiteLLMClient
from src.services.chat.rag.qdrant_client import QdrantManager
from src.services.chat.rag.retrieval import RAGRetriever
from src.kafka.audit import AuditProducer
from src.shared.database import DatabaseManager
from src.shared.configuration import settings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


async def serve() -> None:
    """Inicializa dependencias y arranca el servidor gRPC."""

    # --- Base de datos ---
    db = DatabaseManager()
    await db.connect()
    await db.init_schema()
    logger.info("PostgreSQL conectado y schema verificado")

    # --- Qdrant ---
    qdrant = QdrantManager()
    try:
        qdrant.connect()
        logger.info("Qdrant conectado")
    except Exception as e:
        logger.error(f"Error conectando a Qdrant: {e}")
        logger.warning("Chat Service iniciando sin Qdrant (RAG no disponible)")

    # --- Dependencias del servicio ---
    repo = ChatRepository(db)
    llm_client = LiteLLMClient(
        model=settings.llm_model,
        temperature=0.7
    )
    rag_retriever = RAGRetriever(qdrant)
    audit = AuditProducer()

    # --- Servidor gRPC ---
    server = grpc_aio.server()
    chat_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatServiceHandler(repo, llm_client, rag_retriever, audit),
        server,
    )

    listen_addr = f"[::]:{settings.chat_grpc_port}"
    server.add_insecure_port(listen_addr)

    logger.info(f"Chat Service escuchando en {listen_addr}")
    await server.start()

    # --- Graceful shutdown ---
    async def shutdown(sig):
        logger.info(f"Señal {sig} recibida, cerrando servidor...")
        await server.stop(grace=5)
        await db.disconnect()
        qdrant.close()
        logger.info("Chat Service cerrado correctamente")

    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        loop.add_signal_handler(
            getattr(signal, sig_name),
            lambda s=sig_name: asyncio.create_task(shutdown(s)),
        )

    await server.wait_for_termination()


def main():
    """Entry point principal."""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Servidor interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
