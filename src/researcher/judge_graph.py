from src.researcher.judge_state import RefinerState
from src.researcher.response import GeneradorRespuestas
from src.researcher.judge import Judge
from typing import Literal, Dict, Any 
from src.shared.logging_utils import get_logger
from langgraph.graph import StateGraph, END

logger = get_logger(__name__)

# Router para decidir el siguiente paso
def router(state: RefinerState) -> Literal["mejorar", "finalizar"]:
    return state["resultado"]

# Crear el grafo de LangGraph
def crear_sistema_refinamiento(model_name: str = "mistral", max_iteraciones: int = 3, umbral_calidad: float = 8.5):
    # Inicializar los nodos
    generador = GeneradorRespuestas(model_name=model_name)
    juez = Judge(model_name=model_name, umbral_calidad=umbral_calidad)
    
    # Crear el grafo
    workflow = StateGraph(RefinerState)
    
    # Agregar nodos
    workflow.add_node("generador", generador)
    workflow.add_node("juez", juez)
    
    # Definir el flujo: Entrada -> Generador -> Juez -> [Mejorar o Finalizar]
    workflow.set_entry_point("generador")
    workflow.add_edge("generador", "juez")
    workflow.add_conditional_edges(
        "juez",
        router,
        {
            "mejorar": "generador",
            "finalizar": END
        }
    )
    
    # Compilar el grafo
    app = workflow.compile()
    
    return app

# Función para ejecutar el sistema completo
async def generar_respuesta_refinada(
    contexto: str, 
    judge_graph,
    max_iteraciones,
    prompt_adicional: str = ""
) -> Dict[str, Any]:
    """
    Genera una respuesta refinada iterativamente usando el sistema de generación-evaluación.
    
    Args:
        contexto: String con el contexto de la consulta
        prompt_adicional: Instrucciones adicionales
        model_name: Modelo de Ollama a utilizar
        max_iteraciones: Número máximo de iteraciones permitidas
        umbral_calidad: Puntuación mínima (0-10) para considerar una respuesta como suficiente
        
    Returns:
        Dict: Estado final con la respuesta y metadatos
    """
    # Crear el sistema
    sistema = judge_graph
    
    # Estado inicial
    estado_inicial = RefinerState(
        contexto=contexto,
        prompt_adicional=prompt_adicional,
        respuesta_actual="",
        feedback="",
        iteraciones=0,
        max_iteraciones=max_iteraciones,
        resultado="mejorar",  # Comenzar con generación
        calidad_respuesta=0.0,  # Inicializar puntuación en 0
        mejora_necesaria=True   # Inicialmente asumimos que necesitará mejoras
    )
    
    # Ejecutar el flujo
    try:
        resultado = await sistema.ainvoke(estado_inicial)
        return resultado
    except Exception as e:
        logger.error(f"Error en la ejecución del grafo: {str(e)}")
        return {
            "respuesta_actual": f"Error en el sistema: {str(e)}",
            "iteraciones": 0,
            "max_iteraciones": max_iteraciones,
            "calidad_respuesta": 0.0
        }
        