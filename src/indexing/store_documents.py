from typing import List, Optional, BinaryIO
import torch
import uuid
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from src.indexing.docuement_loader import DocumentProcessor
from src.shared.logging_utils import get_logger, timing_decorator

logger = get_logger(__name__)

class EmbeddingProcessor:
    """Procesa documentos y almacena sus embeddings en Chroma."""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Inicializa el procesador de embeddings.
        
        Args:
            persist_directory: Directorio donde se almacenará la base de datos Chroma
        """
        self.persist_directory = persist_directory
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Configurar el modelo de embeddings
        model_name = "BAAI/bge-large-en-v1.5"
        model_kwargs = {'device': device}
        encode_kwargs = {'normalize_embeddings': True}
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs=model_kwargs,
            encode_kwargs=encode_kwargs
        )
        
        self.processor = DocumentProcessor()
        
        # Configurar el divisor de texto
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Inicializar Chroma
        self.db = Chroma(
            persist_directory=persist_directory,
            embedding_function=self.embeddings
        )
        
        logger.info(f"EmbeddingProcessor inicializado con base de datos en {persist_directory}")

    @timing_decorator
    async def process_and_store(
        self, 
        documents: List[tuple[BinaryIO, str]], 
        user_id: str,
        collection_name: Optional[str] = None
    ) -> str:
        """
        Procesa documentos, genera embeddings y los almacena en Chroma.
        
        Args:
            documents: Lista de documentos a procesar
            user_id: ID del usuario para la metadata
            collection_name: Nombre opcional de la colección
            
        Returns:
            str: ID de la colección creada
        """
        try:
            logger.info(f"Iniciando procesamiento para usuario {user_id}")
            
            processed_documents = await self.processor.process_documents(documents)
            
            # Dividir documentos en chunks
            chunks = []
            for doc in processed_documents:
                doc_chunks = self.text_splitter.split_documents([doc])
                # Agregar user_id y otros metadatos relevantes a cada chunk
                for chunk in doc_chunks:
                    chunk.metadata.update({
                        'user_id': user_id,
                        'original_source': doc.metadata.get('source', 'unknown'),
                        'mime_type': doc.metadata.get('mime_type', 'unknown'),
                        'chunk_index': len(chunks)
                    })
                chunks.extend(doc_chunks)
            
            logger.info(f"Generados {len(chunks)} chunks de {len(documents)} documentos")
            
            # Crear una nueva colección si no se especificó una
            if not collection_name:
                collection_name = f"user_{user_id}_{uuid.uuid4()}"
            
            db = Chroma(
                collection_name=collection_name,
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
            # Agregar los documentos a la colección
            db.add_documents(chunks)
                
            logger.info(f"Documentos agregados a la colección {collection_name}")        
            logger.info(f"Documentos almacenados exitosamente en colección {collection_name}")
            return collection_name
            
        except Exception as e:
            logger.error(f"Error procesando documentos: {str(e)}")
            raise
