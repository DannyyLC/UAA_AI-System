"""Consumer base de Kafka usando aiokafka."""

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from aiokafka.structs import ConsumerRecord

from src.kafka.config import kafka_config
from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class KafkaConsumerManager:
    """
    Manager para consumer de Kafka con manejo automático de errores y reintentos.

    Características:
    - Deserialización JSON automática
    - Commit manual controlado
    - Manejo de errores y reintentos
    - Graceful shutdown
    """

    def __init__(
        self,
        topics: List[str],
        group_id: str,
        handler: Callable[[Dict[str, Any], str, int, int], Any],
    ):
        """
        Inicializa el consumer.

        Args:
            topics: Lista de topics a consumir
            group_id: ID del grupo de consumidores
            handler: Función async que procesa cada mensaje
                     Recibe (value, topic, partition, offset)
        """
        self._topics = topics
        self._group_id = group_id
        self._handler = handler
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Inicia el consumer y la tarea de consumo."""
        if self._running:
            logger.warning(f"Consumer {self._group_id} ya está corriendo")
            return

        try:
            config = kafka_config.get_consumer_config(self._group_id)

            self._consumer = AIOKafkaConsumer(
                *self._topics,
                **config,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")) if m else None,
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
            )

            await self._consumer.start()
            self._running = True

            logger.info(
                f"Kafka Consumer iniciado - Group: {self._group_id}, "
                f"Topics: {', '.join(self._topics)}"
            )

            # Iniciar tarea de consumo
            self._task = asyncio.create_task(self._consume_loop())

        except Exception as e:
            logger.error(f"Error iniciando Kafka Consumer: {e}")
            raise

    async def stop(self):
        """Detiene el consumer y espera que termine de procesar."""
        if not self._running:
            return

        logger.info(f"Deteniendo consumer {self._group_id}...")
        self._running = False

        # Cancelar tarea de consumo
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Detener consumer
        if self._consumer:
            try:
                await self._consumer.stop()
                logger.info(f"Consumer {self._group_id} detenido")
            except Exception as e:
                logger.error(f"Error deteniendo consumer: {e}")
            finally:
                self._consumer = None

    async def _consume_loop(self):
        """Loop principal de consumo de mensajes."""
        logger.info(f"Iniciando loop de consumo para {self._group_id}")

        try:
            while self._running:
                try:
                    # Obtener batch de mensajes
                    messages = await self._consumer.getmany(
                        timeout_ms=1000, max_records=kafka_config.consumer_max_poll_records
                    )

                    if not messages:
                        continue

                    # Procesar mensajes por partición
                    for topic_partition, records in messages.items():
                        for record in records:
                            try:
                                await self._process_message(record)
                            except Exception as e:
                                logger.error(
                                    f"Error procesando mensaje de {record.topic} "
                                    f"(partition={record.partition}, offset={record.offset}): {e}",
                                    exc_info=True,
                                )
                                # Continuar con el siguiente mensaje
                                continue

                        # Commit después de procesar todo el batch de esta partición
                        try:
                            await self._consumer.commit()
                            logger.debug(
                                f"Commit exitoso - Topic: {topic_partition.topic}, "
                                f"Partition: {topic_partition.partition}"
                            )
                        except Exception as e:
                            logger.error(f"Error haciendo commit: {e}")

                except asyncio.CancelledError:
                    logger.info("Loop de consumo cancelado")
                    break
                except KafkaError as e:
                    logger.error(f"Error de Kafka en consumer: {e}")
                    await asyncio.sleep(5)  # Esperar antes de reintentar
                except Exception as e:
                    logger.error(f"Error inesperado en loop de consumo: {e}", exc_info=True)
                    await asyncio.sleep(5)

        finally:
            logger.info(f"Loop de consumo terminado para {self._group_id}")

    async def _process_message(self, record: ConsumerRecord):
        """
        Procesa un mensaje individual.

        Args:
            record: Registro de Kafka con el mensaje
        """
        logger.debug(
            f"Procesando mensaje - Topic: {record.topic}, "
            f"Partition: {record.partition}, Offset: {record.offset}"
        )

        try:
            # Llamar al handler del mensaje
            await self._handler(
                value=record.value,
                topic=record.topic,
                partition=record.partition,
                offset=record.offset,
            )

            logger.debug(
                f"Mensaje procesado exitosamente - "
                f"Topic: {record.topic}, Offset: {record.offset}"
            )

        except Exception as e:
            logger.error(
                f"Error en handler para mensaje de {record.topic} "
                f"(offset={record.offset}): {e}",
                exc_info=True,
            )
            # Re-lanzar para que el loop lo maneje
            raise

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
