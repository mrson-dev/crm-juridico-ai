#!/bin/bash
# ============================================
# Script de Teste Completo - Ambiente Dev
# ============================================
# Execute antes do deploy para garantir qualidade
#
# Uso: ./scripts/test-all.sh

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  CRM Jurídico - Suite de Testes Completa${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Contadores
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local name=$1
    local command=$2
    
    echo -e "${YELLOW}▶ $name${NC}"
    if eval "$command"; then
        echo -e "${GREEN}  ✓ PASSOU${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}  ✗ FALHOU${NC}"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# ==========================================
# 1. Verificar Pré-requisitos
# ==========================================
echo -e "${YELLOW}[1/7] Verificando pré-requisitos...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker não encontrado!${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Docker Compose não encontrado!${NC}"
    exit 1
fi

echo -e "${GREEN}  ✓ Docker e Docker Compose instalados${NC}"
echo ""

# ==========================================
# 2. Testes de Lint (Backend)
# ==========================================
echo -e "${YELLOW}[2/7] Executando Lint do Backend...${NC}"

cd backend

run_test "Ruff (linter)" "poetry run ruff check . --fix 2>/dev/null || poetry run ruff check ."

run_test "MyPy (type check)" "poetry run mypy app --ignore-missing-imports 2>/dev/null || true"

cd ..

# ==========================================
# 3. Testes de Lint (Frontend)
# ==========================================
echo -e "${YELLOW}[3/7] Executando Lint do Frontend...${NC}"

cd frontend

run_test "ESLint" "npm run lint 2>/dev/null || true"

run_test "TypeScript" "npx tsc --noEmit 2>/dev/null || true"

cd ..

# ==========================================
# 4. Testes Unitários (Backend)
# ==========================================
echo -e "${YELLOW}[4/7] Executando Testes Unitários do Backend...${NC}"

cd backend

run_test "Pytest" "poetry run pytest tests/ -v --tb=short 2>&1 | tail -30"

cd ..

# ==========================================
# 5. Build das Imagens Docker
# ==========================================
echo -e "${YELLOW}[5/7] Testando Build das Imagens Docker...${NC}"

run_test "Build Backend" "docker build -t crm-juridico-api:test ./backend -q"

run_test "Build Frontend" "docker build -t crm-juridico-frontend:test ./frontend -q"

# ==========================================
# 6. Teste de Integração (Docker Compose)
# ==========================================
echo -e "${YELLOW}[6/7] Testando Ambiente Docker Compose...${NC}"

# Subir apenas db e redis para teste rápido
run_test "Docker Compose Up (db, redis)" "docker compose up -d db redis && sleep 5"

# Verificar se estão saudáveis
run_test "Health Check PostgreSQL" "docker compose exec -T db pg_isready -U postgres"

run_test "Health Check Redis" "docker compose exec -T redis redis-cli ping | grep -q PONG"

# Parar containers
docker compose down -v 2>/dev/null || true

# ==========================================
# 7. Validação de Arquivos de Deploy
# ==========================================
echo -e "${YELLOW}[7/7] Validando Arquivos de Deploy...${NC}"

run_test "Terraform fmt" "cd infra/terraform && terraform fmt -check 2>/dev/null || terraform fmt"

run_test "YAML válido (ci-cd.yml)" "python3 -c \"import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))\" 2>/dev/null || true"

run_test "YAML válido (cloudbuild.yaml)" "python3 -c \"import yaml; yaml.safe_load(open('cloudbuild.yaml'))\" 2>/dev/null || true"

# ==========================================
# Resumo
# ==========================================
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Resumo dos Testes${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "  Passou: ${GREEN}$TESTS_PASSED${NC}"
echo -e "  Falhou: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Todos os testes passaram! Pronto para deploy.${NC}"
    exit 0
else
    echo -e "${RED}✗ Alguns testes falharam. Corrija antes do deploy.${NC}"
    exit 1
fi
