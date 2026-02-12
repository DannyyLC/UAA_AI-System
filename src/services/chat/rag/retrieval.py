"""
Sistema de Retrieval - Búsqueda semántica y construcción de contexto.

Responsable de:
- Generar embeddings de consultas
- Buscar en Qdrant con filtros
- Construir contexto para el LLM
"""

from typing import List, Dict, Any, Optional
import httpx

from src.services.chat.rag.qdrant_client import QdrantManager
from src.shared.configuration import settings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class RAGRetriever:
    """
    Retriever de contexto RAG.
    
    Flujo:
    1. Genera embedding de la consulta del usuario
    2. Busca chunks relevantes en Qdrant
    3. Construye contexto formateado para el LLM
    """
    
    def __init__(self, qdrant_manager: QdrantManager):
        """
        Inicializa el retriever.
        
        Args:
            qdrant_manager: Cliente de Qdrant ya conectado
        """
        self.qdrant = qdrant_manager
        self.embedding_model = settings.embedding_model
        self.embedding_api_key = settings.openai_api_key
        
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Genera embedding usando OpenAI API.
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            Vector de embedding
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.embedding_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": text,
                        "model": self.embedding_model
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                embedding = data["data"][0]["embedding"]
                
                logger.debug(f"Embedding generado: {len(embedding)} dimensiones")
                
                return embedding
                
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            raise
    
    async def search(
        self,
        query: str,
        user_id: str,
        topic: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Busca contexto relevante para una consulta.
        
        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            topic: Tema a buscar (opcional). Si es None, busca en todos los temas.
            limit: Número máximo de chunks a recuperar
            
        Returns:
            Diccionario con:
            {
                "context": "Contexto formateado para el LLM",
                "sources": ["file1.pdf (p.5)", "file2.pdf (p.12)", ...],
                "chunks": [lista de chunks originales]
            }
        """
        try:
            # 1. Generar embedding de la consulta
            logger.info(f"Generando embedding para: '{query[:50]}...'")
            query_vector = await self.generate_embedding(query)
            
            # 2. Buscar en Qdrant
            logger.info(f"Buscando en Qdrant (user_id={user_id}, topic={topic}, limit={limit})")
            chunks = await self.qdrant.search(
                query_vector=query_vector,
                user_id=user_id,
                topic=topic,
                limit=limit,
                score_threshold=0.7
            )
            
            if not chunks:
                logger.info("No se encontraron chunks relevantes")
                return {
                    "context": "",
                    "sources": [],
                    "chunks": []
                }
            
            # 3. Construir contexto
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(chunks, 1):
                # Formatear fuente
                source = f"{chunk['filename']}"
                if chunk.get('page'):
                    source += f" (p.{chunk['page']})"
                sources.append(source)
                
                # Formatear chunk para el contexto
                context_parts.append(
                    f"[Documento {i}: {source}]\\n"
                    f"{chunk['content']}\\n"
                )
            
            context = "\\n".join(context_parts)
            
            logger.info(f"Contexto construido: {len(chunks)} chunks, {len(context)} caracteres")
            
            return {
                "context": context,
                "sources": list(dict.fromkeys(sources)),  # Eliminar duplicados preservando orden
                "chunks": chunks
            }
            
        except Exception as e:
            logger.error(f"Error en retrieval: {e}")
            raise
    
    async def get_user_topics(self, user_id: str) -> List[str]:
        """
        Obtiene los temas únicos disponibles para un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de temas únicos
        """
        return await self.qdrant.get_user_topics(user_id)
