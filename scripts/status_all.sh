#!/bin/bash

# Script para verificar el estado de todos los servicios
# Uso: ./scripts/status_all.sh

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorios
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDS_DIR="$PROJECT_ROOT/.pids"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Sistema RAG - Estado de Servicios   ${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Función para verificar estado de un servicio
check_service_status() {
    local name=$1
    local pid_file="$PIDS_DIR/$name.pid"
    local display_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}$display_name${NC} - Corriendo (PID: $pid)"
            return 0
        else
            echo -e "${RED}$display_name${NC} - Detenido (PID obsoleto: $pid)"
            return 1
        fi
    else
        echo -e "${RED}$display_name${NC} - No iniciado"
        return 1
    fi
}

# Función para verificar servicios Docker
check_docker_service() {
    local name=$1
    local display_name=$2
    
    if docker compose ps "$name" 2>/dev/null | grep -q "Up"; then
        local port=$(docker compose ps "$name" | grep "$name" | awk '{print $NF}')
        echo -e "${GREEN}$display_name${NC} - Corriendo ($port)"
        return 0
    else
        echo -e "${RED}$display_name${NC} - Detenido"
        return 1
    fi
}

cd "$PROJECT_ROOT"

# Verificar servicios Docker
echo -e "${BLUE}Infraestructura Docker:${NC}"
check_docker_service "postgres" "PostgreSQL"
check_docker_service "kafka" "Kafka"
check_docker_service "qdrant" "Qdrant"

echo ""

# Verificar servicios Python
echo -e "${BLUE}Servicios Python:${NC}"
check_service_status "auth_service" "Auth Service"
check_service_status "chat_service" "Chat Service"
check_service_status "gateway" "API Gateway"
check_service_status "audit_consumer" "Audit Consumer"

echo ""

# Verificar API Gateway con health check
echo -e "${BLUE}Health Check API:${NC}"
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    response=$(curl -s http://localhost:8000/api/health)
    status=$(echo $response | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$status" == "healthy" ]; then
        echo -e "${GREEN}API Gateway${NC} - http://localhost:8000/api/health"
        echo -e "   Swagger UI: http://localhost:8000/docs"
    else
        echo -e "${YELLOW}API Gateway${NC} - Respondiendo pero no healthy"
    fi
else
    echo -e "${RED}API Gateway${NC} - No responde"
fi

echo -e "\n${BLUE}========================================${NC}\n"

# Mostrar comandos útiles
echo -e "${YELLOW}Comandos útiles:${NC}"
echo -e "  • Iniciar todo:    ./scripts/start_all.sh"
echo -e "  • Detener todo:    ./scripts/stop_all.sh"
echo -e "  • Ver logs:        tail -f logs/<servicio>.log"
echo -e "  • Docker logs:     docker compose logs -f <servicio>"
echo -e ""
