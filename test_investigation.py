import asyncio
import logging
import httpx

# Configurar el logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_research_plan(prompt: str, model: str = "llama3:8b") -> list[str]:
    """Genera un plan de investigación paso a paso basado en un prompt de usuario utilizando Ollama.

    Args:
        prompt (str): El tema o pregunta que el usuario quiere investigar.
        model (str): Modelo de Ollama a utilizar (por defecto "llama3.2:1b").

    Returns:
        list[str]: Lista de pasos a seguir en la investigación.
    """
    logger.info("Generando plan de investigación con Ollama...")

    try:
        # Prompt de sistema para estructurar la respuesta en pasos concretos
        system_prompt = (
            "Eres un asistente de investigación experto en estructurar planes de estudio."
            "Tu tarea es generar un plan de investigación claro y organizado para el siguiente tema.\n\n"
            "**Instrucciones:**\n"
            "- El plan debe tener **entre 1 y 5 pasos**, nunca más.\n"
            "- Cada paso debe ser claro, breve y específico.\n"
            "- Utiliza una lista numerada.\n\n"
            "**Ejemplo de formato:**\n"
            "1. Buscar la definición y conceptos básicos.\n"
            "2. Investigar casos de uso en distintas fuentes.\n"
            "3. Analizar artículos académicos y estudios relevantes.\n"
            "4. Comparar diferentes perspectivas y teorías.\n"
            "5. Resumir los hallazgos principales y elaborar conclusiones.\n\n"
            f"**Tema a investigar:** {prompt}\n\n"
            "Por favor, genera el plan de investigación con entre **1 y 5 pasos**."
        )

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

        logger.info(f"Plan de investigación generado con {len(steps)} pasos")
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

# Función principal para ejecutar la investigación
async def main():
    prompt_usuario = input("Ingrese el tema de investigación: ")

    # Llamar a la función para generar el plan
    plan = await generate_research_plan(prompt_usuario)

    # Mostrar el resultado
    print("\n🔍 Plan de investigación generado:")
    for i, step in enumerate(plan, 1):
        print(f"{i}. {step}")

# Ejecutar la función principal
asyncio.run(main())
