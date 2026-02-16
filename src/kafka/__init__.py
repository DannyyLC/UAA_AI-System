"""
Kafka module — Producer y consumidores compartidos.
"""

from src.kafka.audit import AuditProducer
from src.kafka.producer import KafkaProducerManager

__all__ = ["KafkaProducerManager", "AuditProducer"]
