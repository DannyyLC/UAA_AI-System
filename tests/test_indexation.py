import pytest
import os
import tempfile
import io
import asyncio
import unittest.mock as mock
from typing import List, BinaryIO
import torch

from langchain_core.documents import Document
from src.indexing.docuement_loader import DocumentProcessor
from src.indexing.store_documents import EmbeddingProcessor

# Fixtures para crear archivos de prueba
@pytest.fixture
def sample_text_file():
    content = "Este es un archivo de texto de prueba.\nContiene múltiples líneas.\nPara probar el procesamiento de documentos."
    file = io.BytesIO(content.encode('utf-8'))
    return file, "test_document.txt"

@pytest.fixture
def sample_pdf_content():
    # Esto no es un PDF real, pero simularemos la detección MIME
    content = b"%PDF-1.5\nFake PDF content"
    file = io.BytesIO(content)
    return file, "test_document.pdf"

@pytest.fixture
def sample_documents_list():
    doc1 = Document(
        page_content="Contenido del documento 1",
        metadata={"source": "test1.txt", "mime_type": "text/plain"}
    )
    doc2 = Document(
        page_content="Contenido del documento 2",
        metadata={"source": "test2.txt", "mime_type": "text/plain"}
    )
    return [doc1, doc2]

# Tests para DocumentProcessor
class TestDocumentProcessor:
    
    @pytest.mark.asyncio
    async def test_init(self):
        processor = DocumentProcessor()
        assert len(processor.file_sources) > 0
        assert 'application/pdf' in processor.file_sources
        assert 'text/plain' in processor.file_sources
        
    @pytest.mark.asyncio
    @mock.patch('magic.Magic')
    @mock.patch('src.indexing.docuement_loader.TextLoader')
    async def test_process_text_document(self, mock_text_loader, mock_magic, sample_text_file):
        # Configurar el mock
        mock_magic_instance = mock_magic.return_value
        mock_magic_instance.from_buffer.return_value = 'text/plain'
        
        # Configurar el mock del loader con un documento de prueba
        mock_loader_instance = mock_text_loader.return_value
        test_doc = Document(page_content="Contenido de prueba", metadata={})
        
        # Crear un generador asíncrono para simular el comportamiento de alazy_load
        async def mock_async_generator():
            yield test_doc
        
        # Asignar el generador asíncrono a alazy_load
        mock_loader_instance.alazy_load.return_value = mock_async_generator()
        
        processor = DocumentProcessor()
        result = await processor.process_documents([sample_text_file])
        
        # Verificaciones
        assert len(result) == 1
        assert result[0].page_content == "Contenido de prueba"
        assert result[0].metadata['source'] == sample_text_file[1]
        assert result[0].metadata['mime_type'] == 'text/plain'
        
    @pytest.mark.asyncio
    @mock.patch('magic.Magic')
    async def test_unsupported_mime_type(self, mock_magic, sample_text_file):
        # Configurar el mock para devolver un tipo no soportado
        mock_magic_instance = mock_magic.return_value
        mock_magic_instance.from_buffer.return_value = 'application/unknown'
        
        processor = DocumentProcessor()
        result = await processor.process_documents([sample_text_file])
        
        # Verificar que no se procesó el documento
        assert len(result) == 0
        
    @pytest.mark.asyncio
    @mock.patch('magic.Magic')
    @mock.patch('src.indexing.docuement_loader.PyPDFLoader')
    async def test_process_pdf_document(self, mock_pdf_loader, mock_magic, sample_pdf_content):
        # Configurar el mock
        mock_magic_instance = mock_magic.return_value
        mock_magic_instance.from_buffer.return_value = 'application/pdf'
        
        # Configurar el mock del loader con un documento de prueba
        mock_loader_instance = mock_pdf_loader.return_value
        test_doc = Document(page_content="Contenido PDF de prueba", metadata={})
        
        # Crear un generador asíncrono para simular el comportamiento de alazy_load
        async def mock_async_generator():
            yield test_doc
        
        # Asignar el generador asíncrono a alazy_load
        mock_loader_instance.alazy_load.return_value = mock_async_generator()
        
        processor = DocumentProcessor()
        result = await processor.process_documents([sample_pdf_content])
        
        # Verificaciones
        assert len(result) == 1
        assert result[0].page_content == "Contenido PDF de prueba"
        assert result[0].metadata['source'] == sample_pdf_content[1]
        assert result[0].metadata['mime_type'] == 'application/pdf'
        
    @pytest.mark.asyncio
    @mock.patch('magic.Magic')
    @mock.patch('tempfile.NamedTemporaryFile')
    async def test_exception_handling(self, mock_tempfile, mock_magic, sample_text_file):
        # Configurar mocks
        mock_magic_instance = mock_magic.return_value
        mock_magic_instance.from_buffer.return_value = 'text/plain'
        
        # Simular una excepción durante el procesamiento
        mock_tempfile.side_effect = Exception("Error de prueba")
        
        processor = DocumentProcessor()
        result = await processor.process_documents([sample_text_file])
        
        # Verificar que la excepción fue manejada y se devolvió una lista vacía
        assert len(result) == 0

