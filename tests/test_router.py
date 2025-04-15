from src.researcher.router import Router

# Ejemplo de uso
if __name__ == "__main__":
    query_router = Router()
    
    # Prueba con una consulta
    query1 = "¿Cómo se resuelven ecuaciones diferenciales en matemáticas?"
    category1 = query_router.classify_with_llm(query1)
    print(f"Categoría: {category1}")  # Esperamos "matematicas"
    
    query2 = "¿Qué es el cambio climático?"
    category2 = query_router.classify_with_llm(query2)
    print(f"Categoría: {category2}")  # Esperamos "general"
    
    query3 = "Explícame cómo funciona la programación orientada a objetos"
    category3 = query_router.classify_with_llm(query3)
    print(f"Categoría: {category3}")  # Esperamos "programacion"
    
    query4 = "¿Cómo resuelvo una integral de cálculo diferencial?"
    category4 = query_router.classify_with_llm(query4)
    print(f"Categoría: {category4}")  # Esperamos "calculo_diferencial"