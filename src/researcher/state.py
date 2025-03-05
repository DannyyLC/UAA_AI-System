from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage 
import operator

class State(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    investigation: bool # Bandera la cual indicara si el usuarrio esta dispuesto a hacer una investigacion
    current_query: str
    research_plan: list[str]
    retrieval_queries: list[str]
    query_category: str
    research_collections: list[str]
    current_step: str