# app.py
import asyncio
import os
import sqlite3
from io import BytesIO
from typing import Dict, Any, List, Optional
from pathlib import Path
import shutil

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ====== Imports de tu proyecto ======
from src.indexing import EmbeddingProcessor
from src.shared.logging_utils import get_logger
from langchain_core.messages import HumanMessage
from src.researcher.graph import build_graph
from src.researcher.router import Router
from src.researcher.retrieval import Retrieval
from src.researcher.judge_graph import crear_sistema_refinamiento
from src.api.APIManager import APIManager
from chromadb import PersistentClient
from chromadb.config import Settings


# ====== Configuración base ======
logger = get_logger(__name__)
USE_API = True

app = FastAPI(title="RAG_UAA", version="1.0.0")
# Ruta absoluta a ./chroma_db junto al archivo actual
BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"
DB_PATH = BASE_DIR / "query_results.db"

# CORS (ajusta origins en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # cámbialo a ["https://tu-dominio.com"] en prod
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ====== Modelos I/O de la API ======
class QueryIn(BaseModel):
    query: str
    answer: str
    especialidad: str

class QueryOut(BaseModel):
    results: Dict[str, Any]

# (Opcional) Respuesta del endpoint de indexación
class IndexOut(BaseModel):
    status: str
    collection: str
    filename: str
    user_id: str

