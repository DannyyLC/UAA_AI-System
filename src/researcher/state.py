from typing import TypedDict, Literal

class RefinerState(TypedDict):
    contexto: str                  # Contexto original
    prompt_adicional: str          # Instrucciones adicionales
    respuesta_actual: str          # Respuesta generada actual
    feedback: str                  # Retroalimentación del juez
    iteraciones: int               # Número de iteraciones realizadas
    max_iteraciones: int           # Número máximo de iteraciones permitidas
    resultado: Literal["mejorar", "finalizar"]  # Decisión del juez
    calidad_respuesta: float       # Puntuación de calidad (0-10)
    mejora_necesaria: bool         # Indicador si la respuesta necesita mejoras