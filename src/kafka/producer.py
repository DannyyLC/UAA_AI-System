"""
Kafka Producer Manager — Singleton para producción asíncrona de mensajes.

Usado por todos los servicios para enviar eventos a Kafka.
"""

import json
from typing import Any, Optional

from aiokafka import AIOKafkaProducer

from src.shared.configuration import settings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class KafkaProducerManager:
    """
    Singleton que gestiona un AIOKafkaProducer compartido.

    Uso:
        kafka = KafkaProducerManager()
        await kafka.start()
        await kafka.send("audit.events", {"action": "user.login"}, key="user-123")
        await kafka.stop()
    """

    _instance: Optional["KafkaProducerManager"] = None
    _producer: Optional[AIOKafkaProducer] = None

    def __new__(cls) -> "KafkaProducerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def start(self) -> None:
        """Inicia el producer de Kafka."""
        if self._producer is not None:
            logger.debug("Kafka producer ya iniciado")
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer iniciado")

    async def stop(self) -> None:
        """Detiene el producer de Kafka."""
        if self._producer:
            await self._producer.stop()
            self._producer = None
            KafkaProducerManager._instance = None
            logger.info("Kafka producer detenido")

    @property
    def is_connected(self) -> bool:
        return self._producer is not None

    async def send(
        self,
        topic: str,
        value: dict[str, Any],
        key: Optional[str] = None,
    ) -> None:
        """Envía un mensaje a un topic de Kafka."""
        if self._producer is None:
            logger.warning(f"Kafka producer no iniciado, evento descartado: {topic}")
            return

        try:
            await self._producer.send_and_wait(topic, value=value, key=key)
            logger.debug(f"Mensaje enviado a {topic}")
        except Exception as e:
            logger.error(f"Error enviando mensaje a {topic}: {e}")
            raise
