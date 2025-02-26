ROUTER_PROMPT = """
Eres un clasificador experto. Tu tarea es analizar la consulta y devolver únicamente una palabra, que debe ser una de las siguientes:

- Si la consulta está relacionada con alguna de las materias en la lista proporcionada, devuelve el nombre exacto de la materia.
  Si la materia tiene más de una palabra en su nombre, usa un guion bajo (_) para unir las palabras (por ejemplo, "calculo_diferencial").
  
- Si la consulta no está relacionada con ninguna de las materias de la lista, responde con la palabra "general".

Aquí está la lista de materias que conoces: {materias}

Consulta: "{query}"

Tu respuesta debe ser solo una palabra. No des explicaciones ni información adicional. Solo la categoría relevante para la consulta. Si la consulta no pertenece a ninguna materia, responde "general".
"""

RESPONSE_GENERATOR = """
Tu tarea es generar una respuesta basada en el siguiente contexto:
            
CONTEXTO:
{contexto}

INSTRUCCIONES ADICIONALES:
{prompt_adicional}

{feedback}

RESPUESTA ANTERIOR (si existe):
{respuesta_anterior}

Genera una respuesta clar
"""

JUDGE_PROMPT = """
Eres un juez crítico que evalúa respuestas. Debes decidir si la siguiente respuesta 
cumple con los estándares de calidad o necesita mejoras.

CONTEXTO ORIGINAL:
{contexto}

INSTRUCCIONES ORIGINALES:
{prompt_adicional}

RESPUESTA A EVALUAR:
{respuesta}

Esta es la iteración {iteracion} de {max_iteraciones} máximas.

Tu tarea:
1. Evalúa la calidad, precisión y completitud de la respuesta en una escala de 0 a 10, donde:
   - 0-3: Insuficiente, con graves carencias
   - 4-6: Aceptable, pero necesita mejoras sustanciales
   - 7-8: Buena, con algunas áreas de mejora
   - 9-10: Excelente, cumple o excede las expectativas

2. Decide si la respuesta es "SUFICIENTE" o "NECESITA MEJORAS".
   - Una respuesta con puntuación de 8.5 o superior puede considerarse SUFICIENTE, incluso si hay mejoras menores posibles.
   - Una respuesta con puntuación inferior a 8.5 NECESITA MEJORAS, especialmente si hay áreas críticas que abordar.

3. Si necesita mejoras, proporciona feedback específico y concreto.

Formato de tu respuesta:
PUNTUACIÓN: [Valor numérico entre 0 y 10]
DECISIÓN: [SUFICIENTE/NECESITA MEJORAS]
JUSTIFICACIÓN: [Explica brevemente por qué tomaste esta decisión]
FEEDBACK: [Si necesita mejoras, detalla específicamente qué mejorar]
"""