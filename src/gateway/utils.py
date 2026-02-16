"""Utilidades para conversión entre protobuf y modelos Pydantic."""

from datetime import datetime, timezone

from src.gateway.models import UserResponse
from src.generated import common_pb2


def proto_timestamp_to_iso(timestamp: common_pb2.Timestamp) -> str:
    """
    Convierte un Timestamp de protobuf a string ISO 8601.

    Args:
        timestamp: Timestamp de protobuf

    Returns:
        String en formato ISO 8601
    """
    if not timestamp or not hasattr(timestamp, "seconds"):
        # Si no hay timestamp válido, retornar fecha actual
        return datetime.now(timezone.utc).isoformat()

    dt = datetime.fromtimestamp(timestamp.seconds, tz=timezone.utc)
    return dt.isoformat()


def proto_user_to_response(user: common_pb2.User) -> UserResponse:
    """
    Convierte un User de protobuf a UserResponse de Pydantic.

    Args:
        user: Usuario en formato protobuf (common.v1.User)

    Returns:
        UserResponse con los datos del usuario
    """
    # Mapear rol de enum a string
    role_map = {
        common_pb2.USER_ROLE_USER: "user",
        common_pb2.USER_ROLE_ADMIN: "admin",
        common_pb2.USER_ROLE_UNSPECIFIED: "user",
    }

    # Verificar que el timestamp tenga el formato correcto
    try:
        created_at_str = proto_timestamp_to_iso(user.created_at)
    except Exception as e:
        # Fallback a fecha actual si hay error
        created_at_str = datetime.now(timezone.utc).isoformat()

    return UserResponse(
        user_id=user.id,  # El proto usa 'id', no 'user_id'
        email=user.email,
        full_name=user.name,  # El proto usa 'name', en API REST es 'full_name'
        created_at=created_at_str,
        role=role_map.get(user.role, "user"),
    )
