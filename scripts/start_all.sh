#!/bin/bash

# Script para iniciar todos los servicios del sistema RAG
# Uso: ./scripts/start_all.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorios
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$PROJECT_ROOT/logs"
PIDS_DIR="$PROJECT_ROOT/.pids"

# Crear directorios necesarios
mkdir -p "$LOGS_DIR"
mkdir -p "$PIDS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Sistema RAG - Inicio de Servicios   ${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Función para verificar si un proceso está corriendo
check_service() {
    local name=$1
    local pid_file="$PIDS_DIR/$name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Función para esperar que un servicio esté listo
wait_for_service() {
    local name=$1
    local max_wait=$2
    local check_cmd=$3
    
    echo -e "${YELLOW}⏳ Esperando que $name esté listo...${NC}"
    
    for i in $(seq 1 $max_wait); do
        if eval "$check_cmd" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name está listo${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}❌ Timeout esperando $name${NC}"
    return 1
}

# Cambiar al directorio del proyecto
cd "$PROJECT_ROOT"

# Activar entorno virtual si existe
if [ -d .venv ]; then
    echo -e "${BLUE}🐍 Activando entorno virtual...${NC}"
    source .venv/bin/activate
    echo -e "${GREEN}✅ Entorno virtual activado${NC}"
elif [ -d venv ]; then
    echo -e "${BLUE}🐍 Activando entorno virtual...${NC}"
    source venv/bin/activate
    echo -e "${GREEN}✅ Entorno virtual activado${NC}"
else
    echo -e "${YELLOW}⚠️  No se encontró entorno virtual (.venv o venv)${NC}"
fi

# Cargar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo -e "${GREEN}✅ Variables de entorno cargadas${NC}"
else
    echo -e "${RED}❌ Archivo .env no encontrado${NC}"
    exit 1
fi

# Verificar que Python esté disponible
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python no encontrado${NC}"
    echo -e "${YELLOW}💡 Asegúrate de tener Python instalado o activa tu entorno virtual manualmente${NC}"
    exit 1
fi

# Paso 1: Verificar Docker Compose
echo -e "\n${BLUE}[1/5]${NC} Verificando infraestructura Docker..."

if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Docker Compose no está corriendo. Iniciando...${NC}"
    docker compose up -d
    sleep 5
fi

# Verificar servicios específicos de Docker
wait_for_service "PostgreSQL" 30 "docker compose exec -T postgres pg_isready -U rag_uaa"
wait_for_service "Qdrant" 30 "curl -s http://localhost:6333/healthz"

echo -e "${GREEN}✅ Infraestructura Docker lista${NC}"

# Paso 2: Iniciar Auth Service
echo -e "\n${BLUE}[2/5]${NC} Iniciando Auth Service..."

if check_service "auth_service"; then
    echo -e "${YELLOW}⚠️  Auth Service ya está corriendo${NC}"
else
    python -m src.services.auth.server > "$LOGS_DIR/auth_service.log" 2>&1 &
    echo $! > "$PIDS_DIR/auth_service.pid"
    
    # Esperar a que Auth Service esté listo
    sleep 3
    
    if check_service "auth_service"; then
        echo -e "${GREEN}✅ Auth Service iniciado (PID: $(cat $PIDS_DIR/auth_service.pid))${NC}"
    else
        echo -e "${RED}❌ Error al iniciar Auth Service. Ver logs: $LOGS_DIR/auth_service.log${NC}"
        exit 1
    fi
fi

# Paso 3: Iniciar Chat Service
echo -e "\n${BLUE}[3/5]${NC} Iniciando Chat Service..."

if check_service "chat_service"; then
    echo -e "${YELLOW}⚠️  Chat Service ya está corriendo${NC}"
else
    python -m src.services.chat.server > "$LOGS_DIR/chat_service.log" 2>&1 &
    echo $! > "$PIDS_DIR/chat_service.pid"
    
    # Esperar a que Chat Service esté listo
    sleep 3
    
    if check_service "chat_service"; then
        echo -e "${GREEN}✅ Chat Service iniciado (PID: $(cat $PIDS_DIR/chat_service.pid))${NC}"
    else
        echo -e "${RED}❌ Error al iniciar Chat Service. Ver logs: $LOGS_DIR/chat_service.log${NC}"
        exit 1
    fi
fi

# Paso 4: Iniciar API Gateway
echo -e "\n${BLUE}[4/5]${NC} Iniciando API Gateway..."

if check_service "gateway"; then
    echo -e "${YELLOW}⚠️  API Gateway ya está corriendo${NC}"
else
    python -m src.gateway.main > "$LOGS_DIR/gateway.log" 2>&1 &
    echo $! > "$PIDS_DIR/gateway.pid"
    
    # Esperar a que Gateway esté listo
    wait_for_service "API Gateway" 10 "curl -s http://localhost:8000/api/health"
    
    if check_service "gateway"; then
        echo -e "${GREEN}✅ API Gateway iniciado (PID: $(cat $PIDS_DIR/gateway.pid))${NC}"
    else
        echo -e "${RED}❌ Error al iniciar API Gateway. Ver logs: $LOGS_DIR/gateway.log${NC}"
        exit 1
    fi
fi

# Paso 5: Iniciar Audit Consumer (opcional)
echo -e "\n${BLUE}[5/5]${NC} Iniciando Audit Consumer..."

if check_service "audit_consumer"; then
    echo -e "${YELLOW}⚠️  Audit Consumer ya está corriendo${NC}"
else
    python -m src.kafka.consumers.audit_consumer > "$LOGS_DIR/audit_consumer.log" 2>&1 &
    echo $! > "$PIDS_DIR/audit_consumer.pid"
    
    # Esperar un poco
    sleep 2
    
    if check_service "audit_consumer"; then
        echo -e "${GREEN}✅ Audit Consumer iniciado (PID: $(cat $PIDS_DIR/audit_consumer.pid))${NC}"
    else
        echo -e "${YELLOW}⚠️  Audit Consumer no pudo iniciarse (opcional)${NC}"
    fi
fi

# Resumen
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Sistema RAG iniciado correctamente${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "📝 ${YELLOW}Logs disponibles en:${NC} $LOGS_DIR/"
echo -e "🔍 ${YELLOW}PIDs guardados en:${NC} $PIDS_DIR/"
echo -e ""
echo -e "📡 ${YELLOW}Servicios activos:${NC}"
echo -e "   • Auth Service:    grpc://localhost:50051"
echo -e "   • Chat Service:    grpc://localhost:50052"
echo -e "   • API Gateway:     http://localhost:8000"
echo -e "   • Swagger UI:      http://localhost:8000/docs"
echo -e ""
echo -e "🔧 ${YELLOW}Comandos útiles:${NC}"
echo -e "   • Ver logs:        tail -f $LOGS_DIR/<servicio>.log"
echo -e "   • Health check:    curl http://localhost:8000/api/health"
echo -e "   • Detener todo:    ./scripts/stop_all.sh"
echo -e ""
