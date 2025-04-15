import asyncio
from src.researcher.investigation import generate_research_plan


# Función principal para ejecutar la investigación
async def main():
    prompt_usuario = input("Ingrese el tema de investigación: ")

    # Llamar a la función para generar el plan
    plan = await generate_research_plan(prompt=prompt_usuario, model="llama3.2:1b")

    # Mostrar el resultado
    print("\n🔍 Plan de investigación generado:")
    for i, step in enumerate(plan, 1):
        print(f"{i}. {step}")

# Ejecutar la función principal
asyncio.run(main())
