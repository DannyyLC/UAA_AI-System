"""
Configuración global del sistema.

Carga variables de entorno desde .env y expone un objeto `settings`
tipado con Pydantic Settings para todos los servicios.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración centralizada — se carga desde variables de entorno / .env"""

    # --- PostgreSQL ---
    database_url: str = Field(
        default="postgresql://rag_uaa:rag_uaa_secret@localhost:5432/rag_uaa",
        description="URL de conexión a PostgreSQL",
    )
    db_pool_min_size: int = Field(default=2, description="Conexiones mínimas en el pool")
    db_pool_max_size: int = Field(default=10, description="Conexiones máximas en el pool")

    # --- Qdrant ---
    qdrant_host: str = Field(default="localhost", description="Host de Qdrant")
    qdrant_port: int = Field(default=6333, description="Puerto REST de Qdrant")
    qdrant_grpc_port: int = Field(default=6334, description="Puerto gRPC de Qdrant")
    qdrant_collection_name: str = Field(default="documents", description="Nombre de la colección")

    # --- Kafka ---
    kafka_bootstrap_servers: str = Field(default="localhost:9092")

    # --- JWT / Auth ---
    jwt_secret: str = Field(default="cambiar-en-produccion-por-un-secreto-seguro")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60)
    jwt_refresh_expiration_days: int = Field(default=7)

    # --- LLM (LiteLLM) ---
    llm_model: str = Field(default="gpt-4o-mini")
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)

    # --- Puertos gRPC ---
    auth_grpc_port: int = Field(default=50051)
    chat_grpc_port: int = Field(default=50052)
    rag_grpc_port: int = Field(default=50054)

    # --- Gateway ---
    gateway_port: int = Field(default=8000)
    gateway_host: str = Field(default="0.0.0.0")

    # --- Embeddings ---
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Modelo de embeddings (OpenAI)",
    )
    embedding_dimension: int = Field(
        default=1536,
        description="Dimensión de los vectores (1536 para text-embedding-3-small)"
    )

    # --- General ---
    environment: str = Field(default="development")  # development | staging | production
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Singleton cacheado de la configuración."""
    return Settings()


# Instancia global para import directo
settings = get_settings()
