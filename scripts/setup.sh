#!/bin/bash
# Script para configuración inicial del sistema de indexación

set -e  # Exit on error

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}     UAA RAG System - Setup Inicial    ${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: No se encuentra docker-compose.yml${NC}"
    echo -e "${YELLOW} Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker no está instalado${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose no está instalado${NC}"
    exit 1
fi

# Verificar .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Archivo .env no encontrado${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}   Copiando .env.example a .env...${NC}"
        cp .env.example .env
        echo -e "${GREEN}Archivo .env creado${NC}"
        echo -e "${YELLOW}IMPORTANTE: Edita .env y configura OPENAI_API_KEY${NC}"
        exit 1
    else
        echo -e "${RED}Tampoco se encuentra .env.example${NC}"
        exit 1
    fi
fi

# Verificar OPENAI_API_KEY
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo -e "${YELLOW}OPENAI_API_KEY no configurada en .env${NC}"
    echo -e "${YELLOW}   Configúrala antes de continuar${NC}"
    exit 1
fi

echo -e "${GREEN}Configuración validada${NC}\n"

# 1. Iniciar infraestructura
echo -e "${BLUE}Iniciando infraestructura (PostgreSQL, Qdrant, Kafka)...${NC}"
docker-compose up -d postgres qdrant kafka

echo -e "${YELLOW}Esperando a que los servicios estén listos (30 segundos)...${NC}"
sleep 30

# 2. Inicializar base de datos
echo -e "${BLUE}Inicializando base de datos...${NC}"
if python scripts/init_db.py; then
    echo -e "${GREEN}Base de datos inicializada${NC}"
else
    echo -e "${YELLOW}Base de datos ya estaba inicializada${NC}"
fi

# 3. Crear topics de Kafka
echo -e "${BLUE}Creando topics de Kafka...${NC}"
if python scripts/create_kafka_topics.py; then
    echo -e "${GREEN}Topics creados${NC}"
else
    echo -e "${YELLOW}Topics ya existían${NC}"
fi

# 4. Validar sistema
echo -e "${BLUE}Validando sistema...${NC}"
if python scripts/validate_indexing.py; then
    echo -e "${GREEN}Validación exitosa${NC}"
else
    echo -e "${RED}Validación falló - revisa los errores arriba${NC}"
    exit 1
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Sistema configurado correctamente${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "${YELLOW}Próximos pasos:${NC}\n"

echo -e "${BLUE}Opción 1 - Iniciar todos los servicios automáticamente:${NC}"
echo -e "  ${GREEN}bash scripts/start_all.sh${NC}\n"

echo -e "${BLUE}Opción 2 - Iniciar servicios manualmente en terminales separadas:${NC}"
echo -e "  Terminal 1: uvicorn src.gateway.main:app --reload --port 8000"
echo -e "  Terminal 2: python src/services/auth/main.py"
echo -e "  Terminal 3: python src/services/chat/main.py"
echo -e "  Terminal 4: python -m src.services.indexing.main\n"

echo -e "${YELLOW}Comandos útiles:${NC}"
echo -e "  • Iniciar todo:     ${GREEN}bash scripts/start_all.sh${NC}"
echo -e "  • Ver estado:       ${GREEN}bash scripts/status_all.sh${NC}"
echo -e "  • Detener todo:     ${GREEN}bash scripts/stop_all.sh${NC}"
echo -e "  • Validar sistema:  ${GREEN}python scripts/validate_indexing.py${NC}\n"

echo -e "${BLUE}Documentación:${NC}"
echo -e "  • API Swagger:      http://localhost:8000/docs"
echo -e "  • Quick Start:      docs/quick-start-indexing.md"
echo -e "  • Arquitectura:     docs/indexing-system.md\n"
