from src.indexing import EmbeddingProcessor
from src.shared.logging_utils import get_logger
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from src.researcher.graph import build_graph  
from src.researcher.router import Router
from src.researcher.retrieval import Retrieval
from src.researcher.judge_graph import crear_sistema_refinamiento
from data.questions import questions
import time
import pandas as pd
import asyncio

logger = get_logger(__name__)

# Instancias
embedding_processor = EmbeddingProcessor(persist_directory="./chroma_db")

models = ["gemma3:4b", "mistral:7b","llama3:8b"]

async def run_graph_with_query(query: str, graph, state) -> Dict[str, Any]:
    """
    Ejecuta el grafo de investigación con una consulta específica.
    
    Args:
        query (str): La consulta del usuario.
        
    Returns:
        Dict[str, Any]: El estado final tras ejecutar el grafo.
    """
    try:
        
        # Ejecutar el grafo
        print(f"Iniciando grafo con consulta: {query}")
        result = await graph.ainvoke(state)
        
        return result
    except Exception as e:
        logger.error(f"Error en run_graph_with_query: {str(e)}")
        raise

async def evaluation(graph, state):
    """Maneja la opción de consulta al sistema."""
    logger.info("\n============= COMENZANDO EVALUACION =============")
    try:    
        for model in models:
            logger.info(f"\n============= EVALUANDO {model.upper()} =============")
            model_start_time = time.time()
            with open(f"{model}.txt", 'w') as f:
                for query in questions:
                    question_start_time = time.time()
                    try:
                        # Agregar el mensaje de usuario al historial
                        state["messages"].append(HumanMessage(content=query))
                        state["current_query"] = query
                        
                        # Ejecutar el grafo con la consulta
                        final_state = await run_graph_with_query(query, graph, state)
                        
                        state.update(final_state)
                        
                        # Mostrar respuesta
                        print("\n=== RESPUESTA ===")
                        
                        # Escribir la pregunta en el archivo
                        f.write(f"Pregunta: {query}\n")
                        
                        if state["messages"] and len(state["messages"]) > 1:
                            ai_response = state["messages"][-1]
                            # print(ai_response.content)
                            f.write(f"Respuesta: {ai_response.content}\n")
                            
                            # Si hay metadatos disponibles, mostrarlos
                            if hasattr(ai_response, "additional_kwargs") and ai_response.additional_kwargs:
                                print("\n=== Metadatos ===")
                                f.write("Metadatos:\n")
                                for key, value in ai_response.additional_kwargs.items():
                                    print(f"{key}: {value}")
                                    f.write(f"{key}: {value}\n")
                                f.write("\n")
                        else:
                            print("No se obtuvo una respuesta.")
                            f.write("\n")
                    except Exception as e:
                        logger.error(f"Error al procesar la consulta: {str(e)}")
                        f.write(f"Pregunta: {query}\n")
                        f.write(f"Error: {str(e)}\n\n")
                    finally:
                        question_end_time = time.time()
                        question_time = question_end_time - question_start_time
                        print(f"\nTiempo de respuesta para esta pregunta: {question_time:.2f} segundos")
                        f.write(f"Tiempo de respuesta: {question_time:.2f} segundos\n\n")
            
            model_end_time = time.time()
            total_model_time = model_end_time - model_start_time
            print(f"\nTiempo total para el modelo {model}: {total_model_time:.2f} segundos")
            with open(f"{model}.txt", 'a') as f:
                f.write(f"\nTiempo total de ejecución del modelo: {total_model_time:.2f} segundos\n")
    except Exception as e:
        logger.error(f"Error al procesar la consulta: {str(e)}")
        print(f"Error: {str(e)}")

