"""
Utilidades generales compartidas entre servicios.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from google.protobuf.timestamp_pb2 import Timestamp as ProtoTimestamp

from src.generated import common_pb2


def generate_id() -> str:
    """Genera un UUID v4 como string."""
    return str(uuid.uuid4())


def now_utc() -> datetime:
    """Retorna la fecha/hora actual en UTC."""
    return datetime.now(timezone.utc)


def datetime_to_proto_timestamp(dt: datetime | str) -> common_pb2.Timestamp:
    """
    Convierte un datetime o string ISO a common.v1.Timestamp del proto.

    Args:
        dt: datetime object o string en formato ISO 8601

    Returns:
        common_pb2.Timestamp

    Raises:
        ValueError: Si el input no puede ser convertido a timestamp
    """
    try:
        # Si es un string, convertirlo a datetime
        if isinstance(dt, str):
            # Intentar parsear el string ISO 8601
            # Formatos comunes: "2024-03-25T10:30:00Z" o "2024-03-25T10:30:00.123456+00:00"
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        elif not isinstance(dt, datetime):
            raise ValueError(f"Expected datetime or str, got {type(dt).__name__}")

        ts = dt.timestamp()
        return common_pb2.Timestamp(seconds=int(ts), nanos=int((ts % 1) * 1e9))
    except (ValueError, AttributeError, TypeError) as e:
        # En caso de error, loggear y usar timestamp actual como fallback
        from src.shared.logging_utils import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error convirtiendo a proto timestamp: {e}, input={dt!r}, usando timestamp actual")
        now = datetime.now(timezone.utc)
        ts = now.timestamp()
        return common_pb2.Timestamp(seconds=int(ts), nanos=int((ts % 1) * 1e9))


def proto_timestamp_to_datetime(seconds: int, nanos: int = 0) -> datetime:
    """
    Convierte seconds/nanos del proto a un datetime UTC.
    """
    ts = seconds + nanos / 1e9
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def paginate(total: int, page: int, page_size: int) -> dict:
    """
    Calcula los datos de paginación.

    Returns:
        dict con page, page_size, total, total_pages
    """
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def sanitize_string(value: Optional[str], max_length: int = 500) -> str:
    """Limpia y trunca un string."""
    if not value:
        return ""
    return value.strip()[:max_length]
