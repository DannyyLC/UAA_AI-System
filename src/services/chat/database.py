"""
Chat Repository — Queries de base de datos para gestión de conversaciones y mensajes.

Todas las operaciones usan el DatabaseManager compartido (asyncpg pool).
"""

from typing import Optional, List, Dict, Any
from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class ChatRepository:
    """Repositorio de datos para el servicio de chat."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ================================================================
    # CONVERSATIONS
    # ================================================================

    async def create_conversation(
        self, user_id: str, title: str = "Nueva conversación"
    ) -> Optional[Dict[str, Any]]:
        """
        Crea una nueva conversación para un usuario.
        
        Args:
            user_id: ID del usuario
            title: Título de la conversación
            
        Returns:
            Registro de la conversación creada
        """
        row = await self.db.fetchone(
            """
            INSERT INTO conversations (user_id, title)
            VALUES ($1::uuid, $2)
            RETURNING id, user_id, title, created_at, updated_at
            """,
            user_id,
            title,
        )
        return dict(row) if row else None

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una conversación por ID.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            Registro de la conversación
        """
        row = await self.db.fetchone(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE id = $1::uuid
            """,
            conversation_id,
        )
        return dict(row) if row else None

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lista las conversaciones de un usuario (ordenadas por más reciente).
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de conversaciones
            offset: Offset para paginación
            
        Returns:
            Lista de conversaciones
        """
        rows = await self.db.fetchall(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE user_id = $1::uuid
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )
        return [dict(row) for row in rows]

    async def count_conversations(self, user_id: str) -> int:
        """
        Cuenta el total de conversaciones de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Número total de conversaciones
        """
        count = await self.db.fetchval(
            """
            SELECT COUNT(*)
            FROM conversations
            WHERE user_id = $1::uuid
            """,
            user_id,
        )
        return count or 0

    async def update_conversation_title(
        self, conversation_id: str, title: str
    ) -> Optional[Dict[str, Any]]:
        """
        Actualiza el título de una conversación.
        
        Args:
            conversation_id: ID de la conversación
            title: Nuevo título
            
        Returns:
            Registro actualizado
        """
        row = await self.db.fetchone(
            """
            UPDATE conversations
            SET title = $2, updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING id, user_id, title, created_at, updated_at
            """,
            conversation_id,
            title,
        )
        return dict(row) if row else None

    async def update_conversation_timestamp(self, conversation_id: str) -> None:
        """
        Actualiza el timestamp de última modificación de una conversación.
        Se llama cada vez que se agrega un mensaje.
        
        Args:
            conversation_id: ID de la conversación
        """
        await self.db.execute(
            """
            UPDATE conversations
            SET updated_at = NOW()
            WHERE id = $1::uuid
            """,
            conversation_id,
        )

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Elimina una conversación y todos sus mensajes (CASCADE).
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            True si se eliminó, False si no existía
        """
        result = await self.db.execute(
            """
            DELETE FROM conversations
            WHERE id = $1::uuid
            """,
            conversation_id,
        )
        # asyncpg retorna el número de filas afectadas como string "DELETE N"
        return result != "DELETE 0"

    async def conversation_belongs_to_user(
        self, conversation_id: str, user_id: str
    ) -> bool:
        """
        Verifica que una conversación pertenezca a un usuario.
        
        Args:
            conversation_id: ID de la conversación
            user_id: ID del usuario
            
        Returns:
            True si la conversación pertenece al usuario
        """
        count = await self.db.fetchval(
            """
            SELECT COUNT(*)
            FROM conversations
            WHERE id = $1::uuid AND user_id = $2::uuid
            """,
            conversation_id,
            user_id,
        )
        return count > 0

    # ================================================================
    # MESSAGES
    # ================================================================

    async def create_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        used_rag: bool = False,
        sources: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Crea un nuevo mensaje en una conversación.
        
        Args:
            conversation_id: ID de la conversación
            role: Rol del mensaje ('user', 'assistant', 'system', 'tool')
            content: Contenido del mensaje
            used_rag: Si se usó RAG para generar este mensaje
            sources: Lista de fuentes consultadas (si used_rag=True)
            
        Returns:
            Registro del mensaje creado
        """
        if sources is None:
            sources = []
        
        row = await self.db.fetchone(
            """
            INSERT INTO messages (conversation_id, role, content, used_rag, sources)
            VALUES ($1::uuid, $2, $3, $4, $5)
            RETURNING id, conversation_id, role, content, used_rag, sources, created_at
            """,
            conversation_id,
            role,
            content,
            used_rag,
            sources,
        )
        
        # Actualizar timestamp de la conversación
        await self.update_conversation_timestamp(conversation_id)
        
        return dict(row) if row else None

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Obtiene los mensajes de una conversación (ordenados cronológicamente).
        
        Args:
            conversation_id: ID de la conversación
            limit: Número máximo de mensajes
            offset: Offset para paginación
            
        Returns:
            Lista de mensajes
        """
        rows = await self.db.fetchall(
            """
            SELECT id, conversation_id, role, content, used_rag, sources, created_at
            FROM messages
            WHERE conversation_id = $1::uuid
            ORDER BY created_at ASC
            LIMIT $2 OFFSET $3
            """,
            conversation_id,
            limit,
            offset,
        )
        return [dict(row) for row in rows]

    async def count_messages(self, conversation_id: str) -> int:
        """
        Cuenta el total de mensajes en una conversación.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            Número total de mensajes
        """
        count = await self.db.fetchval(
            """
            SELECT COUNT(*)
            FROM messages
            WHERE conversation_id = $1::uuid
            """,
            conversation_id,
        )
        return count or 0

    async def get_conversation_history(
        self, conversation_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el historial reciente de mensajes para contexto del LLM.
        
        Args:
            conversation_id: ID de la conversación
            limit: Número máximo de mensajes recientes
            
        Returns:
            Lista de mensajes en formato para LLM
        """
        rows = await self.db.fetchall(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT $2
            """,
            conversation_id,
            limit,
        )
        # Revertir para que queden en orden cronológico
        return [dict(row) for row in reversed(rows)]

    # ================================================================
    # TOPICS (para filtros de RAG)
    # ================================================================

    async def get_user_topics(self, user_id: str) -> List[str]:
        """
        Obtiene los temas únicos de documentos indexados por un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de temas únicos (ordenados alfabéticamente)
        """
        rows = await self.db.fetchall(
            """
            SELECT DISTINCT topic
            FROM indexing_jobs
            WHERE user_id = $1::uuid AND status = 'completed'
            ORDER BY topic
            """,
            user_id,
        )
        return [row["topic"] for row in rows]
