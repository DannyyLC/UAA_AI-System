import time
import logging
from functools import wraps
from typing import Callable, Any

# Configuración básica del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

def timing_decorator(func: Callable) -> Callable:
    """
    Decorador para medir y registrar el tiempo de ejecución de una función.
    
    Args:
        func: La función a decorar.
        
    Returns:
        Callable: La función decorada que incluye medición de tiempo.
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        logger.info(f"Iniciando {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"Completado {func.__name__} - Tiempo: {duration:.2f} segundos")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en {func.__name__}: {str(e)}")
            raise
            
    return wrapper

def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado para un módulo específico.
    
    Args:
        name: Nombre del módulo que solicita el logger.
        
    Returns:
        logging.Logger: Logger configurado.
    """
    return logging.getLogger(name)
