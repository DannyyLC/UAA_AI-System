"""
Kafka Producer para API Gateway.

Publica trabajos de indexación en la cola de Kafka.
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class IndexingProducer:
    """
    Producer de Kafka para encolar trabajos de indexación.
    
    Singleton que mantiene una conexión persistente.
    """
    
    _instance: Optional["IndexingProducer"] = None
    _producer: Optional[AIOKafkaProducer] = None
    
    def __new__(cls) -> "IndexingProducer":
        """Singleton — una sola instancia."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializa configuración pero no conecta."""
        if not hasattr(self, "_initialized"):
            self.bootstrap_servers = os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
            )
            self.topic = os.getenv("KAFKA_INDEXING_QUEUE", "indexing.queue")
            self._initialized = True
    
    async def connect(self) -> None:
        """Establece conexión con Kafka."""
        if self._producer is not None:
            logger.debug("Kafka producer ya conectado")
            return
        
        try:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                compression_type="gzip",
                acks="all",  # Esperar confirmación de todos los brokers
                retries=3,
                max_in_flight_requests_per_connection=1,  # Garantizar orden
            )
            await self._producer.start()
            logger.info(f"Kafka producer conectado: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Error conectando Kafka producer: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Cierra la conexión con Kafka."""
        if self._producer:
            await self._producer.stop()
            self._producer = None
            IndexingProducer._instance = None
            logger.info("Kafka producer desconectado")
    
    async def publish_indexing_job(
        self,
        job_id: str,
        user_id: str,
        file_path: str,
        filename: str,
        mime_type: str,
        topic: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publica un trabajo de indexación en Kafka.
        
        Args:
            job_id: ID único del trabajo (UUID)
            user_id: ID del usuario
            file_path: Ruta completa al archivo en disco
            filename: Nombre original del archivo
            mime_type: Tipo MIME del archivo
            topic: Tema académico
            metadata: Metadatos adicionales opcionales
            
        Returns:
            True si se publicó exitosamente
        """
        if not self._producer:
            await self.connect()
        
        message = {
            "job_id": job_id,
            "user_id": user_id,
            "file_path": file_path,
            "filename": filename,
            "mime_type": mime_type,
            "topic": topic,
            "metadata": metadata or {},
            "retry_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            # Usar job_id como key para garantizar orden por job
            future = await self._producer.send(
                self.topic,
                value=message,
                key=job_id,
            )
            
            # Esperar confirmación
            record_metadata = await future
            
            logger.info(
                f"📤 Job {job_id} publicado en Kafka "
                f"(topic={record_metadata.topic}, "
                f"partition={record_metadata.partition}, "
                f"offset={record_metadata.offset})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error publicando job {job_id} en Kafka: {e}", exc_info=True)
            return False
    
    async def publish_retry(
        self,
        job_id: str,
        user_id: str,
        file_path: str,
        filename: str,
        mime_type: str,
        topic: str,
        retry_count: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Publica un trabajo para reintento después de un error temporal.
        
        Args:
            job_id: ID del trabajo
            user_id: ID del usuario
            file_path: Ruta al archivo
            filename: Nombre del archivo
            mime_type: Tipo MIME
            topic: Tema académico
            retry_count: Número de reintentos realizados
            metadata: Metadatos adicionales
            
        Returns:
            True si se publicó exitosamente
        """
        if not self._producer:
            await self.connect()
        
        message = {
            "job_id": job_id,
            "user_id": user_id,
            "file_path": file_path,
            "filename": filename,
            "mime_type": mime_type,
            "topic": topic,
            "metadata": metadata or {},
            "retry_count": retry_count,
            "retry_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            future = await self._producer.send(
                self.topic,
                value=message,
                key=job_id,
            )
            
            await future
            
            logger.warning(
                f"🔄 Job {job_id} reencolado para reintento #{retry_count}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error reencolando job {job_id}: {e}", exc_info=True)
            return False
    
    async def publish_to_dlq(
        self,
        job_id: str,
        original_message: Dict[str, Any],
        error: str,
    ) -> bool:
        """
        Publica un trabajo fallido en la Dead Letter Queue.
        
        Args:
            job_id: ID del trabajo
            original_message: Mensaje original que falló
            error: Descripción del error
            
        Returns:
            True si se publicó exitosamente
        """
        if not self._producer:
            await self.connect()
        
        dlq_topic = os.getenv("KAFKA_INDEXING_DLQ", "indexing.dlq")
        
        message = {
            "job_id": job_id,
            "original_message": original_message,
            "error": error,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            future = await self._producer.send(
                dlq_topic,
                value=message,
                key=job_id,
            )
            
            await future
            
            logger.error(
                f"💀 Job {job_id} enviado a DLQ: {error}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error enviando a DLQ job {job_id}: {e}", exc_info=True)
            return False


# Instancia global (singleton)
indexing_producer = IndexingProducer()
