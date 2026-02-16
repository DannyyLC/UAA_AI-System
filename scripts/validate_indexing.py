#!/usr/bin/env python3
"""
Script de validación del sistema de indexación.

Verifica que todos los componentes estén correctamente configurados.
"""

import asyncio
import os
import sys
from pathlib import Path

# Cargar variables de entorno desde .env
from dotenv import load_dotenv

load_dotenv()

# Colores para terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text: str):
    """Imprime encabezado."""
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def print_success(text: str):
    """Imprime mensaje de éxito."""
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text: str):
    """Imprime mensaje de error."""
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text: str):
    """Imprime advertencia."""
    print(f"{YELLOW}⚠️  {text}{RESET}")


def check_file_exists(file_path: str) -> bool:
    """Verifica que un archivo exista."""
    exists = Path(file_path).exists()
    if exists:
        print_success(f"Archivo encontrado: {file_path}")
    else:
        print_error(f"Archivo no encontrado: {file_path}")
    return exists


def check_env_var(var_name: str, required: bool = True) -> bool:
    """Verifica que una variable de entorno esté configurada."""
    value = os.getenv(var_name)
    if value:
        # Ocultar valores sensibles
        if "KEY" in var_name.upper() or "PASSWORD" in var_name.upper():
            display_value = f"{value[:8]}..." if len(value) > 8 else "***"
        else:
            display_value = value
        print_success(f"{var_name} = {display_value}")
        return True
    else:
        if required:
            print_error(f"{var_name} no está configurada")
        else:
            print_warning(f"{var_name} no configurada (opcional)")
        return not required


async def check_kafka_connection():
    """Verifica conexión a Kafka."""
    try:
        from aiokafka import AIOKafkaProducer

        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

        producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers, request_timeout_ms=5000)

        await producer.start()
        print_success(f"Conectado a Kafka: {bootstrap_servers}")
        await producer.stop()
        return True

    except Exception as e:
        print_error(f"Error conectando a Kafka: {e}")
        return False


async def check_postgres_connection():
    """Verifica conexión a PostgreSQL."""
    try:
        import asyncpg

        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print_error("DATABASE_URL no configurada")
            return False

        conn = await asyncpg.connect(db_url)

        # Verificar que la tabla indexing_jobs existe
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'indexing_jobs'
            )
            """)

        await conn.close()

        if result:
            print_success("Conectado a PostgreSQL - tabla indexing_jobs existe")
        else:
            print_warning("Conectado a PostgreSQL - tabla indexing_jobs NO existe")
            print_warning("  → Ejecuta: python scripts/init_db.py")

        return True

    except Exception as e:
        print_error(f"Error conectando a PostgreSQL: {e}")
        return False


async def check_qdrant_connection():
    """Verifica conexión a Qdrant."""
    try:
        from qdrant_client import AsyncQdrantClient

        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))

        client = AsyncQdrantClient(host=host, port=port)

        # Verificar colección documents
        collections = await client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if "documents" in collection_names:
            print_success(f"Conectado a Qdrant: {host}:{port} - colección 'documents' existe")
        else:
            print_warning(f"Conectado a Qdrant: {host}:{port} - colección 'documents' NO existe")
            print_warning("  → Se creará automáticamente al indexar primer documento")

        return True

    except Exception as e:
        print_error(f"Error conectando a Qdrant: {e}")
        return False


async def check_openai_api():
    """Verifica API key de OpenAI."""
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print_error("OPENAI_API_KEY no configurada")
            return False

        client = AsyncOpenAI(api_key=api_key)

        # Hacer request de prueba (lista de modelos)
        await client.models.list()

        print_success(f"OpenAI API Key válida (sk-...{api_key[-4:]})")
        return True

    except Exception as e:
        print_error(f"Error validando OpenAI API: {e}")
        return False


async def main():
    """Validación principal."""
    print_header("🔍 VALIDACIÓN DEL SISTEMA DE INDEXACIÓN")

    errors = []

    # 1. Verificar archivos críticos
    print_header("📁 Verificando archivos del sistema")

    critical_files = [
        "src/services/indexing/worker.py",
        "src/services/indexing/dlq_consumer.py",
        "src/services/indexing/launcher.py",
        "src/services/indexing/main.py",
        "src/services/indexing/database.py",
        "src/services/indexing/document_processor.py",
        "src/services/indexing/chunking.py",
        "src/services/indexing/embeddings.py",
        "src/services/indexing/qdrant_manager.py",
        "src/gateway/kafka_producer.py",
        "src/gateway/routes/documents.py",
        "scripts/create_kafka_topics.py",
    ]

    for file_path in critical_files:
        if not check_file_exists(file_path):
            errors.append(f"Archivo faltante: {file_path}")

    # 2. Verificar variables de entorno
    print_header("🔧 Verificando variables de entorno")

    required_vars = [
        "DATABASE_URL",
        "KAFKA_BOOTSTRAP_SERVERS",
        "OPENAI_API_KEY",
    ]

    optional_vars = [
        ("QDRANT_HOST", "localhost"),
        ("QDRANT_PORT", "6333"),
        ("KAFKA_INDEXING_QUEUE", "indexing.queue"),
        ("KAFKA_INDEXING_DLQ", "indexing.dlq"),
        ("INDEXING_WORKERS", "2"),
        ("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    ]

    for var in required_vars:
        if not check_env_var(var, required=True):
            errors.append(f"Variable requerida no configurada: {var}")

    for var, default in optional_vars:
        check_env_var(var, required=False)

    # 3. Verificar conexiones
    print_header("🌐 Verificando conexiones")

    print("\n🔌 PostgreSQL:")
    if not await check_postgres_connection():
        errors.append("No se pudo conectar a PostgreSQL")

    print("\n🔌 Qdrant:")
    if not await check_qdrant_connection():
        errors.append("No se pudo conectar a Qdrant")

    print("\n🔌 Kafka:")
    if not await check_kafka_connection():
        errors.append("No se pudo conectar a Kafka")

    print("\n🔌 OpenAI:")
    if not await check_openai_api():
        errors.append("OpenAI API Key inválida")

    # 4. Verificar directorio de uploads
    print_header("📦 Verificando directorios")

    uploads_dir = Path("data/uploads")
    if uploads_dir.exists():
        print_success(f"Directorio de uploads existe: {uploads_dir}")
    else:
        print_warning(f"Directorio de uploads no existe: {uploads_dir}")
        print_warning("  → Se creará automáticamente al subir primer documento")

    # Resumen final
    print_header("📊 RESUMEN")

    if errors:
        print(f"\n{RED}Se encontraron {len(errors)} errores:{RESET}\n")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print(f"\n{RED}❌ Sistema NO está listo{RESET}")
        print(f"\n{YELLOW}Soluciona los errores antes de iniciar el sistema{RESET}\n")
        sys.exit(1)
    else:
        print(f"\n{GREEN}✅ ¡Todo listo!{RESET}")
        print(f"\n{GREEN}El sistema de indexación está correctamente configurado{RESET}")
        print(f"\n{BLUE}Para iniciar el sistema:{RESET}")
        print(f"  1. Crear topics: {YELLOW}python scripts/create_kafka_topics.py{RESET}")
        print(f"  2. Iniciar workers: {YELLOW}python -m src.services.indexing.main{RESET}")
        print(f"  3. Iniciar gateway: {YELLOW}uvicorn src.gateway.main:app --reload{RESET}")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Validación interrumpida{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Error fatal: {e}{RESET}")
        sys.exit(1)
