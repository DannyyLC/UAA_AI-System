import asyncio
import os
from io import BytesIO
from src.indexing import EmbeddingProcessor
from src.shared.logging_utils import get_logger
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from src.researcher.graph import build_graph  
from src.researcher.router import Router
from src.researcher.retrieval import Retrieval
from src.researcher.judge_graph import crear_sistema_refinamiento
from src.api.APIManager import APIManager

logger = get_logger(__name__)
USE_API = True

async def run_graph_with_query(query: str, graph, state) -> Dict[str, Any]:
    """
    Ejecuta el grafo de investigación con una consulta específica.
    
    Args:
        query (str): La consulta del usuario.
        
    Returns:
        Dict[str, Any]: El estado final tras ejecutar el grafo.
    """
    try:
        
        # Ejecutar el grafo
        print(f"Iniciando grafo con consulta: {query}")
        result = await graph.ainvoke(state)
        
        return result
    except Exception as e:
        logger.error(f"Error en run_graph_with_query: {str(e)}")
        raise

async def process_query(graph, state):
    """Maneja la opción de consulta al sistema."""
    print("\n=== Modo de Consulta ===")
    query = input("Ingresa tu pregunta: ")
    
    try:
        # Agregar el mensaje de usuario al historial
        state["messages"].append(HumanMessage(content=query))
        state["current_query"] = query
        
        # Ejecutar el grafo con la consulta
        final_state = await run_graph_with_query(query, graph, state)
        
        state.update(final_state)
        
        # Mostrar respuesta
        print("\n=== Respuesta ===")
        if state["messages"] and len(state["messages"]) > 1:
            ai_response = state["messages"][-1]
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

async def index_documents(embedding_processor: EmbeddingProcessor):
    """Maneja la opción de indexación de documentos."""
    pdf_path = input("Dame el nombre del archivo: ")
    collection = input("Dame el nombre de la coleccion: ")

    # Leer el archivo PDF
    with open(pdf_path, 'rb') as pdf_file:
        pdf_content = pdf_file.read()
    
    # Crear el BytesIO con el contenido del PDF
    pdf_bytes = BytesIO(pdf_content)
    
    # Obtener el nombre del archivo del path
    pdf_name = os.path.basename(pdf_path)
    
    # Crear la lista de documentos
    documents = [(pdf_bytes, pdf_name)]
    
    # Procesar y almacenar embeddings
    collection_name = await embedding_processor.process_and_store(
        documents=documents,
        user_id="usuario_123",
        collection_name=collection
    )
    
    print(f"Embeddings almacenados en la colección: {collection_name}")
    
async def process_query_multiple_models(query):
    models = ["gemma3", "mistral"]

    for model in models:
        logger.info(f"\n============= RESPUESTA {model.upper()} =============")
        # Construir el grafo
        graph = build_graph()
        model_name = model
        judge_graph = crear_sistema_refinamiento(model_name=model_name)

        state = {
            "messages": [],
            "investigation": True,
            "current_query": "",
            "research_plan": [],
            "retrieval_queries": [],
            "query_category": "",
            "research_collections": [],
            "current_step": "",
            "needs_research": False,
            "retrieval_results": {},
            "context_for_generation": "",
            "research_completed": False,
            "retrieval_obj" : Retrieval(persist_directory="./chroma_db"),
            "router_obj" : Router(model_name=model),
            "judge_obj" : judge_graph,
            "response_model" : model,
            "api":APIManager(USE_API)
        }

        state["router_obj"].retriever = state["retrieval_obj"]

        # Agregar el mensaje de usuario al historial
        state["messages"].append(HumanMessage(content=query))
        state["current_query"] = query

        final_state = await run_graph_with_query(query, graph, state)
        
        state.update(final_state)
        
        # Mostrar respuesta
        print("\n=== Respuesta ===")
        if state["messages"] and len(state["messages"]) > 1:
            ai_response = state["messages"][-1]
            print(ai_response.content)
            
            # Si hay metadatos disponibles, mostrarlos
            if hasattr(ai_response, "additional_kwargs") and ai_response.additional_kwargs:
                print("\n=== Metadatos ===")
                for key, value in ai_response.additional_kwargs.items():
                    print(f"{key}: {value}")
        else:
            print("No se obtuvo una respuesta.")


async def main():
    """Función principal que muestra el menú y maneja las opciones."""
    # Instancias
    embedding_processor = EmbeddingProcessor(True, persist_directory="./chroma_db")
    # Construir el grafo
    print("Construyendo grafo...")
    graph = build_graph()
    model_name = "gemma3:4b"
    judge_graph = crear_sistema_refinamiento(model_name=model_name)

    # Estado inicial
    print("Creando estado inicial...")
    state = {
        "messages": [],
        "investigation": True,
        "current_query": "",
        "research_plan": [],
        "retrieval_queries": [],
        "query_category": "",
        "research_collections": [],
        "current_step": "",
        "needs_research": False,
        "retrieval_results": {},
        "context_for_generation": "",
        "research_completed": False,
        "retrieval_obj" : Retrieval(persist_directory="./chroma_db"),
        "router_obj" : Router(model_name),
        "judge_obj" : judge_graph,
        "response_model" : model_name,
        "api":APIManager(USE_API, model_name)
    }
    
    state["router_obj"].retriever = state["retrieval_obj"]

    while True:
        print("\n=== Sistema de Investigación ===")
        print("1. Indexar documentos")
        print("2. Realizar consulta")
        print("3. Salir")
        
        choice = input("Selecciona una opción (1-3): ")
        
        if choice == "1":
            await index_documents(embedding_processor)
        elif choice == "2":
            while True:
                print("\n1. Realizar query en modelo por defecto")
                print("2. Realizar query en todos los modelos")
                print("3. Regresar a menu principal")

                choice_query = input("Selecciona una opción (1-3): ")

                if choice_query == "1":
                    await process_query(graph, state)
                elif choice_query == "2":
                    query = input("Ingresa tu pregunta: ")
                    await process_query_multiple_models(query=query)
                elif choice_query == "3":
                    break
                else:
                    print("Opción no válida. Por favor, intenta de nuevo.")
        elif choice == "3":
            print("Saliendo del sistema. ¡Hasta pronto!")
            break
        else:
            print("Opción no válida. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    # Ejecutar el bucle principal de forma asíncrona
    asyncio.run(main())