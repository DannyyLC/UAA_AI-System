#!/bin/bash

# Script para iniciar el Audit Consumer
# Uso: ./scripts/start_audit_consumer.sh

set -e

echo "🚀 Iniciando Audit Consumer..."

# Cargar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Iniciar Audit Consumer
python -m src.kafka.consumers.audit_consumer
