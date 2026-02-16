"""
Estrategias de chunking para dividir texto en fragmentos.

Usa RecursiveCharacterTextSplitter para dividir de manera inteligente
manteniendo el contexto y coherencia de los chunks.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List

from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """Representa un fragmento de texto con su metadata."""

    text: str
    index: int
    metadata: Dict[str, Any]
    start_char: int
    end_char: int


class RecursiveCharacterTextSplitter:
    """
    Divide texto en chunks usando separadores jerárquicos.

    Intenta dividir por párrafos primero, luego oraciones, luego palabras,
    manteniendo el contexto y evitando cortar en medio de ideas.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: List[str] = None,
        keep_separator: bool = True,
    ):
        """
        Inicializa el splitter.

        Args:
            chunk_size: Tamaño máximo de cada chunk en caracteres
            chunk_overlap: Solapamiento entre chunks para mantener contexto
            separators: Lista de separadores jerárquicos (de más a menos importante)
            keep_separator: Si True, mantiene el separador en el texto
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",  # Párrafos
            "\n",  # Líneas
            ". ",  # Oraciones
            "! ",  # Exclamaciones
            "? ",  # Preguntas
            "; ",  # Punto y coma
            ", ",  # Comas
            " ",  # Palabras
            "",  # Caracteres
        ]
        self.keep_separator = keep_separator

    def split_text(self, text: str) -> List[str]:
        """
        Divide el texto en chunks.

        Args:
            text: Texto a dividir

        Returns:
            Lista de chunks de texto
        """
        if not text or not text.strip():
            return []

        return self._split_text_recursive(text, self.separators)

    def _split_text_recursive(self, text: str, separators: List[str]) -> List[str]:
        """Divide texto recursivamente usando separadores jerárquicos."""
        final_chunks = []

        # Separador a usar en esta iteración
        separator = separators[-1] if separators else ""
        new_separators = []

        # Encontrar el separador apropiado
        for i, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1 :]
                break

        # Dividir por el separador
        splits = self._split_by_separator(text, separator)

        # Combinar splits en chunks del tamaño apropiado
        good_splits = []
        current_chunk_group = []
        current_length = 0

        for split in splits:
            split_len = len(split)

            # Si un solo split es muy grande, dividirlo más
            if split_len > self.chunk_size:
                if current_chunk_group:
                    # Guardar lo acumulado
                    merged = self._merge_splits(current_chunk_group, separator)
                    good_splits.extend(merged)
                    current_chunk_group = []
                    current_length = 0

                # Dividir el split grande recursivamente
                if new_separators:
                    good_splits.extend(self._split_text_recursive(split, new_separators))
                else:
                    # Última opción: dividir por tamaño fijo
                    good_splits.extend(self._split_by_char_count(split))
            else:
                # Verificar si agregar este split excede el tamaño
                if current_length + split_len + len(separator) > self.chunk_size:
                    if current_chunk_group:
                        # Guardar chunk actual
                        merged = self._merge_splits(current_chunk_group, separator)
                        good_splits.extend(merged)

                        # Mantener overlap
                        if self.chunk_overlap > 0:
                            overlap_text = (
                                "".join(current_chunk_group[-2:])
                                if len(current_chunk_group) > 1
                                else current_chunk_group[-1]
                            )
                            if len(overlap_text) <= self.chunk_overlap:
                                current_chunk_group = [overlap_text, split]
                                current_length = len(overlap_text) + split_len
                            else:
                                current_chunk_group = [split]
                                current_length = split_len
                        else:
                            current_chunk_group = [split]
                            current_length = split_len
                    else:
                        current_chunk_group = [split]
                        current_length = split_len
                else:
                    current_chunk_group.append(split)
                    current_length += split_len + (len(separator) if current_chunk_group else 0)

        # Agregar último grupo
        if current_chunk_group:
            merged = self._merge_splits(current_chunk_group, separator)
            good_splits.extend(merged)

        return good_splits

    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """Divide texto por un separador específico."""
        if separator:
            if self.keep_separator:
                # Mantener el separador al final de cada split
                splits = text.split(separator)
                splits = [
                    (s + separator).strip() if i < len(splits) - 1 else s.strip()
                    for i, s in enumerate(splits)
                    if s.strip()
                ]
            else:
                splits = [s.strip() for s in text.split(separator) if s.strip()]
        else:
            splits = [text]

        return [s for s in splits if s]

    def _split_by_char_count(self, text: str) -> List[str]:
        """Divide texto por conteo de caracteres (último recurso)."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Intentar no cortar en medio de una palabra
            if end < len(text):
                # Buscar el último espacio antes del límite
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Aplicar overlap
            start = end - self.chunk_overlap if self.chunk_overlap > 0 else end

        return chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Combina splits en un chunk."""
        if not splits:
            return []

        # Si ya están dentro del tamaño, devolver como está
        merged = separator.join(splits) if separator else "".join(splits)
        if len(merged) <= self.chunk_size:
            return [merged]

        # Si es muy grande, devolver los splits individuales
        return splits


class ChunkingStrategy:
    """
    Estrategia de chunking para documentos.

    Wrapper que coordina el chunking y agrega metadata.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        """
        Inicializa la estrategia de chunking.

        Args:
            chunk_size: Tamaño máximo de cada chunk en caracteres (~250 tokens)
            chunk_overlap: Solapamiento entre chunks para contexto
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def create_chunks(
        self,
        text: str,
        document_metadata: Dict[str, Any] = None,
    ) -> List[Chunk]:
        """
        Crea chunks de un texto con metadata.

        Args:
            text: Texto a dividir
            document_metadata: Metadata del documento original

        Returns:
            Lista de objetos Chunk
        """
        if not text or not text.strip():
            logger.warning("Texto vacío, no se generan chunks")
            return []

        document_metadata = document_metadata or {}

        # Dividir texto
        text_chunks = self.splitter.split_text(text)

        if not text_chunks:
            logger.warning("No se generaron chunks del texto")
            return []

        # Crear objetos Chunk con metadata
        chunks = []
        current_pos = 0

        for i, chunk_text in enumerate(text_chunks):
            # Encontrar posición en el texto original
            start_pos = text.find(chunk_text, current_pos)
            if start_pos == -1:
                start_pos = current_pos
            end_pos = start_pos + len(chunk_text)

            chunk = Chunk(
                text=chunk_text,
                index=i,
                metadata={
                    **document_metadata,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                    "chunk_size": len(chunk_text),
                },
                start_char=start_pos,
                end_char=end_pos,
            )
            chunks.append(chunk)

            current_pos = end_pos

        logger.info(
            f"Texto dividido en {len(chunks)} chunks "
            f"(tamaño promedio: {sum(len(c.text) for c in chunks) // len(chunks)} chars)"
        )

        return chunks


def chunk_document(
    text: str,
    document_metadata: Dict[str, Any] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Chunk]:
    """
    Función de utilidad para crear chunks de un documento.

    Args:
        text: Texto a dividir
        document_metadata: Metadata del documento
        chunk_size: Tamaño máximo de chunk
        chunk_overlap: Solapamiento entre chunks

    Returns:
        Lista de chunks
    """
    strategy = ChunkingStrategy(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return strategy.create_chunks(text, document_metadata)
