from langgraph.graph import StateGraph, END
from src.researcher.state import State
from src.researcher.investigation import generate_research_plan
from src.researcher.judge_graph import generar_respuesta_refinada
from src.researcher.router import Router
from src.researcher.response import GeneradorRespuestas
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.llms import ollama
from src.researcher.retrieval import Retrieval
from typing import Literal, Dict, Any
from src.shared.models import get_llm
from langgraph.graph import StateGraph, END, START
from src.shared.logging_utils import get_logger
from typing import List

logger = get_logger(__name__)

# Functions, Clases and objects of the graph

# Node input
def input(state: State) -> State:
    """
    Captura la pregunta del usuario y la almacena en el estado.
    """
    user_question = input("Usuario: ") 
    user_message = HumanMessage(content=user_question)
    state["investigation"] = True
    
    state.investigation = True

    return {
            **state,
            "messages": state["messages"] + [user_message],
    }

# Node response
def response(state: State) -> State:
    """
    Genera una respuesta usando el modelo Mistral de Ollama.
    Args:
        state (State): El estado actual del grafo de investigación.
    Returns:
        State: Estado actualizado con la respuesta generada.
    """
    last_message = state["messages"][-1].content
    llm = get_llm(model_name="llama3.2:1b", temperature=0.1)  
    
    try:
        response_text = llm.invoke(last_message)
        ai_response = AIMessage(content=response_text)
        return {
            **state,
            "messages": state["messages"] + [ai_response]
        }
    
    except Exception as e:
        error_message = AIMessage(content=f"Error al generar respuesta: {str(e)}")
        
        return {
            **state,
            "messages": state["messages"] + [error_message]
        }



def build_graph():
    builder = StateGraph(State)

    # Nodes
    builder.add_node("start", START)
    builder.add_node("input", input)
    builder.add_node("response", response)
    builder.add_node("router", ...)
    builder.add_node("investigation", ...)
    builder.add_node("retrieval", ...)
    builder.add_node("judge", ...) # IA as a Judge graph
    builder.add_node("end", END)

    # Edges
    builder.add_edge("start", "input")
    builder.add_conditional_edges(
        source_node="input",
        condition=lambda state: state["investigation"],
        paths={
            True: "router",
            False: "response"
        }
    )
    builder.add_edge("response", "end") # Genera una resuesta final directa
    builder.add_edge("router", "investigation") # Comienza con el flujo de la investigacion
    builder.add_edge("investigation", "retrieval")
    builder.add_edge("retrieval", "judge")
    builder.add_edge("judge", "end")

    # Compila y retorna el grafo
    graph = builder.compile()
    return graph
