from langchain_ollama import OllamaLLM
from src.shared.prompts import JUDGE_PROMPT
from src.shared.logging_utils import get_logger
from src.researcher.judge_state import RefinerState

logger = get_logger(__name__)

# Nodo Juez - Modificado para permitir terminación temprana
class Judge:
    def __init__(self, model_name: str = "mistral", umbral_calidad: float = 8.5):
        self.llm = OllamaLLM(model=model_name)
        self.umbral_calidad = umbral_calidad  # Umbral para considerar una respuesta como suficiente
    
    def __call__(self, state: RefinerState) -> RefinerState:
        try:
            logger.info(f"Evaluando respuesta. Iteración {state['iteraciones']}/{state['max_iteraciones']}")
            
            # Generar prompt para el juez
            prompt = JUDGE_PROMPT.format(
                contexto=state["contexto"],
                prompt_adicional=state["prompt_adicional"],
                respuesta=state["respuesta_actual"],
                iteracion=state["iteraciones"],
                max_iteraciones=state["max_iteraciones"]
            )
            
            # Invocar el modelo
            if state["api"].enabled:
                evaluacion = state["api"].getResponse(prompt)
            else:
                evaluacion = self.llm.invoke(prompt)
            
            # Parsear la respuesta del juez
            lines = evaluacion.strip().split("\n")
            decision = ""
            feedback = ""
            puntuacion = 0.0
            
            for i, line in enumerate(lines):
                if line.startswith("PUNTUACIÓN:"):
                    try:
                        # Extraer y convertir la puntuación a float
                        score_text = line.replace("PUNTUACIÓN:", "").strip()
                        puntuacion = float(score_text)
                    except ValueError:
                        logger.warning(f"No se pudo convertir la puntuación: {score_text}")
                        puntuacion = 0.0
                elif line.startswith("DECISIÓN:"):
                    decision = line.replace("DECISIÓN:", "").strip()
                elif line.startswith("FEEDBACK:"):
                    feedback = line.replace("FEEDBACK:", "").strip()
                    # Capturar también las líneas siguientes como parte del feedback
                    feedback_index = i
                    if feedback_index < len(lines) - 1:
                        additional_feedback = "\n".join(lines[feedback_index + 1:])
                        feedback += "\n" + additional_feedback
                        break  # Salir después de capturar todo el feedback
            
            # Actualizar el estado con la puntuación
            state["calidad_respuesta"] = puntuacion
            state["mejora_necesaria"] = decision != "SUFICIENTE"
            
            # Registrar la puntuación en los logs
            logger.info(f"Evaluación: Puntuación = {puntuacion}/10, Decisión = {decision}")
            
            # Decidir si continuar o finalizar
            # Terminación temprana si la respuesta es suficientemente buena (supera el umbral de calidad)
            if decision == "SUFICIENTE" or puntuacion >= self.umbral_calidad:
                state["resultado"] = "finalizar"
                logger.info("Evaluación: Respuesta aprobada - Terminación temprana")
            # Terminación por alcanzar el máximo de iteraciones
            elif state["iteraciones"] >= state["max_iteraciones"]:
                state["resultado"] = "finalizar"
                logger.info("Evaluación: Máximo de iteraciones alcanzado")
            # Continuar con el refinamiento
            else:
                state["resultado"] = "mejorar"
                state["feedback"] = feedback
                logger.info(f"Evaluación: Respuesta necesita mejoras (Puntuación: {puntuacion})")
            
            return state
            
        except Exception as e:
            error_msg = f"Error en la evaluación: {str(e)}"
            logger.error(error_msg)
            state["feedback"] = error_msg
            state["resultado"] = "finalizar"  # En caso de error, terminar
            return state

