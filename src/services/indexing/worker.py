"""
Indexing Worker - Consumidor de Kafka que procesa documentos.

Consume mensajes de indexing.queue, procesa documentos y almacena en Qdrant.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from src.services.indexing.chunking import chunk_document
from src.services.indexing.database import IndexingRepository, JobStatus
from src.services.indexing.document_processor import process_document
from src.services.indexing.embeddings import EmbeddingsGenerator
from src.services.indexing.qdrant_manager import QdrantIndexer
from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class IndexingWorker:
    """
    Worker que consume trabajos de indexación desde Kafka.

    Flujo:
    1. Consume mensaje de Kafka
    2. Verifica que job no está cancelado
    3. Actualiza status a PROCESSING
    4. Lee y procesa el archivo
    5. Divide en chunks
    6. Genera embeddings
    7. Almacena en Qdrant
    8. Actualiza status a COMPLETED
    9. Commit offset de Kafka
    10. Limpia archivo temporal
    """

    def __init__(
        self,
        worker_id: int = 1,
        max_retries: int = 3,
    ):
        """
        Inicializa el worker.

        Args:
            worker_id: ID del worker (para logging)
            max_retries: Máximo de reintentos por job
        """
        self.worker_id = worker_id
        self.max_retries = max_retries
        self.running = False

        # Configuración de Kafka
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.topic = os.getenv("KAFKA_INDEXING_QUEUE", "indexing.queue")
        self.dlq_topic = os.getenv("KAFKA_INDEXING_DLQ", "indexing.dlq")
        self.consumer_group = os.getenv("KAFKA_CONSUMER_GROUP", "indexing-workers")

        # Configuración de chunking
        self.chunk_size = int(os.getenv("INDEXING_CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("INDEXING_CHUNK_OVERLAP", "200"))

        # Componentes
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.db: Optional[DatabaseManager] = None
        self.repo: Optional[IndexingRepository] = None
        self.embeddings: Optional[EmbeddingsGenerator] = None
        self.qdrant: Optional[QdrantIndexer] = None

        logger.info(f"Worker #{worker_id} inicializado")

    async def start(self) -> None:
        """Inicia el worker y sus dependencias."""
        logger.info(f"🚀 Iniciando worker #{self.worker_id}...")

        try:
            # Conectar a base de datos
            self.db = DatabaseManager()
            await self.db.connect()
            await self.db.init_schema()
            self.repo = IndexingRepository(self.db)
            logger.info("✅ Conectado a PostgreSQL")

            # Inicializar generador de embeddings
            self.embeddings = EmbeddingsGenerator(
                batch_size=100,
                max_retries=3,
            )
            logger.info("✅ Embeddings generator inicializado")

            # Conectar a Qdrant
            self.qdrant = QdrantIndexer()
            self.qdrant.connect()
            logger.info("✅ Conectado a Qdrant")

            # Crear consumer de Kafka
            self.consumer = AIOKafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                enable_auto_commit=False,  # Commit manual
                auto_offset_reset="earliest",
                max_poll_interval_ms=300000,  # 5 minutos
                session_timeout_ms=30000,  # 30 segundos
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
            )

            await self.consumer.start()
            logger.info(f"✅ Kafka consumer iniciado: {self.topic}")

            self.running = True
            logger.info(f"✅ Worker #{self.worker_id} listo para procesar jobs")

            # Iniciar loop de consumo
            await self.consume_loop()

        except Exception as e:
            logger.error(f"Error iniciando worker: {e}", exc_info=True)
            await self.stop()
            raise

    async def stop(self) -> None:
        """Detiene el worker y limpia recursos."""
        logger.info(f"🛑 Deteniendo worker #{self.worker_id}...")

        self.running = False

        if self.consumer:
            await self.consumer.stop()

        if self.qdrant:
            self.qdrant.close()

        if self.db:
            await self.db.disconnect()

        logger.info(f"✅ Worker #{self.worker_id} detenido")

    async def consume_loop(self) -> None:
        """Loop principal de consumo de mensajes."""
        logger.info(f"Worker #{self.worker_id} esperando mensajes...")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    await self.process_message(message)
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}", exc_info=True)
                    # No hacer commit para que Kafka reintente
                    continue

        except asyncio.CancelledError:
            logger.info(f"Worker #{self.worker_id} cancelado")
        except Exception as e:
            logger.error(f"Error en consume loop: {e}", exc_info=True)
            raise

    async def process_message(self, message) -> None:
        """
        Procesa un mensaje de Kafka.

        Args:
            message: Mensaje de Kafka con job de indexación
        """
        data = message.value
        job_id = data.get("job_id")

        logger.info(f"📨 Worker #{self.worker_id} procesando job {job_id}")

        try:
            # Verificar que el job existe y no está cancelado
            job = await self.repo.get_job(job_id)

            if not job:
                logger.warning(f"Job {job_id} no encontrado en DB, skipping")
                await self.consumer.commit()
                return

            if job["status"] == JobStatus.CANCELLED:
                logger.info(f"Job {job_id} cancelado, skipping")
                await self.consumer.commit()
                return

            if job["status"] == JobStatus.COMPLETED:
                logger.info(f"Job {job_id} ya completado, skipping")
                await self.consumer.commit()
                return

            # Procesar el job
            success = await self.process_job(data)

            if success:
                # Commit offset solo si fue exitoso
                await self.consumer.commit()
                logger.info(f"✅ Job {job_id} procesado y committed")
            else:
                # No commit, Kafka reintentará
                logger.warning(f"Job {job_id} falló, no committing (Kafka reintentará)")

        except Exception as e:
            logger.error(f"Error en process_message para job {job_id}: {e}", exc_info=True)

            # Manejar reintentos
            retry_count = data.get("retry_count", 0)

            if retry_count >= self.max_retries:
                # Enviar a DLQ
                await self.send_to_dlq(data, str(e))
                # Marcar job como failed
                await self.repo.mark_failed(job_id, f"Max reintentos excedidos: {str(e)}")
                # Commit para sacarlo de la cola
                await self.consumer.commit()
            else:
                # No commit, dejar que Kafka reintente
                pass

            raise

    async def process_job(self, data: Dict[str, Any]) -> bool:
        """
        Procesa un trabajo de indexación completo.

        Args:
            data: Datos del mensaje de Kafka

        Returns:
            True si fue exitoso, False si hubo error
        """
        job_id = data["job_id"]
        user_id = data["user_id"]
        file_path = Path(data["file_path"])
        filename = data["filename"]
        mime_type = data["mime_type"]
        topic = data["topic"]
        metadata = data.get("metadata", {})

        try:
            # 1. Actualizar status a PROCESSING
            await self.repo.update_status(job_id, JobStatus.PROCESSING)
            logger.info(f"Job {job_id} → PROCESSING")

            # 2. Verificar que el archivo existe
            if not file_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

            # 3. Extraer texto del documento
            logger.info(f"Extrayendo texto de {filename}...")
            doc_result = process_document(file_path, mime_type)
            text = doc_result["text"]
            doc_metadata = doc_result["metadata"]

            if not text or not text.strip():
                raise ValueError("Documento sin texto extraíble")

            logger.info(
                f"Texto extraído: {len(text)} caracteres "
                f"({doc_metadata.get('pages', 'N/A')} páginas)"
            )

            # 4. Dividir en chunks
            logger.info(
                f"Dividiendo en chunks (size={self.chunk_size}, overlap={self.chunk_overlap})..."
            )
            chunks_objects = chunk_document(
                text=text,
                document_metadata={
                    **doc_metadata,
                    **metadata,
                    "source": filename,
                    "topic": topic,
                },
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            if not chunks_objects:
                raise ValueError("No se generaron chunks del documento")

            chunks_text = [chunk.text for chunk in chunks_objects]
            logger.info(f"✅ {len(chunks_text)} chunks creados")

            # 5. Generar embeddings
            logger.info(f"Generando embeddings...")
            embeddings = await self.embeddings.generate_for_chunks(
                chunks_text,
                show_progress=True,
            )

            if len(embeddings) != len(chunks_text):
                raise ValueError(
                    f"Mismatch: {len(chunks_text)} chunks vs {len(embeddings)} embeddings"
                )

            # 6. Indexar en Qdrant
            logger.info(f"Indexando en Qdrant...")
            indexed_count = self.qdrant.index_chunks(
                chunks=chunks_text,
                embeddings=embeddings,
                user_id=user_id,
                job_id=job_id,
                filename=filename,
                topic=topic,
                metadata={
                    **doc_metadata,
                    "file_size": metadata.get("file_size", 0),
                },
            )

            logger.info(f"✅ {indexed_count} chunks indexados en Qdrant")

            # 7. Actualizar job como completado
            await self.repo.mark_completed(job_id, len(chunks_text))
            logger.info(f"✅ Job {job_id} → COMPLETED")

            # 8. Limpiar archivo temporal
            try:
                file_path.unlink()
                # Intentar limpiar directorios vacíos
                if file_path.parent.exists() and not any(file_path.parent.iterdir()):
                    file_path.parent.rmdir()
                logger.info(f"🗑️  Archivo temporal eliminado: {file_path}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal: {e}")

            logger.info(
                f"🎉 Job {job_id} completado exitosamente: " f"{len(chunks_text)} chunks indexados"
            )

            return True

        except Exception as e:
            logger.error(f"Error procesando job {job_id}: {e}", exc_info=True)

            # Actualizar job como failed
            error_msg = f"{type(e).__name__}: {str(e)}"
            await self.repo.mark_failed(job_id, error_msg)

            return False

    async def send_to_dlq(self, original_message: Dict[str, Any], error: str) -> None:
        """
        Envía un mensaje fallido a la Dead Letter Queue.

        Args:
            original_message: Mensaje original que falló
            error: Descripción del error
        """
        try:
            from src.gateway.kafka_producer import indexing_producer

            await indexing_producer.publish_to_dlq(
                job_id=original_message["job_id"],
                original_message=original_message,
                error=error,
            )

        except Exception as e:
            logger.error(f"Error enviando a DLQ: {e}", exc_info=True)


async def run_worker(worker_id: int = 1) -> None:
    """
    Función principal para ejecutar un worker.

    Args:
        worker_id: ID del worker
    """
    worker = IndexingWorker(worker_id=worker_id)

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Interrupción recibida, deteniendo worker...")
    except Exception as e:
        logger.error(f"Error fatal en worker: {e}", exc_info=True)
    finally:
        await worker.stop()


if __name__ == "__main__":
    """Ejecutar worker standalone."""
    import sys

    worker_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    logger.info(f"🚀 Iniciando Indexing Worker #{worker_id}")

    try:
        asyncio.run(run_worker(worker_id))
    except KeyboardInterrupt:
        logger.info("Worker detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
