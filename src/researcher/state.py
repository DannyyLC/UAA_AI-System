from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage 
import operator
from src.researcher.router import Router
from src.researcher.retrieval import Retrieval

class State(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    investigation: bool 
    current_query: str
    research_plan: list[str]
    retrieval_queries: list[str]
    query_category: str
    research_collections: list[str]
    current_step: str
    needs_research: str
    retrieval_results: dict[str, dict[str, list]]
    context_for_generation: str
    research_completed: bool
    router_obj: Router
    retrieval_obj: Retrieval
    judge_obj: object
    response_model: str