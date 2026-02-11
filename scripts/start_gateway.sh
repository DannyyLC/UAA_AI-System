#!/bin/bash

# Script para iniciar el API Gateway
# Uso: ./scripts/start_gateway.sh

set -e

echo "Iniciando API Gateway..."

# Cargar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Iniciar Gateway
python -m src.gateway.main
