import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import torch

# Conectar a la base de datos persistente
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Obtener y mostrar todas las colecciones
collections = chroma_client.list_collections()
print("Colecciones en la base de datos:")
for collection in collections:
    print(collection)  # Acceder directamente al nombre

# Obtener la colección (cambia el nombre según necesites)
collection = chroma_client.get_collection(name="machine_learning")

# Obtener todos los documentos almacenados
documents = collection.get()  # Sin filtros, obtiene todos

# Mostrar los IDs y metadatos
print("Documentos en la colección:")
for doc_id, metadata in zip(documents["ids"], documents.get("metadatas", [])):
    print(f"ID: {doc_id}, Metadata: {metadata}")
    

    
device = "cuda" if torch.cuda.is_available() else "cpu"
model_name = "BAAI/bge-large-en-v1.5"
model_kwargs = {'device': device}
encode_kwargs = {'normalize_embeddings': True}
embeddings = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)
    
db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="machine_learning"
)

pregunta = "Que es el machine learning"
respuesta = db.similarity_search(query=pregunta, k=3)
print(respuesta)