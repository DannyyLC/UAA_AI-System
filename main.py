import asyncio
from src.shared.logging_utils import get_logger
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from src.researcher.graph import build_graph  

logger = get_logger(__name__)

async def run_graph_with_query(query: str) -> Dict[str, Any]:
    """
    Ejecuta el grafo de investigación con una consulta específica.
    
    Args:
        query (str): La consulta del usuario.
        
    Returns:
        Dict[str, Any]: El estado final tras ejecutar el grafo.
    """
    try:
        # Construir el grafo
        print("Construyendo grafo...")
        graph = build_graph()
        
        # Estado inicial
        print("Creando estado inicial...")
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "investigation": True,
            "current_query": query,
            "research_plan": [],
            "retrieval_queries": [],
            "query_category": "",
            "research_collections": [],
            "current_step": "",
            "needs_research": False,
            "retrieval_results": {},
            "context_for_generation": "",
            "research_completed": False
        }
        
        # Ejecutar el grafo
        print(f"Iniciando grafo con consulta: {query}")
        result = await graph.ainvoke(initial_state)
        
        return result
    except Exception as e:
        logger.error(f"Error en run_graph_with_query: {str(e)}")
        raise

async def process_query():
    """Maneja la opción de consulta al sistema."""
    print("\n=== Modo de Consulta ===")
    query = input("Ingresa tu pregunta: ")
    
    try:
        # Ejecutar el grafo con la consulta
        final_state = await run_graph_with_query(query)
        
        # Mostrar respuesta
        print("\n=== Respuesta ===")
        if final_state["messages"] and len(final_state["messages"]) > 1:
            ai_response = final_state["messages"][-1]
            print(ai_response.content)
            
            # Si hay metadatos disponibles, mostrarlos
            if hasattr(ai_response, "additional_kwargs") and ai_response.additional_kwargs:
                print("\n=== Metadatos ===")
                for key, value in ai_response.additional_kwargs.items():
                    print(f"{key}: {value}")
        else:
            print("No se obtuvo una respuesta.")
        
    except Exception as e:
        logger.error(f"Error al procesar la consulta: {str(e)}")
        print(f"Error: {str(e)}")

def index_documents():
    """Maneja la opción de indexación de documentos."""
    print("\n=== Modo de Indexación ===")
    print("Indexando documentos... Esta funcionalidad está pendiente de implementación.")
    # Aquí iría el código para indexar documentos
    # Por ejemplo:
    # retriever = Retrieval(persist_directory="./chroma_db")
    # retriever.index_documents(...)

async def main():
    """Función principal que muestra el menú y maneja las opciones."""
    while True:
        print("\n=== Sistema de Investigación ===")
        print("1. Indexar documentos")
        print("2. Realizar consulta")
        print("3. Salir")
        
        choice = input("Selecciona una opción (1-3): ")
        
        if choice == "1":
            index_documents()
        elif choice == "2":
            await process_query()
        elif choice == "3":
            print("Saliendo del sistema. ¡Hasta pronto!")
            break
        else:
            print("Opción no válida. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    # Ejecutar el bucle principal de forma asíncrona
    asyncio.run(main())