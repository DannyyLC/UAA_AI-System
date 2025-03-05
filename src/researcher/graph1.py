from langgraph.graph import StateGraph, END
from src.researcher.state import State
from src.researcher.investigation import generate_research_plan
from src.researcher.judge import Judge
from src.researcher.router import Router
from src.researcher.response import GeneradorRespuestas
from src.researcher.retrieval import Retrieval
from typing import Literal, Dict, Any
from datetime import datetime
from langgraph.graph import StateGraph, END
from src.shared.logging_utils import get_logger
from typing import List


logger = get_logger(__name__)

# Router to decide the next step
def flow_router(state: State) -> Literal[
    "research_planning", 
    "generation",
    "retrieval",
    "evaluation",
    "complete"
    ]:
    """Decides the next step in the workflow based on the current state."""
    
    # Check current step to determine next action
    current_step = state["current_step"]
    
    if current_step == "routing":
        # After routing, either go to research or directly to generation
        return "research_planning" if state["needs_research"] else "generation"
    
    elif current_step == "research_planning":
        # After planning, always go to retrieval
        return "retrieval"
    
    elif current_step == "retrieval":
        # After retrieval, always go to generation
        return "generation"
    
    elif current_step == "generation":
        # After generation, go to evaluation
        return "evaluation"
    
    elif current_step == "evaluation":
        # After evaluation, either loop back to generation or end
        if state["response_evaluated"] and state["calidad_respuesta"] >= 8.5:
            return "complete"
        elif state["iteraciones"] >= state["max_iteraciones"]:
            return "complete"
        else:
            return "generation"
    
    # Default case - should not reach here
    logger.warning(f"Unexpected state in flow_router: {current_step}")
    return "complete"

# Query Router Node
class QueryRouter:
    def __init__(self):
        self.router = Router()
    
    def __call__(self, state: State) -> State:
        logger.info("Executing query router")
        
        # Classify the query using the Router
        query = state["current_query"]
        category = self.router.classify_with_llm(query)
        
        # Update state with classification result
        state["query_category"] = category
        
        # Determine if research is needed based on category
        # Assume general category doesn't need research, others do
        state["needs_research"] = category != "general"
        
        # Update current step
        state["current_step"] = "routing"
        
        return state

# Research Planning Node
class ResearchPlanner:
    def __init__(self):
        pass
    
    async def __call__(self, state: State) -> State:
        if not state["needs_research"]:
            logger.info("Skipping research planning - not needed")
            return state
            
        logger.info("Executing research planning")
        
        # Generate research plan
        query = state["current_query"]
        plan = await generate_research_plan(query)
        
        # Update state with research plan
        state["research_plan"] = plan
        
        # Prepare queries for retrieval based on research plan
        # Using the original query and adding queries derived from the plan
        retrieval_queries = [query]
        for step in plan[:3]:  # Using first 3 steps as additional queries
            retrieval_queries.append(f"{query} {step}")
        
        state["retrieval_queries"] = retrieval_queries
        
        # Determine which collections to search based on category
        category = state["query_category"]
        # This mapping would need to be configured based on your collections
        collection_mapping = {
            "programacion": ["programming_docs", "code_examples"],
            "estructura_de_datos": ["data_structures", "algorithms"],
            "unix": ["unix_docs", "command_references"],
            "ecuaciones_diferenciales": ["math_concepts", "differential_equations"]
        }
        
        state["research_collections"] = collection_mapping.get(category, ["general_knowledge"])
        
        # Update current step
        state["current_step"] = "research_planning"
        
        return state

