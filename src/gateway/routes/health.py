"""Routes de health check."""

from fastapi import APIRouter, status
from datetime import datetime, timezone
import grpc

from src.gateway.models import HealthResponse
from src.gateway.grpc_clients.auth_client import auth_client
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Verifica el estado del Gateway y sus dependencias"
)
async def health_check():
    """
    Endpoint de health check.
    
    Verifica:
    - Estado del Gateway
    - Conectividad con Auth Service
    - Timestamp actual
    
    Retorna información sobre el estado de todos los servicios.
    """
    services_status = {}
    
    # Verificar Auth Service
    try:
        # Intentar conectar al Auth Service
        if not auth_client.stub:
            await auth_client.connect()
        services_status["auth_service"] = "connected"
    except Exception as e:
        logger.warning(f"Auth Service no disponible: {e}")
        services_status["auth_service"] = "disconnected"
    
    # Timestamp actual
    current_time = datetime.now(timezone.utc).isoformat()
    
    # Determinar estado general
    all_connected = all(
        status == "connected" 
        for status in services_status.values()
    )
    overall_status = "healthy" if all_connected else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=current_time,
        version="1.0.0",
        services=services_status
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root Endpoint",
    description="Endpoint raíz del API"
)
async def root():
    """Endpoint raíz."""
    return {
        "service": "RAG System API Gateway",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }
