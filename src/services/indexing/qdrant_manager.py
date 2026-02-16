"""
Qdrant Manager para indexación de documentos.

Maneja la creación de colecciones y el almacenamiento de embeddings.
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class QdrantIndexer:
    """
    Cliente de Qdrant para operaciones de indexación.
    
    Responsabilidades:
    - Crear/verificar colecciones
    - Indexar chunks con embeddings
    - Eliminar documentos
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        collection_name: str = None,
        vector_size: int = None,
    ):
        """
        Inicializa el cliente de Qdrant.
        
        Args:
            host: Host de Qdrant (default: desde env)
            port: Puerto de Qdrant (default: desde env)
            collection_name: Nombre de la colección (default: documents)
            vector_size: Dimensión de los vectores (default: 1536)
        """
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = int(port or os.getenv("QDRANT_PORT", "6333"))
        self.collection_name = collection_name or os.getenv(
            "QDRANT_COLLECTION_NAME", "documents"
        )
        self.vector_size = int(vector_size or os.getenv("EMBEDDING_DIMENSION", "1536"))
        
        self.client: Optional[QdrantClient] = None
    
    def connect(self) -> None:
        """Conecta con Qdrant y verifica/crea la colección."""
        try:
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                timeout=30.0,
            )
            
            logger.info(f"Conectado a Qdrant: {self.host}:{self.port}")
            
            # Verificar/crear colección
            self.ensure_collection()
            
        except Exception as e:
            logger.error(f"Error conectando a Qdrant: {e}")
            raise
    
    def ensure_collection(self) -> None:
        """Verifica que la colección existe, la crea si no."""
        try:
            # Intentar obtener info de la colección
            self.client.get_collection(self.collection_name)
            logger.info(f"Colección '{self.collection_name}' ya existe")
            
        except (UnexpectedResponse, Exception):
            # Colección no existe, crearla
            logger.info(
                f"Creando colección '{self.collection_name}' "
                f"(vector_size={self.vector_size})"
            )
            
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=20000,
                ),
                # Payload index para filtros rápidos
                # Se crean automáticamente para campos usados en filtros
            )
            
            logger.info(f"✅ Colección '{self.collection_name}' creada")
    
    def index_chunks(
        self,
        chunks: List[str],
        embeddings: List[List[float]],
        user_id: str,
        job_id: str,
        filename: str,
        topic: str,
        metadata: Dict[str, Any] = None,
    ) -> int:
        """
        Indexa chunks con sus embeddings en Qdrant.
        
        Args:
            chunks: Lista de textos de chunks
            embeddings: Lista de embeddings correspondientes
            user_id: ID del usuario
            job_id: ID del trabajo de indexación
            filename: Nombre del archivo original
            topic: Tema académico
            metadata: Metadata adicional opcional
            
        Returns:
            Número de chunks indexados
            
        Raises:
            ValueError: Si chunks y embeddings no coinciden en tamaño
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )
        
        if not chunks:
            logger.warning("No hay chunks para indexar")
            return 0
        
        metadata = metadata or {}
        
        # Preparar puntos para Qdrant
        points = []
        
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            point_id = str(uuid.uuid4())
            
            payload = {
                "user_id": user_id,
                "job_id": job_id,
                "source": filename,
                "topic": topic,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "text": chunk_text,
                "char_count": len(chunk_text),
                **metadata,
            }
            
            point = models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
            
            points.append(point)
        
        # Upsert en batches (100 por vez para evitar timeouts)
        batch_size = 100
        total_indexed = 0
        
        for batch_start in range(0, len(points), batch_size):
            batch_end = min(batch_start + batch_size, len(points))
            batch_points = points[batch_start:batch_end]
            
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points,
                    wait=True,  # Esperar confirmación
                )
                
                total_indexed += len(batch_points)
                
                logger.debug(
                    f"Batch indexado: {batch_start + 1}-{batch_end}/{len(points)}"
                )
                
            except Exception as e:
                logger.error(
                    f"Error indexando batch {batch_start}-{batch_end}: {e}"
                )
                raise
        
        logger.info(
            f"✅ {total_indexed} chunks indexados en Qdrant "
            f"(job={job_id}, user={user_id}, topic={topic})"
        )
        
        return total_indexed
    
    def delete_by_job(self, job_id: str) -> int:
        """
        Elimina todos los chunks de un trabajo específico.
        
        Args:
            job_id: ID del trabajo
            
        Returns:
            Número de puntos eliminados (estimado)
        """
        try:
            # Buscar puntos del job
            result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="job_id",
                            match=models.MatchValue(value=job_id),
                        )
                    ]
                ),
                limit=10000,  # Máximo por scroll
                with_payload=False,
                with_vectors=False,
            )
            
            points = result[0]
            point_ids = [point.id for point in points]
            
            if not point_ids:
                logger.info(f"No se encontraron puntos para job {job_id}")
                return 0
            
            # Eliminar puntos
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids,
                ),
                wait=True,
            )
            
            logger.info(f"🗑️  {len(point_ids)} chunks eliminados (job={job_id})")
            
            return len(point_ids)
            
        except Exception as e:
            logger.error(f"Error eliminando chunks del job {job_id}: {e}")
            raise
    
    def delete_by_user_and_topic(self, user_id: str, topic: str) -> int:
        """
        Elimina todos los chunks de un usuario en un tema específico.
        
        Args:
            user_id: ID del usuario
            topic: Tema académico
            
        Returns:
            Número de puntos eliminados (estimado)
        """
        try:
            # Buscar puntos
            result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id),
                        ),
                        models.FieldCondition(
                            key="topic",
                            match=models.MatchValue(value=topic),
                        ),
                    ]
                ),
                limit=10000,
                with_payload=False,
                with_vectors=False,
            )
            
            points = result[0]
            point_ids = [point.id for point in points]
            
            if not point_ids:
                return 0
            
            # Eliminar
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=point_ids,
                ),
                wait=True,
            )
            
            logger.info(
                f"🗑️  {len(point_ids)} chunks eliminados "
                f"(user={user_id}, topic={topic})"
            )
            
            return len(point_ids)
            
        except Exception as e:
            logger.error(f"Error eliminando chunks: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Obtiene información de la colección.
        
        Returns:
            Dict con info de la colección
        """
        try:
            info = self.client.get_collection(self.collection_name)
            
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo info de colección: {e}")
            return {}
    
    def close(self) -> None:
        """Cierra la conexión con Qdrant."""
        if self.client:
            self.client.close()
            logger.info("Conexión con Qdrant cerrada")
