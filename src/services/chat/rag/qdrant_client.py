"""
Cliente Qdrant para búsqueda semántica.

Maneja conexión y operaciones con el vector database.
"""

from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from src.shared.configuration import settings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class QdrantManager:
    """
    Cliente para interactuar con Qdrant.

    Configuración:
    - Collection name: "documents" (una sola colección para todo)
    - Filtros: user_id (UUID) y topic (string)
    - Vector dimension: según el modelo de embeddings (ej: 1536 para text-embedding-3-small)
    """

    def __init__(self):
        """Inicializa conexión con Qdrant."""
        self.client: QdrantClient = None
        self.collection_name = settings.qdrant_collection_name
        self.vector_size = settings.embedding_dimension

    def connect(self):
        """Establece conexión con Qdrant."""
        try:
            self.client = QdrantClient(
                host=settings.qdrant_host, port=settings.qdrant_port, timeout=10.0
            )
            logger.info(f"Conectado a Qdrant: {settings.qdrant_host}:{settings.qdrant_port}")

            # Verificar/crear colección
            self._ensure_collection()

        except Exception as e:
            logger.error(f"Error conectando a Qdrant: {e}")
            raise

    def _ensure_collection(self):
        """Crea la colección si no existe."""
        try:
            # Verificar si la colección existe
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)

            if not collection_exists:
                logger.info(f"Creando colección: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
                )

                # Crear índices para filtros
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="user_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="topic",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

                logger.info(f"Colección '{self.collection_name}' creada con índices")
            else:
                logger.info(f"Colección '{self.collection_name}' ya existe")

        except Exception as e:
            logger.error(f"Error verificando/creando colección: {e}")
            raise

    async def search(
        self,
        query_vector: List[float],
        user_id: str,
        topic: Optional[str] = None,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos similares con filtros.

        Args:
            query_vector: Vector de embedding de la consulta
            user_id: ID del usuario (filtro obligatorio)
            topic: Tema específico (filtro opcional)
            limit: Número máximo de resultados
            score_threshold: Score mínimo para considerar resultados

        Returns:
            Lista de resultados con formato:
            [
                {
                    "id": "punto_id",
                    "score": 0.95,
                    "content": "texto del chunk",
                    "topic": "Matemáticas",
                    "filename": "calculo.pdf",
                    "page": 5
                },
                ...
            ]
        """
        try:
            # Construir filtros
            filter_conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]

            # Agregar filtro de tema si se especifica
            if topic:
                filter_conditions.append(FieldCondition(key="topic", match=MatchValue(value=topic)))

            query_filter = Filter(must=filter_conditions)

            # Realizar búsqueda
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
            )

            # Formatear resultados
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "id": result.id,
                        "score": result.score,
                        "content": result.payload.get("content", ""),
                        "topic": result.payload.get("topic", ""),
                        "filename": result.payload.get("filename", ""),
                        "page": result.payload.get("page"),
                        "chunk_index": result.payload.get("chunk_index"),
                    }
                )

            logger.info(
                f"Búsqueda en Qdrant: {len(formatted_results)} resultados "
                f"(user_id={user_id}, topic={topic}, threshold={score_threshold})"
            )

            return formatted_results

        except Exception as e:
            logger.error(f"Error en búsqueda Qdrant: {e}")
            raise

    async def get_user_topics(self, user_id: str) -> List[str]:
        """
        Obtiene los temas únicos disponibles para un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de temas únicos (strings)
        """
        try:
            # Scroll por todos los puntos del usuario
            # Esto puede ser ineficiente con muchos documentos,
            # idealmente se obtendría desde la DB (indexing_jobs)

            filter_condition = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
            )

            # Scroll para obtener todos los puntos
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=1000,  # Ajustar según necesidad
                with_payload=["topic"],
                with_vectors=False,
            )

            # Extraer temas únicos
            topics = set()
            for point in points:
                if "topic" in point.payload:
                    topics.add(point.payload["topic"])

            topics_list = sorted(list(topics))

            logger.info(f"Temas encontrados para user {user_id}: {topics_list}")

            return topics_list

        except Exception as e:
            logger.error(f"Error obteniendo temas del usuario: {e}")
            return []

    def close(self):
        """Cierra la conexión con Qdrant."""
        if self.client:
            self.client.close()
            logger.info("Conexión con Qdrant cerrada")
