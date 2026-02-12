# Guía de Inicio del Sistema RAG

Esta guía detalla los pasos para levantar todos los componentes del sistema RAG distribuido.

## Pre-requisitos

- Python 3.11+
- Docker y Docker Compose
- Variables de entorno configuradas (ver sección Configuración)

## Configuración

### 1. Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con:

```bash
# PostgreSQL
DATABASE_URL=postgresql://rag_uaa:rag_uaa_secret@localhost:5432/rag_uaa

# JWT
JWT_SECRET=tu-secreto-super-seguro-cambiar-en-produccion
JWT_EXPIRATION_MINUTES=60

# OpenAI (requerido para LLM y embeddings)
OPENAI_API_KEY=sk-proj-...

# LLM
LLM_MODEL=gpt-4o-mini

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Puertos
AUTH_GRPC_PORT=50051
CHAT_GRPC_PORT=50052
GATEWAY_PORT=8000

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

### 2. Instalar Dependencias

```bash
# Activar entorno virtual
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Compilar Protobuf

```bash
bash scripts/compile_protos.sh
```

---

## Inicio del Sistema

### 🚀 Inicio Rápido (Recomendado)

**Levanta todo el sistema con un solo comando:**

```bash
# El script activa automáticamente el entorno virtual
./scripts/start_all.sh
```

> **Nota:** El script detecta y activa automáticamente el entorno virtual (`.venv` o `venv`) si existe.

Esto levanta automáticamente:
- ✅ Infraestructura Docker (PostgreSQL, Kafka, Qdrant)
- ✅ Auth Service (puerto 50051)
- ✅ Chat Service (puerto 50052)
- ✅ API Gateway (puerto 8000)
- ✅ Audit Consumer (opcional)

**Ver estado:**
```bash
./scripts/status_all.sh
```

**Detener todo:**
```bash
./scripts/stop_all.sh
```

**Ver logs:**
```bash
# Logs de servicios Python
tail -f logs/gateway.log
tail -f logs/auth_service.log
tail -f logs/chat_service.log
tail -f logs/audit_consumer.log

# Logs de Docker
docker compose logs -f postgres
docker compose logs -f kafka
docker compose logs -f qdrant
```

---

### 📋 Inicio Manual (Alternativa)

Si prefieres controlar cada servicio individualmente:

#### Paso 1: Levantar Infraestructura (Docker)

```bash
docker-compose up -d
```

Esto levanta:
- **PostgreSQL** (puerto 5432)
- **Kafka** (puerto 9092)
- **Qdrant** (puerto 6333)

Verificar que estén corriendo:
```bash
docker-compose ps
```

#### Paso 2: Levantar Microservicios

Abre **4 terminales** y ejecuta cada servicio en una terminal diferente:

#### Terminal 1 - Auth Service

```bash
# Activar entorno virtual
source .venv/bin/activate

# Levantar Auth Service (Puerto 50051)
python -m src.services.auth.server
```

**Salida esperada:**
```
2026-02-12 10:00:00 INFO PostgreSQL conectado y schema verificado
2026-02-12 10:00:00 INFO Kafka producer iniciado
2026-02-12 10:00:00 INFO Auth Service escuchando en [::]:50051
```

#### Terminal 2 - Chat Service

```bash
# Activar entorno virtual
source .venv/bin/activate

# Levantar Chat Service (Puerto 50052)
python -m src.services.chat.server
```

**Salida esperada:**
```
2026-02-12 10:00:01 INFO PostgreSQL conectado y schema verificado
2026-02-12 10:00:01 INFO Qdrant conectado
2026-02-12 10:00:01 INFO Chat Service escuchando en [::]:50052
```

#### Terminal 3 - API Gateway

```bash
# Activar entorno virtual
source .venv/bin/activate

# Levantar Gateway (Puerto 8000)
python -m src.gateway.main
```

**Salida esperada:**
```
2026-02-12 10:00:02 INFO Iniciando API Gateway...
2026-02-12 10:00:02 INFO Conectado a Auth Service
2026-02-12 10:00:02 INFO Conectado a Chat Service
2026-02-12 10:00:02 INFO API Gateway listo
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Terminal 4 - Audit Consumer (Opcional)

```bash
# Activar entorno virtual
source .venv/bin/activate

# Levantar Audit Consumer
python -m src.kafka.consumers.audit_consumer
```

**Salida esperada:**
```
2026-02-12 10:00:03 INFO Iniciando Audit Event Consumer...
2026-02-12 10:00:03 INFO Conexión a PostgreSQL establecida
2026-02-12 10:00:03 INFO Kafka Consumer iniciado - Group: audit-consumer-group
2026-02-12 10:00:03 INFO Audit Event Consumer iniciado correctamente
```

---

## Verificación del Sistema

### 1. Health Check

```bash
curl http://localhost:8000/api/health
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-12T10:00:00+00:00",
  "version": "1.0.0",
  "services": {
    "auth_service": "connected"
  }
}
```

### 2. Documentación API

Abre en tu navegador:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Flujo de Prueba Completo

### 1. Registrar Usuario

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "estudiante@uaa.mx",
    "password": "Password123",
    "full_name": "Juan Pérez"
  }'
```

