"""
Prompts y utilidades para el flujo de clasificación y respuesta con RAG.

En lugar de depender del function calling del LLM, usamos un flujo fijo:
1. Clasificar la pregunta del usuario en una colección o "general"
2. Si es una colección → buscar contexto con RAG → responder con contexto
3. Si es "general" → responder directamente sin contexto
"""

import json
import re
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

    # Build few-shot examples using available topics
    example_topic = topics[0] if topics else "matemáticas"
    second_topic = topics[1] if len(topics) > 1 else "historia"

    system = f"""Clasifica la pregunta del usuario. Responde con UNA SOLA PALABRA: el nombre exacto de la colección o "general".

COLECCIONES:
{topics_list}

INSTRUCCIONES:
- Si la pregunta menciona o se relaciona con una colección → responde el nombre de esa colección.
- Si NO se relaciona con ninguna → responde: general
- Ante la duda, elige la colección (NO general).
- Responde SOLO el nombre. Sin explicaciones, sin puntuación, sin comillas.

EJEMPLOS:
Pregunta: ¿Puedes revisar mis documentos de {example_topic}?
→ {example_topic}

Pregunta: Tengo una pregunta sobre "{second_topic}"
→ {second_topic}

Pregunta: Ve a mi colección de {example_topic} y resúmelo
→ {example_topic}

Pregunta: Hola, ¿cómo estás?
→ general

Pregunta: ¿Cuánto es 2 + 2?
→ general"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Pregunta: {user_message}\n→"},
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
# Plan de Investigación
# ============================================================


def create_research_plan_prompt(user_message: str, topic: str) -> List[dict]:
    """
    Crea los mensajes para pedirle al LLM que genere un plan de investigación
    con 3 sub-preguntas orientadas a buscar contexto en la base documental.

    Args:
        user_message: Pregunta original del usuario
        topic: Colección/tema en la que se va a buscar

    Returns:
        Lista de mensajes en formato OpenAI
    """
    system = f"""Eres un asistente de investigación académica. Tu tarea es descomponer la pregunta del usuario en exactamente 3 sub-preguntas de búsqueda que permitan recuperar la información más relevante de una base de documentos sobre "{topic}".

REGLAS:
1. Genera exactamente 3 preguntas.
2. Cada pregunta debe cubrir un aspecto distinto de la pregunta original.
3. Las preguntas deben ser específicas y orientadas a buscar fragmentos relevantes en documentos académicos.
4. Responde ÚNICAMENTE con un JSON array de 3 strings.
5. No agregues explicaciones, solo el JSON.

EJEMPLO DE FORMATO:
["¿Cuál es la definición de X?", "¿Cuáles son las propiedades principales de X?", "¿Qué ejemplos o aplicaciones tiene X?"]"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]


def parse_research_plan(response: str) -> List[str]:
    """
    Extrae las 3 sub-preguntas del plan de investigación generado por el LLM.

    Args:
        response: Texto de respuesta del LLM (esperado: JSON array de strings)

    Returns:
        Lista de 3 sub-preguntas. Si el parseo falla, devuelve la pregunta original
        replicada 3 veces como fallback.
    """
    cleaned = response.strip()

    # Intentar extraer JSON array del texto
    match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
    if match:
        try:
            questions = json.loads(match.group())
            if isinstance(questions, list) and len(questions) >= 3:
                return [str(q) for q in questions[:3]]
        except (json.JSONDecodeError, TypeError):
            pass

    # Fallback: intentar separar por líneas numeradas
    lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
    questions = []
    for line in lines:
        # Remover numeración como "1.", "1)", "- "
        clean_line = re.sub(r'^[\d]+[.)\-]\s*', '', line).strip()
        clean_line = re.sub(r'^[-•]\s*', '', clean_line).strip()
        if clean_line and clean_line.startswith('¿') or clean_line.endswith('?'):
            questions.append(clean_line)

    if len(questions) >= 3:
        return questions[:3]

    return []


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
