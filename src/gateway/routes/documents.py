"""
Routes de gestión de documentos e indexación.
"""

import os
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import (
    APIRouter,
    HTTPException,
    status,
    Depends,
    UploadFile,
    File,
    Form,
    Query,
)
from src.gateway.models import (
    UserResponse,
    ErrorResponse,
)
from src.gateway.dependencies import get_current_user
from src.gateway.kafka_producer import indexing_producer
from src.services.indexing.database import IndexingRepository, JobStatus
from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documentos"])

# Configuración
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "20")) * 1024 * 1024  # 20 MB
UPLOADS_DIR = Path(os.getenv("UPLOADS_PATH", "data/uploads"))
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}

# Crear directorio de uploads si no existe
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_indexing_repo() -> IndexingRepository:
    """Dependency: Repositorio de trabajos de indexación."""
    db = DatabaseManager()
    return IndexingRepository(db)


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"description": "Documento aceptado para indexación"},
        400: {"model": ErrorResponse, "description": "Archivo inválido"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
        413: {"model": ErrorResponse, "description": "Archivo muy grande"},
        422: {"model": ErrorResponse, "description": "Datos inválidos"},
        503: {"model": ErrorResponse, "description": "Servicio no disponible"},
    },
    summary="Subir documento para indexación",
    description="Acepta un documento y lo encola para procesamiento asíncrono",
)
async def upload_document(
    file: UploadFile = File(..., description="Archivo a indexar"),
    topic: str = Form(..., description="Tema académico del documento"),
    current_user: UserResponse = Depends(get_current_user),
    repo: IndexingRepository = Depends(get_indexing_repo),
):
    """
    Sube un documento para indexación.
    
    - **file**: Archivo (PDF, TXT, MD, DOCX)
    - **topic**: Tema académico (ej: matematicas, programacion, fisica)
    
    El documento se guarda en disco y se encola en Kafka para procesamiento asíncrono.
    Retorna el job_id para consultar el estado posteriormente.
    """
    try:
        # Validar que hay archivo
        if not file or not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionó ningún archivo",
            )
        
        # Validar extensión
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extensión no permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}",
            )
        
        # Validar MIME type
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido. Permitidos: PDF, TXT, MD, DOCX",
            )
        
        # Generar job_id único
        job_id = str(uuid.uuid4())
        
        # Crear directorio para el usuario
        user_dir = UPLOADS_DIR / current_user.id / job_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Sanitizar nombre de archivo
        safe_filename = "".join(
            c for c in file.filename if c.isalnum() or c in "._- "
        ).rstrip()
        if not safe_filename:
            safe_filename = f"document{file_ext}"
        
        # Guardar archivo en disco
        file_path = user_dir / safe_filename
        
        # Leer y guardar por chunks para evitar consumir mucha memoria
        file_size = 0
        try:
            with open(file_path, "wb") as f:
                while chunk := await file.read(8192):  # 8 KB chunks
                    file_size += len(chunk)
                    
                    # Validar tamaño máximo
                    if file_size > MAX_FILE_SIZE:
                        # Eliminar archivo parcial
                        file_path.unlink()
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Archivo muy grande. Máximo: {MAX_FILE_SIZE // 1024 // 1024} MB",
                        )
                    
                    f.write(chunk)
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error guardando archivo: {e}")
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando el archivo",
            )
        
        logger.info(
            f"Archivo guardado: {file_path} ({file_size} bytes) para user {current_user.id}"
        )
        
        # Crear registro en base de datos
        job = await repo.create_job(
            job_id=job_id,
            user_id=current_user.id,
            filename=safe_filename,
            topic=topic,
            mime_type=mime_type,
            file_size=file_size,
        )
        
        if not job:
            # Limpiar archivo si falla la creación del job
            file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creando el trabajo de indexación",
            )
        
        # Publicar en Kafka
        published = await indexing_producer.publish_indexing_job(
            job_id=job_id,
            user_id=current_user.id,
            file_path=str(file_path),
            filename=safe_filename,
            mime_type=mime_type,
            topic=topic,
            metadata={
                "file_size": file_size,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "user_email": current_user.email,
            },
        )
        
        if not published:
            logger.error(f"Error publicando job {job_id} en Kafka")
            # No eliminamos el archivo ni el registro, se puede reintentar
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Error encolando el documento. Intente nuevamente.",
            )
        
        logger.info(f"Job {job_id} encolado exitosamente para user {current_user.id}")
        
        return {
            "job_id": job_id,
            "filename": safe_filename,
            "topic": topic,
            "status": JobStatus.PENDING,
            "message": "Documento aceptado. El procesamiento comenzará pronto.",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor",
        )


