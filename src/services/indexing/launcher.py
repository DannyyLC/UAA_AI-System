#!/usr/bin/env python3
"""
Launcher para múltiples Indexing Workers.

Lanza N workers en paralelo para procesar documentos.
"""

import asyncio
import os
import signal
import sys
from typing import List

from src.services.indexing.worker import IndexingWorker
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class WorkerLauncher:
    """Lanza y gestiona múltiples workers."""
    
    def __init__(self, num_workers: int = 2):
        """
        Inicializa el launcher.
        
        Args:
            num_workers: Número de workers a lanzar
        """
        self.num_workers = num_workers
        self.workers: List[IndexingWorker] = []
        self.tasks: List[asyncio.Task] = []
        self.running = False
        
        logger.info(f"WorkerLauncher inicializado con {num_workers} workers")
    
    async def start(self) -> None:
        """Inicia todos los workers."""
        logger.info(f"🚀 Lanzando {self.num_workers} indexing workers...")
        
        self.running = True
        
        # Crear y lanzar workers
        for i in range(1, self.num_workers + 1):
            worker = IndexingWorker(worker_id=i)
            self.workers.append(worker)
            
            # Crear tarea para cada worker
            task = asyncio.create_task(
                worker.start(),
                name=f"worker-{i}"
            )
            self.tasks.append(task)
        
        logger.info(f"✅ {self.num_workers} workers lanzados")
        
        # Esperar a que terminen (o sean cancelados)
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Workers cancelados")
        except Exception as e:
            logger.error(f"Error en workers: {e}", exc_info=True)
    
    async def stop(self) -> None:
        """Detiene todos los workers gracefully."""
        logger.info("🛑 Deteniendo todos los workers...")
        
        self.running = False
        
        # Cancelar todas las tareas
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Esperar a que terminen
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Detener workers
        for worker in self.workers:
            await worker.stop()
        
        logger.info("✅ Todos los workers detenidos")


async def main():
    """Función principal."""
    # Número de workers desde env o default
    num_workers = int(os.getenv("INDEXING_WORKERS", "2"))
    
    logger.info(f"🚀 Iniciando sistema de indexación con {num_workers} workers")
    
    launcher = WorkerLauncher(num_workers=num_workers)
    
    # Setup signal handlers para graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler(sig):
        logger.info(f"Señal {sig} recibida, iniciando shutdown...")
        asyncio.create_task(launcher.stop())
    
    # Registrar handlers
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    
    try:
        await launcher.start()
    except KeyboardInterrupt:
        logger.info("Interrupción recibida")
    finally:
        await launcher.stop()
    
    logger.info("Sistema de indexación detenido")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown completo")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        sys.exit(1)
