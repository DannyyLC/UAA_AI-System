import torch
from typing import List, Dict
from langchain_chroma import Chroma
from chromadb import PersistentClient
from langchain_huggingface import HuggingFaceEmbeddings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

class Retrieval:
    """Módulo para buscar información en una o varias colecciones de ChromaDB con LangChain."""
    
    def __init__(self, persist_directory: str):
        """Inicializa el módulo con una base de datos vectorial en ChromaDB y define el modelo de embeddings."""
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.embedding_model = HuggingFaceEmbeddings(
            model_name="BAAI/bge-large-en-v1.5",
            model_kwargs={'device': device},
        )
        
        self.persist_directory = persist_directory
        self.client = PersistentClient(path=persist_directory)
        
        self.collection_instances = {}      
        self.existing_collections = set(self.client.list_collections())
        
        logger.info("Iniciando instancia de Retrieval")
        
    def _get_collection(self, collection_name: str) -> Chroma:
        """
        Obtiene una instancia de Chroma para la colección especificada si existe.
        
        Raises:
            ValueError: Si la colección no existe en la base de datos.
        """
        # Verificar primero si la colección existe
        if collection_name not in self.existing_collections:
            raise ValueError(f"La colección '{collection_name}' no existe en la base de datos.")
            
        # Usar el caché si ya tenemos la instancia
        if collection_name not in self.collection_instances:
            try:
                self.collection_instances[collection_name] = Chroma(
                    collection_name=collection_name,
                    client=self.client,
                    embedding_function=self.embedding_model
                )
            except Exception as e:
                raise ValueError(f"Error al acceder a la colección '{collection_name}': {str(e)}")
                
        return self.collection_instances[collection_name]
    
    def search(self, queries: List[str], collections: List[str], top_k: int = 3) -> Dict[str, Dict[str, List]]:
        """
        Realiza una búsqueda de similitud en múltiples colecciones existentes usando múltiples queries.
        
        Args:
            queries: Lista de consultas a buscar
            collections: Lista de nombres de colecciones donde buscar (deben existir)
            top_k: Número de resultados a devolver por consulta
            
        Returns:
            Un diccionario organizado por colección y consulta con los resultados
            
        Raises:
            ValueError: Si alguna de las colecciones especificadas no existe
        """
        logger.info("Comenzando la busqueda en la base de datos")
        results = {}
        
        self.existing_collections = set(self.client.list_collections())
        
        for collection_name in collections:
            try:
                collection_db = self._get_collection(collection_name)
                
                collection_results = {}
                for query in queries:
                    search_results = collection_db.similarity_search(query, k=top_k)
                    collection_results[query] = search_results
                
                results[collection_name] = collection_results
            except ValueError as e:
                raise e
        logger.info("Retornando la informacion obtenida")   
        return results
    
    def get_existing_collections(self) -> List[str]:
        """Devuelve la lista de nombres de colecciones existentes en la base de datos."""
        self.existing_collections = set(self.client.list_collections())
        return list(self.existing_collections)
    
    def extract_text_from_search_results(self, search_results: Dict[str, Dict[str, List]]) -> str:
        """
        Extrae todo el contenido textual de los resultados de búsqueda y lo combina en un solo string.
        
        Args:
            search_results: El diccionario retornado por la función search() que contiene
                        resultados organizados por colección y consulta
        
        Returns:
            str: Un string único con todo el contenido de texto extraído
        """
        extracted_text = []
        
        # Iterar por todas las colecciones
        for collection_name, collection_data in search_results.items():
            # Iterar por todas las consultas en esta colección
            for query, documents in collection_data.items():
                # Iterar por todos los documentos retornados
                for doc in documents:
                    # Extraer el texto del documento y agregarlo a nuestra lista
                    extracted_text.append(doc.page_content)
        
        # Unir todos los textos con un espacio entre ellos
        combined_text = " ".join(extracted_text)
        return combined_text
    