# Retrieval Node
class RetrievalNode:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.retriever = Retrieval(persist_directory=persist_directory)
    
    def __call__(self, state: State) -> State:
        if not state["needs_research"]:
            logger.info("Skipping retrieval - not needed")
            return state
            
        logger.info("Executing retrieval")
        
        try:
            # Execute retrieval with queries and collections from state
            queries = state["retrieval_queries"]
            collections = state["research_collections"]
            
            # Get available collections and filter to those that exist
            available_collections = self.retriever.get_existing_collections()
            valid_collections = [c for c in collections if c in available_collections]
            
            if not valid_collections:
                logger.warning(f"No valid collections found among: {collections}")
                valid_collections = ["general_knowledge"]  # Fallback
            
            # Perform search
            search_results = self.retriever.search(queries, valid_collections)
            
            # Extract text from results
            context_text = self.retriever.extract_text_from_search_results(search_results)
            
            # Update state
            state["retrieval_results"] = search_results
            state["context_for_generation"] = context_text
            state["research_completed"] = True
            
        except Exception as e:
            logger.error(f"Error in retrieval: {str(e)}")
            state["retrieval_results"] = {}
            state["context_for_generation"] = ""
            state["research_completed"] = False
        
        # Update current step
        state["current_step"] = "retrieval"
        
        return state

# Generator Wrapper
class GeneratorNode:
    def __init__(self, model_name: str = "mistral"):
        self.generator = GeneradorRespuestas(model_name=model_name)
    
    def __call__(self, state: State) -> State:
        logger.info(f"Executing generator. Iteration {state['iteraciones']+1}/{state['max_iteraciones']}")
        
        # Prepare input for generator
        refiner_state = {
            "contexto": state["current_query"],
            "prompt_adicional": state["context_for_generation"] if state["needs_research"] else "",
            "respuesta_actual": state.get("respuesta_actual", ""),
            "feedback": state.get("feedback", ""),
            "iteraciones": state["iteraciones"],
            "max_iteraciones": state["max_iteraciones"],
            "resultado": "mejorar",
            "calidad_respuesta": state.get("calidad_respuesta", 0.0),
            "mejora_necesaria": True
        }
        
        # Call generator
        result = self.generator(refiner_state)
        
        # Update state with generator results
        state["respuesta_actual"] = result["respuesta_actual"]
        state["iteraciones"] = result["iteraciones"]
        state["response_generated"] = True
        
        # Update current step
        state["current_step"] = "generation"
        
        return state

# Judge Wrapper
class JudgeNode:
    def __init__(self, model_name: str = "mistral", umbral_calidad: float = 8.5):
        self.judge = Judge(model_name=model_name, umbral_calidad=umbral_calidad)
    
    def __call__(self, state: State) -> State:
        logger.info(f"Executing judge. Iteration {state['iteraciones']}/{state['max_iteraciones']}")
        
        # Prepare input for judge
        refiner_state = {
            "contexto": state["current_query"],
            "prompt_adicional": state["context_for_generation"] if state["needs_research"] else "",
            "respuesta_actual": state["respuesta_actual"],
            "feedback": state.get("feedback", ""),
            "iteraciones": state["iteraciones"],
            "max_iteraciones": state["max_iteraciones"],
            "resultado": "mejorar",
            "calidad_respuesta": state.get("calidad_respuesta", 0.0),
            "mejora_necesaria": True
        }
        
        # Call judge
        result = self.judge(refiner_state)
        
        # Update state with judge results
        state["feedback"] = result.get("feedback", "")
        state["calidad_respuesta"] = result.get("calidad_respuesta", 0.0)
        state["response_evaluated"] = True
        
        # If judge says we're done or reached max iterations, prepare final response
        if result["resultado"] == "finalizar" or state["iteraciones"] >= state["max_iteraciones"]:
            state["final_response"] = state["respuesta_actual"]
            
            # Add evaluation message to conversation
            timestamp = datetime.now().isoformat()
            evaluation_msg = Message(
                role="system",
                content=f"Response quality: {state['calidad_respuesta']}/10 after {state['iteraciones']} iterations",
                timestamp=timestamp
            )
            state["messages"].append(evaluation_msg)
            
            # Add final assistant message
            assistant_msg = Message(
                role="assistant",
                content=state["final_response"],
                timestamp=timestamp
            )
            state["messages"].append(assistant_msg)
        
        # Update current step
        state["current_step"] = "evaluation"
        
        return state

