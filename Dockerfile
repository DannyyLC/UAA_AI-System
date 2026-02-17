# ============================================================
# Dockerfile Multi-Servicio
# ============================================================
# Este Dockerfile único sirve para todos los servicios Python:
# - Gateway (FastAPI)
# - Auth Service (gRPC)
# - Chat Service (gRPC)
# - Indexing Service (gRPC consumer)
# ============================================================
# Usamos Python 3.11 slim
FROM python:3.11-slim AS base

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos dependencias del sistema necesarias para compilar algunas librerías Python
FROM base AS dependencies

# Instalamos dependencias del sistema:
# - gcc: compilador para extensiones C
# - g++: compilador C++ para algunas librerías
# - build-essential: herramientas de compilación
# - curl: para healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos los archivos de dependencias
COPY requirements.txt .

# Instalamos las dependencias de Python
# Se instalan en esta etapa para aprovechar el cache de Docker
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# --- Etapa Final ---
FROM base AS final

# Copiamos curl para healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiamos las dependencias instaladas desde la etapa anterior
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copiamos todo el código fuente del proyecto
COPY . .

# Creamos los directorios necesarios para logs y uploads
RUN mkdir -p /app/logs /app/data/uploads

# El CMD será especificado en docker-compose.yml para cada servicio
# Esto permite que el mismo Dockerfile ejecute diferentes servicios

# Puerto predeterminado (puede ser sobreescrito por docker-compose)
EXPOSE 8000 50051 50052

# Comando por defecto (puede ser sobreescrito)
CMD ["python", "-m", "src.gateway.main"]
