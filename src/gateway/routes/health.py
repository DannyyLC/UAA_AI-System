"""Routes de health check."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import grpc
from fastapi import APIRouter, Query, status

from src.gateway.grpc_clients.auth_client import auth_client
from src.gateway.grpc_clients.chat_client import chat_client
from src.gateway.kafka_producer import indexing_producer
from src.gateway.models import HealthResponse
from src.shared.database import DatabaseManager
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Verifica el estado del Gateway y sus dependencias",
)
async def health_check():
    """
    Endpoint de health check.

    Verifica:
    - Estado del Gateway
    - Conectividad con Auth Service
    - Conectividad con Chat Service
    - Conectividad con Kafka Producer
    - Conectividad con la base de datos PostgreSQL
    - Timestamp actual

    Retorna información sobre el estado de todos los servicios.
    """
    services_status = {}

    # Verificar Auth Service
    try:
        if not auth_client.stub:
            await auth_client.connect()
        services_status["auth_service"] = "connected"
    except Exception as e:
        logger.warning(f"Auth Service no disponible: {e}")
        services_status["auth_service"] = "disconnected"

    # Verificar Chat Service
    try:
        if not chat_client.stub:
            await chat_client.connect()
        services_status["chat_service"] = "connected"
    except Exception as e:
        logger.warning(f"Chat Service no disponible: {e}")
        services_status["chat_service"] = "disconnected"

    # Verificar Kafka Producer
    try:
        if not indexing_producer._producer:
            await indexing_producer.connect()
        services_status["kafka"] = "connected"
    except Exception as e:
        logger.warning(f"Kafka Producer no disponible: {e}")
        services_status["kafka"] = "disconnected"

    # Verificar base de datos PostgreSQL
    try:
        db = DatabaseManager()
        await db.fetchval("SELECT 1")
        services_status["database"] = "connected"
    except Exception as e:
        logger.warning(f"Base de datos no disponible: {e}")
        services_status["database"] = "disconnected"

    # Timestamp actual
    current_time = datetime.now(timezone.utc).isoformat()

    # Determinar estado general
    all_connected = all(s == "connected" for s in services_status.values())
    overall_status = "healthy" if all_connected else "degraded"

    return HealthResponse(
        status=overall_status, timestamp=current_time, version="1.0.0", services=services_status
    )


@router.get(
    "/model-performance",
    status_code=status.HTTP_200_OK,
    summary="Logs de rendimiento de modelos",
    description="Retorna los registros de la tabla model_performance_logs",
)
async def get_model_performance(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(50, ge=1, le=200, description="Registros por página"),
    model: Optional[str] = Query(None, description="Filtrar por modelo"),
    collection_name: Optional[str] = Query(None, description="Filtrar por colección"),
) -> Dict[str, Any]:
    """Retorna los registros de rendimiento de modelos con paginación opcional."""
    db = DatabaseManager()

    conditions: List[str] = []
    params: List[Any] = []

    if model:
        params.append(model)
        conditions.append(f"model = ${len(params)}")
    if collection_name:
        params.append(collection_name)
        conditions.append(f"collection_name = ${len(params)}")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    offset = (page - 1) * page_size
    params.extend([page_size, offset])

    query = f"""
        SELECT id, question, answer, expected_answer, similarity_score,
               collection_name, model, response_time_ms, user_id,
               conversation_id, created_at
        FROM model_performance_logs
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${len(params) - 1} OFFSET ${len(params)}
    """

    count_query = f"SELECT COUNT(*) FROM model_performance_logs {where_clause}"

    try:
        rows = await db.fetch(query, *params)
        total = await db.fetchval(count_query, *params[: len(params) - 2])
    except Exception as e:
        logger.error(f"Error consultando model_performance_logs: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Error consultando la base de datos")

    records = [dict(row) for row in rows]
    # Convertir tipos no serializables
    for r in records:
        for key, val in r.items():
            if hasattr(val, "isoformat"):
                r[key] = val.isoformat()
            elif hasattr(val, "__str__") and not isinstance(val, (str, int, float, bool, type(None))):
                r[key] = str(val)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "records": records,
    }


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root Endpoint",
    description="Endpoint raíz del API",
)
async def root():
    """Endpoint raíz."""
    return {
        "service": "RAG System API Gateway",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }
