"""
Kafka module — Producer y consumidores compartidos.
"""

from src.kafka.producer import KafkaProducerManager
from src.kafka.audit import AuditProducer

__all__ = ["KafkaProducerManager", "AuditProducer"]
