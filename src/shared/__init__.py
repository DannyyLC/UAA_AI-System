"""
Shared module — Código compartido entre todos los microservicios.
"""

from src.shared.configuration import settings
from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

__all__ = ["settings", "get_logger", "DatabaseManager"]
