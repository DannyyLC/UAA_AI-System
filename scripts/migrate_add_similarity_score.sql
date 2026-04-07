-- ============================================================
-- Migración: agregar similarity_score a model_performance_logs
-- Ejecutar en bases de datos existentes (idempotente con IF NOT EXISTS)
-- ============================================================

ALTER TABLE model_performance_logs
    ADD COLUMN IF NOT EXISTS similarity_score DOUBLE PRECISION;

-- Actualizar comentario en expected_answer (cosmético)
COMMENT ON COLUMN model_performance_logs.expected_answer IS
    'Respuesta esperada para evaluación de similitud de investigación';

COMMENT ON COLUMN model_performance_logs.similarity_score IS
    'Similitud de coseno entre answer y expected_answer (0.0–1.0). NULL si no se proveyó expected_answer';
