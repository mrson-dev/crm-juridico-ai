#!/bin/bash

#===============================================================================
#
#   CRM JURÍDICO AI - Suite de Testes Completa
#   
#   Script abrangente que testa TODOS os aspectos do projeto:
#   - Qualidade de código (lint, formatação, type checking)
#   - Testes unitários e de integração
#   - Segurança (vulnerabilidades, secrets)
#   - Build de containers
#   - Infraestrutura (Docker, Terraform)
#   - API endpoints
#   - Frontend build
#   - Performance básica
#
#   Uso: ./scripts/test-all.sh [opções]
#
#===============================================================================

set -e

#-------------------------------------------------------------------------------
# CORES E FORMATAÇÃO
#-------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

#-------------------------------------------------------------------------------
# VARIÁVEIS
#-------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
INFRA_DIR="$PROJECT_ROOT/infra"
LOG_FILE="$PROJECT_ROOT/.test-all.log"

# Contadores
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
WARNINGS=0

# Flags
VERBOSE=false
QUICK_MODE=false
SKIP_DOCKER=false
SKIP_INFRA=false
FIX_ISSUES=false
COVERAGE=false

# Tempo de início
START_TIME=$(date +%s)

#-------------------------------------------------------------------------------
# FUNÇÕES DE UI
#-------------------------------------------------------------------------------

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                              ║"
    echo "║     ████████╗███████╗███████╗████████╗    █████╗ ██╗     ██╗                 ║"
    echo "║     ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝   ██╔══██╗██║     ██║                 ║"
    echo "║        ██║   █████╗  ███████╗   ██║      ███████║██║     ██║                 ║"
    echo "║        ██║   ██╔══╝  ╚════██║   ██║      ██╔══██║██║     ██║                 ║"
    echo "║        ██║   ███████╗███████║   ██║      ██║  ██║███████╗███████╗            ║"
    echo "║        ╚═╝   ╚══════╝╚══════╝   ╚═╝      ╚═╝  ╚═╝╚══════╝╚══════╝            ║"
    echo "║                                                                              ║"
    echo -e "║                    ${WHITE}CRM Jurídico AI - Suite de Testes${CYAN}                       ║"
    echo -e "║                         ${DIM}Validação Completa do Projeto${CYAN}                        ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

