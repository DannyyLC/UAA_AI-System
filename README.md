# Sistema RAG Distribuido - UAA

Sistema de pregunta-respuesta académico basado en Retrieval-Augmented Generation (RAG) con arquitectura de microservicios.

## Arquitectura del Sistema

### Descripción General

El sistema implementa una arquitectura distribuida basada en microservicios que se comunican mediante gRPC para operaciones síncronas y Kafka para procesamiento asíncrono. El flujo principal permite a un modelo de lenguaje (LLM) decidir autónomamente cuándo necesita buscar información en la base de conocimiento mediante function calling nativo.

Toda la infraestructura se orquesta mediante **Docker Compose** (sin Dockerfiles individuales). Los servicios Python corren directamente desde el código fuente montado como volumen, facilitando el desarrollo local.

### Componentes Principales

#### 1. API Gateway (FastAPI)
- **Puerto**: 8000
- **Responsabilidades**:
  - Exponer API REST al frontend
  - Validación de requests
  - Orquestación de llamadas gRPC a microservicios
  - Gestión de CORS y rate limiting
  - SSE (Server-Sent Events) para streaming de respuestas del LLM

#### 2. Auth Service (gRPC)
- **Puerto**: 50051
- **Responsabilidades**:
  - Registro y autenticación de usuarios
  - Gestión de tokens JWT
  - Validación de sesiones
  - Acceso a PostgreSQL (tablas: users, sessions)
  - Publicación de eventos de autenticación en Kafka

#### 3. Chat Service (gRPC)
- **Puerto**: 50052
- **Responsabilidades**:
  - Gestión de conversaciones y mensajes
  - Integración con LiteLLM (múltiples proveedores de LLM)
  - Decisión automática de uso de RAG tool mediante function calling
  - Almacenamiento de mensajes en PostgreSQL
  - Publicación de eventos de chat en Kafka

#### 4. RAG Service (gRPC)
- **Puerto**: 50054
- **Responsabilidades**:
  - Clasificación de categorías de consultas
  - Búsqueda semántica en Qdrant
  - Ranking y extracción de contexto relevante
  - Llamado exclusivamente por Chat Service cuando el LLM decide usar la tool

#### 5. Indexing Workers
- **Responsabilidades**:
  - Consumo de trabajos desde Kafka
  - Procesamiento de documentos (chunking, embeddings)
  - Almacenamiento de vectores en Qdrant
  - Actualización de estado de trabajos en PostgreSQL
  - Procesamiento paralelo mediante múltiples workers

#### 6. Audit Consumer
- **Responsabilidades**:
  - Consumo de eventos de auditoría desde Kafka
  - Almacenamiento permanente en PostgreSQL (tabla: audit_log)
  - Registro de todas las operaciones del sistema

### Bases de Datos y Almacenamiento

#### PostgreSQL
- **Puerto**: 5432
- **Base de datos**: `rag_uaa`
- **Tablas**:
  - `users`: Información de usuarios
  - `sessions`: Tokens y sesiones activas
  - `conversations`: Conversaciones de usuarios
  - `messages`: Mensajes de cada conversación
  - `indexing_jobs`: Estado de trabajos de indexación
  - `audit_log`: Registro de eventos del sistema
- **Ventajas sobre SQLite**:
  - Soporte de escritura concurrente (múltiples servicios escribiendo simultáneamente)
  - Conexiones vía red (cada microservicio se conecta de forma independiente)
  - Transacciones ACID completas con aislamiento real

#### Qdrant (Vector Database)
- **Puerto REST**: 6333
- **Puerto gRPC**: 6334
- **Responsabilidades**:
  - Almacenamiento de embeddings de documentos
  - Búsqueda semántica mediante vectores
  - Gestión de colecciones por categoría académica

