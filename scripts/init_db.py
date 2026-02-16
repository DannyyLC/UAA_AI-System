"""
Script para inicializar el schema de la base de datos.

Uso:
    python -m scripts.init_db

Requiere que PostgreSQL esté corriendo (docker compose up postgres).
"""

import asyncio
import sys
from pathlib import Path

# Agregar el root del proyecto al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.shared.configuration import settings
from src.shared.database import DatabaseManager


async def main():
    print(f"Conectando a: {settings.database_url}")

    db = DatabaseManager()
    await db.connect()

    # Leer y ejecutar el schema SQL
    schema_path = Path(__file__).parent / "init_schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    print("Ejecutando schema...")
    await db.execute(schema_sql)
    print("✓ Schema creado exitosamente")

    # Verificar tablas creadas
    tables = await db.fetch("""
        SELECT tablename FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    print(f"\nTablas en la base de datos ({len(tables)}):")
    for t in tables:
        print(f"  • {t['tablename']}")

    # Verificar admin seed
    admin = await db.fetchone("SELECT id, email, role FROM users WHERE role = 'admin' LIMIT 1")
    if admin:
        print(f"\n✓ Admin seed: {admin['email']} (id: {admin['id']})")
    else:
        print("\n⚠ No se encontró usuario admin")

    await db.disconnect()
    print("\n✓ Inicialización completada")


if __name__ == "__main__":
    asyncio.run(main())
