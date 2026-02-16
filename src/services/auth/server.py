"""
Auth Service gRPC Server — Entry point.

Levanta el servidor gRPC en el puerto configurado (default: 50051).
Inicializa las dependencias: PostgreSQL, Kafka, JWT Manager.

Ejecución:
    python -m src.services.auth.server
"""

import asyncio
import signal

import grpc
from grpc import aio as grpc_aio

from src.generated import auth_pb2_grpc
from src.kafka.audit import AuditProducer
from src.kafka.producer import KafkaProducerManager
from src.services.auth.database import AuthRepository
from src.services.auth.handlers import AuthServiceHandler
from src.services.auth.jwt_manager import JWTManager
from src.shared.configuration import settings
from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


async def serve() -> None:
    """Inicializa dependencias y arranca el servidor gRPC."""

    # --- Base de datos ---
    db = DatabaseManager()
    await db.connect()
    await db.init_schema()
    logger.info("PostgreSQL conectado y schema verificado")

    # --- Kafka (no bloquea si no está disponible) ---
    kafka = KafkaProducerManager()
    try:
        await kafka.start()
    except Exception as e:
        logger.warning(
            f"Kafka no disponible ({e}). "
            "Los eventos de auditoría serán descartados hasta que Kafka esté activo."
        )

    # --- Dependencias del servicio ---
    repo = AuthRepository(db)
    jwt_manager = JWTManager()
    audit = AuditProducer()

    # --- Servidor gRPC ---
    server = grpc_aio.server()
    auth_pb2_grpc.add_AuthServiceServicer_to_server(
        AuthServiceHandler(repo, jwt_manager, audit),
        server,
    )

    port = settings.auth_grpc_port
    server.add_insecure_port(f"[::]:{port}")

    await server.start()
    logger.info(f"Auth Service escuchando en [::]:{port}")

    # --- Graceful shutdown ---
    shutdown_event = asyncio.Event()

    def _signal_handler(sig: signal.Signals) -> None:
        logger.info(f"Señal {sig.name} recibida, iniciando apagado...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler, sig)

    # Esperar hasta señal de apagado
    await shutdown_event.wait()

    # Apagar limpiamente
    logger.info("Deteniendo Auth Service...")
    await server.stop(grace=5)
    await kafka.stop()
    await db.disconnect()
    logger.info("Auth Service detenido")


if __name__ == "__main__":
    asyncio.run(serve())
