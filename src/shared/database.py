"""
Cliente PostgreSQL con pool de conexiones async.

Usa asyncpg para conexiones asíncronas con pool.
Provee un DatabaseManager singleton para uso compartido entre servicios.
"""

import asyncpg
from typing import Any, Optional
from src.shared.configuration import settings
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Gestiona el pool de conexiones a PostgreSQL.

    Uso:
        db = DatabaseManager()
        await db.connect()
        row = await db.fetchone("SELECT * FROM users WHERE id = $1", user_id)
        await db.disconnect()
    """

    _instance: Optional["DatabaseManager"] = None
    _pool: Optional[asyncpg.Pool] = None

    def __new__(cls) -> "DatabaseManager":
        """Singleton — una sola instancia por proceso."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self, dsn: Optional[str] = None) -> None:
        """Inicializa el pool de conexiones."""
        if self._pool is not None:
            logger.debug("Pool de conexiones ya inicializado")
            return

        dsn = dsn or settings.database_url
        try:
            self._pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                command_timeout=30,
            )
            logger.info("Pool de conexiones PostgreSQL inicializado")
        except Exception as e:
            logger.error(f"Error al conectar a PostgreSQL: {e}")
            raise

    async def disconnect(self) -> None:
        """Cierra el pool de conexiones."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            DatabaseManager._instance = None
            logger.info("Pool de conexiones PostgreSQL cerrado")

    @property
    def pool(self) -> asyncpg.Pool:
        """Retorna el pool, lanzando error si no está conectado."""
        if self._pool is None:
            raise RuntimeError(
                "DatabaseManager no conectado. Llama a connect() primero."
            )
        return self._pool

    # ----------------------------------------------------------------
    # Métodos de conveniencia
    # ----------------------------------------------------------------

    async def execute(self, query: str, *args: Any) -> str:
        """Ejecuta un query sin retorno (INSERT, UPDATE, DELETE)."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def executemany(self, query: str, args: list[tuple]) -> None:
        """Ejecuta un query para múltiples filas."""
        async with self.pool.acquire() as conn:
            await conn.executemany(query, args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Ejecuta un query y retorna todas las filas."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchone(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        """Ejecuta un query y retorna la primera fila."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args: Any) -> Any:
        """Ejecuta un query y retorna un solo valor."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def transaction(self):
        """
        Context manager para transacciones.

        Uso:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO ...", ...)
                await conn.execute("UPDATE ...", ...)
        """
        conn = await self.pool.acquire()
        tx = conn.transaction()
        await tx.start()

        class TransactionContext:
            def __init__(self, connection, transaction):
                self._conn = connection
                self._tx = transaction

            async def __aenter__(self):
                return self._conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    await self._tx.rollback()
                else:
                    await self._tx.commit()
                await self._conn.close()
                return False

        return TransactionContext(conn, tx)

    # ----------------------------------------------------------------
    # Inicialización del schema
    # ----------------------------------------------------------------

    async def init_schema(self) -> None:
        """Crea las tablas del sistema si no existen, leyendo el archivo SQL."""
        from pathlib import Path

        schema_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "init_schema.sql"
        if not schema_path.exists():
            logger.warning(f"Schema SQL no encontrado en {schema_path}, saltando init_schema")
            return

        schema_sql = schema_path.read_text(encoding="utf-8")
        await self.execute(schema_sql)
        logger.info("Schema de base de datos inicializado")
