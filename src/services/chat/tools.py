"""
Prompts y utilidades para el flujo de clasificación y respuesta con RAG.

En lugar de depender del function calling del LLM, usamos un flujo fijo:
1. Clasificar la pregunta del usuario en una colección o "general"
2. Si es una colección → buscar contexto con RAG → responder con contexto
3. Si es "general" → responder directamente sin contexto
"""

from typing import List


# ============================================================
# Prompt de Clasificación
# ============================================================


def create_classification_prompt(topics: List[str], user_message: str) -> List[dict]:
    """
    Crea los mensajes para pedirle al LLM que clasifique la pregunta del usuario.

    El LLM debe responder SOLO con el nombre exacto de la colección o "general".

    Args:
        topics: Lista de temas/colecciones disponibles del usuario
        user_message: Pregunta del usuario

    Returns:
        Lista de mensajes en formato OpenAI
    """
    topics_list = "\n".join(f"- {topic}" for topic in topics)

    # Build a few-shot example using the first available topic
    example_topic = topics[0] if topics else "matemáticas"
    example_question = f"¿Puedes revisar mis documentos de {example_topic} y resumirlos?"

    system = f"""Eres un clasificador de preguntas. Tu ÚNICA tarea es determinar si la pregunta del usuario está relacionada con alguna de las siguientes colecciones de documentos, o si es una pregunta general.

COLECCIONES DISPONIBLES:
{topics_list}

REGLAS ESTRICTAS:
1. Si la pregunta menciona, hace referencia, o puede responderse con alguna colección → responde ÚNICAMENTE con el nombre EXACTO de esa colección (copiado de la lista).
2. Si la pregunta NO tiene ninguna relación con ninguna colección → responde ÚNICAMENTE con: general
3. PROHIBIDO agregar explicaciones, signos de puntuación, comillas, saltos de línea o cualquier otro texto.
4. Tu respuesta debe ser exactamente UNA línea.
5. Ante la duda de si una pregunta es relevante para una colección, elige la colección (NO general).

EJEMPLOS:
Usuario: {example_question}
Respuesta: {example_topic}

Usuario: ¿Cuánto es 2 + 2?
Respuesta: general

Usuario: ¿Qué dice mi documento sobre {example_topic}?
Respuesta: {example_topic}"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]


def parse_classification_result(result: str, topics: List[str]) -> str:
    """
    Parsea el resultado de la clasificación del LLM.

    Args:
        result: Texto de respuesta del LLM
        topics: Lista de temas válidos

    Returns:
        Nombre de la colección o "general"
    """
    cleaned = result.strip().strip('"').strip("'").strip(".").strip()

    # Búsqueda exacta (case-insensitive)
    for topic in topics:
        if cleaned.lower() == topic.lower():
            return topic

    # Búsqueda parcial: si el resultado contiene el nombre del topic
    for topic in topics:
        if topic.lower() in cleaned.lower():
            return topic

    return "general"


# ============================================================
# System Messages para Respuesta
# ============================================================


def create_general_system_message() -> str:
    """
    Crea el system message para respuestas generales (sin RAG).

    Returns:
        Mensaje del sistema
    """
    return """Eres un asistente académico inteligente de la UAA (Universidad Autónoma de Aguascalientes).

Tu objetivo es ayudar a estudiantes respondiendo sus preguntas de manera clara y precisa.
Responde de forma directa y útil."""


def create_rag_system_message(context: str, sources: List[str]) -> str:
    """
    Crea el system message para respuestas basadas en RAG (con contexto).

    Args:
        context: Contexto recuperado de la base de conocimiento
        sources: Lista de fuentes encontradas

    Returns:
        Mensaje del sistema con el contexto inyectado
    """
    sources_text = "\n".join(f"- {s}" for s in sources)

    return f"""Eres un asistente académico inteligente de la UAA (Universidad Autónoma de Aguascalientes).

Tu objetivo es ayudar a estudiantes respondiendo sus preguntas de manera clara y precisa.

CONTEXTO DE LA BASE DE CONOCIMIENTO:
{context}

FUENTES CONSULTADAS:
{sources_text}

INSTRUCCIONES:
- Basa tu respuesta en el contexto proporcionado arriba.
- Si el contexto no contiene información suficiente para responder, indícalo claramente y ofrece tu mejor respuesta.
- Menciona las fuentes consultadas cuando sea relevante.
- Responde de forma clara, organizada y útil para un estudiante."""