# ====== Funciones de base de datos ======
def init_database():
    """Inicializa la base de datos SQLite y crea la tabla si no existe."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pregunta TEXT NOT NULL,
            respuesta TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            gemma TEXT,
            mistral TEXT,
            llama TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_query_result(pregunta: str, respuesta: str, especialidad: str, results: Dict[str, Any]):
    """Guarda el resultado de una consulta en la base de datos."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    gemma = results.get("gemma3:4b", "")
    mistral = results.get("mistral:7b", "")
    llama = results.get("llama3.1:8b", "")
    
    cursor.execute("""
        INSERT INTO query_results (pregunta, respuesta, especialidad, gemma, mistral, llama)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (pregunta, respuesta, especialidad, gemma, mistral, llama))
    
    conn.commit()
    conn.close()

# ====== Helpers reutilizables ======
async def run_graph_with_query(graph, state) -> Dict[str, Any]:
    """
    Ejecuta el grafo con el estado dado y devuelve el estado final.
    """
    try:
        result = await graph.ainvoke(state)
        return result
    except Exception as e:
        logger.error(f"Error en run_graph_with_query: {str(e)}")
        raise

async def process_query(graph, state):
    """
    Versión interactiva por consola (con input()).
    NO se usa en la API, se conserva para referencia.
    """
    print("\n=== Modo de Consulta ===")
    query = input("Ingresa tu pregunta: ")

    try:
        state["messages"].append(HumanMessage(content=query))
        state["current_query"] = query

        final_state = await run_graph_with_query(graph, state)
        state.update(final_state)

        print("\n=== Respuesta ===")
        if state["messages"] and len(state["messages"]) > 1:
            ai_response = state["messages"][-1]
            print(ai_response.content)

            if hasattr(ai_response, "additional_kwargs") and ai_response.additional_kwargs:
                print("\n=== Metadatos ===")
                for key, value in ai_response.additional_kwargs.items():
                    print(f"{key}: {value}")
        else:
            print("No se obtuvo una respuesta.")
    except Exception as e:
        logger.error(f"Error al procesar la consulta: {str(e)}")
        print(f"Error: {str(e)}")

async def index_documents(embedding_processor: EmbeddingProcessor):
    """
    Indexación por consola (con input()).
    NO se usa en la API, se conserva para referencia.
    """
    pdf_path = input("Dame el nombre del archivo: ")
    collection = input("Dame el nombre de la coleccion: ")

    with open(pdf_path, 'rb') as pdf_file:
        pdf_content = pdf_file.read()

    pdf_bytes = BytesIO(pdf_content)
    pdf_name = os.path.basename(pdf_path)
    documents = [(pdf_bytes, pdf_name)]

    collection_name = await embedding_processor.process_and_store(
        documents=documents,
        user_id="usuario_123",
        collection_name=collection
    )

    print(f"Embeddings almacenados en la colección: {collection_name}")

async def process_query_multiple_models(query: str) -> Dict[str, Any]:
    """
    Ejecuta la consulta en múltiples modelos y devuelve {modelo: respuesta}.
    """
    models = ["gemma3:4b", "mistral:7b", "llama3.1:8b"]
    response: Dict[str, Any] = {}

    for model in models:
        logger.info(f"\n============= RESPUESTA {model.upper()} =============")

        graph = build_graph()
        judge_graph = crear_sistema_refinamiento(model_name=model)

        state = {
            "messages": [],
            "investigation": True,
            "current_query": "",
            "research_plan": [],
            "retrieval_queries": [],
            "query_category": "",
            "research_collections": [],
            "current_step": "",
            "needs_research": False,
            "retrieval_results": {},
            "context_for_generation": "",
            "research_completed": False,
            "retrieval_obj": Retrieval(persist_directory="./chroma_db"),
            "router_obj": Router(model_name=model),
            "judge_obj": judge_graph,
            "response_model": model,
            "api": APIManager(USE_API, model)
        }

        state["router_obj"].retriever = state["retrieval_obj"]

        # Agregar el mensaje de usuario al historial
        state["messages"].append(HumanMessage(content=query))
        state["current_query"] = query

        final_state = await run_graph_with_query(graph, state)
        state.update(final_state)

        # Extraer la última respuesta del historial
        msgs = final_state.get("messages") or state.get("messages") or []
        if msgs:
            last = msgs[-1]
            content = getattr(last, "content", None)
            response[model] = content if content is not None else ""
        else:
            response[model] = ""

    return response

# ====== Endpoints de la API ======
@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}

@app.post("/query", response_model=QueryOut, tags=["query"])
async def query_endpoint(payload: QueryIn):
    """
    Body:
    {
      "query": "tu pregunta"
      "answer": "respuesta esperada"
      "especialidad": "especialidad"
    }
    """
    q = (payload.query or "").strip()
    answer = (payload.answer or "").strip()
    especialidad = (payload.especialidad or "").strip()

    if not q:
        raise HTTPException(status_code=400, detail="Falta 'query'.")

    try:
        results = await process_query_multiple_models(q)
        
        # Guardar en la base de datos
        save_query_result(q, answer, especialidad, results)
        
        return {"results": results}
    except Exception as e:
        logger.error(f"Error en /query: {e}")
        raise HTTPException(status_code=500, detail="Error procesando la consulta")

@app.post("/reiniciar")
def reiniciar_chroma():
    try:
        import os, shutil
        from uuid import UUID
        from chromadb import PersistentClient

        # 0) Soltar referencias vivas para evitar locks
        app.state.embedding_processor = None

        # 1) Borrado lógico de TODAS las colecciones (sin allow_reset)
        client = PersistentClient(path=str(CHROMA_DIR))  # usa la misma ruta absoluta de siempre
        for col in client.list_collections():
            client.delete_collection(col.name)

        # 2) Limpieza de carpetas UUID huérfanas dentro de CHROMA_DIR
        #    (solo borra directorios cuyo nombre es UUID y que no correspondan a colecciones vivas)
        live_ids = set()
        # después de borrar deberían quedar 0, pero por si acaso:
        for c in client.list_collections():
            # algunos bindings exponen .id; si no, get_collection para obtenerlo
            cid = getattr(c, "id", None)
            if not cid:
                cid = client.get_collection(c.name).id
            live_ids.add(str(cid))

        for entry in CHROMA_DIR.iterdir():
            if entry.is_dir():
                # verificar si el nombre del directorio "parece" un UUID
                is_uuid = False
                try:
                    UUID(entry.name)
                    is_uuid = True
                except Exception:
                    pass

                # si es UUID y no está en la lista de colecciones vivas => borrar
                if is_uuid and (entry.name not in live_ids):
                    shutil.rmtree(entry, ignore_errors=True)

        # 3) (Opcional) limpiar archivos WAL/SHM si no hay conexiones abiertas
        for fname in ("chroma.sqlite3-wal", "chroma.sqlite3-shm"):
            p = CHROMA_DIR / fname
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    # si hay lock, lo dejamos pasar
                    pass

        # 4) Permisos del directorio para evitar "read-only" por usuario/FS
        try:
            os.chmod(CHROMA_DIR, 0o777)  # ajusta a 775 si prefieres
        except Exception:
            pass

        # 5) Re-inicializar el EmbeddingProcessor apuntando a la RUTA ABSOLUTA
        app.state.embedding_processor = EmbeddingProcessor(
            api=USE_API,
            persist_directory=str(CHROMA_DIR)
        )

        return {
            "status": "ok",
            "mensaje": "Colecciones eliminadas y disco saneado",
            "path": str(CHROMA_DIR),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo reiniciar chroma_db: {e}")

@app.post("/index", response_model=IndexOut, tags=["documents"])
async def index_endpoint(
    file: UploadFile = File(...),
    collection: str = Form(...),
    user_id: str = Form("usuario_123"),
):
    """
    Recibe un archivo y lo indexa con EmbeddingProcessor.process_and_store.
    - file: documento (PDF, DOCX, MD, etc.)
    - collection: nombre de la colección a crear/usar en Chroma
    - user_id: agregado a la metadata de chunks
    """
    try:
        # Leer archivo subido
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="El archivo está vacío.")

        file_bytes = BytesIO(contents)

        # Usamos el EmbeddingProcessor inicializado en startup
        if not hasattr(app.state, "embedding_processor"):
            # Fallback por si startup no corrió (no debería suceder)
            logger.warning("embedding_processor no inicializado en app.state; creando uno temporal.")
            embedding_processor = EmbeddingProcessor(True, persist_directory="./chroma_db")
        else:
            embedding_processor = app.state.embedding_processor

        # Procesar e indexar
        collection_name = await embedding_processor.process_and_store(
            documents=[(file_bytes, file.filename)],
            user_id=user_id,
            collection_name=collection
        )

        return IndexOut(
            status="ok",
            collection=collection_name,
            filename=file.filename,
            user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /index: {e}")
        raise HTTPException(status_code=500, detail="Error indexando el documento")

# ====== Inicialización de recursos pesados ======
@app.on_event("startup")
async def on_startup():
    """
    Inicializa el EmbeddingProcessor una sola vez para reutilizarlo.
    Evita descargar/cargar modelos en cada request.
    También inicializa la base de datos SQLite.
    """
    try:
        app.state.embedding_processor = EmbeddingProcessor(
            USE_API,  # usa API si tu EmbeddingProcessor lo interpreta así
            persist_directory="./chroma_db"
        )
        logger.info("EmbeddingProcessor inicializado en startup.")
        
        # Inicializar base de datos
        init_database()
        logger.info("Base de datos SQLite inicializada en startup.")
    except Exception as e:
        logger.error(f"Fallo inicializando recursos: {e}")
        # No hacemos raise para permitir levantar el servidor; /index hará fallback.

# ====== Bloque CLI original (comentado para conservarlo) ======
"""
async def main():
    embedding_processor = EmbeddingProcessor(True, persist_directory="./chroma_db")

    print("Construyendo grafo...")
    graph = build_graph()
    model_name = "gemma3:4b"
    judge_graph = crear_sistema_refinamiento(model_name=model_name)

    print("Creando estado inicial...")
    state = {
        "messages": [],
        "investigation": True,
        "current_query": "",
        "research_plan": [],
        "retrieval_queries": [],
        "query_category": "",
        "research_collections": [],
        "current_step": "",
        "needs_research": False,
        "retrieval_results": {},
        "context_for_generation": "",
        "research_completed": False,
        "retrieval_obj": Retrieval(persist_directory="./chroma_db"),
        "router_obj": Router(model_name),
        "judge_obj": judge_graph,
        "response_model": model_name,
        "api": APIManager(USE_API, model_name)
    }
    state["router_obj"].retriever = state["retrieval_obj"]

    while True:
        print("\n=== Sistema de Investigación ===")
        print("1. Indexar documentos")
        print("2. Realizar consulta")
        print("3. Salir")

        choice = input("Selecciona una opción (1-3): ")

        if choice == "1":
            await index_documents(embedding_processor)
        elif choice == "2":
            while True:
                print("\n1. Realizar query en modelo por defecto")
                print("2. Realizar query en todos los modelos")
                print("3. Regresar a menu principal")

                choice_query = input("Selecciona una opción (1-3): ")

                if choice_query == "1":
                    await process_query(graph, state)
                elif choice_query == "2":
                    query = input("Ingresa tu pregunta: ")
                    await process_query_multiple_models(query=query)
                elif choice_query == "3":
                    break
                else:
                    print("Opción no válida. Por favor, intenta de nuevo.")
        elif choice == "3":
            print("Saliendo del sistema. ¡Hasta pronto!")
            break
        else:
            print("Opción no válida. Por favor, intenta de nuevo.")

if __name__ == "__main__":
    asyncio.run(main())
"""