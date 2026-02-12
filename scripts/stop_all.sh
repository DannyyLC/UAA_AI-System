#!/bin/bash

# Script para detener todos los servicios del sistema RAG
# Uso: ./scripts/stop_all.sh

set -e

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
echo -e "${BLUE}   Sistema RAG - Detener Servicios     ${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Función para detener un servicio
stop_service() {
    local name=$1
    local pid_file="$PIDS_DIR/$name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}Deteniendo $name (PID: $pid)...${NC}"
            kill $pid 2>/dev/null || true
            
            # Esperar a que el proceso termine
            for i in {1..10}; do
                if ! ps -p $pid > /dev/null 2>&1; then
                    echo -e "${GREEN}$name detenido${NC}"
                    rm "$pid_file"
                    return 0
                fi
                sleep 1
            done
            
            # Si no se detuvo, forzar
            echo -e "${RED}Forzando cierre de $name...${NC}"
            kill -9 $pid 2>/dev/null || true
            rm "$pid_file"
        else
            echo -e "${YELLOW}$name no está corriendo (PID obsoleto: $pid)${NC}"
            rm "$pid_file"
        fi
    else
        echo -e "${YELLOW}$name no tiene PID registrado${NC}"
    fi
}

# Detener servicios en orden inverso
echo -e "${BLUE}[1/4]${NC} Deteniendo Audit Consumer..."
stop_service "audit_consumer"

echo -e "\n${BLUE}[2/4]${NC} Deteniendo API Gateway..."
stop_service "gateway"

echo -e "\n${BLUE}[3/4]${NC} Deteniendo Chat Service..."
stop_service "chat_service"

echo -e "\n${BLUE}[4/4]${NC} Deteniendo Auth Service..."
stop_service "auth_service"

# Preguntar si se debe detener Docker Compose
echo -e "\n${YELLOW}¿Deseas detener también la infraestructura Docker? (postgres, kafka, qdrant)${NC}"
echo -e "${YELLOW}[y/N]:${NC} "
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo -e "\n${BLUE}Deteniendo Docker Compose...${NC}"
    cd "$PROJECT_ROOT"
    docker compose stop
    echo -e "${GREEN}Docker Compose detenido${NC}"
fi

# Limpiar directorio de PIDs si está vacío
if [ -d "$PIDS_DIR" ] && [ -z "$(ls -A $PIDS_DIR)" ]; then
    rmdir "$PIDS_DIR"
fi

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Servicios detenidos correctamente${NC}"
echo -e "${BLUE}========================================${NC}\n"
