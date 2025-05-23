import httpx
from src.shared.prompts import INVESTIGATION_PROMPT
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

async def generate_research_plan(prompt: str, model: str = "llama3.2:1b") -> list[str]:
    """Genera un plan de investigación paso a paso basado en un prompt de usuario utilizando Ollama.

    Args:
        prompt (str): El tema o pregunta que el usuario quiere investigar.
        model (str): Modelo de Ollama a utilizar (por defecto "llama3.2:1b").

    Returns:
        list[str]: Lista de pasos a seguir en la investigación.
    """

    try:
        # Prompt de sistema para estructurar la respuesta en pasos concretos
        system_prompt = INVESTIGATION_PROMPT.format(prompt=prompt)

        # Hacer la solicitud a la API de Ollama
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",  # URL del servidor Ollama
                json={"model": model, "prompt": system_prompt, "stream": False},
                timeout=60
            )

        # Verificar si la respuesta es válida
        if response.status_code != 200:
            logger.error(f"Error en la respuesta de Ollama: {response.text}")
            return ["Error al generar el plan. Verifique que Ollama esté en ejecución."]

        # Extraer el contenido de la respuesta
        content = response.json().get("response", "")
        if not content:
            return ["No se pudo generar un plan de investigación válido."]

        # Extraer pasos numerados del contenido generado
        steps = [
            line.strip().lstrip("1234567890-. ")
            for line in content.split("\n")
            if line.strip() and (
                line.strip()[0].isdigit() or 
                line.strip().startswith("-") or 
                line.strip().startswith("•")
            )
        ]

        # Si no se extrajeron pasos, usar un plan genérico
        if not steps:
            logger.warning("No se pudieron extraer pasos del plan, usando plan por defecto")
            steps = [
                "Definir los conceptos clave del tema",
                "Buscar fuentes confiables en línea",
                "Leer artículos académicos y estudios de caso",
                "Comparar diferentes perspectivas sobre el tema",
                "Redactar un resumen con las conclusiones más importantes"
            ]

        return steps

    except Exception as e:
        logger.error(f"Error al generar el plan de investigación: {str(e)}")
        return [
            "Definir los conceptos clave del tema",
            "Buscar fuentes confiables en línea",
            "Leer artículos académicos y estudios de caso",
            "Comparar diferentes perspectivas sobre el tema",
            "Redactar un resumen con las conclusiones más importantes"
        ]
        