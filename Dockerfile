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

# Instalar Miniconda con detección de arquitectura
WORKDIR /opt
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"; \
    else \
        echo "Arquitectura no soportada: $ARCH" && exit 1; \
    fi && \
    curl -o miniconda.sh $MINICONDA_URL && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh

ENV PATH="/opt/conda/bin:$PATH"

# Crear el entorno Python sin usar environment.yml
RUN conda create -n rag-Agent python=3.10 -y

# Activar el entorno y instalar dependencias específicas por arquitectura
RUN /opt/conda/envs/rag-Agent/bin/pip install --upgrade pip

# Instalar PyTorch según la arquitectura
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        /opt/conda/envs/rag-Agent/bin/pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121; \
    else \
        /opt/conda/envs/rag-Agent/bin/pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu; \
    fi

# Copiar e instalar el resto de dependencias
WORKDIR /app
COPY requirements.txt .

RUN /opt/conda/envs/rag-Agent/bin/pip install -r requirements.txt

# Configurar el entorno
ENV PATH="/opt/conda/envs/rag-Agent/bin:$PATH"
ENV CONDA_DEFAULT_ENV="rag-Agent"
ENV TRANSFORMERS_CACHE=/opt/hf_cache

# Crear script de activación
RUN echo "source activate rag-Agent" > ~/.bashrc

# Descargar el modelo Hugging Face
RUN mkdir -p /opt/hf_cache && \
    /opt/conda/envs/rag-Agent/bin/python -c "\
from transformers import AutoModel, AutoTokenizer; \
AutoModel.from_pretrained('BAAI/bge-large-en-v1.5'); \
AutoTokenizer.from_pretrained('BAAI/bge-large-en-v1.5')"

# Instalar Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

EXPOSE 8000 11434

# Copiar el código de la aplicación
COPY . .

# Crear script de entrada
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

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "ollama serve && tail -f /dev/null"]