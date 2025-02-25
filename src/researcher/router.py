from src.shared.models import get_llm
from src.shared.prompts import ROUTER_PROMPT

class Router:
    """Clase para enrutar consultas a diferentes categorías."""

    def __init__(self):
        self.llm = get_llm(model_name="llama3.2:1b", temperature=0.1)  
        self.available_subjects = "programacion, estructura_de_datos, unix, ecuaciones_diferenciales"
        
    def classify_with_llm(self, query: str) -> str:
        """Clasifica la consulta usando el modelo de lenguaje con el prompt de clasificación."""
        try:
            prompt = ROUTER_PROMPT.format(materias=self.available_subjects, query=query)
            
            category = self.llm.invoke(prompt)
            return category.strip()
        except Exception as e:
            return f"Error al clasificar la consulta: {str(e)}"  