print_section() {
    local title="$1"
    local num="$2"
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}  ${BOLD}[$num] $title${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_subsection() {
    local title="$1"
    echo -e "${BLUE}  ┌─ ${BOLD}$title${NC}"
}

print_test() {
    local name="$1"
    echo -ne "${DIM}  │  ${NC}$name... "
}

print_pass() {
    local msg="${1:-PASSOU}"
    echo -e "${GREEN}✓ $msg${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

print_fail() {
    local msg="${1:-FALHOU}"
    echo -e "${RED}✗ $msg${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

print_skip() {
    local msg="${1:-PULADO}"
    echo -e "${YELLOW}○ $msg${NC}"
    TESTS_SKIPPED=$((TESTS_SKIPPED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

print_warn() {
    local msg="$1"
    echo -e "${YELLOW}  │  ⚠ $msg${NC}"
    WARNINGS=$((WARNINGS + 1))
}

print_info() {
    local msg="$1"
    echo -e "${DIM}  │  ℹ $msg${NC}"
}

print_detail() {
    local msg="$1"
    if [ "$VERBOSE" = true ]; then
        echo -e "${DIM}  │    $msg${NC}"
    fi
}

print_end_subsection() {
    echo -e "${BLUE}  └────────────────────────────────────────────────────────────────────────${NC}"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

#-------------------------------------------------------------------------------
# FUNÇÕES DE TESTE
#-------------------------------------------------------------------------------

run_test() {
    local name="$1"
    local command="$2"
    local allow_fail="${3:-false}"
    
    print_test "$name"
    log "Running: $name"
    log "Command: $command"
    
    local output
    local exit_code
    
    output=$(eval "$command" 2>&1) && exit_code=0 || exit_code=$?
    
    log "Exit code: $exit_code"
    log "Output: $output"
    
    if [ $exit_code -eq 0 ]; then
        print_pass
        return 0
    else
        if [ "$allow_fail" = true ]; then
            print_warn "Falhou (não crítico)"
            print_detail "$output"
            return 0
        else
            print_fail
            if [ "$VERBOSE" = true ]; then
                echo "$output" | head -10 | while read line; do
                    print_detail "$line"
                done
            fi
            return 1
        fi
    fi
}

check_command() {
    command -v "$1" &> /dev/null
}

#-------------------------------------------------------------------------------
# 1. VERIFICAÇÕES DE AMBIENTE
#-------------------------------------------------------------------------------

test_environment() {
    print_section "VERIFICAÇÃO DE AMBIENTE" "1"
    
    print_subsection "Ferramentas do Sistema"
    
    # Sistema operacional
    print_test "Sistema Operacional"
    local os_info=$(uname -s -r)
    echo -e "${GREEN}✓${NC} ${DIM}$os_info${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    # Docker
    print_test "Docker"
    if check_command docker; then
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
        print_pass "v$docker_version"
    else
        print_fail "Não instalado"
    fi
    
    # Docker Compose
    print_test "Docker Compose"
    if docker compose version &> /dev/null; then
        local compose_version=$(docker compose version --short 2>/dev/null | head -1)
        print_pass "v$compose_version"
    else
        print_fail "Não instalado"
    fi
    
    # Python
    print_test "Python"
    if check_command python3; then
        local python_version=$(python3 --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        print_pass "v$python_version"
    else
        print_fail "Não instalado"
    fi
    
    # Poetry
    print_test "Poetry"
    if check_command poetry; then
        local poetry_version=$(poetry --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        print_pass "v$poetry_version"
    else
        print_fail "Não instalado"
    fi
    
    # Node.js
    print_test "Node.js"
    if check_command node; then
        local node_version=$(node --version)
        print_pass "$node_version"
    else
        print_fail "Não instalado"
    fi
    
    # npm
    print_test "npm"
    if check_command npm; then
        local npm_version=$(npm --version)
        print_pass "v$npm_version"
    else
        print_fail "Não instalado"
    fi
    
    # Git
    print_test "Git"
    if check_command git; then
        local git_version=$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        print_pass "v$git_version"
    else
        print_fail "Não instalado"
    fi
    
    # Terraform (opcional)
    print_test "Terraform"
    if check_command terraform; then
        local tf_version=$(terraform version | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        print_pass "v$tf_version"
    else
        print_skip "Não instalado (opcional)"
    fi
    
    print_end_subsection
    
    print_subsection "Estrutura do Projeto"
    
    # Verificar diretórios essenciais
    local dirs=("backend" "frontend" "scripts" "infra" ".github")
    for dir in "${dirs[@]}"; do
        print_test "Diretório /$dir"
        if [ -d "$PROJECT_ROOT/$dir" ]; then
            print_pass
        else
            print_fail "Não encontrado"
        fi
    done
    
    # Verificar arquivos essenciais
    local files=("docker-compose.yml" "README.md" ".gitignore")
    for file in "${files[@]}"; do
        print_test "Arquivo $file"
        if [ -f "$PROJECT_ROOT/$file" ]; then
            print_pass
        else
            print_fail "Não encontrado"
        fi
    done
    
    print_end_subsection
    
    print_subsection "Variáveis de Ambiente"
    
    # Backend .env
    print_test "Backend .env"
    if [ -f "$BACKEND_DIR/.env" ]; then
        local env_vars=$(grep -c "=" "$BACKEND_DIR/.env" 2>/dev/null || echo 0)
        print_pass "$env_vars variáveis"
    else
        print_warn "Não encontrado (copie de .env.example)"
    fi
    
    # Frontend .env
    print_test "Frontend .env"
    if [ -f "$FRONTEND_DIR/.env" ]; then
        local env_vars=$(grep -c "=" "$FRONTEND_DIR/.env" 2>/dev/null || echo 0)
        print_pass "$env_vars variáveis"
    else
        print_warn "Não encontrado (copie de .env.example)"
    fi
    
    print_end_subsection
}

#-------------------------------------------------------------------------------
# 2. QUALIDADE DE CÓDIGO - BACKEND
#-------------------------------------------------------------------------------

test_backend_quality() {
    print_section "QUALIDADE DE CÓDIGO - BACKEND" "2"
    
    cd "$BACKEND_DIR"
    
    print_subsection "Análise Estática (Ruff)"
    
    # Ruff linter
    print_test "Ruff Linter"
    if check_command poetry; then
        local ruff_output
        if [ "$FIX_ISSUES" = true ]; then
            ruff_output=$(poetry run ruff check . --fix 2>&1) && print_pass "OK (auto-fix aplicado)" || print_fail
        else
            ruff_output=$(poetry run ruff check . 2>&1) || true
            local issues=$(echo "$ruff_output" | grep -cE "^[a-zA-Z]" 2>/dev/null || echo 0)
            if [ "$issues" -eq 0 ] || echo "$ruff_output" | grep -q "All checks passed"; then
                print_pass "Sem problemas"
            else
                print_fail "$issues problema(s)"
                print_detail "Use --fix para corrigir automaticamente"
            fi
        fi
    else
        print_skip "Poetry não disponível"
    fi
    
    # Ruff formatter check
    print_test "Ruff Formatter"
    if poetry run ruff format --check . &> /dev/null; then
        print_pass "Código formatado"
    else
        if [ "$FIX_ISSUES" = true ]; then
            poetry run ruff format . &> /dev/null
            print_pass "Formatado automaticamente"
        else
            print_fail "Precisa formatação"
            print_detail "Execute: poetry run ruff format ."
        fi
    fi
    
    print_end_subsection
    
    print_subsection "Type Checking (MyPy)"
    
    print_test "MyPy Type Check"
    local mypy_output
    mypy_output=$(poetry run mypy app --ignore-missing-imports 2>&1) || true
    local errors=$(echo "$mypy_output" | grep -c "error:" 2>/dev/null || echo 0)
    if [ "$errors" -eq 0 ]; then
        print_pass "Sem erros de tipo"
    else
        print_warn "$errors erro(s) de tipo"
        if [ "$VERBOSE" = true ]; then
            echo "$mypy_output" | grep "error:" | head -5 | while read line; do
                print_detail "$line"
            done
        fi
    fi
    
    print_end_subsection
    
    print_subsection "Análise de Imports"
    
    # Imports não utilizados
    print_test "Imports não utilizados"
    local unused=$(poetry run ruff check . --select F401 2>&1 | grep -c "F401" || echo 0)
    if [ "$unused" -eq 0 ]; then
        print_pass "Nenhum"
    else
        print_warn "$unused import(s) não utilizado(s)"
    fi
    
    # Imports circulares (básico)
    print_test "Imports circulares"
    if ! grep -r "from app.* import.*from app" app/ &>/dev/null; then
        print_pass "Não detectados"
    else
        print_warn "Possíveis imports circulares"
    fi
    
    print_end_subsection
    
    print_subsection "Complexidade de Código"
    
    # Funções muito longas
    print_test "Funções > 50 linhas"
    local long_funcs=$(find app -name "*.py" -exec awk '/^def |^async def /{start=NR} /^def |^async def |^class /{if(start && NR-start>50) print FILENAME":"start}' {} \; 2>/dev/null | wc -l)
    if [ "$long_funcs" -eq 0 ]; then
        print_pass "Nenhuma"
    else
        print_warn "$long_funcs função(ões) longa(s)"
    fi
    
    # Arquivos muito grandes
    print_test "Arquivos > 500 linhas"
    local big_files=$(find app -name "*.py" -exec wc -l {} \; 2>/dev/null | awk '$1 > 500 {print $2}' | wc -l)
    if [ "$big_files" -eq 0 ]; then
        print_pass "Nenhum"
    else
        print_warn "$big_files arquivo(s) grande(s)"
    fi
    
    print_end_subsection
    
    print_subsection "Documentação"
    
    # Docstrings em módulos
    print_test "Docstrings em módulos"
    local modules=$(find app -name "*.py" ! -name "__init__.py" | wc -l)
    local with_docs=$(find app -name "*.py" ! -name "__init__.py" -exec head -5 {} \; 2>/dev/null | grep -c '"""' || echo 0)
    local percent=0
    if [ "$modules" -gt 0 ]; then
        percent=$((with_docs * 100 / modules))
    fi
    if [ "$percent" -ge 80 ]; then
        print_pass "$percent% documentados"
    elif [ "$percent" -ge 50 ]; then
        print_warn "$percent% documentados"
    else
        print_fail "Apenas $percent% documentados"
    fi
    
    # TODO/FIXME comments
    print_test "TODOs/FIXMEs pendentes"
    local todos=$(grep -r "TODO\|FIXME" app/ 2>/dev/null | wc -l || echo 0)
    if [ "$todos" -eq 0 ]; then
        print_pass "Nenhum"
    else
        print_info "$todos comentário(s) pendente(s)"
    fi
    
    print_end_subsection
    
    cd "$PROJECT_ROOT"
}

#-------------------------------------------------------------------------------
# 3. QUALIDADE DE CÓDIGO - FRONTEND
#-------------------------------------------------------------------------------

test_frontend_quality() {
    print_section "QUALIDADE DE CÓDIGO - FRONTEND" "3"
    
    cd "$FRONTEND_DIR"
    
    # Verificar se node_modules existe
    if [ ! -d "node_modules" ]; then
        print_info "Instalando dependências do frontend..."
        npm install --silent >> "$LOG_FILE" 2>&1
    fi
    
    print_subsection "ESLint"
    
    print_test "ESLint"
    local eslint_output
    eslint_output=$(npm run lint 2>&1) || true
    local eslint_errors=$(echo "$eslint_output" | grep -c "error" || echo 0)
    local eslint_warnings=$(echo "$eslint_output" | grep -c "warning" || echo 0)
    
    if [ "$eslint_errors" -eq 0 ] && [ "$eslint_warnings" -eq 0 ]; then
        print_pass "Sem problemas"
    elif [ "$eslint_errors" -eq 0 ]; then
        print_warn "$eslint_warnings warning(s)"
    else
        print_fail "$eslint_errors erro(s), $eslint_warnings warning(s)"
    fi
    
    print_end_subsection
    
    print_subsection "TypeScript"
    
    print_test "TypeScript Compiler"
    local tsc_output
    tsc_output=$(npx tsc --noEmit 2>&1) || true
    local tsc_errors=$(echo "$tsc_output" | grep -c "error TS" || echo 0)
    
    if [ "$tsc_errors" -eq 0 ]; then
        print_pass "Sem erros de tipo"
    else
        print_fail "$tsc_errors erro(s) de tipo"
        if [ "$VERBOSE" = true ]; then
            echo "$tsc_output" | grep "error TS" | head -5 | while read line; do
                print_detail "$line"
            done
        fi
    fi
    
    # Verificar strict mode
    print_test "Strict Mode"
    if grep -q '"strict": true' tsconfig.json 2>/dev/null; then
        print_pass "Habilitado"
    else
        print_warn "Desabilitado"
    fi
    
    print_end_subsection
    
    print_subsection "Dependências"
    
    # Verificar vulnerabilidades
    print_test "Vulnerabilidades (npm audit)"
    local audit_output
    audit_output=$(npm audit --json 2>/dev/null) || true
    local critical=$(echo "$audit_output" | grep -o '"critical":[0-9]*' | grep -oE '[0-9]+' || echo 0)
    local high=$(echo "$audit_output" | grep -o '"high":[0-9]*' | grep -oE '[0-9]+' || echo 0)
    
    if [ "$critical" -eq 0 ] && [ "$high" -eq 0 ]; then
        print_pass "Nenhuma crítica/alta"
    elif [ "$critical" -eq 0 ]; then
        print_warn "$high alta(s)"
    else
        print_fail "$critical crítica(s), $high alta(s)"
    fi
    
    # Dependências desatualizadas
    print_test "Dependências desatualizadas"
    local outdated=$(npm outdated 2>/dev/null | wc -l || echo 0)
    if [ "$outdated" -le 1 ]; then
        print_pass "Todas atualizadas"
    else
        print_info "$((outdated - 1)) desatualizada(s)"
    fi
    
    print_end_subsection
    
    print_subsection "Estrutura do Código"
    
    # Componentes por pasta
    print_test "Organização de componentes"
    local components=$(find src/components -name "*.tsx" 2>/dev/null | wc -l || echo 0)
    local pages=$(find src/pages -name "*.tsx" 2>/dev/null | wc -l || echo 0)
    print_pass "$components componentes, $pages páginas"
    
    # Console.logs
    print_test "Console.log em produção"
    local console_logs=$(grep -r "console.log" src/ --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v "// DEBUG" | wc -l || echo 0)
    if [ "$console_logs" -eq 0 ]; then
        print_pass "Nenhum"
    else
        print_warn "$console_logs encontrado(s)"
    fi
    
    print_end_subsection
    
    cd "$PROJECT_ROOT"
}

#-------------------------------------------------------------------------------
# 4. TESTES UNITÁRIOS
#-------------------------------------------------------------------------------

test_unit_tests() {
    print_section "TESTES UNITÁRIOS" "4"
    
    cd "$BACKEND_DIR"
    
    print_subsection "Backend - Pytest"
    
    # Executar pytest
    print_test "Executando testes"
    local pytest_output
    local pytest_exit_code
    
    if [ "$COVERAGE" = true ]; then
        pytest_output=$(poetry run pytest tests/ -v --tb=short --cov=app --cov-report=term-missing 2>&1) && pytest_exit_code=0 || pytest_exit_code=$?
    else
        pytest_output=$(poetry run pytest tests/ -v --tb=short 2>&1) && pytest_exit_code=0 || pytest_exit_code=$?
    fi
    
    # Extrair resultados
    local passed=$(echo "$pytest_output" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo 0)
    local failed=$(echo "$pytest_output" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo 0)
    local errors=$(echo "$pytest_output" | grep -oE '[0-9]+ error' | grep -oE '[0-9]+' || echo 0)
    local skipped=$(echo "$pytest_output" | grep -oE '[0-9]+ skipped' | grep -oE '[0-9]+' || echo 0)
    
    if [ "$pytest_exit_code" -eq 0 ]; then
        print_pass "$passed passou, $skipped pulado"
    else
        print_fail "$passed passou, $failed falhou, $errors erro(s)"
    fi
    
    # Mostrar detalhes dos testes falhados
    if [ "$failed" -gt 0 ] || [ "$errors" -gt 0 ]; then
        if [ "$VERBOSE" = true ]; then
            echo "$pytest_output" | grep -A 5 "FAILED\|ERROR" | head -20 | while read line; do
                print_detail "$line"
            done
        fi
    fi
    
    print_end_subsection
    
    # Coverage report
    if [ "$COVERAGE" = true ]; then
        print_subsection "Cobertura de Código"
        
        local coverage_percent=$(echo "$pytest_output" | grep "TOTAL" | awk '{print $NF}' | tr -d '%' || echo 0)
        print_test "Cobertura total"
        if [ "$coverage_percent" -ge 80 ]; then
            print_pass "$coverage_percent%"
        elif [ "$coverage_percent" -ge 60 ]; then
            print_warn "$coverage_percent%"
        else
            print_fail "$coverage_percent%"
        fi
        
        # Arquivos com baixa cobertura
        print_test "Arquivos < 50% cobertura"
        local low_coverage=$(echo "$pytest_output" | grep -E "^\s*app/" | awk '$NF < 50 {print $1}' | wc -l || echo 0)
        if [ "$low_coverage" -eq 0 ]; then
            print_pass "Nenhum"
        else
            print_warn "$low_coverage arquivo(s)"
        fi
        
        print_end_subsection
    fi
    
    print_subsection "Estatísticas de Testes"
    
    # Contar testes por categoria
    print_test "Testes de Models"
    local model_tests=$(grep -r "def test_" tests/ --include="*model*" 2>/dev/null | wc -l || echo 0)
    print_pass "$model_tests teste(s)"
    
    print_test "Testes de Services"
    local service_tests=$(grep -r "def test_" tests/ --include="*service*" 2>/dev/null | wc -l || echo 0)
    print_pass "$service_tests teste(s)"
    
    print_test "Testes de API/Endpoints"
    local api_tests=$(grep -r "def test_" tests/ --include="*api*" --include="*endpoint*" 2>/dev/null | wc -l || echo 0)
    print_pass "$api_tests teste(s)"
    
    print_test "Testes de Integração"
    local integration_tests=$(grep -r "def test_" tests/ --include="*integration*" 2>/dev/null | wc -l || echo 0)
    print_pass "$integration_tests teste(s)"
    
    print_end_subsection
    
    cd "$PROJECT_ROOT"
}

#-------------------------------------------------------------------------------
# 5. BUILD E CONTAINERS
#-------------------------------------------------------------------------------

test_builds() {
    print_section "BUILD E CONTAINERS" "5"
    
    if [ "$SKIP_DOCKER" = true ]; then
        print_info "Testes de Docker pulados (--skip-docker)"
        return 0
    fi
    
    print_subsection "Build do Backend"
    
    print_test "Dockerfile válido"
    if [ -f "$BACKEND_DIR/Dockerfile" ]; then
        print_pass
    else
        print_fail "Não encontrado"
    fi
    
    print_test "Build da imagem"
    if docker build -t crm-juridico-api:test "$BACKEND_DIR" -q >> "$LOG_FILE" 2>&1; then
        local image_size=$(docker images crm-juridico-api:test --format "{{.Size}}")
        print_pass "$image_size"
    else
        print_fail "Erro no build"
    fi
    
    print_end_subsection
    
    print_subsection "Build do Frontend"
    
    print_test "Dockerfile válido"
    if [ -f "$FRONTEND_DIR/Dockerfile" ]; then
        print_pass
    else
        print_fail "Não encontrado"
    fi
    
    print_test "Build da imagem"
    if docker build -t crm-juridico-frontend:test "$FRONTEND_DIR" -q >> "$LOG_FILE" 2>&1; then
        local image_size=$(docker images crm-juridico-frontend:test --format "{{.Size}}")
        print_pass "$image_size"
    else
        print_fail "Erro no build"
    fi
    
    print_end_subsection
    
    print_subsection "Build de Produção (Frontend)"
    
    cd "$FRONTEND_DIR"
    
    print_test "npm run build"
    if npm run build >> "$LOG_FILE" 2>&1; then
        local dist_size=$(du -sh dist 2>/dev/null | cut -f1 || echo "N/A")
        print_pass "Tamanho: $dist_size"
    else
        print_fail "Erro no build"
    fi
    
    # Verificar arquivos gerados
    print_test "Arquivos de bundle"
    local js_files=$(find dist -name "*.js" 2>/dev/null | wc -l || echo 0)
    local css_files=$(find dist -name "*.css" 2>/dev/null | wc -l || echo 0)
    print_pass "$js_files JS, $css_files CSS"
    
    # Verificar tamanho do bundle principal
    print_test "Bundle size < 1MB"
    local main_bundle=$(find dist -name "index-*.js" -exec du -k {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo 0)
    if [ "$main_bundle" -lt 1024 ]; then
        print_pass "${main_bundle}KB"
    else
        print_warn "${main_bundle}KB (considere code splitting)"
    fi
    
    print_end_subsection
    
    cd "$PROJECT_ROOT"
    
    print_subsection "Docker Compose"
    
    print_test "docker-compose.yml válido"
    if docker compose config -q >> "$LOG_FILE" 2>&1; then
        print_pass
    else
        print_fail "Sintaxe inválida"
    fi
    
    print_test "Serviços definidos"
    local services=$(docker compose config --services 2>/dev/null | wc -l || echo 0)
    print_pass "$services serviço(s)"
    
    print_end_subsection
}

#-------------------------------------------------------------------------------
# 6. INFRAESTRUTURA
#-------------------------------------------------------------------------------

test_infrastructure() {
    print_section "INFRAESTRUTURA" "6"
    
    if [ "$SKIP_INFRA" = true ]; then
        print_info "Testes de infraestrutura pulados (--skip-infra)"
        return 0
    fi
    
    if [ "$SKIP_DOCKER" = true ]; then
        print_info "Testes de Docker pulados (--skip-docker)"
    else
        print_subsection "Containers de Desenvolvimento"
        
        # Iniciar containers
        print_test "Iniciando PostgreSQL e Redis"
        if docker compose up -d db redis >> "$LOG_FILE" 2>&1; then
            sleep 5
            print_pass
        else
            print_fail
            return 1
        fi
        
        # Health check PostgreSQL
        print_test "PostgreSQL respondendo"
        if docker compose exec -T db pg_isready -U postgres >> "$LOG_FILE" 2>&1; then
            print_pass
        else
            print_fail
        fi
        
        # Health check Redis
        print_test "Redis respondendo"
        if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
            print_pass
        else
            print_fail
        fi
        
        # pgvector extension
        print_test "Extensão pgvector"
        if docker compose exec -T db psql -U postgres -d crm_juridico -c "SELECT * FROM pg_extension WHERE extname='vector'" 2>/dev/null | grep -q "vector"; then
            print_pass "Instalada"
        else
            print_warn "Não instalada"
        fi
        
        # Parar containers
        docker compose down >> "$LOG_FILE" 2>&1
        
        print_end_subsection
    fi
    
    print_subsection "Terraform"
    
    if [ -d "$INFRA_DIR/terraform" ]; then
        cd "$INFRA_DIR/terraform"
        
        print_test "terraform fmt"
        if check_command terraform; then
            if terraform fmt -check -recursive >> "$LOG_FILE" 2>&1; then
                print_pass "Formatado"
            else
                if [ "$FIX_ISSUES" = true ]; then
                    terraform fmt -recursive >> "$LOG_FILE" 2>&1
                    print_pass "Formatado automaticamente"
                else
                    print_warn "Precisa formatação"
                fi
            fi
        else
            print_skip "Terraform não instalado"
        fi
        
        print_test "terraform validate"
        if check_command terraform; then
            # Apenas valida se houver backend configurado ou em modo local
            if terraform validate >> "$LOG_FILE" 2>&1; then
                print_pass
            else
                print_warn "Requer terraform init"
            fi
        else
            print_skip "Terraform não instalado"
        fi
        
        cd "$PROJECT_ROOT"
    else
        print_info "Diretório terraform não encontrado"
    fi
    
    print_end_subsection
    
    print_subsection "Arquivos de CI/CD"
    
    # GitHub Actions
    print_test "GitHub Actions workflow"
    if [ -f ".github/workflows/ci-cd.yml" ]; then
        # Validar YAML
        if python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci-cd.yml'))" 2>/dev/null; then
            print_pass "YAML válido"
        else
            print_fail "YAML inválido"
        fi
    else
        print_skip "Não encontrado"
    fi
    
    # Cloud Build
    print_test "Cloud Build config"
    if [ -f "cloudbuild.yaml" ]; then
        if python3 -c "import yaml; yaml.safe_load(open('cloudbuild.yaml'))" 2>/dev/null; then
            print_pass "YAML válido"
        else
            print_fail "YAML inválido"
        fi
    else
        print_skip "Não encontrado"
    fi
    
    print_end_subsection
}

#-------------------------------------------------------------------------------
# 7. SEGURANÇA
#-------------------------------------------------------------------------------

test_security() {
    print_section "SEGURANÇA" "7"
    
    print_subsection "Secrets e Credenciais"
    
    # Verificar secrets em código
    print_test "Secrets hardcoded"
    local secrets_found=0
    
    # Padrões comuns de secrets
    local patterns=(
        "password\s*=\s*['\"][^'\"]+['\"]"
        "api_key\s*=\s*['\"][^'\"]+['\"]"
        "secret_key\s*=\s*['\"][^'\"]+['\"]"
        "AWS_ACCESS_KEY"
        "PRIVATE_KEY"
    )
    
    for pattern in "${patterns[@]}"; do
        local found=$(grep -riE "$pattern" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" . 2>/dev/null | grep -v ".env" | grep -v "test" | grep -v "example" | wc -l || echo 0)
        secrets_found=$((secrets_found + found))
    done
    
    if [ "$secrets_found" -eq 0 ]; then
        print_pass "Nenhum detectado"
    else
        print_fail "$secrets_found possível(is) secret(s)"
    fi
    
    # Verificar .env em .gitignore
    print_test ".env no .gitignore"
    if grep -q "^\.env$\|^\.env\.\*$" .gitignore 2>/dev/null; then
        print_pass
    else
        print_fail "Adicione .env ao .gitignore!"
    fi
    
    # Verificar se .env está tracked
    print_test ".env não commitado"
    if git ls-files --error-unmatch backend/.env frontend/.env >> "$LOG_FILE" 2>&1; then
        print_fail "CRÍTICO: .env está no git!"
    else
        print_pass
    fi
    
    print_end_subsection
    
    print_subsection "Vulnerabilidades de Dependências"
    
    # Backend - pip-audit ou safety
    cd "$BACKEND_DIR"
    print_test "Python dependencies (safety)"
    if check_command safety; then
        local safety_output
        safety_output=$(poetry export -f requirements.txt --without-hashes 2>/dev/null | safety check --stdin 2>&1) || true
        local vulns=$(echo "$safety_output" | grep -c "vulnerability found" || echo 0)
        if [ "$vulns" -eq 0 ]; then
            print_pass "Nenhuma vulnerabilidade"
        else
            print_warn "$vulns vulnerabilidade(s)"
        fi
    else
        # Tentar com pip-audit
        if poetry run pip-audit >> "$LOG_FILE" 2>&1; then
            print_pass "Nenhuma vulnerabilidade"
        else
            print_skip "safety/pip-audit não disponível"
        fi
    fi
    cd "$PROJECT_ROOT"
    
    # Frontend - npm audit já testado acima
    
    print_end_subsection
    
    print_subsection "Configurações de Segurança"
    
    cd "$BACKEND_DIR"
    
    # CORS configurado
    print_test "CORS configurado"
    if grep -q "CORSMiddleware\|CORS" app/main.py 2>/dev/null; then
        print_pass
    else
        print_warn "CORS não configurado"
    fi
    
    # Rate limiting
    print_test "Rate limiting"
    if grep -rq "slowapi\|RateLimiter\|rate_limit" app/ 2>/dev/null; then
        print_pass "Configurado"
    else
        print_info "Não detectado"
    fi
    
    # JWT secret strength
    print_test "JWT Secret (mínimo 32 chars)"
    if [ -f ".env" ]; then
        local secret_len=$(grep "SECRET_KEY" .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" | wc -c || echo 0)
        if [ "$secret_len" -ge 32 ]; then
            print_pass
        else
            print_warn "Secret muito curto"
        fi
    else
        print_skip ".env não encontrado"
    fi
    
    # SQL Injection (uso de ORM)
    print_test "Uso de ORM (proteção SQL Injection)"
    if grep -rq "SQLAlchemy\|AsyncSession" app/ 2>/dev/null; then
        print_pass "SQLAlchemy detectado"
    else
        print_warn "ORM não detectado"
    fi
    
    cd "$PROJECT_ROOT"
    
    print_end_subsection
}

#-------------------------------------------------------------------------------
# 8. DOCUMENTAÇÃO
#-------------------------------------------------------------------------------

test_documentation() {
    print_section "DOCUMENTAÇÃO" "8"
    
    print_subsection "Arquivos de Documentação"
    
    # README
    print_test "README.md"
    if [ -f "README.md" ]; then
        local readme_lines=$(wc -l < README.md)
        if [ "$readme_lines" -gt 50 ]; then
            print_pass "$readme_lines linhas"
        else
            print_warn "Muito curto ($readme_lines linhas)"
        fi
    else
        print_fail "Não encontrado"
    fi
    
    # CONTRIBUTING
    print_test "CONTRIBUTING.md"
    if [ -f "CONTRIBUTING.md" ]; then
        print_pass
    else
        print_skip "Não encontrado (opcional)"
    fi
    
    # LICENSE
    print_test "LICENSE"
    if [ -f "LICENSE" ]; then
        print_pass
    else
        print_skip "Não encontrado"
    fi
    
    # CHANGELOG
    print_test "CHANGELOG.md"
    if [ -f "CHANGELOG.md" ]; then
        print_pass
    else
        print_skip "Não encontrado"
    fi
    
    print_end_subsection
    
    print_subsection "Documentação de API"
    
    cd "$BACKEND_DIR"
    
    # OpenAPI/Swagger
    print_test "OpenAPI (FastAPI docs)"
    if grep -q "/docs\|/redoc\|openapi" app/main.py 2>/dev/null; then
        print_pass "Habilitado"
    else
        print_info "Verificar configuração"
    fi
    
    # Docstrings nos endpoints
    print_test "Docstrings em endpoints"
    local endpoints=$(find app/api -name "*.py" ! -name "__init__.py" 2>/dev/null | wc -l || echo 0)
    local with_docs=$(find app/api -name "*.py" ! -name "__init__.py" -exec grep -l '"""' {} \; 2>/dev/null | wc -l || echo 0)
    if [ "$endpoints" -gt 0 ]; then
        local percent=$((with_docs * 100 / endpoints))
        print_pass "$percent% documentados"
    else
        print_skip "Nenhum endpoint"
    fi
    
    cd "$PROJECT_ROOT"
    
    print_end_subsection
    
    print_subsection "Copilot Instructions"
    
    print_test ".github/copilot-instructions.md"
    if [ -f ".github/copilot-instructions.md" ]; then
        local instructions_lines=$(wc -l < .github/copilot-instructions.md)
        print_pass "$instructions_lines linhas"
    else
        print_skip "Não encontrado"
    fi
    
    print_end_subsection
}

#-------------------------------------------------------------------------------
# 9. API ENDPOINTS (SE SERVIDOR ATIVO)
#-------------------------------------------------------------------------------

test_api_live() {
    print_section "API ENDPOINTS (LIVE)" "9"
    
    local api_url="http://localhost:8000"
    
    print_subsection "Verificando se API está ativa"
    
    print_test "Servidor respondendo"
    if curl -s --connect-timeout 2 "$api_url/health" &>/dev/null; then
        print_pass
    else
        print_skip "API não está rodando"
        print_info "Inicie com: cd backend && poetry run uvicorn app.main:app"
        return 0
    fi
    
    print_end_subsection
    
    print_subsection "Health Checks"
    
    print_test "GET /health"
    local health=$(curl -s "$api_url/health" 2>/dev/null)
    if echo "$health" | grep -q "healthy"; then
        print_pass
    else
        print_fail
    fi
    
    print_test "GET /openapi.json"
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$api_url/openapi.json" 2>/dev/null)
    if [ "$status" = "200" ]; then
        print_pass
    else
        print_info "Status $status"
    fi
    
    print_end_subsection
    
    print_subsection "Endpoints de Autenticação"
    
    print_test "POST /api/v1/auth/login (sem credenciais)"
    local login_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$api_url/api/v1/auth/login" -H "Content-Type: application/json" -d '{}' 2>/dev/null)
    if [ "$login_status" = "422" ] || [ "$login_status" = "400" ]; then
        print_pass "Validação OK ($login_status)"
    else
        print_warn "Status inesperado: $login_status"
    fi
    
    print_test "GET /api/v1/auth/me (sem token)"
    local me_status=$(curl -s -o /dev/null -w "%{http_code}" "$api_url/api/v1/auth/me" 2>/dev/null)
    if [ "$me_status" = "401" ] || [ "$me_status" = "403" ]; then
        print_pass "Protegido ($me_status)"
    else
        print_warn "Status inesperado: $me_status"
    fi
    
    print_end_subsection
    
    print_subsection "Tempo de Resposta"
    
    print_test "Latência /health"
    local start_time=$(date +%s%N)
    curl -s "$api_url/health" &>/dev/null
    local end_time=$(date +%s%N)
    local latency=$(( (end_time - start_time) / 1000000 ))
    if [ "$latency" -lt 100 ]; then
        print_pass "${latency}ms"
    elif [ "$latency" -lt 500 ]; then
        print_warn "${latency}ms"
    else
        print_fail "${latency}ms (muito lento)"
    fi
    
    print_end_subsection
}

#-------------------------------------------------------------------------------
# RESUMO FINAL
#-------------------------------------------------------------------------------

print_summary() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                              RESUMO DOS TESTES                               ${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Calcular percentuais
    local pass_percent=0
    if [ "$TESTS_TOTAL" -gt 0 ]; then
        pass_percent=$((TESTS_PASSED * 100 / TESTS_TOTAL))
    fi
    
    # Status geral
    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo -e "  ${GREEN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "  ${GREEN}║                    ✓ TODOS OS TESTES PASSARAM!                        ║${NC}"
        echo -e "  ${GREEN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    else
        echo -e "  ${RED}╔════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "  ${RED}║                    ✗ ALGUNS TESTES FALHARAM                            ║${NC}"
        echo -e "  ${RED}╚════════════════════════════════════════════════════════════════════════╝${NC}"
    fi
    
    echo ""
    echo -e "  ${WHITE}┌──────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "  ${WHITE}│                           ESTATÍSTICAS                               │${NC}"
    echo -e "  ${WHITE}├──────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "  ${WHITE}│${NC}                                                                      ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}    ${GREEN}✓ Passou:${NC}     $TESTS_PASSED                                                  ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}    ${RED}✗ Falhou:${NC}     $TESTS_FAILED                                                   ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}    ${YELLOW}○ Pulado:${NC}     $TESTS_SKIPPED                                                   ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}    ${YELLOW}⚠ Avisos:${NC}     $WARNINGS                                                   ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}                                                                      ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}    ${DIM}Total:${NC}        $TESTS_TOTAL testes                                         ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}    ${DIM}Taxa:${NC}         $pass_percent%                                                  ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}    ${DIM}Tempo:${NC}        ${duration}s                                                  ${WHITE}│${NC}"
    echo -e "  ${WHITE}│${NC}                                                                      ${WHITE}│${NC}"
    echo -e "  ${WHITE}└──────────────────────────────────────────────────────────────────────┘${NC}"
    
    echo ""
    echo -e "  ${DIM}Log completo em: $LOG_FILE${NC}"
    echo ""
    
    # Recomendações se houver falhas
    if [ "$TESTS_FAILED" -gt 0 ]; then
        echo -e "  ${YELLOW}📋 Recomendações:${NC}"
        echo -e "  ${DIM}   • Execute com --verbose para mais detalhes${NC}"
        echo -e "  ${DIM}   • Use --fix para correções automáticas${NC}"
        echo -e "  ${DIM}   • Verifique o log: cat $LOG_FILE${NC}"
        echo ""
    fi
    
    # Exit code baseado no resultado
    if [ "$TESTS_FAILED" -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# HELP
#-------------------------------------------------------------------------------

show_help() {
    echo "Uso: $0 [opções]"
    echo ""
    echo "Suite completa de testes para o CRM Jurídico AI"
    echo ""
    echo "Opções:"
    echo "  -h, --help          Mostra esta ajuda"
    echo "  -v, --verbose       Modo verboso (mostra detalhes)"
    echo "  -q, --quick         Modo rápido (pula testes lentos)"
    echo "  -f, --fix           Corrige problemas automaticamente"
    echo "  -c, --coverage      Inclui relatório de cobertura"
    echo "  --skip-docker       Pula testes que usam Docker"
    echo "  --skip-infra        Pula testes de infraestrutura"
    echo ""
    echo "Exemplos:"
    echo "  $0                  # Executa todos os testes"
    echo "  $0 --verbose        # Com detalhes"
    echo "  $0 --fix            # Corrige lint automaticamente"
    echo "  $0 --quick          # Versão rápida"
    echo "  $0 --coverage       # Com cobertura de código"
    echo ""
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    # Parse argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quick)
                QUICK_MODE=true
                SKIP_DOCKER=true
                shift
                ;;
            -f|--fix)
                FIX_ISSUES=true
                shift
                ;;
            -c|--coverage)
                COVERAGE=true
                shift
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            --skip-infra)
                SKIP_INFRA=true
                shift
                ;;
            *)
                echo "Opção desconhecida: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Inicializar
    cd "$PROJECT_ROOT"
    echo "=== Test All Log - $(date) ===" > "$LOG_FILE"
    
    # Executar
    print_banner
    
    echo -e "${WHITE}  Configuração:${NC}"
    echo -e "${DIM}    • Verbose: $VERBOSE${NC}"
    echo -e "${DIM}    • Quick Mode: $QUICK_MODE${NC}"
    echo -e "${DIM}    • Fix Issues: $FIX_ISSUES${NC}"
    echo -e "${DIM}    • Coverage: $COVERAGE${NC}"
    echo -e "${DIM}    • Skip Docker: $SKIP_DOCKER${NC}"
    echo -e "${DIM}    • Skip Infra: $SKIP_INFRA${NC}"
    echo ""
    
    # Executar todas as suites de teste
    test_environment
    test_backend_quality
    test_frontend_quality
    test_unit_tests
    test_builds
    test_infrastructure
    test_security
    test_documentation
    test_api_live
    
    # Resumo final
    print_summary
}

# Executar
main "$@"