### 2. Login (guarda la cookie)

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "estudiante@uaa.mx",
    "password": "Password123"
  }' \
  -c cookies.txt
```

### 3. Crear Conversación

```bash
curl -X POST http://localhost:8000/api/chat/conversations \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Ayuda con Matemáticas"
  }'
```

**Guarda el `id` de la conversación de la respuesta.**

### 4. Obtener Temas Disponibles

```bash
curl http://localhost:8000/api/chat/topics \
  -b cookies.txt
```

### 5. Enviar Mensaje (Streaming con SSE)

```bash
curl -N -X POST http://localhost:8000/api/chat/conversations/{CONVERSATION_ID}/messages \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{
    "content": "¿Qué es el cálculo diferencial?"
  }'
```

**Nota:** Reemplaza `{CONVERSATION_ID}` con el ID obtenido en el paso 3.

### 6. Listar Conversaciones

```bash
curl http://localhost:8000/api/chat/conversations \
  -b cookies.txt
```

### 7. Obtener Conversación con Mensajes

```bash
curl http://localhost:8000/api/chat/conversations/{CONVERSATION_ID} \
  -b cookies.txt
```

---

## Detener el Sistema

### Detener Servicios Python

En cada terminal, presiona `Ctrl+C` para detener cada servicio.

### Detener Infraestructura Docker

```bash
# Detener contenedores (mantiene datos)
docker-compose stop

# O detener y eliminar contenedores (mantiene volúmenes)
docker-compose down

# O eliminar todo incluyendo datos
docker-compose down -v
```

---

## Troubleshooting

### Error: "Conectando a Auth Service"

**Causa:** Auth Service no está corriendo.

**Solución:** Verifica que `python -m src.services.auth.server` esté ejecutándose sin errores.

### Error: "OpenAI API key not found"

**Causa:** Variable `OPENAI_API_KEY` no configurada.

**Solución:** Agrega tu API key en el archivo `.env`.

### Error: "Connection refused to Qdrant"

**Causa:** Qdrant no está corriendo.

**Solución:**
```bash
docker-compose ps qdrant
docker-compose up -d qdrant
```

### Error: "Kafka broker not available"

**Causa:** Kafka no está corriendo o aún no está listo.

**Solución:**
```bash
docker-compose restart kafka
# Espera 30 segundos para que Kafka inicie completamente
```

### Chat Service: "RAG no disponible"

**Causa:** No hay documentos indexados aún.

**Solución:** Esto es normal si es la primera vez. El sistema funcionará pero sin usar RAG hasta que se indexen documentos.

---

## Logs y Monitoreo

### Ver logs de servicios Docker

```bash
# Todos los servicios
docker-compose logs -f

# Servicio específico
docker-compose logs -f postgres
docker-compose logs -f kafka
docker-compose logs -f qdrant
```

### Inspeccionar Base de Datos

```bash
# Conectar a PostgreSQL
docker exec -it agenticsystem-postgres-1 psql -U rag_uaa -d rag_uaa

# Ver tablas
\dt

# Ver usuarios
SELECT * FROM users;

# Ver conversaciones
SELECT * FROM conversations;

# Ver mensajes
SELECT * FROM messages ORDER BY created_at DESC LIMIT 10;

# Ver audit log
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10;

# Salir
\q
```

### Verificar Qdrant

Abre en tu navegador:
- **Qdrant Dashboard**: http://localhost:6333/dashboard

---

## Orden de Inicio Recomendado

1. ✅ Docker Compose (infraestructura)
2. ✅ Auth Service
3. ✅ Chat Service
4. ✅ API Gateway
5. ✅ Audit Consumer (opcional)

**Importante:** Espera que cada servicio inicie completamente antes de pasar al siguiente.

---

## Puertos Utilizados

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| PostgreSQL | 5432 | Base de datos |
| Kafka | 9092 | Message broker |
| Qdrant | 6333 | Vector database (REST) |
| Qdrant | 6334 | Vector database (gRPC) |
| Auth Service | 50051 | Autenticación (gRPC) |
| Chat Service | 50052 | Chat y RAG (gRPC) |
| API Gateway | 8000 | REST API |

---

## Próximos Pasos

Una vez que el sistema esté funcionando:

1. **Indexar documentos** - Implementar el Indexing Service para subir PDFs
2. **Probar RAG** - Subir documentos y hacer preguntas sobre ellos
3. **Frontend** - Conectar una interfaz web al API Gateway
4. **Producción** - Configurar variables de entorno para producción

---

## Comandos Rápidos

```bash
# Setup inicial (solo primera vez)
docker-compose up -d
source .venv/bin/activate
bash scripts/compile_protos.sh

# === FORMA RÁPIDA (Recomendado) ===
./scripts/start_all.sh                  # Inicia todo
./scripts/status_all.sh                 # Ver estado
./scripts/stop_all.sh                   # Detener todo

# === FORMA MANUAL (Alternativa) ===
# En terminales separadas
python -m src.services.auth.server      # Terminal 1
python -m src.services.chat.server      # Terminal 2
python -m src.gateway.main              # Terminal 3
python -m src.kafka.consumers.audit_consumer  # Terminal 4 (opcional)

# Verificar
curl http://localhost:8000/api/health
```
