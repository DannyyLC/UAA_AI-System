# Usar una imagen base con CUDA y cuDNN
FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

# Configuración para evitar interacciones durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    git \
    wget \
    vim \
    build-essential \
    libtbb-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    python3-dev \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Instalar Miniconda
WORKDIR /opt
RUN curl -o miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh
ENV PATH="/opt/conda/bin:$PATH"

# Copiar archivos del entorno Conda
WORKDIR /app
COPY environment.yml .

# Crear el entorno Conda
RUN conda env create -f environment.yml && \
    conda clean -afy

# Configurar el shell para utilizar el entorno Conda
RUN echo "source activate rag-Agent" > ~/.bashrc
ENV PATH="/opt/conda/envs/rag-Agent/bin:$PATH"
ENV CONDA_DEFAULT_ENV="rag-Agent"

# Establecer caché para transformers
ENV TRANSFORMERS_CACHE=/opt/hf_cache

# Descargar el modelo Hugging Face durante la construcción
RUN mkdir -p /opt/hf_cache && \
    python -c "\
from transformers import AutoModel, AutoTokenizer; \
AutoModel.from_pretrained('BAAI/bge-large-en-v1.5'); \
AutoTokenizer.from_pretrained('BAAI/bge-large-en-v1.5')"

# Instalar Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Exponer los puertos que tu aplicación necesite
EXPOSE 8000 11434

# Copiar el código de la aplicación
COPY . .

# Crear un script para descargar múltiples modelos de Ollama durante el inicio
RUN echo '#!/bin/bash\n\
ollama serve &\n\
sleep 10\n\
if ! ollama list | grep -q "llama3:8b"; then\n\
  ollama pull llama3:8b\n\
fi\n\
if ! ollama list | grep -q "mistral:7b"; then\n\
  ollama pull mistral:7b\n\
fi\n\
if ! ollama list | grep -q "gemma3:4b"; then\n\
  ollama pull gemma3:4b\n\
fi\n\
kill -TERM $(pgrep ollama)\n\
exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Usar el script como punto de entrada
ENTRYPOINT ["/app/entrypoint.sh"]

# Mantener el contenedor en ejecución después de iniciar Ollama
CMD ["sh", "-c", "ollama serve && tail -f /dev/null"]