@router.get(
    "/jobs/{job_id}",
    responses={
        200: {"description": "Estado del trabajo"},
        404: {"model": ErrorResponse, "description": "Trabajo no encontrado"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
    },
    summary="Consultar estado de un trabajo",
    description="Obtiene el estado actual de un trabajo de indexación",
)
async def get_job_status(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user),
    repo: IndexingRepository = Depends(get_indexing_repo),
):
    """
    Consulta el estado de un trabajo de indexación.
    
    - **job_id**: ID del trabajo retornado al subir el documento
    
    Retorna: status, progreso, chunks creados, errores (si los hay)
    """
    try:
        job = await repo.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trabajo no encontrado",
            )
        
        # Verificar que el job pertenece al usuario actual
        if job["user_id"] != uuid.UUID(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trabajo no encontrado",
            )
        
        return {
            "job_id": str(job["id"]),
            "filename": job["filename"],
            "topic": job["topic"],
            "status": job["status"],
            "chunks_created": job["chunks_created"],
            "error_message": job["error_message"],
            "created_at": job["created_at"].isoformat(),
            "updated_at": job["updated_at"].isoformat(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error consultando job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando el estado del trabajo",
        )


@router.get(
    "/jobs",
    responses={
        200: {"description": "Lista de trabajos"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
    },
    summary="Listar trabajos de indexación",
    description="Lista los trabajos de indexación del usuario con filtros opcionales",
)
async def list_jobs(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filtrar por estado"
    ),
    topic_filter: Optional[str] = Query(
        None, alias="topic", description="Filtrar por tema"
    ),
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    current_user: UserResponse = Depends(get_current_user),
    repo: IndexingRepository = Depends(get_indexing_repo),
):
    """
    Lista los trabajos de indexación del usuario.
    
    Filtros opcionales:
    - **status**: pending, processing, completed, failed, cancelled
    - **topic**: tema académico
    
    Paginación:
    - **page**: número de página (default: 1)
    - **page_size**: elementos por página (default: 20, max: 100)
    """
    try:
        offset = (page - 1) * page_size
        
        jobs = await repo.list_jobs(
            user_id=current_user.id,
            status=status_filter,
            topic=topic_filter,
            limit=page_size,
            offset=offset,
        )
        
        total = await repo.count_jobs(
            user_id=current_user.id,
            status=status_filter,
            topic=topic_filter,
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "jobs": [
                {
                    "job_id": str(job["id"]),
                    "filename": job["filename"],
                    "topic": job["topic"],
                    "status": job["status"],
                    "chunks_created": job["chunks_created"],
                    "error_message": job["error_message"],
                    "created_at": job["created_at"].isoformat(),
                    "updated_at": job["updated_at"].isoformat(),
                }
                for job in jobs
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
        }
    
    except Exception as e:
        logger.error(f"Error listando jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando los trabajos",
        )


@router.delete(
    "/jobs/{job_id}",
    responses={
        200: {"description": "Trabajo cancelado"},
        404: {"model": ErrorResponse, "description": "Trabajo no encontrado"},
        409: {"model": ErrorResponse, "description": "No se puede cancelar"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
    },
    summary="Cancelar trabajo de indexación",
    description="Cancela un trabajo pendiente o en proceso",
)
async def cancel_job(
    job_id: str,
    current_user: UserResponse = Depends(get_current_user),
    repo: IndexingRepository = Depends(get_indexing_repo),
):
    """
    Cancela un trabajo de indexación.
    
    Solo se pueden cancelar trabajos en estado PENDING o PROCESSING.
    """
    try:
        job = await repo.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trabajo no encontrado",
            )
        
        # Verificar pertenencia
        if job["user_id"] != uuid.UUID(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trabajo no encontrado",
            )
        
        # Verificar que se puede cancelar
        if job["status"] not in [JobStatus.PENDING, JobStatus.PROCESSING]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"No se puede cancelar un trabajo en estado {job['status']}",
            )
        
        # Cancelar
        success = await repo.mark_cancelled(job_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error cancelando el trabajo",
            )
        
        logger.info(f"Job {job_id} cancelado por user {current_user.id}")
        
        return {
            "job_id": job_id,
            "status": JobStatus.CANCELLED,
            "message": "Trabajo cancelado exitosamente",
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelando job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cancelando el trabajo",
        )


@router.get(
    "/sources",
    responses={
        200: {"description": "Lista de documentos indexados"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
    },
    summary="Listar documentos indexados",
    description="Lista los documentos completamente indexados del usuario",
)
async def list_sources(
    topic: Optional[str] = Query(None, description="Filtrar por tema"),
    current_user: UserResponse = Depends(get_current_user),
    repo: IndexingRepository = Depends(get_indexing_repo),
):
    """
    Lista documentos completamente indexados.
    
    Opcionalmente filtrado por tema académico.
    """
    try:
        sources = await repo.list_completed_sources(
            user_id=current_user.id,
            topic=topic,
        )
        
        # Agrupar por tema
        by_topic = {}
        for source in sources:
            topic_key = source["topic"]
            if topic_key not in by_topic:
                by_topic[topic_key] = []
            by_topic[topic_key].append({
                "job_id": str(source["id"]),
                "filename": source["filename"],
                "chunks": source["chunks_created"],
                "indexed_at": source["updated_at"].isoformat(),
            })
        
        return {
            "topics": list(by_topic.keys()),
            "sources": by_topic,
            "total": len(sources),
        }
    
    except Exception as e:
        logger.error(f"Error listando sources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando los documentos",
        )


@router.get(
    "/stats",
    responses={
        200: {"description": "Estadísticas de indexación"},
        401: {"model": ErrorResponse, "description": "No autenticado"},
    },
    summary="Estadísticas de indexación",
    description="Obtiene estadísticas de trabajos del usuario",
)
async def get_stats(
    current_user: UserResponse = Depends(get_current_user),
    repo: IndexingRepository = Depends(get_indexing_repo),
):
    """
    Obtiene estadísticas de indexación del usuario.
    
    Retorna contadores por estado y totales.
    """
    try:
        stats = await repo.get_stats(current_user.id)
        
        return {
            "pending": stats.get("pending", 0),
            "processing": stats.get("processing", 0),
            "completed": stats.get("completed", 0),
            "failed": stats.get("failed", 0),
            "cancelled": stats.get("cancelled", 0),
            "total_jobs": stats.get("total", 0),
            "total_chunks": stats.get("total_chunks", 0),
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo estadísticas",
        )
