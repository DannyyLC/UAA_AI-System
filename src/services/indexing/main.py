#!/bin/bash
"""
Script para iniciar el sistema de indexación completo.

Lanza:
- N workers para procesar indexing.queue
- 1 DLQ consumer para monitorear fallos
"""

import asyncio
import os
import signal
import sys
from typing import List

from src.services.indexing.dlq_consumer import DLQConsumer
from src.services.indexing.launcher import WorkerLauncher
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class IndexingSystem:
    """Gestiona todo el sistema de indexación."""

    def __init__(self, num_workers: int = 2):
        """
        Inicializa el sistema.

        Args:
            num_workers: Número de workers a lanzar
        """
        self.num_workers = num_workers
        self.launcher = WorkerLauncher(num_workers=num_workers)
        self.dlq_consumer = DLQConsumer()
        self.tasks: List[asyncio.Task] = []
        self.running = False

        logger.info(f"Sistema de indexación inicializado: {num_workers} workers")

    async def start(self) -> None:
        """Inicia el sistema completo."""
        logger.info("🚀 INICIANDO SISTEMA DE INDEXACIÓN 🚀")
        logger.info("=" * 60)

        self.running = True

        # Lanzar workers
        logger.info(f"📦 Lanzando {self.num_workers} workers...")
        workers_task = asyncio.create_task(self.launcher.start(), name="workers")
        self.tasks.append(workers_task)

        # Dar tiempo a que los workers se inicien
        await asyncio.sleep(2)

        # Lanzar DLQ consumer
        logger.info("💀 Lanzando DLQ consumer...")
        dlq_task = asyncio.create_task(self.dlq_consumer.start(), name="dlq-consumer")
        self.tasks.append(dlq_task)

        logger.info("=" * 60)
        logger.info("✅ SISTEMA DE INDEXACIÓN ACTIVO")
        logger.info(f"   - Workers: {self.num_workers}")
        logger.info(f"   - DLQ Consumer: activo")
        logger.info(f"   - Kafka Topic: indexing.queue (3 partitions)")
        logger.info(f"   - DLQ Topic: indexing.dlq")
        logger.info("=" * 60)

        # Esperar a que terminen
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Sistema cancelado")
        except Exception as e:
            logger.error(f"Error en sistema: {e}", exc_info=True)

    async def stop(self) -> None:
        """Detiene el sistema completo gracefully."""
        logger.info("=" * 60)
        logger.info("🛑 DETENIENDO SISTEMA DE INDEXACIÓN")

        self.running = False

        # Detener workers
        await self.launcher.stop()

        # Detener DLQ consumer
        await self.dlq_consumer.stop()

        # Cancelar tareas pendientes
        for task in self.tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("✅ SISTEMA DETENIDO COMPLETAMENTE")
        logger.info("=" * 60)


async def main():
    """Función principal."""
    print("\n" + "=" * 60)
    print("🚀 UAA RAG SYSTEM - INDEXING SERVICE")
    print("=" * 60 + "\n")

    # Configuración
    num_workers = int(os.getenv("INDEXING_WORKERS", "2"))

    system = IndexingSystem(num_workers=num_workers)

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        logger.info(f"\n⚠️  Señal {sig} recibida")
        asyncio.create_task(system.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupción de teclado recibida")
    except Exception as e:
        logger.error(f"\n❌ Error fatal: {e}", exc_info=True)
    finally:
        await system.stop()

    print("\n👋 Sistema de indexación cerrado\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Adiós!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
