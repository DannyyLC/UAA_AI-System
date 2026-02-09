"""
Shared module — Código compartido entre todos los microservicios.
"""

from src.shared.configuration import settings
from src.shared.logging_utils import get_logger
from src.shared.database import DatabaseManager

__all__ = ["settings", "get_logger", "DatabaseManager"]