async def evaluationpd():
    """Maneja la opción de consulta al sistema utilizando pandas para organizar los resultados."""
    logger.info("\n============= COMENZANDO EVALUACION CON PANDAS =============")
    
    # Crear un diccionario para almacenar los resultados
    resultados = {}
    
    try:
        for model in models:
            logger.info(f"\n============= EVALUANDO {model.upper()} =============")
            model_start_time = time.time()

            # Construir el grafo
            graph = build_graph()
            model_name = model
            judge_graph = crear_sistema_refinamiento(model_name=model_name)
            # Estado inicial
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
                "retrieval_obj" : Retrieval(persist_directory="./chroma_db"),
                "router_obj" : Router(model_name=model),
                "judge_obj" : judge_graph,
                "response_model" : model
            }

            state["router_obj"].retriever = state["retrieval_obj"]
            
            # Diccionario para almacenar los resultados de este modelo
            resultados_modelo = {
                "Preguntas": [],
                "Tiempos por pregunta": [],
                "Respuestas": [],
                "Metadatos": []
            }
            
            for query in questions:
                question_start_time = time.time()
                try:
                    # Agregar el mensaje de usuario al historial
                    state["messages"].append(HumanMessage(content=query))
                    state["current_query"] = query
                    
                    # Ejecutar el grafo con la consulta
                    final_state = await run_graph_with_query(query, graph, state)
                    state.update(final_state)
                    
                    # Almacenar la pregunta
                    resultados_modelo["Preguntas"].append(query)
                    
                    if state["messages"] and len(state["messages"]) > 1:
                        ai_response = state["messages"][-1]
                        resultados_modelo["Respuestas"].append(ai_response.content)
                        
                        # Almacenar metadatos si existen
                        if hasattr(ai_response, "additional_kwargs") and ai_response.additional_kwargs:
                            resultados_modelo["Metadatos"].append(str(ai_response.additional_kwargs))
                        else:
                            resultados_modelo["Metadatos"].append("Sin metadatos")
                    else:
                        resultados_modelo["Respuestas"].append("No se obtuvo una respuesta")
                        resultados_modelo["Metadatos"].append("Sin metadatos")
                        
                except Exception as e:
                    logger.error(f"Error al procesar la consulta: {str(e)}")
                    resultados_modelo["Preguntas"].append(query)
                    resultados_modelo["Respuestas"].append(f"Error: {str(e)}")
                    resultados_modelo["Metadatos"].append("Error en procesamiento")
                finally:
                    question_end_time = time.time()
                    question_time = question_end_time - question_start_time
                    resultados_modelo["Tiempos por pregunta"].append(question_time)
            
            model_end_time = time.time()
            total_model_time = model_end_time - model_start_time
            
            # Agregar el tiempo total al diccionario
            resultados_modelo["Tiempo total"] = total_model_time
            
            # Guardar los resultados del modelo
            resultados[model] = resultados_modelo
            
            # Crear DataFrame para este modelo
            df_modelo = pd.DataFrame(resultados_modelo)
            
            # Guardar el DataFrame en un archivo CSV
            df_modelo.to_csv(f"{model}_resultados.csv", index=False)
            
            # Imprimir resumen
            print(f"\nResumen para el modelo {model}:")
            print(f"Tiempo total de ejecución: {total_model_time:.2f} segundos")
            print(f"Tiempo promedio por pregunta: {sum(resultados_modelo['Tiempos por pregunta'])/len(resultados_modelo['Tiempos por pregunta']):.2f} segundos")
            
    except Exception as e:
        logger.error(f"Error en la evaluación: {str(e)}")
        print(f"Error: {str(e)}")
    
    # Crear un DataFrame final con todos los modelos
    df_final = pd.DataFrame()
    for model, datos in resultados.items():
        df_temp = pd.DataFrame(datos)
        df_temp['Modelo'] = model
        df_final = pd.concat([df_final, df_temp], ignore_index=True)
    
    # Guardar el DataFrame final
    df_final.to_csv('resultados_finales.csv', index=False)
    
    return df_final
    
if __name__ == "__main__":
    asyncio.run(evaluationpd())
