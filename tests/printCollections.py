from src.researcher.retrieval import Retrieval

retriever = Retrieval(persist_directory="./chroma_db")

available_collections = retriever.get_existing_collections()
print(available_collections)