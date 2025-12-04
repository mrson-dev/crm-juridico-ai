-- ============================================
-- Script de Inicialização do PostgreSQL
-- ============================================
-- Executado automaticamente na criação do container

-- Habilitar extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Habilitar extensão UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Habilitar extensão para busca textual
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Log de inicialização
DO $$
BEGIN
    RAISE NOTICE 'Database initialized with extensions: vector, uuid-ossp, pg_trgm';
END
$$;
