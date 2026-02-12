# Scripts de Gestión del Sistema

Esta carpeta contiene scripts para gestionar el sistema RAG completo.

## Scripts de Inicio y Control

### `start_all.sh` 🚀
Inicia todos los servicios del sistema con un solo comando.

**Uso:**
```bash
./scripts/start_all.sh
```

**Qué hace:**
1. Verifica y levanta infraestructura Docker (PostgreSQL, Kafka, Qdrant)
2. Inicia Auth Service en background
3. Inicia Chat Service en background
4. Inicia API Gateway en background
5. Inicia Audit Consumer en background (opcional)
6. Guarda PIDs en `.pids/`
7. Redirige logs a `logs/`

**Logs generados:**
- `logs/auth_service.log`
- `logs/chat_service.log`
- `logs/gateway.log`
- `logs/audit_consumer.log`

### `stop_all.sh` 🛑
Detiene todos los servicios de forma ordenada.

**Uso:**
```bash
./scripts/stop_all.sh
```

**Qué hace:**
1. Detiene Audit Consumer
2. Detiene API Gateway
3. Detiene Chat Service
4. Detiene Auth Service
5. Opcionalmente detiene Docker Compose
6. Limpia archivos PID

### `status_all.sh` 📊
Muestra el estado de todos los servicios.

**Uso:**
```bash
./scripts/status_all.sh
```

**Qué muestra:**
- Estado de servicios Docker (PostgreSQL, Kafka, Qdrant)
- Estado de servicios Python (Auth, Chat, Gateway, Audit Consumer)
- Health check del API Gateway
- URLs de acceso

## Scripts Individuales (Existentes)

### `start_gateway.sh`
Inicia solo el API Gateway.

### `start_audit_consumer.sh`
Inicia solo el Audit Consumer.

### `compile_protos.sh`
Compila archivos Protocol Buffer.

### `init_db.py`
Inicializa la base de datos con el schema.

## Ejemplos de Uso

### Inicio Rápido Completo
```bash
# Primera vez
source .venv/bin/activate
bash scripts/compile_protos.sh

# Iniciar sistema
./scripts/start_all.sh

# Verificar estado
./scripts/status_all.sh

# Ver logs en tiempo real
tail -f logs/gateway.log
```

### Ver logs de todos los servicios
```bash
# Servicios Python
tail -f logs/*.log

# Servicios Docker
docker compose logs -f
```

### Detener y reiniciar
```bash
# Detener todo
./scripts/stop_all.sh

# Reiniciar un servicio específico
# (El script detectará que los demás ya están corriendo)
./scripts/start_all.sh
```

## Estructura de Archivos Generados

```
AgenticSystem/
├── logs/                      # Logs de servicios Python
│   ├── auth_service.log
│   ├── chat_service.log
│   ├── gateway.log
│   └── audit_consumer.log
├── .pids/                     # PIDs de procesos
│   ├── auth_service.pid
│   ├── chat_service.pid
│   ├── gateway.pid
│   └── audit_consumer.pid
└── scripts/
    ├── start_all.sh          # ⭐ Iniciar todo
    ├── stop_all.sh           # ⭐ Detener todo
    └── status_all.sh         # ⭐ Ver estado
```

## Troubleshooting

### "Python no encontrado"
```bash
# Activar entorno virtual primero
source .venv/bin/activate
```

### "Archivo .env no encontrado"
```bash
# Crear archivo .env según docs/startup-guide.md
cp .env.example .env
# Editar con tus credenciales
```

### Servicio no inicia
```bash
# Ver logs para diagnóstico
tail -f logs/<servicio>.log

# O verificar manualmente
python -m src.services.auth.server
```

### Puerto ya en uso
```bash
# Ver qué proceso usa el puerto
lsof -i :8000

# Detener proceso anterior
./scripts/stop_all.sh
```

### Limpiar todo y empezar de cero
```bash
# Detener servicios
./scripts/stop_all.sh

# Limpiar Docker
docker compose down -v

# Limpiar logs y PIDs
rm -rf logs/* .pids/*

# Reiniciar
docker compose up -d
./scripts/start_all.sh
```

## Notas

- Los scripts usan colores para mejor visualización
- Los PIDs se guardan automáticamente
- Los logs se rotan manualmente (no automático)
- Los servicios se inician en orden de dependencias
- Se incluyen timeouts y reintentos automáticos
