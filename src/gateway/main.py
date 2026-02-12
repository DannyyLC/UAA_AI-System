"""
API Gateway - RAG System UAA

Gateway REST que orquesta las llamadas a los microservicios gRPC.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from src.gateway.middleware.cors import setup_cors
from src.gateway.routes import auth, health, chat
from src.gateway.grpc_clients.auth_client import auth_client
from src.gateway.grpc_clients.chat_client import chat_client
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager para el ciclo de vida de la aplicación.
    
    Maneja la inicialización y limpieza de recursos:
    - Conexión con servicios gRPC
    - Limpieza al cerrar
    """
    # Startup
    logger.info("Iniciando API Gateway...")
    
    try:
        # Conectar con Auth Service
        await auth_client.connect()
        logger.info("Conectado a Auth Service")
    except Exception as e:
        logger.error(f"Error conectando a Auth Service: {e}")
        logger.warning("Gateway iniciando en modo degradado")
    
    try:
        # Conectar con Chat Service
        await chat_client.connect()
        logger.info("Conectado a Chat Service")
    except Exception as e:
        logger.error(f"Error conectando a Chat Service: {e}")
        logger.warning("Chat Service no disponible")
    
    logger.info("API Gateway listo")
    
    yield
    
    # Shutdown
    logger.info("Cerrando API Gateway...")
    
    try:
        await auth_client.close()
        await chat_client.close()
        logger.info("Conexiones gRPC cerradas")
    except Exception as e:
        logger.error(f"Error cerrando conexiones: {e}")
    
    logger.info("API Gateway cerrado")


# Crear aplicación FastAPI
app = FastAPI(
    title="RAG System API Gateway",
    description="""
    API Gateway para el sistema RAG distribuido de la UAA.
    
    ## Características
    
    * **Autenticación JWT**: Registro, login y logout con cookies httpOnly
    * **CORS**: Configurado para desarrollo local
    * **Microservicios**: Orquestación de llamadas gRPC
    * **Documentación**: OpenAPI/Swagger automática
    
    ## Autenticación
    
    El sistema utiliza tokens JWT almacenados en cookies httpOnly para mayor seguridad.
    Los endpoints protegidos requieren estar autenticado previamente.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configurar CORS
setup_cors(app)

# Registrar routers
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


# ============================================================
# Exception Handlers
# ============================================================

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handler para excepciones HTTP."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": str(exc.detail),
            "status_code": exc.status_code
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handler para errores de validación de Pydantic."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Datos de entrada inválidos",
            "detail": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler para excepciones generales no capturadas."""
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Error interno del servidor",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else None
        }
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    reload = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Iniciando servidor en {host}:{port}")
    
    uvicorn.run(
        "src.gateway.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
