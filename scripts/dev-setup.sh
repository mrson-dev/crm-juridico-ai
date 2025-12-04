#!/bin/bash

#===============================================================================
#
#   CRM JURÍDICO AI - Script de Configuração do Ambiente de Desenvolvimento
#   
#   Este script configura e testa todo o ambiente de desenvolvimento local
#   para o CRM Jurídico especializado em Direito Previdenciário.
#
#   Autor: CRM Jurídico AI Team
#   Versão: 1.0.0
#   Data: 2025-12-04
#
#===============================================================================

set -e  # Parar em caso de erro

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
NC='\033[0m' # No Color
BOLD='\033[1m'
DIM='\033[2m'

#-------------------------------------------------------------------------------
# VARIÁVEIS GLOBAIS
#-------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG_FILE="$PROJECT_ROOT/.dev-setup.log"

# Versões mínimas requeridas
PYTHON_MIN_VERSION="3.11"
NODE_MIN_VERSION="18"
DOCKER_MIN_VERSION="20"

# Contadores
STEPS_TOTAL=0
STEPS_PASSED=0
STEPS_FAILED=0
WARNINGS=0

#-------------------------------------------------------------------------------
# FUNÇÕES DE UI
#-------------------------------------------------------------------------------

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                              ║"
    echo "║     ██████╗██████╗ ███╗   ███╗         ██╗██╗   ██╗██████╗ ██╗██████╗       ║"
    echo "║    ██╔════╝██╔══██╗████╗ ████║         ██║██║   ██║██╔══██╗██║██╔══██╗      ║"
    echo "║    ██║     ██████╔╝██╔████╔██║         ██║██║   ██║██████╔╝██║██║  ██║      ║"
    echo "║    ██║     ██╔══██╗██║╚██╔╝██║    ██   ██║██║   ██║██╔══██╗██║██║  ██║      ║"
    echo "║    ╚██████╗██║  ██║██║ ╚═╝ ██║    ╚█████╔╝╚██████╔╝██║  ██║██║██████╔╝      ║"
    echo "║     ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝     ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝       ║"
    echo "║                                                                              ║"
    echo -e "║                    ${WHITE}Configuração do Ambiente de Desenvolvimento${CYAN}              ║"
    echo -e "║                         ${DIM}Direito Previdenciário + IA${CYAN}                          ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

