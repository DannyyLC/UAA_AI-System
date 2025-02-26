# test_retrieval.py
import os
import sys

# Añadir directorio src al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from researcher.retrieval import Retrieval

def main():
    """
    Función principal para probar el módulo Retrieval.
    Busca información en colecciones existentes basada en consultas de ejemplo.
    """
    # Ruta donde están almacenadas las colecciones de ChromaDB
    persist_directory = "./chroma_db"
    
    # Asegúrate de que el directorio existe
    if not os.path.exists(persist_directory):
        print(f"Error: El directorio {persist_directory} no existe.")
        print("Por favor, crea el directorio y añade algunas colecciones primero.")
        return
    
    print(f"Inicializando Retrieval con directorio: {persist_directory}")
    
    # Inicializa el módulo de recuperación
    try:
        retriever = Retrieval(persist_directory=persist_directory)
        print("Módulo Retrieval inicializado correctamente.")
    except Exception as e:
        print(f"Error al inicializar el módulo Retrieval: {str(e)}")
        return
    
    # Obtiene las colecciones existentes
    try:
        existing_collections = retriever.get_existing_collections()
        print(f"Colecciones disponibles: {existing_collections}")
        
        if not existing_collections:
            print("No hay colecciones disponibles en la base de datos.")
            return
    except Exception as e:
        print(f"Error al obtener las colecciones: {str(e)}")
        return
    
    # Define algunas consultas de ejemplo
    queries = [
        "¿Cuáles son las mejores prácticas para el procesamiento de lenguaje natural?",
        "Explica el funcionamiento de los transformers en deep learning"
    ]
    
    # Selecciona colecciones para buscar (usando las existentes o un subconjunto)
    collections_to_search = existing_collections[:2] if len(existing_collections) > 1 else existing_collections
    
    print(f"\nRealizando búsqueda con las siguientes consultas:")
    for i, query in enumerate(queries, 1):
        print(f"{i}. {query}")
    
    print(f"\nEn las siguientes colecciones: {collections_to_search}")
    
    # Realiza la búsqueda
    try:
        print("\nBuscando información relevante...")
        results = retriever.search(queries=queries, collections=collections_to_search, top_k=3)
        context = retriever.extract_text_from_search_results(results)
        
        # Muestra los resultados
        print("\n--- RESULTADOS DE LA BÚSQUEDA ---")
        print(context)
        
    except ValueError as e:
        print(f"Error en la búsqueda: {str(e)}")
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()