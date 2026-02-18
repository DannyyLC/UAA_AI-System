#!/usr/bin/env bash
# ============================================================
# Compila todos los archivos .proto a stubs Python + gRPC
# Output: src/generated/
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PROTO_DIR="$PROJECT_ROOT/proto"
OUT_DIR="$PROJECT_ROOT/src/generated"

echo "=== Compilando protobuf ==="
echo "Proto dir : $PROTO_DIR"
echo "Output dir: $OUT_DIR"

# Limpiar y recrear directorio de salida
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# Compilar solo los .proto activos (excluir archived/)
# Servicios implementados: auth.proto, chat.proto, common.proto
echo "Compilando: common.proto, auth.proto, chat.proto"
python -m grpc_tools.protoc \
  --proto_path="$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --pyi_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR"/common.proto \
  "$PROTO_DIR"/auth.proto \
  "$PROTO_DIR"/chat.proto

# Corregir imports para que sean relativos dentro del paquete
# (grpcio-tools genera "import common_pb2" en vez de "from . import common_pb2")
echo "=== Corrigiendo imports a relativos ==="
cd "$OUT_DIR"
for f in *.py; do
  # Solo corregir imports de nuestros propios módulos (no google.protobuf, etc.)
  sed -i 's/^import common_pb2/from . import common_pb2/' "$f"
  sed -i 's/^import auth_pb2/from . import auth_pb2/' "$f"
  sed -i 's/^import chat_pb2/from . import chat_pb2/' "$f"
done

# Crear __init__.py con exports
cat > "$OUT_DIR/__init__.py" << 'EOF'
"""
Stubs generados automáticamente desde archivos .proto.

NO EDITAR MANUALMENTE — regenerar con: bash scripts/compile_protos.sh
"""
EOF

echo "=== Compilación completa ==="
echo "Archivos generados:"
ls -la "$OUT_DIR"
