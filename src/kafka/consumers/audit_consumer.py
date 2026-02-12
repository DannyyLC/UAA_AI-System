"""
Audit Consumer - Consume eventos de auditoría y los persiste en PostgreSQL.

Este consumer escucha el topic audit.events y guarda todos los eventos
en la tabla audit_log para trazabilidad completa del sistema.
"""

import asyncio
import json
import os
from typing import Dict, Any
from datetime import datetime

from src.kafka.consumer import KafkaConsumerManager
from src.kafka.config import kafka_config
from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class AuditEventConsumer:
    """
    Consumer de eventos de auditoría.
    
    Características:
    - Consume del topic audit.events
    - Persiste en tabla audit_log de PostgreSQL
    - Manejo de errores sin perder mensajes
    - Procesamiento idempotente (puede procesar el mismo mensaje múltiples veces)
    """
    
    def __init__(self):
        """Inicializa el consumer de auditoría."""
        self.consumer: KafkaConsumerManager = None
        self.db = DatabaseManager()
        
    async def start(self):
        """Inicia el consumer y la conexión a la base de datos."""
        logger.info("Iniciando Audit Event Consumer...")
        
        # Inicializar conexión a PostgreSQL
        try:
            await self.db.connect()
            logger.info("Conexión a PostgreSQL establecida")
        except Exception as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            raise
        
        # Inicializar consumer de Kafka
        self.consumer = KafkaConsumerManager(
            topics=[kafka_config.audit_events_topic],
            group_id=kafka_config.audit_consumer_group,
            handler=self._handle_audit_event
        )
        
        await self.consumer.start()
        logger.info("Audit Event Consumer iniciado correctamente")
    
    async def stop(self):
        """Detiene el consumer y cierra conexiones."""
        logger.info("Deteniendo Audit Event Consumer...")
        
        if self.consumer:
            await self.consumer.stop()
        
        if self.db:
            await self.db.disconnect()
            logger.info("Conexión a PostgreSQL cerrada")
        
        logger.info("Audit Event Consumer detenido")
    
    async def _handle_audit_event(
        self,
        value: Dict[str, Any],
        topic: str,
        partition: int,
        offset: int
    ):
        """
        Procesa un evento de auditoría y lo guarda en PostgreSQL.
        
        Args:
            value: Evento de auditoría con estructura:
                   {
                       "id": "uuid",
                       "action": "user.login",
                       "service": "auth",
                       "user_id": "uuid" | None,
                       "detail": {},
                       "ip_address": "127.0.0.1" | None,
                       "timestamp": "2026-02-11T10:30:00Z"
                   }
            topic: Nombre del topic
            partition: Partición del mensaje
            offset: Offset del mensaje
        """
        try:
            logger.info(f"Evento recibido de Kafka - Topic: {topic}, Partition: {partition}, Offset: {offset}")
            
            # Extraer datos del evento
            event_id = value.get("id")
            action = value.get("action")
            service = value.get("service")
            user_id = value.get("user_id")
            detail = value.get("detail")
            ip_address = value.get("ip_address")
            timestamp_str = value.get("timestamp")
            
            logger.info(f"Procesando evento: {action} (service={service}, user_id={user_id})")
            
            # Validaciones básicas
            if not action or not service:
                logger.warning(f"Evento inválido recibido (sin action/service): {value}")
                return
            
            # Convertir timestamp
            try:
                if timestamp_str:
                    created_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    created_at = datetime.utcnow()
            except Exception as e:
                logger.warning(f"Error parseando timestamp '{timestamp_str}': {e}")
                created_at = datetime.utcnow()
            
            # Insertar en PostgreSQL
            # Convertir detail a JSON string para JSONB
            detail_json = json.dumps(detail) if detail else None
            
            await self.db.execute(
                """
                INSERT INTO audit_log (id, user_id, action, service, detail, ip_address, created_at)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                ON CONFLICT (id) DO NOTHING
                """,
                event_id,
                user_id,
                action,
                service,
                detail_json,  # Pasar como string JSON
                ip_address,
                created_at
            )
            
            logger.info(
                f"Evento de auditoría guardado: {action} "
                f"(service={service}, user_id={user_id}, event_id={event_id})"
            )
            
        except Exception as e:
            logger.error(
                f"Error procesando evento de auditoría "
                f"(topic={topic}, offset={offset}): {e}",
                exc_info=True
            )
            # Re-lanzar para que Kafka no haga commit del offset
            raise
    
    async def run(self):
        """Ejecuta el consumer indefinidamente."""
        try:
            await self.start()
            
            # Mantener el consumer corriendo
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupción recibida, cerrando...")
        except Exception as e:
            logger.error(f"Error fatal en Audit Consumer: {e}", exc_info=True)
            raise
        finally:
            await self.stop()


async def main():
    """Función principal para correr el consumer."""
    consumer = AuditEventConsumer()
    await consumer.run()


if __name__ == "__main__":
    asyncio.run(main())
