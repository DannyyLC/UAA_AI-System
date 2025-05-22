""" Listas con las preguntas con las cuales se evaluara el desempeño de los modelos 
            Se estaran usando aproximadamente 10 preguntas de cada area"""
# Tecnologia
redes = [
    "¿Cuál es la diferencia entre una dirección IP pública y una privada?",
    "¿Qué es el modelo OSI y cuáles son sus 7 capas?",
    "¿Cómo funciona el protocolo TCP y en qué se diferencia de UDP?",
    "¿Qué es una máscara de subred y para qué sirve?",
    "¿Qué es el protocolo ARP y cómo se utiliza en una red local?",
    "¿Qué diferencia hay entre una red LAN, MAN y WAN?",
    "¿Qué es el DNS y cómo resuelve nombres de dominio?",
    "¿Cómo se detectan y previenen ataques de tipo spoofing en redes?",
    "¿Cómo se implementa NAT y cuál es su función en una red doméstica?",
    "¿Cuál es la diferencia entre HTTP y HTTPS?"
]

# IA
ia = [
    "¿Qué es la inteligencia artificial?",
    "¿Cuál es la diferencia entre IA débil y IA fuerte?",
    "¿Qué es un algoritmo de aprendizaje automático?",
    "¿Qué es una red neuronal artificial?",
    "¿Qué es el procesamiento del lenguaje natural (NLP)?",
    "¿Qué es el aprendizaje por refuerzo?",
    "¿Qué es la visión por computadora?",
    "¿Qué es el sesgo en los algoritmos de IA y por qué es importante?",
    "¿Qué es la explicabilidad en IA y por qué es crucial?",
    "¿Qué son los sistemas expertos y cómo funcionan?"
]

# Matematicas
matematicas = [
    "¿Qué es un número primo?",
    "¿Cuál es la fórmula para calcular el área de un círculo?",
    "¿Qué es una función lineal?",
    "¿Qué es la derivada de una función?",
    "¿Qué es una integral definida?",
    "¿Qué es una matriz y para qué se utiliza?",
    "¿Qué es el teorema de Pitágoras y en qué contexto se aplica?",
    "¿Qué es una serie de Fourier?",
    "¿Qué es la transformada de Laplace y cuál es su propósito?",
    "¿Qué es la teoría de grupos en álgebra abstracta?"
]

# Quimica
quimica = [
    "¿Qué es un átomo?",
    "¿Cuál es la diferencia entre un elemento y un compuesto?",
    "¿Qué es la tabla periódica y qué información proporciona?",
    "¿Qué es una reacción química?",
    "¿Qué es la estequiometría?",
    "¿Qué es un enlace covalente?",
    "¿Qué es la termodinámica química?",
    "¿Qué es la cinética química?",
    "¿Qué es la espectroscopia y cómo se utiliza en química?",
    "¿Qué es la química cuántica?"
]

# Leyes
leyes = [
    "¿Qué es una ley?",
    "¿Cuál es la diferencia entre derecho civil y derecho penal?",
    "¿Qué es un contrato?",
    "¿Qué es la jurisprudencia?",
    "¿Qué es el derecho internacional?",
    "¿Qué es la propiedad intelectual?",
    "¿Qué es el derecho constitucional?",
    "¿Qué es la teoría del derecho?",
    "¿Qué es el derecho comparado?",
    "¿Qué es la filosofía del derecho?"
]

# Finanzas
finanzas = [
    "¿Qué es el dinero?",
    "¿Qué es una acción en el mercado de valores?",
    "¿Qué es un bono?",
    "¿Qué es la inflación?",
    "¿Qué es el Producto Interno Bruto (PIB)?",
    "¿Qué es la diversificación en inversiones?",
    "¿Qué es el análisis fundamental en finanzas?",
    "¿Qué es la teoría de portafolios?",
    "¿Qué es la econometría?",
    "¿Qué es la finanza conductual?"
]

# Biologia
biologia = [
    "¿Qué es una célula?",
    "¿Cuál es la diferencia entre ADN y ARN?",
    "¿Qué es la fotosíntesis?",
    "¿Qué es la evolución?",
    "¿Qué es la genética mendeliana?",
    "¿Qué es la ecología?",
    "¿Qué es la biotecnología?",
    "¿Qué es la neurobiología?",
    "¿Qué es la biología molecular?",
    "¿Qué es la bioinformática?"
]

# Automotriz
sistemas_operativos = [
    "¿Cuál es la diferencia entre multiprocesamiento y multitarea?",
    "¿Qué es un deadlock y cómo se puede evitar?",
    "¿En qué consiste la planificación de CPU Round Robin y cuáles son sus ventajas?",
    "¿Qué es la memoria virtual y cómo funciona la paginación?",
    "¿Cuál es la diferencia entre un proceso y un hilo (thread)?",
    "¿Cómo se implementa un sistema de archivos en un sistema operativo?",
    "¿Qué es el modo kernel y modo usuario, y por qué es importante esta separación?",
    "¿Qué son los semáforos y cómo se utilizan para sincronización de procesos?",
    "¿Qué es el sistema de planificación por prioridades y qué problemas puede generar?",
    "¿Cuál es la función del scheduler en un sistema operativo?"
]

# Medicina
medicina = [
    "¿Qué es un órgano?",
    "¿Cuál es la función del corazón?",
    "¿Qué es una bacteria?",
    "¿Qué es la anatomía humana?",
    "¿Qué es la fisiología?",
    "¿Qué es la farmacología?",
    "¿Qué es la epidemiología?",
    "¿Qué es la cirugía mínimamente invasiva?",
    "¿Qué es la medicina regenerativa?",
    "¿Qué es la neurocirugía?"
]

# Fisica
fisica = [
    "¿Qué es la fuerza?",
    "¿Qué es la energía?",
    "¿Qué es la ley de la gravitación universal?",
    "¿Qué es la termodinámica?",
    "¿Qué es la mecánica cuántica?",
    "¿Qué es la relatividad general?",
    "¿Qué es la física de partículas?",
    "¿Qué es la óptica cuántica?",
    "¿Qué es la astrofísica?",
    "¿Qué es la teoría de cuerdas?"
]

questions = []
questions = redes + ia + matematicas + quimica + leyes + finanzas + biologia + sistemas_operativos + medicina + fisica
