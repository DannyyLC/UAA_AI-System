from src.shared.models import get_llm
from src.shared.prompts import ROUTER_PROMPT
from src.shared.logging_utils import get_logger, timing_decorator

logger = get_logger(__name__)

class Router:
    """Clase para enrutar consultas a diferentes categorías."""

    def __init__(self, model_name : str = "llama3:8b"):
        self.llm = get_llm(model_name, temperature=0.1)  
        self.available_subjects = "programacion, estructura_de_datos, unix, ecuaciones_diferenciales"
        self.retriever = None
        
    def classify_with_llm(self, query: str, state) -> str:
        """Clasifica la consulta usando el modelo de lenguaje con el prompt de clasificación."""
        try:
            available_subjects = self.retriever.get_existing_collections()
            prompt = ROUTER_PROMPT.format(materias=available_subjects, query=query)
            if state["api"].enabled:
                category = state["api"].getResponse(prompt)
            else:
                category = self.llm.invoke(prompt)
            logger.info(f"Consulta clasificada como: {category.strip()}")
            return category.strip()
        except Exception as e:
            logger.error("Error al clasificar la consulta")
            return f"Error al clasificar la consulta: {str(e)}"  
