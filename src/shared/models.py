from langchain_ollama import OllamaLLM
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

def get_llm(model_name: str = "mistral", temperature: float = 0.1, **kwargs) -> OllamaLLM:
    """ Carga un modelo de lenguaje desde Ollama con los parámetros especificados.
    Args:
        model_name (str): Nombre del modelo en Ollama (ej. "mistral", "llama3").
        temperature (float): Controla la creatividad de las respuestas (0 = determinista, >0 = más aleatorio).
        **kwargs: Parámetros adicionales compatibles con `OllamaLLM`.

    Returns:
        OllamaLLM: Instancia del modelo cargado en LangChain.

    Excepciones:
        - Lanza ValueError si Ollama no está corriendo o el modelo no está disponible.
    """
    try:
        logger.info(f"Loading {model_name}, temperature: {temperature}")
        return OllamaLLM(model=model_name, temperature=temperature, **kwargs)
    except Exception as e:
        logger.error("Error al cargar el modelo")
        raise ValueError(f"Error al cargar el modelo '{model_name}': {e}")
