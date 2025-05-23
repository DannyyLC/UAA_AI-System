from langchain_ollama import OllamaLLM
from src.shared.prompts import RESPONSE_GENERATOR
from src.shared.logging_utils import get_logger
from src.researcher.judge_state import RefinerState

logger = get_logger(__name__)

# Nodo Generador
class GeneradorRespuestas:
    def __init__(self, model_name: str = "mistral"):
        self.llm = OllamaLLM(model=model_name)
    
    def __call__(self, state: RefinerState) -> RefinerState:
        try:
            logger.info(f"Generando respuesta. Iteración {state['iteraciones']+1}/{state['max_iteraciones']}")
            
            # En la primera iteración no hay respuesta anterior ni feedback
            respuesta_anterior = state.get("respuesta_actual", "")
            feedback = state.get("feedback", "")
            
            feedback_text = f"FEEDBACK DEL JUEZ (aplica estas mejoras):\n{feedback}" if feedback else ""
            
            # Generar prompt completo
            prompt = RESPONSE_GENERATOR.format(
                contexto=state["contexto"],
                prompt_adicional=state["prompt_adicional"],
                feedback=feedback_text,
                respuesta_anterior=respuesta_anterior
            )
            
            # Invocar el modelo
            nueva_respuesta = self.llm.invoke(prompt)
            # Actualizar el estado
            state["respuesta_actual"] = nueva_respuesta
            state["iteraciones"] += 1
            
            logger.info("Respuesta generada exitosamente")
            return state
            
        except Exception as e:
            error_msg = f"Error al generar respuesta: {str(e)}"
            logger.error(error_msg)
            state["respuesta_actual"] = error_msg
            state["resultado"] = "finalizar"  # En caso de error, terminar
            return state
