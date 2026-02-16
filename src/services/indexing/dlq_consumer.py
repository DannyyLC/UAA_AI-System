"""
Dead Letter Queue Consumer - Procesa mensajes fallidos.

Consume mensajes de indexing.dlq y los registra para análisis.
No reintenta automáticamente.
"""

import os
import json
import asyncio
from typing import Optional
from aiokafka import AIOKafkaConsumer
from datetime import datetime, timezone

from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class DLQConsumer:
    """
    Consumer de Dead Letter Queue.
    
    Registra mensajes fallidos en audit log para análisis posterior.
    """
    
    def __init__(self):
        """Inicializa el DLQ consumer."""
        self.bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
        )
        self.topic = os.getenv("KAFKA_INDEXING_DLQ", "indexing.dlq")
        self.consumer_group = "dlq-consumer"
        
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.db: Optional[DatabaseManager] = None
        self.running = False
        
        logger.info("DLQ Consumer inicializado")
    
    async def start(self) -> None:
        """Inicia el consumer."""
        logger.info("🚀 Iniciando DLQ Consumer...")
        
        try:
            # Conectar a base de datos
            self.db = DatabaseManager()
            await self.db.connect()
            logger.info("✅ Conectado a PostgreSQL")
            
            # Crear consumer de Kafka
            self.consumer = AIOKafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.consumer_group,
                enable_auto_commit=True,
                auto_offset_reset="earliest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            
            await self.consumer.start()
            logger.info(f"✅ DLQ Consumer iniciado: {self.topic}")
            
            self.running = True
            
            # Iniciar loop de consumo
            await self.consume_loop()
            
        except Exception as e:
            logger.error(f"Error iniciando DLQ consumer: {e}", exc_info=True)
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Detiene el consumer."""
        logger.info("🛑 Deteniendo DLQ Consumer...")
        
        self.running = False
        
        if self.consumer:
            await self.consumer.stop()
        
        if self.db:
            await self.db.disconnect()
        
        logger.info("✅ DLQ Consumer detenido")
    
    async def consume_loop(self) -> None:
        """Loop principal de consumo."""
        logger.info("DLQ Consumer esperando mensajes fallidos...")
        
        try:
            async for message in self.consumer:
                if not self.running:
                    break
                
                try:
                    await self.process_dlq_message(message)
                except Exception as e:
                    logger.error(f"Error procesando mensaje DLQ: {e}", exc_info=True)
        
        except asyncio.CancelledError:
            logger.info("DLQ Consumer cancelado")
        except Exception as e:
            logger.error(f"Error en consume loop: {e}", exc_info=True)
    
    async def process_dlq_message(self, message) -> None:
        """
        Procesa un mensaje de la DLQ.
        
        Args:
            message: Mensaje de Kafka
        """
        data = message.value
        job_id = data.get("job_id")
        error = data.get("error")
        original_message = data.get("original_message", {})
        failed_at = data.get("failed_at")
        
        logger.error(
            f"💀 DLQ: Job {job_id} falló permanentemente\n"
            f"   Error: {error}\n"
            f"   Fallado en: {failed_at}\n"
            f"   Usuario: {original_message.get('user_id')}\n"
            f"   Archivo: {original_message.get('filename')}"
        )
        
        # Registrar en audit log
        try:
            await self.db.execute(
                """
                INSERT INTO audit_log (
                    user_id, action, service, detail, created_at
                )
                VALUES ($1::uuid, $2, $3, $4, $5)
                """,
                original_message.get("user_id"),
                "indexing.dlq",
                "indexing",
                json.dumps({
                    "job_id": job_id,
                    "error": error,
                    "filename": original_message.get("filename"),
                    "topic": original_message.get("topic"),
                    "retry_count": original_message.get("retry_count", 0),
                }),
                datetime.now(timezone.utc),
            )
            
            logger.info(f"📝 Mensaje DLQ registrado en audit log")
            
        except Exception as e:
            logger.error(f"Error registrando en audit log: {e}")


async def run_dlq_consumer() -> None:
    """Función principal para ejecutar el DLQ consumer."""
    consumer = DLQConsumer()
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Interrupción recibida, deteniendo DLQ consumer...")
    except Exception as e:
        logger.error(f"Error fatal en DLQ consumer: {e}", exc_info=True)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    """Ejecutar DLQ consumer standalone."""
    logger.info("🚀 Iniciando DLQ Consumer")
    
    try:
        asyncio.run(run_dlq_consumer())
    except KeyboardInterrupt:
        logger.info("DLQ Consumer detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
