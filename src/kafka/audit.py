"""
Audit Event Producer — Envía eventos de auditoría al topic audit.events.

Todos los servicios usan este módulo para registrar acciones de usuario.
Los eventos son consumidos por el Audit Consumer y persistidos en la tabla audit_log.
"""

from typing import Any, Optional

from src.kafka.producer import KafkaProducerManager
from src.shared.logging_utils import get_logger
from src.shared.utils import generate_id, now_utc

logger = get_logger(__name__)

AUDIT_TOPIC = "audit.events"


class AuditProducer:
    """
    Produce eventos de auditoría a Kafka.

    Diseñado para no fallar el servicio si Kafka no está disponible
    (los eventos se descartan con un log de warning).
    """

    def __init__(self) -> None:
        self._producer = KafkaProducerManager()

    async def send_event(
        self,
        action: str,
        service: str,
        user_id: Optional[str] = None,
        detail: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Envía un evento de auditoría.

        Args:
            action: Acción realizada (e.g. "user.register", "user.login")
            service: Servicio que originó el evento ("auth", "chat", "rag", "indexing")
            user_id: ID del usuario (puede ser None para acciones anónimas)
            detail: Contexto adicional como dict
            ip_address: IP del cliente
        """
        event = {
            "id": generate_id(),
            "action": action,
            "service": service,
            "user_id": user_id,
            "detail": detail or {},
            "ip_address": ip_address,
            "timestamp": now_utc().isoformat(),
        }

        try:
            await self._producer.send(AUDIT_TOPIC, value=event, key=user_id)
            logger.info(f"📤 Audit event enviado: {action} (service={service}, user_id={user_id})")
        except Exception as e:
            # Nunca debe fallar el servicio principal por un error de auditoría
            logger.error(f"Error enviando audit event '{action}': {e}")
