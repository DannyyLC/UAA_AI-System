"""
Indexing Repository — Queries de base de datos para gestión de trabajos de indexación.

Maneja la tabla indexing_jobs en PostgreSQL.
"""

from typing import Any, Dict, List, Optional

from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


# Estados de los trabajos
class JobStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class IndexingRepository:
    """Repositorio de datos para trabajos de indexación."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    # ================================================================
    # CREATE
    # ================================================================

    async def create_job(
        self,
        job_id: str,
        user_id: str,
        filename: str,
        topic: str,
        mime_type: str,
        file_size: int = 0,
    ) -> Optional[Dict[str, Any]]:
        """
        Crea un nuevo trabajo de indexación con estado PENDING.

        Args:
            job_id: ID único del trabajo (UUID)
            user_id: ID del usuario
            filename: Nombre del archivo original
            topic: Tema académico
            mime_type: Tipo MIME del archivo
            file_size: Tamaño del archivo en bytes

        Returns:
            Registro del trabajo creado
        """
        row = await self.db.fetchone(
            """
            INSERT INTO indexing_jobs (
                id, user_id, filename, topic, mime_type, 
                status, chunks_created, created_at, updated_at
            )
            VALUES (
                $1::uuid, $2::uuid, $3, $4, $5,
                $6, 0, NOW(), NOW()
            )
            RETURNING id, user_id, filename, topic, mime_type, 
                      status, chunks_created, error_message, 
                      created_at, updated_at
            """,
            job_id,
            user_id,
            filename,
            topic,
            mime_type,
            JobStatus.PENDING,
        )

        if row:
            logger.info(f"Job creado: {job_id} - {filename} (user={user_id}, topic={topic})")

        return dict(row) if row else None

    # ================================================================
    # READ
    # ================================================================

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un trabajo por su ID.

        Args:
            job_id: ID del trabajo

        Returns:
            Registro del trabajo o None
        """
        row = await self.db.fetchone(
            """
            SELECT id, user_id, filename, topic, mime_type,
                   status, chunks_created, error_message,
                   created_at, updated_at
            FROM indexing_jobs
            WHERE id = $1::uuid
            """,
            job_id,
        )
        return dict(row) if row else None

    async def list_jobs(
        self,
        user_id: str,
        status: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Lista trabajos de un usuario con filtros opcionales.

        Args:
            user_id: ID del usuario
            status: Filtro por estado (opcional)
            topic: Filtro por tema (opcional)
            limit: Límite de resultados
            offset: Offset para paginación

        Returns:
            Lista de trabajos
        """
        # Construir query dinámicamente según filtros
        conditions = ["user_id = $1::uuid"]
        params = [user_id]
        param_count = 1

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)

        if topic:
            param_count += 1
            conditions.append(f"topic = ${param_count}")
            params.append(topic)

        param_count += 1
        limit_param = f"${param_count}"
        params.append(limit)

        param_count += 1
        offset_param = f"${param_count}"
        params.append(offset)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT id, user_id, filename, topic, mime_type,
                   status, chunks_created, error_message,
                   created_at, updated_at
            FROM indexing_jobs
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT {limit_param} OFFSET {offset_param}
        """

        rows = await self.db.fetch(query, *params)
        return [dict(row) for row in rows]

    async def count_jobs(
        self,
        user_id: str,
        status: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> int:
        """
        Cuenta el total de trabajos de un usuario.

        Args:
            user_id: ID del usuario
            status: Filtro por estado (opcional)
            topic: Filtro por tema (opcional)

        Returns:
            Número total de trabajos
        """
        conditions = ["user_id = $1::uuid"]
        params = [user_id]
        param_count = 1

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)

        if topic:
            param_count += 1
            conditions.append(f"topic = ${param_count}")
            params.append(topic)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT COUNT(*)
            FROM indexing_jobs
            WHERE {where_clause}
        """

        count = await self.db.fetchval(query, *params)
        return count or 0

    async def list_completed_sources(
        self, user_id: str, topic: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista documentos completamente indexados de un usuario.

        Args:
            user_id: ID del usuario
            topic: Filtro opcional por tema

        Returns:
            Lista de fuentes indexadas
        """
        if topic:
            rows = await self.db.fetch(
                """
                SELECT id, filename, topic, chunks_created, created_at, updated_at
                FROM indexing_jobs
                WHERE user_id = $1::uuid 
                  AND status = $2 
                  AND topic = $3
                ORDER BY updated_at DESC
                """,
                user_id,
                JobStatus.COMPLETED,
                topic,
            )
        else:
            rows = await self.db.fetch(
                """
                SELECT id, filename, topic, chunks_created, created_at, updated_at
                FROM indexing_jobs
                WHERE user_id = $1::uuid AND status = $2
                ORDER BY updated_at DESC
                """,
                user_id,
                JobStatus.COMPLETED,
            )

        return [dict(row) for row in rows]

    async def get_topics_by_user(self, user_id: str) -> List[str]:
        """
        Obtiene los temas únicos de documentos indexados por un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Lista de temas únicos
        """
        rows = await self.db.fetch(
            """
            SELECT DISTINCT topic
            FROM indexing_jobs
            WHERE user_id = $1::uuid AND status = $2
            ORDER BY topic
            """,
            user_id,
            JobStatus.COMPLETED,
        )
        return [row["topic"] for row in rows]

    async def find_completed_job_by_filename(
        self, user_id: str, filename: str, topic: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Busca un trabajo completado por nombre de archivo.

        Args:
            user_id: ID del usuario
            filename: Nombre del archivo
            topic: Filtro opcional por tema

        Returns:
            Registro del trabajo o None
        """
        if topic:
            row = await self.db.fetchone(
                """
                SELECT id, user_id, filename, topic, mime_type,
                       status, chunks_created, error_message,
                       created_at, updated_at
                FROM indexing_jobs
                WHERE user_id = $1::uuid 
                  AND filename = $2 
                  AND topic = $3
                  AND status = $4
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                user_id,
                filename,
                topic,
                JobStatus.COMPLETED,
            )
        else:
            row = await self.db.fetchone(
                """
                SELECT id, user_id, filename, topic, mime_type,
                       status, chunks_created, error_message,
                       created_at, updated_at
                FROM indexing_jobs
                WHERE user_id = $1::uuid 
                  AND filename = $2
                  AND status = $3
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                user_id,
                filename,
                JobStatus.COMPLETED,
            )

        return dict(row) if row else None

    # ================================================================
    # UPDATE
    # ================================================================

    async def update_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Actualiza el estado de un trabajo.

        Args:
            job_id: ID del trabajo
            status: Nuevo estado
            error_message: Mensaje de error (si aplica)

        Returns:
            True si se actualizó correctamente
        """
        result = await self.db.execute(
            """
            UPDATE indexing_jobs
            SET status = $1,
                error_message = $2,
                updated_at = NOW()
            WHERE id = $3::uuid
            """,
            status,
            error_message,
            job_id,
        )

        success = result == "UPDATE 1"
        if success:
            logger.info(f"Job {job_id} actualizado a estado: {status}")

        return success

    async def update_progress(self, job_id: str, chunks_created: int) -> bool:
        """
        Actualiza el progreso de un trabajo (número de chunks creados).

        Args:
            job_id: ID del trabajo
            chunks_created: Número de chunks generados

        Returns:
            True si se actualizó correctamente
        """
        result = await self.db.execute(
            """
            UPDATE indexing_jobs
            SET chunks_created = $1,
                updated_at = NOW()
            WHERE id = $2::uuid
            """,
            chunks_created,
            job_id,
        )

        return result == "UPDATE 1"

    async def mark_completed(self, job_id: str, chunks_created: int) -> bool:
        """
        Marca un trabajo como completado exitosamente.

        Args:
            job_id: ID del trabajo
            chunks_created: Total de chunks generados

        Returns:
            True si se actualizó correctamente
        """
        result = await self.db.execute(
            """
            UPDATE indexing_jobs
            SET status = $1,
                chunks_created = $2,
                error_message = NULL,
                updated_at = NOW()
            WHERE id = $3::uuid
            """,
            JobStatus.COMPLETED,
            chunks_created,
            job_id,
        )

        success = result == "UPDATE 1"
        if success:
            logger.info(f"Job {job_id} completado: {chunks_created} chunks creados")

        return success

    async def mark_failed(self, job_id: str, error_message: str) -> bool:
        """
        Marca un trabajo como fallido.

        Args:
            job_id: ID del trabajo
            error_message: Descripción del error

        Returns:
            True si se actualizó correctamente
        """
        result = await self.db.execute(
            """
            UPDATE indexing_jobs
            SET status = $1,
                error_message = $2,
                updated_at = NOW()
            WHERE id = $3::uuid
            """,
            JobStatus.FAILED,
            error_message,
            job_id,
        )

        success = result == "UPDATE 1"
        if success:
            logger.error(f"Job {job_id} falló: {error_message}")

        return success

    async def mark_cancelled(self, job_id: str) -> bool:
        """
        Marca un trabajo como cancelado.

        Args:
            job_id: ID del trabajo

        Returns:
            True si se actualizó correctamente
        """
        result = await self.db.execute(
            """
            UPDATE indexing_jobs
            SET status = $1,
                updated_at = NOW()
            WHERE id = $2::uuid
            AND status IN ($3, $4)
            """,
            JobStatus.CANCELLED,
            job_id,
            JobStatus.PENDING,
            JobStatus.PROCESSING,
        )

        success = result == "UPDATE 1"
        if success:
            logger.info(f"Job {job_id} cancelado")

        return success

    # ================================================================
    # DELETE
    # ================================================================

    async def delete_job(self, job_id: str) -> bool:
        """
        Elimina un trabajo de la base de datos.

        Args:
            job_id: ID del trabajo

        Returns:
            True si se eliminó correctamente
        """
        result = await self.db.execute(
            """
            DELETE FROM indexing_jobs
            WHERE id = $1::uuid
            """,
            job_id,
        )

        success = result == "DELETE 1"
        if success:
            logger.info(f"Job {job_id} eliminado de la base de datos")

        return success

    # ================================================================
    # STATS
    # ================================================================

    async def get_stats(self, user_id: str) -> Dict[str, int]:
        """
        Obtiene estadísticas de trabajos de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            Diccionario con contadores por estado
        """
        row = await self.db.fetchone(
            """
            SELECT 
                COUNT(*) FILTER (WHERE status = $2) as pending,
                COUNT(*) FILTER (WHERE status = $3) as processing,
                COUNT(*) FILTER (WHERE status = $4) as completed,
                COUNT(*) FILTER (WHERE status = $5) as failed,
                COUNT(*) FILTER (WHERE status = $6) as cancelled,
                COUNT(*) as total,
                COALESCE(SUM(chunks_created), 0) as total_chunks
            FROM indexing_jobs
            WHERE user_id = $1::uuid
            """,
            user_id,
            JobStatus.PENDING,
            JobStatus.PROCESSING,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        )

        return dict(row) if row else {}