# Tests para EmbeddingProcessor
class TestEmbeddingProcessor:
    
    @pytest.mark.asyncio
    @mock.patch('langchain_huggingface.HuggingFaceEmbeddings')
    @mock.patch('langchain_chroma.Chroma')
    async def test_init(self, mock_chroma, mock_embeddings):
        processor = EmbeddingProcessor(persist_directory="./test_db")
        
        assert processor.persist_directory == "./test_db"
        assert processor.embeddings is not None
        assert processor.processor is not None
        assert processor.text_splitter is not None
        assert processor.db is not None
        
    @pytest.mark.asyncio
    @mock.patch('src.indexing.docuement_loader.DocumentProcessor')
    @mock.patch('src.indexing.store_documents.Chroma')
    @mock.patch('src.indexing.store_documents.HuggingFaceEmbeddings')
    async def test_process_and_store(self, mock_embeddings, mock_chroma, mock_doc_processor, 
                                    sample_text_file, sample_documents_list):
        # Configurar mocks
        mock_processor_instance = mock_doc_processor.return_value
        mock_processor_instance.process_documents = mock.AsyncMock(return_value=sample_documents_list)
        
        mock_chroma_instance = mock_chroma.return_value
        mock_chroma_instance.add_documents = mock.MagicMock()
        
        # Crear el procesador de embeddings
        processor = EmbeddingProcessor(persist_directory="./test_db")
        processor.processor = mock_processor_instance
        
        # Ejecutar la función a probar
        collection_name = await processor.process_and_store(
            documents=[sample_text_file],
            user_id="test_user"
        )
        
        # Verificaciones
        assert collection_name is not None
        assert "test_user" in collection_name
        assert mock_processor_instance.process_documents.called
        assert mock_chroma_instance.add_documents.called
        
    @pytest.mark.asyncio
    @mock.patch('src.indexing.docuement_loader.DocumentProcessor')
    @mock.patch('src.indexing.store_documents.Chroma')
    @mock.patch('src.indexing.store_documents.HuggingFaceEmbeddings')
    async def test_process_with_custom_collection(self, mock_embeddings, mock_chroma, mock_doc_processor, 
                                                sample_text_file, sample_documents_list):
        # Configurar mocks
        mock_processor_instance = mock_doc_processor.return_value
        mock_processor_instance.process_documents = mock.AsyncMock(return_value=sample_documents_list)
        
        mock_chroma_instance = mock_chroma.return_value
        mock_chroma_instance.add_documents = mock.MagicMock()
        
        # Crear el procesador de embeddings
        processor = EmbeddingProcessor(persist_directory="./test_db")
        processor.processor = mock_processor_instance
        
        # Ejecutar la función a probar con nombre de colección personalizado
        collection_name = await processor.process_and_store(
            documents=[sample_text_file],
            user_id="test_user",
            collection_name="test_collection"
        )
        
        # Verificaciones
        assert collection_name == "test_collection"
        assert mock_processor_instance.process_documents.called
        assert mock_chroma_instance.add_documents.called
        
    @pytest.mark.asyncio
    @mock.patch('src.indexing.docuement_loader.DocumentProcessor')
    async def test_process_error_handling(self, mock_doc_processor, sample_text_file):
        # Configurar el mock para lanzar una excepción
        mock_processor_instance = mock_doc_processor.return_value
        mock_processor_instance.process_documents = mock.AsyncMock(side_effect=Exception("Error de prueba"))
        
        # Crear el procesador de embeddings
        processor = EmbeddingProcessor(persist_directory="./test_db")
        processor.processor = mock_processor_instance
        
        # Verificar que la excepción se propaga
        with pytest.raises(Exception) as excinfo:
            await processor.process_and_store(
                documents=[sample_text_file],
                user_id="test_user"
            )
        
        assert "Error de prueba" in str(excinfo.value)

# Tests de integración
class TestIntegration:
    
    @pytest.mark.asyncio
    @mock.patch('magic.Magic')
    @mock.patch('langchain_huggingface.HuggingFaceEmbeddings')
    @mock.patch('langchain_chroma.Chroma')
    @mock.patch('src.indexing.docuement_loader.TextLoader')
    async def test_end_to_end_processing(self, mock_text_loader, mock_chroma, 
                                         mock_embeddings, mock_magic, sample_text_file):
        # Configurar mocks
        mock_magic_instance = mock_magic.return_value
        mock_magic_instance.from_buffer.return_value = 'text/plain'
        
        # Configurar el mock del loader con un documento de prueba
        mock_loader_instance = mock_text_loader.return_value
        test_doc = Document(page_content="Contenido de prueba para integración", metadata={})
        
        # Crear un generador asíncrono para simular el comportamiento de alazy_load
        async def mock_async_generator():
            yield test_doc
        
        # Asignar el generador asíncrono a alazy_load
        mock_loader_instance.alazy_load.return_value = mock_async_generator()
        
        # Mock para Chroma
        mock_chroma_instance = mock_chroma.return_value
        mock_chroma_instance.add_documents = mock.MagicMock()
        
        # Crear los procesadores
        embed_processor = EmbeddingProcessor(persist_directory="./test_integration_db")
        
        # No mockear el DocumentProcessor real dentro de EmbeddingProcessor
        with tempfile.TemporaryDirectory() as temp_dir:
            collection_name = await embed_processor.process_and_store(
                documents=[sample_text_file],
                user_id="integration_test"
            )
            
            # Verificaciones
            assert collection_name is not None
            assert "integration_test" in collection_name
            assert mock_chroma_instance.add_documents.called

# Ejecutor principal para correr las pruebas
if __name__ == "__main__":
    pytest.main(["-v"])