"""
Generador de embeddings para chunks de texto.

Usa OpenAI text-embedding-3-small por defecto con soporte para batch processing,
rate limiting y retry logic.
"""

import asyncio
import os
from typing import List, Optional

import tiktoken
from openai import APIError, AsyncOpenAI, RateLimitError

from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class EmbeddingsGenerator:
    """
    Generador de embeddings usando OpenAI API.

    Características:
    - Batch processing para eficiencia
    - Rate limiting automático
    - Retry con exponential backoff
    - Cálculo de tokens para optimizar costos
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        batch_size: int = 100,
        max_retries: int = 3,
    ):
        """
        Inicializa el generador de embeddings.

        Args:
            model: Modelo de embeddings (default: text-embedding-3-small)
            api_key: API key de OpenAI (default: desde env)
            batch_size: Máximo de textos por batch (default: 100, max OpenAI: 2048)
            max_retries: Máximo de reintentos en caso de error
        """
        self.model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.batch_size = min(batch_size, 100)  # Límite conservador
        self.max_retries = max_retries

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY no configurada")

        self.client = AsyncOpenAI(api_key=api_key)

        # Dimension según modelo
        self.dimension_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        self.dimension = self.dimension_map.get(self.model, 1536)

        # Tokenizer para contar tokens
        try:
            self.encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            logger.warning(f"Encoding no encontrado para {self.model}, usando cl100k_base")
            self.encoding = tiktoken.get_encoding("cl100k_base")

        logger.info(
            f"EmbeddingsGenerator inicializado: "
            f"model={self.model}, "
            f"dimension={self.dimension}, "
            f"batch_size={self.batch_size}"
        )

    def count_tokens(self, text: str) -> int:
        """
        Cuenta el número de tokens en un texto.

        Args:
            text: Texto a analizar

        Returns:
            Número de tokens
        """
        return len(self.encoding.encode(text))

    async def generate(self, text: str) -> List[float]:
        """
        Genera embedding para un solo texto.

        Args:
            text: Texto a convertir en embedding

        Returns:
            Vector de embedding
        """
        embeddings = await self.generate_batch([text])
        return embeddings[0] if embeddings else []

    async def generate_batch(
        self,
        texts: List[str],
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Genera embeddings para un batch de textos.

        Args:
            texts: Lista de textos
            show_progress: Mostrar progreso en logs

        Returns:
            Lista de vectores de embedding
        """
        if not texts:
            return []

        # Filtrar textos vacíos
        valid_texts = [(i, t) for i, t in enumerate(texts) if t and t.strip()]

        if not valid_texts:
            logger.warning("Todos los textos están vacíos")
            return [[0.0] * self.dimension] * len(texts)

        # Procesar en sub-batches si es necesario
        all_embeddings = [None] * len(texts)

        for batch_start in range(0, len(valid_texts), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(valid_texts))
            batch = valid_texts[batch_start:batch_end]
            batch_texts = [t for _, t in batch]

            if show_progress:
                logger.info(
                    f"Generando embeddings: {batch_start + 1}-{batch_end}/{len(valid_texts)}"
                )

            # Generar embeddings con retry logic
            batch_embeddings = await self._generate_with_retry(batch_texts)

            # Colocar embeddings en posiciones correctas
            for (original_idx, _), embedding in zip(batch, batch_embeddings):
                all_embeddings[original_idx] = embedding

        # Rellenar embeddings faltantes (textos vacíos) con vector cero
        for i, emb in enumerate(all_embeddings):
            if emb is None:
                all_embeddings[i] = [0.0] * self.dimension

        return all_embeddings

    async def _generate_with_retry(
        self,
        texts: List[str],
        attempt: int = 0,
    ) -> List[List[float]]:
        """
        Genera embeddings con retry logic.

        Args:
            texts: Lista de textos
            attempt: Número de intento actual

        Returns:
            Lista de embeddings
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float",
            )

            # Extraer embeddings en el orden correcto
            embeddings = [data.embedding for data in response.data]

            # Calcular tokens usados si está disponible
            if hasattr(response, "usage") and response.usage:
                tokens = response.usage.total_tokens
                logger.debug(f"Embeddings generados: {len(texts)} textos, {tokens} tokens")

            return embeddings

        except RateLimitError as e:
            if attempt >= self.max_retries:
                logger.error(f"Rate limit excedido después de {attempt} reintentos")
                raise

            # Exponential backoff: 2^attempt segundos
            wait_time = 2**attempt
            logger.warning(f"Rate limit alcanzado. Esperando {wait_time}s antes de reintentar...")
            await asyncio.sleep(wait_time)

            return await self._generate_with_retry(texts, attempt + 1)

        except APIError as e:
            if attempt >= self.max_retries:
                logger.error(f"Error de API después de {attempt} reintentos: {e}")
                raise

            wait_time = 2**attempt
            logger.warning(
                f"Error de API (intento {attempt + 1}/{self.max_retries}): {e}. "
                f"Reintentando en {wait_time}s..."
            )
            await asyncio.sleep(wait_time)

            return await self._generate_with_retry(texts, attempt + 1)

        except Exception as e:
            logger.error(f"Error generando embeddings: {e}", exc_info=True)
            raise

    async def generate_for_chunks(
        self,
        chunks: List[str],
        show_progress: bool = True,
    ) -> List[List[float]]:
        """
        Genera embeddings para una lista de chunks.

        Wrapper para generate_batch con logging más detallado.

        Args:
            chunks: Lista de textos de chunks
            show_progress: Mostrar progreso

        Returns:
            Lista de embeddings
        """
        if not chunks:
            return []

        # Estadísticas
        total_chars = sum(len(c) for c in chunks)
        total_tokens = sum(self.count_tokens(c) for c in chunks[:10])  # Estimación
        avg_tokens = total_tokens // min(10, len(chunks))
        estimated_total_tokens = avg_tokens * len(chunks)

        logger.info(
            f"Generando embeddings para {len(chunks)} chunks: "
            f"~{total_chars} chars, ~{estimated_total_tokens} tokens estimados"
        )

        embeddings = await self.generate_batch(chunks, show_progress=show_progress)

        logger.info(f"✅ {len(embeddings)} embeddings generados " f"(dimensión: {self.dimension})")

        return embeddings

    def close(self):
        """Cierra el cliente de OpenAI."""
        # AsyncOpenAI no requiere cierre explícito
        pass


# Instancia global singleton (opcional)
_embeddings_generator: Optional[EmbeddingsGenerator] = None


def get_embeddings_generator() -> EmbeddingsGenerator:
    """
    Obtiene instancia global del generador de embeddings (singleton).

    Returns:
        Instancia de EmbeddingsGenerator
    """
    global _embeddings_generator

    if _embeddings_generator is None:
        _embeddings_generator = EmbeddingsGenerator()

    return _embeddings_generator
