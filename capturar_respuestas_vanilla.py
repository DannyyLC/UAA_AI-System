import json
import time
from src.api.APIManager import APIManager
from dotenv import load_dotenv

load_dotenv()

# Cargar el archivo JSON con los resultados existentes
print('Cargando archivo JSON con resultados...')
with open('resuts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

resultados = data['resultados']
print(f'Total de resultados cargados: {len(resultados)}')

# Modelos a procesar
modelos_config = {
    'gemma': 'gemma3:4b',
    'mistral': 'mistral:7b',
    'llama': 'llama3.1:8b'
}

print('\n' + '='*60)
print('CAPTURANDO RESPUESTAS VANILLA (SIN RAG)')
print('='*60)

# Procesar cada resultado
for idx, resultado in enumerate(resultados, 1):
    id_pregunta = resultado['id']
    pregunta = resultado['pregunta']
    especialidad = resultado['especialidad']
    
    print(f'\n[{idx}/{len(resultados)}] Procesando ID={id_pregunta}')
    print(f'Pregunta: {pregunta[:80]}...')
    print(f'Especialidad: {especialidad}')
    
    # Procesar cada modelo
    for modelo_key, modelo_name in modelos_config.items():
        campo_vanilla = f'{modelo_key}_vanilla'
        campo_tiempo_vanilla = f'{modelo_key}_vanilla_time'
        
        # Verificar si ya existe la respuesta vanilla
        if campo_vanilla in resultado and resultado[campo_vanilla]:
            print(f'  ✓ {modelo_key}: Ya tiene respuesta vanilla, saltando...')
            continue
        
        print(f'  → {modelo_key}: Consultando modelo...')
        
        try:
            # Inicializar APIManager para este modelo
            api_manager = APIManager(enabled=True, model=modelo_name)
            
            # Medir tiempo y obtener respuesta
            start_time = time.time()
            respuesta = api_manager.getResponse(pregunta)
            elapsed_time = time.time() - start_time
            
            # Guardar en el resultado
            resultado[campo_vanilla] = respuesta
            resultado[campo_tiempo_vanilla] = elapsed_time
            
            print(f'    ✓ Tiempo: {elapsed_time:.2f}s')
            print(f'    ✓ Respuesta: {respuesta[:100]}...')
            
        except Exception as e:
            print(f'    ✗ ERROR: {str(e)}')
            resultado[campo_vanilla] = f"ERROR: {str(e)}"
            resultado[campo_tiempo_vanilla] = None
    
    # Guardar progreso después de cada pregunta (por seguridad)
    if idx % 5 == 0:  # Guardar cada 5 preguntas
        print(f'\n  💾 Guardando progreso... ({idx}/{len(resultados)})')
        with open('resuts.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

# Guardar resultado final
print('\n' + '='*60)
print('Guardando archivo final...')
with open('resuts.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print('✓ Proceso completado exitosamente')
print(f'✓ Archivo actualizado: resuts.json')

# Mostrar estadísticas
print('\n' + '='*60)
print('ESTADÍSTICAS')
print('='*60)

for modelo_key in modelos_config.keys():
    campo_vanilla = f'{modelo_key}_vanilla'
    respuestas_validas = sum(1 for r in resultados if campo_vanilla in r and r[campo_vanilla] and not r[campo_vanilla].startswith('ERROR'))
    print(f'{modelo_key}: {respuestas_validas}/{len(resultados)} respuestas vanilla capturadas')

print('\n¡Listo! Ahora puedes ejecutar evaluacionResultados.py para comparar RAG vs Vanilla')
