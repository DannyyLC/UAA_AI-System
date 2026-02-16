#!/usr/bin/env python3
"""
Script para crear topics de Kafka necesarios para el sistema de indexación.

Topics:
- indexing.queue: Cola principal de trabajos de indexación
- indexing.dlq: Dead Letter Queue para trabajos fallidos
"""

import asyncio
import os
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_topics():
    """Crea los topics de Kafka si no existen."""
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    
    admin_client = AIOKafkaAdminClient(
        bootstrap_servers=bootstrap_servers,
    )
    
    try:
        await admin_client.start()
        logger.info(f"Conectado a Kafka: {bootstrap_servers}")
        
        # Definir topics
        topics = [
            NewTopic(
                name="indexing.queue",
                num_partitions=3,  # Para paralelizar workers
                replication_factor=1,
                topic_configs={
                    "retention.ms": str(7 * 24 * 60 * 60 * 1000),  # 7 días
                    "compression.type": "gzip",
                }
            ),
            NewTopic(
                name="indexing.dlq",
                num_partitions=1,  # No necesita paralelización
                replication_factor=1,
                topic_configs={
                    "retention.ms": str(30 * 24 * 60 * 60 * 1000),  # 30 días
                    "compression.type": "gzip",
                }
            ),
        ]
        
        # Crear topics
        for topic in topics:
            try:
                await admin_client.create_topics([topic])
                logger.info(f"✅ Topic creado: {topic.name}")
            except TopicAlreadyExistsError:
                logger.info(f"ℹ️  Topic ya existe: {topic.name}")
            except Exception as e:
                logger.error(f"❌ Error creando topic {topic.name}: {e}")
        
        # Listar todos los topics
        metadata = await admin_client.list_topics()
        logger.info(f"\n📋 Topics disponibles: {metadata}")
        
    except Exception as e:
        logger.error(f"Error conectando a Kafka: {e}")
        raise
    finally:
        await admin_client.close()


if __name__ == "__main__":
    asyncio.run(create_topics())