# Final Node
class Finalizer:
    def __call__(self, state: State) -> State:
        logger.info("Finalizing response")
        
        # Ensure we have a final response
        if not state.get("final_response"):
            state["final_response"] = state["respuesta_actual"]
            
            # Add final assistant message if not already added
            timestamp = datetime.now().isoformat()
            assistant_msg = Message(
                role="assistant",
                content=state["final_response"],
                timestamp=timestamp
            )
            state["messages"].append(assistant_msg)
        
        # Update metadata with final stats
        state["metadata"] = {
            "category": state["query_category"],
            "research_needed": state["needs_research"],
            "iterations": state["iteraciones"],
            "quality_score": state["calidad_respuesta"],
            "completion_time": datetime.now().isoformat()
        }
        
        # Update current step
        state["current_step"] = "complete"
        
        return state

# Create the LangGraph
def create_flow_graph(
    model_name: str = "mistral", 
    max_iterations: int = 3, 
    quality_threshold: float = 8.5,
    persist_directory: str = "./chroma_db"
):
    # Initialize nodes
    router_node = QueryRouter()
    research_planner = ResearchPlanner()
    retrieval_node = RetrievalNode(persist_directory=persist_directory)
    generator_node = GeneratorNode(model_name=model_name)
    judge_node = JudgeNode(model_name=model_name, umbral_calidad=quality_threshold)
    finalizer_node = Finalizer()
    
    # Create graph
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("research_planner", research_planner)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("judge", judge_node)
    workflow.add_node("finalizer", finalizer_node)
    
    # Set entry point
    workflow.set_entry_point("router")
    
    # Add conditional edges based on flow router
    workflow.add_conditional_edges(
        "router",
        flow_router,
        {
            "research_planning": "research_planner",
            "generation": "generator"
        }
    )
    
    workflow.add_edge("research_planner", "retrieval")
    workflow.add_edge("retrieval", "generator")
    workflow.add_edge("generator", "judge")
    
    workflow.add_conditional_edges(
        "judge",
        flow_router,
        {
            "generation": "generator",
            "complete": "finalizer"
        }
    )
    
    workflow.add_edge("finalizer", END)
    
    # Compile graph
    app = workflow.compile()
    
    return app

# Main function to process a query
async def process_query(
    query: str,
    conversation_history: List[Message] = None,
    model_name: str = "mistral",
    max_iterations: int = 3,
    quality_threshold: float = 8.5,
    persist_directory: str = "./chroma_db"
) -> Dict[str, Any]:
    """
    Process a user query through the complete flow.
    
    Args:
        query: User query string
        conversation_history: Optional list of previous messages
        model_name: Name of the model to use
        max_iterations: Maximum number of refinement iterations
        quality_threshold: Quality threshold for response (0-10)
        persist_directory: Directory for ChromaDB
        
    Returns:
        Dict: Final state with response and metadata
    """
    # Create flow graph
    flow = create_flow_graph(
        model_name=model_name,
        max_iterations=max_iterations,
        quality_threshold=quality_threshold,
        persist_directory=persist_directory
    )
    
    # Initialize messages if none provided
    if conversation_history is None:
        conversation_history = []
    
    # Add current query to conversation history
    timestamp = datetime.now().isoformat()
    user_msg = Message(
        role="user",
        content=query,
        timestamp=timestamp
    )
    conversation_history.append(user_msg)
    
    # Initialize state
    initial_state = State(
        messages=conversation_history,
        current_query=query,
        needs_research=False,  # Will be determined by router
        research_completed=False,
        response_generated=False,
        response_evaluated=False,
        current_step="routing",  # Start with routing
        query_category="",
        research_plan=[],
        research_collections=[],
        retrieval_queries=[],
        retrieval_results={},
        context_for_generation="",
        respuesta_actual="",
        feedback="",
        calidad_respuesta=0.0,
        iteraciones=0,
        max_iteraciones=max_iterations,
        final_response="",
        metadata={}
    )
    
    # Execute flow
    try:
        final_state = await flow.ainvoke(initial_state)
        return final_state
    except Exception as e:
        logger.error(f"Error in flow execution: {str(e)}")
        
        # Create error response
        error_state = initial_state.copy()
        error_state["final_response"] = f"Error processing your query: {str(e)}"
        error_state["current_step"] = "complete"
        
        # Add error message to conversation
        error_msg = Message(
            role="assistant",
            content=error_state["final_response"],
            timestamp=datetime.now().isoformat()
        )
        error_state["messages"].append(error_msg)
        
        return error_state
    