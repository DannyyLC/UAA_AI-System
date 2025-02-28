import asyncio
import sys
from src.shared.logging_utils import get_logger
from langchain_ollama import OllamaLLM
import requests

# Importar la función principal del sistema de refinamiento mejorado
from src.researcher.graph import generar_respuesta_refinada

# Configurar logger
logger = get_logger("main_improved")

async def listar_modelos_disponibles():
    """Obtiene la lista de modelos disponibles en Ollama"""
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags")
        if response.status_code == 200:
            modelos = [model["name"] for model in response.json()["models"]]
            return modelos
        else:
            logger.error(f"Error al obtener modelos: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error al conectar con Ollama: {str(e)}")
        return []

async def main():
    logger.info("Iniciando prueba del sistema de refinamiento mejorado con terminación temprana")
    
    # Verificar que Ollama esté funcionando y obtener modelos disponibles
    try:
        modelos_disponibles = await listar_modelos_disponibles()
        if not modelos_disponibles:
            logger.error("No se encontraron modelos disponibles en Ollama")
            logger.info("Puedes instalar modelos con: ollama pull llama2 (o cualquier otro modelo)")
            return
        
        logger.info(f"Modelos disponibles: {', '.join(modelos_disponibles)}")
        
        # Seleccionar el primer modelo disponible o permitir selección
        if len(sys.argv) > 1 and sys.argv[1] in modelos_disponibles:
            modelo_seleccionado = sys.argv[1]
        else:
            modelo_seleccionado = modelos_disponibles[1]
            
        logger.info(f"Usando modelo: {modelo_seleccionado}")
        
        # Comprobar que el modelo está funcionando
        llm = OllamaLLM(model=modelo_seleccionado)
        llm.invoke("prueba de conexión")
        logger.info("Conexión con Ollama establecida correctamente")
    except Exception as e:
        logger.error(f"Error al conectar con Ollama: {str(e)}")
        logger.error("Asegúrate de que Ollama esté ejecutándose")
        return
    
    # Definir diferentes umbrales de calidad para probar
    umbrales = [7.0, 8.0, 9.0]
    
    for umbral in umbrales:
        logger.info(f"\n=== PRUEBA CON UMBRAL DE CALIDAD: {umbral} ===")
        
        # Ejemplo: Explicación sencilla de un concepto científico
        contexto_ejemplo = """
        La fotosíntesis es un proceso utilizado por las plantas y otros organismos para convertir la energía 
        luminosa en energía química que puede ser liberada para alimentar las actividades del organismo. 
        Este proceso químico se lleva a cabo en los cloroplastos, específicamente utilizando clorofila, 
        el pigmento verde de las plantas. En la fotosíntesis, la energía luminosa impulsa la síntesis 
        de carbohidratos a partir de dióxido de carbono y agua con la liberación de oxígeno.
        """
        
        prompt_adicional = """
        Explica el proceso de fotosíntesis de manera que un niño de 10 años pueda entenderlo.
        Usa ejemplos simples y evita terminología compleja. Incluye por qué es importante.
        """
        
        resultado = await generar_respuesta_refinada(
            contexto=contexto_ejemplo,
            prompt_adicional=prompt_adicional,
            model_name=modelo_seleccionado,
            max_iteraciones=3,  # Permitimos hasta 5 iteraciones
            umbral_calidad=umbral  # Usando el umbral actual
        )
        
        # Mostrar resultados
        logger.info(f"Resultado con umbral {umbral}:")
        logger.info(f"Iteraciones completadas: {resultado['iteraciones']} de {resultado['max_iteraciones']} máximas")
        logger.info(f"Calidad final de la respuesta: {resultado['calidad_respuesta']}/10")
        logger.info(f"Respuesta:")
        logger.info(resultado["respuesta_actual"])
    
    # Ejemplo adicional con un umbral intermedio
    logger.info("\n=== EJEMPLO DE TEXTO CIENTÍFICO (UMBRAL 8.5) ===")
    
    contexto_cientifico = """
    Los agujeros negros son regiones del espacio-tiempo donde la gravedad es tan fuerte que nada, 
    ni siquiera la luz, puede escapar de ellos una vez ha pasado el horizonte de sucesos. La teoría 
    de la relatividad general predice que una masa suficientemente compacta puede deformar el 
    espacio-tiempo para formar un agujero negro. El límite del agujero negro, llamado horizonte de 
    sucesos, marca el punto de no retorno. Los agujeros negros pueden crecer absorbiendo masa de 
    su entorno y pueden fusionarse con otros agujeros negros. A pesar de su nombre, los agujeros 
    negros no están completamente vacíos, sino que contienen una singularidad de densidad infinita.
    """
    
    prompt_cientifico = """
    Explica el concepto de agujeros negros de manera que un estudiante de secundaria pueda comprenderlo.
    Incluye algunas curiosidades interesantes y por qué son importantes para nuestra comprensión del universo.
    """
    
    resultado_cientifico = await generar_respuesta_refinada(
        contexto=contexto_cientifico,
        prompt_adicional=prompt_cientifico,
        model_name=modelo_seleccionado,
        max_iteraciones=4,
        umbral_calidad=8.5  # Umbral intermedio
    )
    
    logger.info(f"Iteraciones completadas: {resultado_cientifico['iteraciones']} de {resultado_cientifico['max_iteraciones']} máximas")
    logger.info(f"Calidad final de la respuesta: {resultado_cientifico['calidad_respuesta']}/10")
    logger.info(f"Respuesta:")
    logger.info(resultado_cientifico["respuesta_actual"])

if __name__ == "__main__":
    # Ejecutar el bucle de eventos asíncrono
    asyncio.run(main())