from typing import BinaryIO, List, Dict, Type
import magic
import tempfile
import os
import torch
import nltk
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    PDFMinerLoader,
    TextLoader,
    JSONLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredXMLLoader,
    UnstructuredRTFLoader,
    UnstructuredEmailLoader,
    UnstructuredODTLoader,
    BSHTMLLoader,
    CSVLoader,
    PythonLoader
)
from langchain_community.document_loaders.base import BaseLoader
from src.shared.logging_utils import get_logger, timing_decorator

logger = get_logger(__name__)


class DocumentProcessor:
    """Procesador de documentos con detección automática de tipo MIME."""

    def __init__(self):
        self.file_sources: Dict[str, Type[BaseLoader]] = {
            'application/pdf': PyPDFLoader,
            'text/markdown': UnstructuredMarkdownLoader,
            'application/json': JSONLoader,
            'text/html': BSHTMLLoader,
            'text/plain': TextLoader,
            'text/csv': CSVLoader,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': UnstructuredExcelLoader,
            'application/vnd.ms-excel': UnstructuredExcelLoader,
            'application/msword': UnstructuredWordDocumentLoader,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': UnstructuredWordDocumentLoader,
            'application/vnd.ms-powerpoint': UnstructuredPowerPointLoader,
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': UnstructuredPowerPointLoader,
            'application/xml': UnstructuredXMLLoader,
            'text/xml': UnstructuredXMLLoader,
            'application/rtf': UnstructuredRTFLoader,
            'message/rfc822': UnstructuredEmailLoader,
            'application/vnd.oasis.opendocument.text': UnstructuredODTLoader,
            'text/x-python': PythonLoader,
            'application/pdf-alt': PDFMinerLoader,
        }

        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using {self.device}")

        self.mime = magic.Magic(mime=True)

        # Intentar descargar recursos NLTK al inicializar
        self._ensure_nltk_resources()

    def _ensure_nltk_resources(self):
        """Asegura que los recursos NLTK necesarios estén disponibles."""
        recursos = ['punkt_tab', 'averaged_perceptron_tagger_eng', 'punkt']

        for recurso in recursos:
            try:
                # Intentar encontrar el recurso primero
                nltk.data.find(f'tokenizers/{recurso}')
                logger.info(f"Recurso NLTK '{recurso}' ya disponible")
            except LookupError:
                # Si no existe, descargarlo
                logger.info(f"Descargando recurso NLTK: {recurso}")
                try:
                    nltk.download(recurso, quiet=True)
                except Exception as e:
                    logger.warning(f"No se pudo descargar {recurso}: {e}")

    @timing_decorator
    async def process_documents(self, files: List[tuple[BinaryIO, str]]) -> List[Document]:
        """
        Procesa una lista de documentos y retorna sus contenidos.

        Args:
            files: Lista de tuplas (file, filename) a procesar

        Returns:
            List[Document]: Lista de documentos procesados
        """
        processed_documents = []

        for file, filename in files:
            try:
                # Detectar tipo MIME
                file_content = file.read()
                mime_type = self.mime.from_buffer(file_content)

                if mime_type not in self.file_sources:
                    logger.info(f"Tipo de archivo no soportado para {filename}: {mime_type}")
                    continue

                # Crear y procesar archivo temporal
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name

                try:
                    # Obtener el loader apropiado y procesar
                    loader = self.file_sources[mime_type](temp_path)

                    # Usar lazy loading para mejor eficiencia de memoria
                    try:
                        async for page in loader.alazy_load():
                            page.metadata.update({
                                'source': filename,
                                'mime_type': mime_type
                            })
                            processed_documents.append(page)

                    except LookupError as e:
                        # Error específico de NLTK - intentar descargar recursos y reintentar
                        error_msg = str(e)
                        if 'punkt_tab' in error_msg or 'averaged_perceptron_tagger' in error_msg:
                            logger.warning(f"Recurso NLTK faltante para {filename}, intentando descargar...")

                            try:
                                # Descargar recursos que faltan
                                nltk.download('punkt_tab', quiet=True)
                                nltk.download('averaged_perceptron_tagger_eng', quiet=True)
                                nltk.download('punkt', quiet=True)

                                logger.info(f"Recursos NLTK descargados, reintentando procesar {filename}...")

                                # Reintentar con el loader
                                loader = self.file_sources[mime_type](temp_path)
                                async for page in loader.alazy_load():
                                    page.metadata.update({
                                        'source': filename,
                                        'mime_type': mime_type
                                    })
                                    processed_documents.append(page)

                                logger.info(f"Documento {filename} procesado exitosamente después de descargar recursos")

                            except Exception as retry_error:
                                logger.error(f"Error después de descargar recursos NLTK para {filename}: {retry_error}")
                                continue
                        else:
                            # Otro tipo de LookupError
                            raise

                finally:
                    # Asegurar que el archivo temporal se elimine
                    os.unlink(temp_path)

            except Exception as e:
                logger.error(f"Error procesando {filename}: {str(e)}")
                continue

        return processed_documents