#### Kafka
- **Puerto**: 9092
- **Responsabilidades**:
  - Cola de trabajos de indexación (asíncrona)
  - Event bus para auditoría (fire and forget)
  - Topics:
    - `indexing.queue`: Trabajos de procesamiento de documentos
    - `indexing.dlq`: Dead letter queue para fallos
    - `audit.events`: Eventos de auditoría del sistema

## Estructura de Directorios

```
AgenticSystem/
├── docker-compose.yml          # Orquestación de todos los servicios
├── requirements.txt            # Dependencias Python
├── environment.yml             # Ambiente Conda (desarrollo local)
├── README.md                   # Documentación
│
├── proto/                      # Protocol Buffers definitions
│   ├── common.proto           # Tipos compartidos (User, Token, Error)
│   ├── auth.proto             # Definiciones Auth Service
│   ├── chat.proto             # Definiciones Chat Service
│   ├── rag.proto              # Definiciones RAG Service
│   └── indexing.proto         # Definiciones Indexing Service
│
├── src/
│   ├── gateway/               # API Gateway (FastAPI)
│   │   ├── main.py           # Aplicación principal
│   │   ├── routes/           # Endpoints REST
│   │   │   ├── auth.py
│   │   │   ├── chat.py       # Incluye endpoint SSE para streaming
│   │   │   ├── documents.py
│   │   │   └── health.py
│   │   ├── grpc_clients/     # Clientes gRPC
│   │   │   ├── auth_client.py
│   │   │   ├── chat_client.py
│   │   │   └── rag_client.py
│   │   ├── sse.py            # Handler SSE (Server-Sent Events)
│   │   └── middleware/       # Middlewares (CORS, auth, etc)
│   │
│   ├── services/
│   │   ├── auth/             # Auth Service (gRPC Server)
│   │   │   ├── server.py     # Servidor gRPC
│   │   │   ├── handlers.py   # Lógica de autenticación
│   │   │   ├── database.py   # Acceso a PostgreSQL
│   │   │   ├── jwt_manager.py
│   │   │   └── kafka_producer.py
│   │   │
│   │   ├── chat/             # Chat Service (gRPC Server)
│   │   │   ├── server.py
│   │   │   ├── handlers.py
│   │   │   ├── litellm_client.py  # Cliente LiteLLM
│   │   │   ├── tools.py      # Definición RAG tool
│   │   │   ├── database.py   # Acceso a PostgreSQL
│   │   │   └── kafka_producer.py
│   │   │
│   │   ├── rag/              # RAG Service (gRPC Server)
│   │   │   ├── server.py
│   │   │   ├── handlers.py
│   │   │   ├── retrieval.py  # Búsqueda en Qdrant
│   │   │   ├── router.py     # Clasificación de categorías
│   │   │   ├── qdrant_client.py
│   │   │   └── kafka_producer.py
│   │   │
│   │   └── indexing/         # Indexing Workers
│   │       ├── worker.py     # Worker principal
│   │       ├── document_processor.py
│   │       ├── embeddings.py
│   │       └── qdrant_client.py
│   │
│   ├── kafka/
│   │   ├── config.py         # Configuración de Kafka
│   │   ├── producer.py       # Producer base
│   │   ├── consumer.py       # Consumer base
│   │   └── consumers/
│   │       └── audit_consumer.py  # Consumer de auditoría
│   │
│   └── shared/               # Código compartido
│       ├── configuration.py  # Configuración global
│       ├── database.py       # Cliente PostgreSQL (asyncpg / psycopg)
│       ├── logging_utils.py  # Utilidades de logging
│       ├── models.py         # Modelos Pydantic
│       └── utils.py          # Utilidades generales
│
├── data/                     # Datos persistentes (gitignored)
│   ├── postgres/             # Datos de PostgreSQL
│   ├── qdrant/              # Datos de Qdrant
│   └── kafka/               # Logs de Kafka
│
└── tests/                   # Tests
    ├── unit/
    ├── integration/
    └── conftest.py
```
