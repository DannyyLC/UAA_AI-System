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

def datetime_to_proto_timestamp(dt: datetime) -> common_pb2.Timestamp:
    """
    Convierte un datetime a common.v1.Timestamp del proto.
    """
    ts = dt.timestamp()
    return common_pb2.Timestamp(
        seconds=int(ts),
        nanos=int((ts % 1) * 1e9)
    )

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
