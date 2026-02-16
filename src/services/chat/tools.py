"""
Definición de tools (funciones) para function calling del LLM.

El LLM puede decidir llamar a estas functions cuando lo considere necesario.
"""

import json
from typing import Any, Dict, List

# ============================================================
# RAG Tool Definition
# ============================================================

RAG_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": """
Busca información relevante en la base de conocimiento del usuario.
Usa esta función cuando necesites información específica que no conoces,
especialmente sobre temas académicos, documentos o contenido especializado.

IMPORTANTE: Antes de decidir usar esta función, considera los temas disponibles 
que se te proporcionaron en el mensaje del sistema. Solo usa esta función si 
la pregunta está relacionada con alguno de esos temas.
        """.strip(),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "La consulta o pregunta a buscar en la base de conocimiento",
                },
                "topic": {
                    "type": "string",
                    "description": """
El tema/categoría específico donde buscar (ej: 'Matemáticas', 'Física', 'Historia').
Debe ser uno de los temas disponibles que se te proporcionaron.
Si no estás seguro, déjalo vacío para buscar en todos los temas.
                    """.strip(),
                },
            },
            "required": ["query"],
        },
    },
}


def get_rag_tools() -> List[Dict[str, Any]]:
    """
    Retorna la lista de tools disponibles para el LLM.

    Returns:
        Lista de tools en formato OpenAI function calling
    """
    return [RAG_SEARCH_TOOL]


def format_tool_call_result(tool_name: str, result: Dict[str, Any]) -> str:
    """
    Formatea el resultado de una tool call para enviarlo al LLM.

    Args:
        tool_name: Nombre de la tool
        result: Resultado de la ejecución de la tool

    Returns:
        String formateado para el LLM
    """
    if tool_name == "search_knowledge_base":
        if not result.get("context"):
            return "No se encontró información relevante en la base de conocimiento."

        return result["context"]

    return json.dumps(result)


# ============================================================
# System Message Generator
# ============================================================


def create_system_message_with_topics(topics: List[str]) -> str:
    """
    Crea el mensaje del sistema que incluye los temas disponibles.

    Este mensaje se envía ANTES de que el LLM responda, para que sepa
    qué información tiene disponible en la base de conocimiento.

    Args:
        topics: Lista de temas únicos disponibles para el usuario

    Returns:
        Mensaje del sistema formateado
    """
    base_message = """
Eres un asistente académico inteligente de la UAA (Universidad Autónoma de Aguascalientes).

Tu objetivo es ayudar a estudiantes respondiendo sus preguntas de manera clara y precisa.
    """.strip()

    if not topics:
        base_message += (
            "\\n\\nActualmente no hay documentos disponibles en la base de conocimiento."
        )
        return base_message

    topics_list = "\\n".join(f"- {topic}" for topic in topics)

    base_message += f"""

TEMAS DISPONIBLES EN LA BASE DE CONOCIMIENTO:
{topics_list}

INSTRUCCIONES:
- Si la pregunta del estudiante está relacionada con alguno de estos temas, 
  usa la función 'search_knowledge_base' para buscar información específica.
- Si la pregunta NO está relacionada con estos temas o es una pregunta general, 
  responde directamente sin usar la función.
- Cuando uses la base de conocimiento, siempre menciona las fuentes consultadas.
- Si no encuentras información relevante, indícalo claramente y ofrece tu mejor respuesta.
    """.strip()

    return base_message
