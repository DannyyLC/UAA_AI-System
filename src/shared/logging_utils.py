"""
Utilidades de logging con formato consistente para todos los servicios.

Uso:
    from src.shared.logging_utils import get_logger
    logger = get_logger(__name__)
    logger.info("Mensaje")
"""

import logging
import sys
from typing import Optional

from src.shared.configuration import settings

# Formato con color para desarrollo
COLORED_FORMAT = (
    "\033[90m%(asctime)s\033[0m "
    "\033[1m%(levelname)-8s\033[0m "
    "\033[36m%(name)s\033[0m "
    "%(message)s"
)

# Formato simple para producción (JSON-friendly logs)
PLAIN_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"


def get_logger(
    name: str,
    level: Optional[str] = None,
) -> logging.Logger:
    """
    Crea y retorna un logger configurado.

    Args:
        name: Nombre del logger (típicamente __name__)
        level: Nivel de logging (override de settings.log_level)

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)

    # Evitar agregar handlers duplicados
    if logger.handlers:
        return logger

    log_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)
    logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Formato según el entorno
    if settings.environment == "development":
        fmt = COLORED_FORMAT
    else:
        fmt = PLAIN_FORMAT

    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)

    # No propagar al root logger
    logger.propagate = False

    return logger
