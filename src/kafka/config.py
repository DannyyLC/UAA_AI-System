"""Configuración de Kafka."""

import os
from typing import List
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class KafkaConfig:
    """Configuración centralizada de Kafka."""
    
    def __init__(self):
        """Inicializa la configuración de Kafka desde variables de entorno."""
        # Bootstrap servers
        self.bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS", 
            "localhost:9092"
        ).split(",")
        
        # Topics
        self.indexing_queue_topic = "indexing.queue"
        self.indexing_dlq_topic = "indexing.dlq"
        self.audit_events_topic = "audit.events"
        
        # Consumer groups
        self.audit_consumer_group = "audit-consumer-group"
        self.indexing_worker_group = "indexing-worker-group"
        
        # Producer settings
        self.producer_acks = "all"  # Esperar confirmación de todos los replicas
        self.producer_retries = 3
        self.producer_max_in_flight = 5
        self.producer_compression_type = "gzip"
        
        # Consumer settings
        self.consumer_auto_offset_reset = "earliest"  # Leer desde el principio si no hay offset
        self.consumer_enable_auto_commit = False  # Commit manual para garantizar procesamiento
        self.consumer_max_poll_records = 10
        self.consumer_session_timeout_ms = 30000
        self.consumer_heartbeat_interval_ms = 10000
        
        # Retry settings
        self.max_retries = 3
        self.retry_backoff_ms = 1000
        
        logger.info(f"Kafka configurado: {self.bootstrap_servers}")
    
    def get_bootstrap_servers_str(self) -> str:
        """Retorna bootstrap servers como string."""
        return ",".join(self.bootstrap_servers)
    
    def get_producer_config(self) -> dict:
        """Retorna configuración para producer."""
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "acks": self.producer_acks,
            "retries": self.producer_retries,
            "max_in_flight_requests_per_connection": self.producer_max_in_flight,
            "compression_type": self.producer_compression_type,
            "enable_idempotence": True,  # Evitar duplicados
        }
    
    def get_consumer_config(self, group_id: str) -> dict:
        """
        Retorna configuración para consumer.
        
        Args:
            group_id: ID del grupo de consumidores
            
        Returns:
            Diccionario con configuración del consumer
        """
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "group_id": group_id,
            "auto_offset_reset": self.consumer_auto_offset_reset,
            "enable_auto_commit": self.consumer_enable_auto_commit,
            "max_poll_records": self.consumer_max_poll_records,
            "session_timeout_ms": self.consumer_session_timeout_ms,
            "heartbeat_interval_ms": self.consumer_heartbeat_interval_ms,
        }


# Instancia global de configuración
kafka_config = KafkaConfig()