print_section() {
    local title="$1"
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}  ${BOLD}$title${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_step() {
    local step_num="$1"
    local description="$2"
    echo -e "${BLUE}  [${step_num}]${NC} $description"
}

print_substep() {
    local description="$1"
    echo -e "${DIM}      ├─${NC} $description"
}

print_success() {
    local message="$1"
    echo -e "${GREEN}  ✓${NC} $message"
    STEPS_PASSED=$((STEPS_PASSED + 1))
}

print_error() {
    local message="$1"
    echo -e "${RED}  ✗${NC} $message"
    STEPS_FAILED=$((STEPS_FAILED + 1))
}

print_warning() {
    local message="$1"
    echo -e "${YELLOW}  ⚠${NC} $message"
    WARNINGS=$((WARNINGS + 1))
}

print_info() {
    local message="$1"
    echo -e "${CYAN}  ℹ${NC} $message"
}

print_waiting() {
    local message="$1"
    echo -ne "${YELLOW}  ⏳${NC} $message"
}

print_done() {
    echo -e " ${GREEN}Done!${NC}"
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "      \b\b\b\b\b\b"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

#-------------------------------------------------------------------------------
# FUNÇÕES DE VERIFICAÇÃO
#-------------------------------------------------------------------------------

check_command() {
    local cmd="$1"
    if command -v "$cmd" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

version_compare() {
    # Returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

check_prerequisites() {
    print_section "1. VERIFICANDO PRÉ-REQUISITOS"
    
    local all_ok=true
    
    # Docker
    print_step "1.1" "Verificando Docker..."
    if check_command docker; then
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        if version_compare "$docker_version" "$DOCKER_MIN_VERSION"; then
            print_success "Docker $docker_version instalado"
        else
            print_warning "Docker $docker_version (recomendado: $DOCKER_MIN_VERSION+)"
        fi
    else
        print_error "Docker não encontrado. Instale: https://docs.docker.com/get-docker/"
        all_ok=false
    fi
    
    # Docker Compose
    print_step "1.2" "Verificando Docker Compose..."
    if docker compose version &> /dev/null; then
        local compose_version=$(docker compose version --short 2>/dev/null || echo "v2+")
        print_success "Docker Compose $compose_version instalado"
    elif check_command docker-compose; then
        print_success "Docker Compose (legacy) instalado"
    else
        print_error "Docker Compose não encontrado"
        all_ok=false
    fi
    
    # Python
    print_step "1.3" "Verificando Python..."
    if check_command python3; then
        local python_version=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
        if version_compare "$python_version" "$PYTHON_MIN_VERSION"; then
            print_success "Python $python_version instalado"
        else
            print_error "Python $python_version (requerido: $PYTHON_MIN_VERSION+)"
            all_ok=false
        fi
    else
        print_error "Python não encontrado"
        all_ok=false
    fi
    
    # Poetry
    print_step "1.4" "Verificando Poetry..."
    if check_command poetry; then
        local poetry_version=$(poetry --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        print_success "Poetry $poetry_version instalado"
    else
        print_warning "Poetry não encontrado. Instalando..."
        curl -sSL https://install.python-poetry.org | python3 - >> "$LOG_FILE" 2>&1
        export PATH="$HOME/.local/bin:$PATH"
        if check_command poetry; then
            print_success "Poetry instalado com sucesso"
        else
            print_error "Falha ao instalar Poetry"
            all_ok=false
        fi
    fi
    
    # Node.js
    print_step "1.5" "Verificando Node.js..."
    if check_command node; then
        local node_version=$(node --version | grep -oE '[0-9]+' | head -1)
        if version_compare "$node_version" "$NODE_MIN_VERSION"; then
            print_success "Node.js v$node_version instalado"
        else
            print_warning "Node.js v$node_version (recomendado: v$NODE_MIN_VERSION+)"
        fi
    else
        print_error "Node.js não encontrado. Instale: https://nodejs.org/"
        all_ok=false
    fi
    
    # npm
    print_step "1.6" "Verificando npm..."
    if check_command npm; then
        local npm_version=$(npm --version)
        print_success "npm $npm_version instalado"
    else
        print_error "npm não encontrado"
        all_ok=false
    fi
    
    # Git
    print_step "1.7" "Verificando Git..."
    if check_command git; then
        local git_version=$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        print_success "Git $git_version instalado"
    else
        print_error "Git não encontrado"
        all_ok=false
    fi
    
    # curl
    print_step "1.8" "Verificando curl..."
    if check_command curl; then
        print_success "curl instalado"
    else
        print_error "curl não encontrado"
        all_ok=false
    fi
    
    # jq (opcional mas útil)
    print_step "1.9" "Verificando jq..."
    if check_command jq; then
        print_success "jq instalado"
    else
        print_warning "jq não encontrado (opcional, usado para formatar JSON)"
    fi
    
    echo ""
    if [ "$all_ok" = false ]; then
        print_error "Alguns pré-requisitos não foram atendidos. Corrija os erros acima."
        exit 1
    fi
    
    print_success "Todos os pré-requisitos verificados!"
}

#-------------------------------------------------------------------------------
# FUNÇÕES DE SETUP
#-------------------------------------------------------------------------------

setup_environment_files() {
    print_section "2. CONFIGURANDO ARQUIVOS DE AMBIENTE"
    
    # Backend .env
    print_step "2.1" "Configurando backend/.env..."
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        if [ -f "$BACKEND_DIR/.env.example" ]; then
            cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
            print_success "Arquivo .env criado a partir do .env.example"
        else
            cat > "$BACKEND_DIR/.env" << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/crm_juridico

# Security
SECRET_KEY=dev-secret-key-change-in-production-minimum-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Redis
REDIS_URL=redis://localhost:6379/0

# GCP (opcional para desenvolvimento)
GCP_PROJECT_ID=
GCS_BUCKET_DOCUMENTOS=
GOOGLE_APPLICATION_CREDENTIALS=

# Gemini AI (opcional)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-pro

# Firebase (opcional)
FIREBASE_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=
EOF
            print_success "Arquivo .env criado com configurações padrão"
        fi
    else
        print_info "Arquivo .env já existe"
    fi
    
    # Frontend .env
    print_step "2.2" "Configurando frontend/.env..."
    if [ ! -f "$FRONTEND_DIR/.env" ]; then
        if [ -f "$FRONTEND_DIR/.env.example" ]; then
            cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env"
            print_success "Arquivo .env criado a partir do .env.example"
        else
            cat > "$FRONTEND_DIR/.env" << 'EOF'
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_MESSAGING_SENDER_ID=
VITE_FIREBASE_APP_ID=
EOF
            print_success "Arquivo .env criado com configurações padrão"
        fi
    else
        print_info "Arquivo .env já existe"
    fi
}

start_infrastructure() {
    print_section "3. INICIANDO INFRAESTRUTURA (Docker)"
    
    cd "$PROJECT_ROOT"
    
    # Parar containers existentes
    print_step "3.1" "Parando containers existentes..."
    docker compose down --remove-orphans >> "$LOG_FILE" 2>&1 || true
    print_success "Containers parados"
    
    # Iniciar PostgreSQL e Redis
    print_step "3.2" "Iniciando PostgreSQL e Redis..."
    print_waiting "Aguardando containers subirem..."
    docker compose up -d db redis >> "$LOG_FILE" 2>&1
    print_done
    
    # Aguardar PostgreSQL estar pronto
    print_step "3.3" "Aguardando PostgreSQL estar pronto..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker compose exec -T db pg_isready -U postgres >> "$LOG_FILE" 2>&1; then
            print_success "PostgreSQL está pronto!"
            break
        fi
        ((attempt++))
        sleep 1
        echo -ne "${YELLOW}  ⏳${NC} Tentativa $attempt/$max_attempts...\r"
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL não iniciou a tempo"
        exit 1
    fi
    
    # Criar extensão pgvector
    print_step "3.4" "Configurando extensão pgvector..."
    docker compose exec -T db psql -U postgres -d crm_juridico -c "CREATE EXTENSION IF NOT EXISTS vector;" >> "$LOG_FILE" 2>&1 || true
    print_success "Extensão pgvector configurada"
    
    # Criar banco de testes
    print_step "3.5" "Criando banco de dados de testes..."
    docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS test_db;" >> "$LOG_FILE" 2>&1 || true
    docker compose exec -T db psql -U postgres -c "CREATE DATABASE test_db;" >> "$LOG_FILE" 2>&1
    docker compose exec -T db psql -U postgres -d test_db -c "CREATE EXTENSION IF NOT EXISTS vector;" >> "$LOG_FILE" 2>&1 || true
    print_success "Banco de testes criado"
    
    # Verificar Redis
    print_step "3.6" "Verificando Redis..."
    if docker compose exec -T redis redis-cli ping >> "$LOG_FILE" 2>&1; then
        print_success "Redis está pronto!"
    else
        print_error "Redis não respondeu"
        exit 1
    fi
}

setup_backend() {
    print_section "4. CONFIGURANDO BACKEND (Python/FastAPI)"
    
    cd "$BACKEND_DIR"
    
    # Instalar dependências
    print_step "4.1" "Instalando dependências Python..."
    print_waiting "Executando poetry install..."
    poetry install >> "$LOG_FILE" 2>&1
    print_done
    print_success "Dependências instaladas"
    
    # Rodar migrations
    print_step "4.2" "Aplicando migrations do banco de dados..."
    poetry run alembic upgrade head >> "$LOG_FILE" 2>&1
    print_success "Migrations aplicadas"
    
    # Rodar testes
    print_step "4.3" "Executando testes unitários..."
    echo ""
    if poetry run pytest -v --tb=short 2>&1 | tee -a "$LOG_FILE" | grep -E "^(tests/|PASSED|FAILED|ERROR|=====)"; then
        echo ""
        print_success "Testes executados"
    else
        echo ""
        print_warning "Alguns testes podem ter falhado. Verifique o log."
    fi
}

setup_frontend() {
    print_section "5. CONFIGURANDO FRONTEND (React/TypeScript)"
    
    cd "$FRONTEND_DIR"
    
    # Instalar dependências
    print_step "5.1" "Instalando dependências Node.js..."
    print_waiting "Executando npm install..."
    npm install >> "$LOG_FILE" 2>&1
    print_done
    print_success "Dependências instaladas"
    
    # Build para verificar erros de TypeScript
    print_step "5.2" "Verificando build de produção..."
    if npm run build >> "$LOG_FILE" 2>&1; then
        print_success "Build de produção OK"
    else
        print_warning "Build com warnings (verifique o log)"
    fi
}

start_services() {
    print_section "6. INICIANDO SERVIÇOS"
    
    # Matar processos anteriores
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 2
    
    # Iniciar Backend
    print_step "6.1" "Iniciando API Backend (porta 8000)..."
    cd "$BACKEND_DIR"
    nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload >> "$PROJECT_ROOT/.backend.log" 2>&1 &
    local backend_pid=$!
    sleep 3
    
    if kill -0 $backend_pid 2>/dev/null; then
        print_success "Backend iniciado (PID: $backend_pid)"
    else
        print_error "Falha ao iniciar backend. Verifique .backend.log"
    fi
    
    # Iniciar Frontend
    print_step "6.2" "Iniciando Frontend (porta 3000)..."
    cd "$FRONTEND_DIR"
    nohup npm run dev >> "$PROJECT_ROOT/.frontend.log" 2>&1 &
    local frontend_pid=$!
    sleep 3
    
    if kill -0 $frontend_pid 2>/dev/null; then
        print_success "Frontend iniciado (PID: $frontend_pid)"
    else
        print_error "Falha ao iniciar frontend. Verifique .frontend.log"
    fi
    
    # Aguardar serviços
    print_step "6.3" "Aguardando serviços estarem prontos..."
    sleep 5
}

test_api_endpoints() {
    print_section "7. TESTANDO ENDPOINTS DA API"
    
    local api_url="http://localhost:8000"
    
    # Health check
    print_step "7.1" "Testando Health Check..."
    local health_response=$(curl -s "$api_url/health" 2>/dev/null)
    if echo "$health_response" | grep -q "healthy"; then
        print_success "Health Check: OK"
        print_substep "Response: $health_response"
    else
        print_error "Health Check falhou"
        return 1
    fi
    
    # OpenAPI docs
    print_step "7.2" "Verificando documentação OpenAPI..."
    local docs_status=$(curl -s -o /dev/null -w "%{http_code}" "$api_url/openapi.json" 2>/dev/null)
    if [ "$docs_status" = "200" ]; then
        print_success "OpenAPI disponível"
    else
        print_info "OpenAPI desabilitado (modo produção)"
    fi
    
    # Testar onboarding
    print_step "7.3" "Testando endpoint de Onboarding..."
    local onboarding_response=$(curl -s -X POST "$api_url/api/v1/auth/onboarding" \
        -H "Content-Type: application/json" \
        -d '{
            "escritorio_nome": "Advocacia Teste Dev",
            "escritorio_cnpj": "11.222.333/0001-44",
            "escritorio_email": "teste@devtest.com",
            "usuario_nome": "Admin Dev",
            "usuario_email": "admin@devtest.com",
            "usuario_password": "DevTest@123"
        }' 2>/dev/null)
    
    if echo "$onboarding_response" | grep -q "success.*true"; then
        print_success "Onboarding: OK"
        
        # Extrair token
        local token=$(echo "$onboarding_response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$token" ]; then
            # Testar endpoint autenticado
            print_step "7.4" "Testando endpoint autenticado (/me)..."
            local me_response=$(curl -s "$api_url/api/v1/auth/me" \
                -H "Authorization: Bearer $token" 2>/dev/null)
            
            if echo "$me_response" | grep -q "admin@devtest.com"; then
                print_success "Autenticação: OK"
            else
                print_warning "Autenticação com problemas"
            fi
            
            # Testar criar cliente
            print_step "7.5" "Testando criar cliente..."
            local cliente_response=$(curl -s -X POST "$api_url/api/v1/clientes" \
                -H "Authorization: Bearer $token" \
                -H "Content-Type: application/json" \
                -d '{
                    "tipo_pessoa": "fisica",
                    "nome": "Cliente Teste Dev",
                    "cpf": "111.222.333-44",
                    "email": "cliente@teste.dev",
                    "telefone": "11999999999",
                    "consentimento_lgpd": true
                }' 2>/dev/null)
            
            if echo "$cliente_response" | grep -q "success.*true"; then
                print_success "Criar cliente: OK"
            else
                print_warning "Criar cliente com problemas"
            fi
        fi
    else
        print_info "Onboarding já executado anteriormente ou com erro"
    fi
}

print_summary() {
    print_section "8. RESUMO DA CONFIGURAÇÃO"
    
    echo -e "${WHITE}  ┌────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${WHITE}  │                         RESULTADO DA CONFIGURAÇÃO                      │${NC}"
    echo -e "${WHITE}  ├────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${WHITE}  │${NC}  ${GREEN}✓ Sucessos:${NC} $STEPS_PASSED                                                      ${WHITE}│${NC}"
    echo -e "${WHITE}  │${NC}  ${RED}✗ Falhas:${NC}   $STEPS_FAILED                                                        ${WHITE}│${NC}"
    echo -e "${WHITE}  │${NC}  ${YELLOW}⚠ Avisos:${NC}   $WARNINGS                                                         ${WHITE}│${NC}"
    echo -e "${WHITE}  └────────────────────────────────────────────────────────────────────────┘${NC}"
    
    echo ""
    echo -e "${CYAN}  ┌────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}  │                              SERVIÇOS ATIVOS                           │${NC}"
    echo -e "${CYAN}  ├────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}  │${NC}  🗄️  PostgreSQL:     ${GREEN}localhost:5432${NC}                                   ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  📦 Redis:          ${GREEN}localhost:6379${NC}                                   ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  🚀 API Backend:    ${GREEN}http://localhost:8000${NC}                            ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  🎨 Frontend:       ${GREEN}http://localhost:3000${NC}                            ${CYAN}│${NC}"
    echo -e "${CYAN}  └────────────────────────────────────────────────────────────────────────┘${NC}"
    
    echo ""
    echo -e "${PURPLE}  ┌────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${PURPLE}  │                           COMANDOS ÚTEIS                               │${NC}"
    echo -e "${PURPLE}  ├────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${PURPLE}  │${NC}  ${DIM}# Ver logs do backend${NC}                                                  ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}  tail -f .backend.log                                                   ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}                                                                         ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}  ${DIM}# Ver logs do frontend${NC}                                                 ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}  tail -f .frontend.log                                                  ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}                                                                         ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}  ${DIM}# Rodar testes do backend${NC}                                              ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}  cd backend && poetry run pytest -v                                     ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}                                                                         ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}  ${DIM}# Parar tudo${NC}                                                            ${PURPLE}│${NC}"
    echo -e "${PURPLE}  │${NC}  docker compose down && pkill -f uvicorn && pkill -f vite               ${PURPLE}│${NC}"
    echo -e "${PURPLE}  └────────────────────────────────────────────────────────────────────────┘${NC}"
    
    echo ""
    echo -e "${GREEN}  ════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}    ✅ Ambiente de desenvolvimento configurado com sucesso!${NC}"
    echo -e "${GREEN}  ════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${DIM}  Log completo disponível em: $LOG_FILE${NC}"
    echo ""
}

show_help() {
    echo "Uso: $0 [OPÇÃO]"
    echo ""
    echo "Opções:"
    echo "  --help, -h      Mostra esta ajuda"
    echo "  --check         Apenas verifica pré-requisitos"
    echo "  --infra         Apenas inicia infraestrutura (DB + Redis)"
    echo "  --backend       Apenas configura backend"
    echo "  --frontend      Apenas configura frontend"
    echo "  --test          Apenas testa endpoints"
    echo "  --stop          Para todos os serviços"
    echo "  --clean         Para e remove todos os dados"
    echo ""
    echo "Sem argumentos: executa configuração completa"
}

stop_services() {
    print_section "PARANDO SERVIÇOS"
    
    print_step "1" "Parando processos..."
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    print_success "Processos parados"
    
    print_step "2" "Parando containers..."
    cd "$PROJECT_ROOT"
    docker compose down >> "$LOG_FILE" 2>&1 || true
    print_success "Containers parados"
    
    echo ""
    print_success "Todos os serviços foram parados!"
}

clean_all() {
    print_section "LIMPANDO AMBIENTE"
    
    stop_services
    
    print_step "3" "Removendo volumes Docker..."
    docker compose down -v >> "$LOG_FILE" 2>&1 || true
    print_success "Volumes removidos"
    
    print_step "4" "Removendo arquivos de log..."
    rm -f "$PROJECT_ROOT/.backend.log" "$PROJECT_ROOT/.frontend.log" "$LOG_FILE"
    print_success "Logs removidos"
    
    echo ""
    print_success "Ambiente limpo!"
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    # Inicializar log
    echo "=== Dev Setup Log - $(date) ===" > "$LOG_FILE"
    
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --check)
            print_banner
            check_prerequisites
            ;;
        --infra)
            print_banner
            start_infrastructure
            ;;
        --backend)
            print_banner
            setup_backend
            ;;
        --frontend)
            print_banner
            setup_frontend
            ;;
        --test)
            print_banner
            test_api_endpoints
            ;;
        --stop)
            print_banner
            stop_services
            ;;
        --clean)
            print_banner
            clean_all
            ;;
        "")
            # Execução completa
            print_banner
            
            echo -e "${WHITE}  Este script irá:${NC}"
            echo -e "${DIM}    1. Verificar pré-requisitos (Docker, Python, Node.js, etc.)${NC}"
            echo -e "${DIM}    2. Configurar arquivos de ambiente (.env)${NC}"
            echo -e "${DIM}    3. Iniciar infraestrutura (PostgreSQL, Redis)${NC}"
            echo -e "${DIM}    4. Configurar e testar backend (FastAPI)${NC}"
            echo -e "${DIM}    5. Configurar e testar frontend (React)${NC}"
            echo -e "${DIM}    6. Iniciar todos os serviços${NC}"
            echo -e "${DIM}    7. Testar endpoints da API${NC}"
            echo ""
            
            read -p "  Pressione ENTER para continuar ou CTRL+C para cancelar..."
            
            check_prerequisites
            setup_environment_files
            start_infrastructure
            setup_backend
            setup_frontend
            start_services
            test_api_endpoints
            print_summary
            ;;
        *)
            echo "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
}

# Executar
main "$@"
