import json
import pandas as pd
import os
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import time
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Verificar API key
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("Falta OPENAI_API_KEY en el entorno. Asegúrate de tener un archivo .env con tu API key.")

# Inicializar cliente de OpenAI
print('Inicializando cliente de OpenAI...')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EMBEDDING_MODEL = "text-embedding-3-small"
print(f'Usando modelo de embeddings: {EMBEDDING_MODEL}')

# Cargar el archivo JSON
print('Cargando archivo JSON con resultados...')
with open('resuts.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

resultados = data['resultados']
print(f'Total de resultados cargados: {len(resultados)}')

# Función para obtener embeddings usando OpenAI API
def get_embedding(text: str) -> list:
    """Obtiene el embedding de un texto usando la API de OpenAI"""
    try:
        response = client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error obteniendo embedding: {e}")
        return None

# Función para calcular similitud
def calcular_similitud(respuesta_modelo, respuesta_referencia):
    """Calcula la similitud coseno entre dos textos usando embeddings de OpenAI"""
    if not respuesta_modelo or not respuesta_referencia:
        return None
    
    # Obtener embeddings
    embedding_modelo = get_embedding(respuesta_modelo)
    embedding_referencia = get_embedding(respuesta_referencia)
    
    if embedding_modelo is None or embedding_referencia is None:
        return None
    
    # Convertir a arrays numpy y calcular similitud
    emb_modelo = np.array(embedding_modelo).reshape(1, -1)
    emb_referencia = np.array(embedding_referencia).reshape(1, -1)
    
    similitud_matrix = cosine_similarity(emb_modelo, emb_referencia)
    return similitud_matrix[0, 0]

# Preparar listas para almacenar resultados
resultados_evaluacion = []

# Nombres de los modelos
modelos = ['gemma', 'mistral', 'llama']

print('\n' + '='*60)
print('PROCESANDO RESPUESTAS CON RAG Y VANILLA')
print('='*60)
start_time = time.time()

# Procesar cada resultado
for idx, resultado in enumerate(resultados, 1):
    id_pregunta = resultado['id']
    pregunta = resultado['pregunta']
    respuesta_referencia = resultado['respuesta']
    especialidad = resultado['especialidad']
    
    print(f'\n[{idx}/{len(resultados)}] ID={id_pregunta} - {pregunta[:60]}...')
    
    # Evaluar cada modelo (CON RAG)
    for modelo in modelos:
        campo_rag = modelo
        campo_tiempo_rag = f'{modelo}_time'
        
        if campo_rag in resultado:
            respuesta_rag = resultado[campo_rag]
            tiempo_rag = resultado.get(campo_tiempo_rag, None)
            
            # Calcular similitud RAG
            try:
                similitud_rag = calcular_similitud(respuesta_rag, respuesta_referencia)
                print(f'  {modelo} (RAG): similitud={similitud_rag:.3f}, tiempo={tiempo_rag:.2f}s')
            except Exception as e:
                print(f'  {modelo} (RAG): ERROR - {e}')
                similitud_rag = None
            
            # Agregar a resultados
            resultados_evaluacion.append({
                'id': id_pregunta,
                'pregunta': pregunta,
                'respuesta_referencia': respuesta_referencia,
                'especialidad': especialidad,
                'modelo': modelo,
                'tipo': 'RAG',
                'respuesta_modelo': respuesta_rag,
                'similitud': similitud_rag,
                'tiempo_respuesta': tiempo_rag,
                'created_at': resultado.get('created_at', None)
            })
        
        # Evaluar versión VANILLA (sin RAG)
        campo_vanilla = f'{modelo}_vanilla'
        campo_tiempo_vanilla = f'{modelo}_vanilla_time'
        
        if campo_vanilla in resultado:
            respuesta_vanilla = resultado[campo_vanilla]
            tiempo_vanilla = resultado.get(campo_tiempo_vanilla, None)
            
            # Calcular similitud VANILLA
            try:
                similitud_vanilla = calcular_similitud(respuesta_vanilla, respuesta_referencia)
                print(f'  {modelo} (Vanilla): similitud={similitud_vanilla:.3f}, tiempo={tiempo_vanilla:.2f}s')
            except Exception as e:
                print(f'  {modelo} (Vanilla): ERROR - {e}')
                similitud_vanilla = None
            
            # Agregar a resultados
            resultados_evaluacion.append({
                'id': id_pregunta,
                'pregunta': pregunta,
                'respuesta_referencia': respuesta_referencia,
                'especialidad': especialidad,
                'modelo': modelo,
                'tipo': 'Vanilla',
                'respuesta_modelo': respuesta_vanilla,
                'similitud': similitud_vanilla,
                'tiempo_respuesta': tiempo_vanilla,
                'created_at': resultado.get('created_at', None)
            })

elapsed_time = time.time() - start_time
print(f'\nTiempo total de procesamiento: {elapsed_time/60:.2f} minutos')

# Crear DataFrame con todos los resultados
print('\nCreando DataFrame con resultados...')
df = pd.DataFrame(resultados_evaluacion)

# Guardar CSV con todos los detalles
csv_detallado = 'resultados_evaluacion_detallado.csv'
df.to_csv(csv_detallado, index=False, encoding='utf-8')
print(f'✓ Guardado: {csv_detallado}')

# Crear DataFrame pivotado para análisis más fácil
print('\nCreando DataFrames pivotados...')

# Eliminar duplicados
df_unique = df.drop_duplicates(subset=['id', 'modelo', 'tipo'], keep='first')

# Crear pivot para similitud
df_similitud = df_unique.pivot_table(
    index='id',
    columns=['modelo', 'tipo'],
    values='similitud',
    aggfunc='first'
)

# Crear pivot para tiempo_respuesta
df_tiempo = df_unique.pivot_table(
    index='id',
    columns=['modelo', 'tipo'],
    values='tiempo_respuesta',
    aggfunc='first'
)

# Renombrar columnas para claridad
df_similitud.columns = [f'similitud_{mod}_{tipo}' for mod, tipo in df_similitud.columns]
df_tiempo.columns = [f'tiempo_{mod}_{tipo}' for mod, tipo in df_tiempo.columns]

# Combinar ambos pivots
df_pivot = pd.concat([df_similitud, df_tiempo], axis=1)

# Agregar información adicional
df_info = df[['id', 'pregunta', 'respuesta_referencia', 'especialidad']].drop_duplicates('id').set_index('id')
df_pivot = df_pivot.join(df_info)

# Calcular diferencias (RAG - Vanilla)
for modelo in modelos:
    col_rag = f'similitud_{modelo}_RAG'
    col_vanilla = f'similitud_{modelo}_Vanilla'
    if col_rag in df_pivot.columns and col_vanilla in df_pivot.columns:
        df_pivot[f'mejora_{modelo}'] = df_pivot[col_rag] - df_pivot[col_vanilla]

# Guardar CSV pivotado
csv_pivot = 'resultados_evaluacion_pivot.csv'
df_pivot.to_csv(csv_pivot, encoding='utf-8')
print(f'✓ Guardado: {csv_pivot}')

# Mostrar estadísticas
print('\n' + '='*60)
print('ESTADÍSTICAS COMPARATIVAS: RAG vs VANILLA')
print('='*60)

for modelo in modelos:
    print(f'\n{modelo.upper()}:')
    
    # Estadísticas RAG
    df_rag = df[(df['modelo'] == modelo) & (df['tipo'] == 'RAG')]
    similitudes_rag = df_rag['similitud'].dropna()
    tiempos_rag = df_rag['tiempo_respuesta'].dropna()
    
    if len(similitudes_rag) > 0:
        print(f'  RAG:')
        print(f'    Similitud: {similitudes_rag.mean():.3f} (±{similitudes_rag.std():.3f})')
        print(f'    Tiempo:    {tiempos_rag.mean():.2f}s (±{tiempos_rag.std():.2f}s)')
        print(f'    N:         {len(similitudes_rag)}')
    
    # Estadísticas Vanilla
    df_vanilla = df[(df['modelo'] == modelo) & (df['tipo'] == 'Vanilla')]
    similitudes_vanilla = df_vanilla['similitud'].dropna()
    tiempos_vanilla = df_vanilla['tiempo_respuesta'].dropna()
    
    if len(similitudes_vanilla) > 0:
        print(f'  Vanilla:')
        print(f'    Similitud: {similitudes_vanilla.mean():.3f} (±{similitudes_vanilla.std():.3f})')
        print(f'    Tiempo:    {tiempos_vanilla.mean():.2f}s (±{tiempos_vanilla.std():.2f}s)')
        print(f'    N:         {len(similitudes_vanilla)}')
    
    # Diferencia
    if len(similitudes_rag) > 0 and len(similitudes_vanilla) > 0:
        mejora_similitud = similitudes_rag.mean() - similitudes_vanilla.mean()
        mejora_tiempo = tiempos_rag.mean() - tiempos_vanilla.mean()
        print(f'  Mejora con RAG:')
        print(f'    Δ Similitud: {mejora_similitud:+.3f} ({(mejora_similitud/similitudes_vanilla.mean())*100:+.1f}%)')
        print(f'    Δ Tiempo:    {mejora_tiempo:+.2f}s')

# Análisis por especialidad
print('\n' + '='*60)
print('ANÁLISIS POR ESPECIALIDAD')
print('='*60)

especialidades = df['especialidad'].unique()
for especialidad in sorted(especialidades):
    print(f'\n{especialidad.upper()}:')
    df_esp = df[df['especialidad'] == especialidad]
    
    for modelo in modelos:
        # RAG
        sim_rag = df_esp[(df_esp['modelo'] == modelo) & (df_esp['tipo'] == 'RAG')]['similitud'].dropna()
        # Vanilla
        sim_vanilla = df_esp[(df_esp['modelo'] == modelo) & (df_esp['tipo'] == 'Vanilla')]['similitud'].dropna()
        
        if len(sim_rag) > 0 or len(sim_vanilla) > 0:
            print(f'  {modelo}:', end='')
            if len(sim_rag) > 0:
                print(f' RAG={sim_rag.mean():.3f}', end='')
            if len(sim_vanilla) > 0:
                print(f' Vanilla={sim_vanilla.mean():.3f}', end='')
            if len(sim_rag) > 0 and len(sim_vanilla) > 0:
                mejora = sim_rag.mean() - sim_vanilla.mean()
                print(f' Δ={mejora:+.3f}', end='')
            print()

print('\n¡Evaluación completada!')
print('Archivos generados:')
print(f'  - {csv_detallado}')
print(f'  - {csv_pivot}')

