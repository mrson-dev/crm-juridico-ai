#!/bin/bash

#===============================================================================
#
#   CRM JURÍDICO AI - Setup do Ambiente de Desenvolvimento
#   
#   Script interativo para configurar o ambiente local.
#   Especializado em Direito Previdenciário com IA.
#
#   Uso: ./scripts/dev-setup.sh [comando]
#
#===============================================================================

set -euo pipefail

#-------------------------------------------------------------------------------
# CONFIGURAÇÃO
#-------------------------------------------------------------------------------

# Cores
readonly R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m'
readonly P='\033[0;35m' C='\033[0;36m' W='\033[1;37m' D='\033[2m' N='\033[0m'

# Diretórios
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly ROOT="$(dirname "$SCRIPT_DIR")"
readonly BACKEND="$ROOT/backend"
readonly FRONTEND="$ROOT/frontend"
readonly LOG="$ROOT/.dev-setup.log"

# Portas
declare -A PORTS=(
    [postgres]=5432
    [redis]=6379
    [backend]=8000
    [frontend]=5173
)

# Versões mínimas
declare -A MIN_VERSIONS=(
    [python]="3.11"
    [node]="18"
    [docker]="20"
)

# Controle
VERBOSE=false
START_TIME=$(date +%s)

#-------------------------------------------------------------------------------
# FUNÇÕES DE UI
#-------------------------------------------------------------------------------

banner() {
    clear
    echo -e "${C}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ██████╗██████╗ ███╗   ███╗         ██╗██╗   ██╗██████╗ ██╗██████╗        ║
║    ██╔════╝██╔══██╗████╗ ████║         ██║██║   ██║██╔══██╗██║██╔══██╗       ║
║    ██║     ██████╔╝██╔████╔██║         ██║██║   ██║██████╔╝██║██║  ██║       ║
║    ██║     ██╔══██╗██║╚██╔╝██║    ██   ██║██║   ██║██╔══██╗██║██║  ██║       ║
║    ╚██████╗██║  ██║██║ ╚═╝ ██║    ╚█████╔╝╚██████╔╝██║  ██║██║██████╔╝       ║
║     ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝     ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${N}"
}

# Mensagens padronizadas
ok()      { echo -e "${G}  ✓${N} $1"; }
err()     { echo -e "${R}  ✗${N} $1"; }
warn()    { echo -e "${Y}  ⚠${N} $1"; }
info()    { echo -e "${C}  ℹ${N} $1"; }
step()    { echo -e "${B}  [$1]${N} $2"; }
wait_msg() { echo -ne "${Y}  ⏳${N} $1..."; }
done_msg() { echo -e " ${G}OK${N}"; }

section() {
    echo ""
    echo -e "${P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo -e "${P}  $1${N}"
    echo -e "${P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo ""
}

explain() { echo -e "${D}      $1${N}"; }

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# Mostra tempo decorrido
show_duration() {
    local end_time duration mins secs
    end_time=$(date +%s)
    duration=$((end_time - START_TIME))
    mins=$((duration / 60))
    secs=$((duration % 60))
    echo ""
    info "Tempo total: ${mins}m ${secs}s"
}

# Confirmação do usuário
confirm() {
    local msg="$1"
    echo ""
    echo -e "${Y}  ⚠️  $msg${N}"
    echo ""
    read -rp "  Digite 'sim' para confirmar: " answer
    [[ "$answer" =~ ^[sS]([iI][mM])?$ ]]
}

# Verificação de comando
has() { command -v "$1" &>/dev/null; }

# Comparação de versão (retorna 0 se $1 >= $2)
ver_gte() { printf '%s\n%s\n' "$2" "$1" | sort -V -C; }

#-------------------------------------------------------------------------------
# DETECÇÃO DE SISTEMA
#-------------------------------------------------------------------------------

detect_os() {
    if [[ -f /etc/os-release ]]; then
        # shellcheck source=/dev/null
        source /etc/os-release
        echo "$ID"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

# Gerenciador de pacotes baseado no OS
pkg_install() {
    local pkg="$1"
    local os
    os=$(detect_os)
    
    case "$os" in
        ubuntu|debian|pop|linuxmint)
            sudo apt-get update -qq >> "$LOG" 2>&1
            sudo apt-get install -y "$pkg" >> "$LOG" 2>&1
            ;;
        fedora) sudo dnf install -y "$pkg" >> "$LOG" 2>&1 ;;
        arch|manjaro) sudo pacman -S --noconfirm "$pkg" >> "$LOG" 2>&1 ;;
        macos) has brew && brew install "$pkg" >> "$LOG" 2>&1 ;;
        *) return 1 ;;
    esac
}

#-------------------------------------------------------------------------------
# VERIFICAÇÃO DE ESTRUTURA
#-------------------------------------------------------------------------------

check_structure() {
    local missing=()
    
    [[ ! -d "$BACKEND" ]] && missing+=("backend/")
    [[ ! -d "$FRONTEND" ]] && missing+=("frontend/")
    [[ ! -f "$ROOT/docker-compose.yml" ]] && missing+=("docker-compose.yml")
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        err "Estrutura do projeto incompleta!"
        for item in "${missing[@]}"; do
            echo -e "    ${R}✗${N} Faltando: $item"
        done
        echo ""
        info "Execute este script na raiz do projeto CRM Jurídico AI"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# INSTALADORES
#-------------------------------------------------------------------------------

install_docker() {
    local os
    os=$(detect_os)
    
    case "$os" in
        ubuntu|debian|pop|linuxmint)
            curl -fsSL https://get.docker.com | sudo sh >> "$LOG" 2>&1
            sudo usermod -aG docker "$USER"
            warn "Faça logout/login para usar Docker sem sudo"
            ;;
        macos)
            err "Instale Docker Desktop: https://docker.com/products/docker-desktop"
            return 1
            ;;
        *) 
            err "Instale Docker manualmente: https://docs.docker.com/get-docker/"
            return 1
            ;;
    esac
}

install_node() {
    local os
    os=$(detect_os)
    
    case "$os" in
        ubuntu|debian|pop|linuxmint)
            curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >> "$LOG" 2>&1
            sudo apt-get install -y nodejs >> "$LOG" 2>&1
            ;;
        macos) has brew && brew install node@20 >> "$LOG" 2>&1 ;;
        *) 
            err "Instale Node.js manualmente: https://nodejs.org"
            return 1
            ;;
    esac
}

install_poetry() {
    curl -sSL https://install.python-poetry.org | python3 - >> "$LOG" 2>&1
    export PATH="$HOME/.local/bin:$PATH"
    grep -q '.local/bin' ~/.bashrc 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
}

#-------------------------------------------------------------------------------
# VERIFICAÇÃO DE PRÉ-REQUISITOS
#-------------------------------------------------------------------------------

check_prerequisites() {
    section "📋 VERIFICANDO PRÉ-REQUISITOS"
    
    local os all_ok=true v
    os=$(detect_os)
    info "Sistema: $os"
    explain "Verificando ferramentas necessárias para desenvolvimento..."
    echo ""
    
    # Docker
    step "1" "Docker (containerização)"
    explain "Necessário para PostgreSQL, Redis e deploy"
    if has docker; then
        v=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        ok "Docker $v instalado"
    else
        warn "Docker não encontrado. Instalando..."
        if install_docker; then
            ok "Docker instalado"
        else
            err "Falha na instalação"
            all_ok=false
        fi
    fi
    
    # Docker Compose
    step "2" "Docker Compose (orquestração)"
    explain "Gerencia múltiplos containers (DB, Redis, API)"
    if docker compose version &>/dev/null; then
        ok "Docker Compose disponível"
    else
        warn "Docker Compose não encontrado (incluído no Docker moderno)"
    fi
    
    # Python
    step "3" "Python 3.11+ (backend)"
    explain "Linguagem do backend FastAPI"
    if has python3; then
        v=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
        if ver_gte "$v" "${MIN_VERSIONS[python]}"; then
            ok "Python $v instalado"
        else
            err "Python $v muito antigo (mínimo: ${MIN_VERSIONS[python]})"
            all_ok=false
        fi
    else
        warn "Python não encontrado. Instalando..."
        if pkg_install python3; then
            ok "Python instalado"
        else
            err "Falha"
            all_ok=false
        fi
    fi
    
    # Poetry
    step "4" "Poetry (gerenciador de pacotes Python)"
    explain "Gerencia dependências e virtualenv do backend"
    if has poetry; then
        ok "Poetry instalado"
    else
        warn "Poetry não encontrado. Instalando..."
        if install_poetry; then
            ok "Poetry instalado"
        else
            err "Falha"
            all_ok=false
        fi
    fi
    
    # Node.js
    step "5" "Node.js 18+ (frontend)"
    explain "Runtime do React/Vite"
    if has node; then
        v=$(node --version | grep -oE '[0-9]+' | head -1)
        if ver_gte "$v" "${MIN_VERSIONS[node]}"; then
            ok "Node.js v$v instalado"
        else
            warn "Node.js v$v antigo. Atualizando..."
            install_node && ok "Node.js atualizado" || warn "Atualize manualmente"
        fi
    else
        warn "Node.js não encontrado. Instalando v20..."
        if install_node; then
            ok "Node.js instalado"
        else
            err "Falha"
            all_ok=false
        fi
    fi
    
    # Git
    step "6" "Git (controle de versão)"
    explain "Necessário para commits e deploy"
    if has git; then
        ok "Git instalado"
    else
        warn "Git não encontrado. Instalando..."
        if pkg_install git; then
            ok "Git instalado"
        else
            err "Falha"
            all_ok=false
        fi
    fi
    
    # Ferramentas auxiliares
    step "7" "Ferramentas auxiliares (curl, jq)"
    explain "Úteis para testes de API e debug"
    has curl && ok "curl disponível" || pkg_install curl 2>/dev/null || true
    has jq && ok "jq disponível" || { pkg_install jq 2>/dev/null || info "jq não instalado (opcional)"; }
    
    echo ""
    if [[ "$all_ok" == "false" ]]; then
        err "Alguns requisitos falharam. Corrija e execute novamente."
        return 1
    fi
    ok "Todos os pré-requisitos OK!"
}

#-------------------------------------------------------------------------------
# VALIDAÇÃO GCP (PRODUÇÃO)
#-------------------------------------------------------------------------------

check_gcp_ready() {
    section "☁️  VALIDAÇÃO GCP (PRODUÇÃO)"
    
    explain "Verifica se o ambiente está pronto para deploy na Google Cloud"
    echo ""
    
    local all_ok=true
    
    # gcloud CLI
    step "1" "Google Cloud CLI (gcloud)"
    explain "Necessário para deploy no Cloud Run"
    if has gcloud; then
        local gcloud_version
        gcloud_version=$(gcloud version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+' || echo "unknown")
        ok "gcloud $gcloud_version instalado"
        
        # Verificar autenticação
        step "2" "Autenticação GCP"
        explain "Conta ativa para acessar recursos"
        local account
        account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
        if [[ -n "$account" ]]; then
            ok "Autenticado como: $account"
        else
            warn "Não autenticado. Execute: gcloud auth login"
            all_ok=false
        fi
        
        # Verificar projeto
        step "3" "Projeto GCP"
        explain "Projeto onde os recursos serão criados"
        local project
        project=$(gcloud config get-value project 2>/dev/null || true)
        if [[ -n "$project" && "$project" != "(unset)" ]]; then
            ok "Projeto: $project"
        else
            warn "Projeto não configurado. Execute: gcloud config set project PROJECT_ID"
            all_ok=false
        fi
        
        # Verificar Application Default Credentials
        step "4" "Application Default Credentials"
        explain "Credenciais para aplicações locais"
        if [[ -f "$HOME/.config/gcloud/application_default_credentials.json" ]]; then
            ok "ADC configurado"
        else
            warn "ADC não configurado. Execute: gcloud auth application-default login"
            all_ok=false
        fi
        
    else
        warn "gcloud não instalado"
        explain "Instale: https://cloud.google.com/sdk/docs/install"
        all_ok=false
    fi
    
    # Variáveis de ambiente
    step "5" "Variáveis de ambiente (backend/.env)"
    explain "Chaves de API e configurações GCP"
    if [[ -f "$BACKEND/.env" ]]; then
        local gcp_project gemini_key
        gcp_project=$(grep -E "^GCP_PROJECT_ID=" "$BACKEND/.env" 2>/dev/null | cut -d'=' -f2 || true)
        gemini_key=$(grep -E "^GEMINI_API_KEY=" "$BACKEND/.env" 2>/dev/null | cut -d'=' -f2 || true)
        
        if [[ -n "$gcp_project" && "$gcp_project" != "" ]]; then
            ok "GCP_PROJECT_ID configurado"
        else
            warn "GCP_PROJECT_ID não definido em backend/.env"
            all_ok=false
        fi
        
        if [[ -n "$gemini_key" && "$gemini_key" != "" ]]; then
            ok "GEMINI_API_KEY configurado"
        else
            info "GEMINI_API_KEY não definido (opcional para IA)"
        fi
    else
        warn "backend/.env não existe"
        all_ok=false
    fi
    
    # Docker para Artifact Registry
    step "6" "Docker + Artifact Registry"
    explain "Autenticação do Docker com GCP"
    if has docker && has gcloud; then
        if gcloud auth configure-docker --quiet 2>/dev/null; then
            ok "Docker configurado para GCR"
        else
            info "Configure com: gcloud auth configure-docker"
        fi
    fi
    
    # APIs necessárias
    step "7" "APIs GCP necessárias"
    explain "Cloud Run, Secret Manager, Cloud SQL, Storage"
    if has gcloud; then
        local current_project
        current_project=$(gcloud config get-value project 2>/dev/null || true)
        if [[ -n "$current_project" && "$current_project" != "(unset)" ]]; then
            local apis_enabled
            apis_enabled=$(gcloud services list --enabled --format="value(NAME)" 2>/dev/null || true)
            
            local required_apis=("run.googleapis.com" "secretmanager.googleapis.com" "sqladmin.googleapis.com" "storage.googleapis.com" "artifactregistry.googleapis.com")
            local missing_apis=()
            
            for api in "${required_apis[@]}"; do
                if echo "$apis_enabled" | grep -q "$api"; then
                    ok "$api ✓"
                else
                    warn "$api não habilitada"
                    missing_apis+=("$api")
                fi
            done
            
            if [[ ${#missing_apis[@]} -gt 0 ]]; then
                echo ""
                info "Habilite com: gcloud services enable ${missing_apis[*]}"
                all_ok=false
            fi
        else
            info "Pule esta verificação (projeto não configurado)"
        fi
    fi
    
    echo ""
    if [[ "$all_ok" == "true" ]]; then
        echo -e "${G}  ════════════════════════════════════════════════════════════${N}"
        echo -e "${G}    ✅ Ambiente pronto para deploy GCP!${N}"
        echo -e "${G}  ════════════════════════════════════════════════════════════${N}"
    else
        echo -e "${Y}  ════════════════════════════════════════════════════════════${N}"
        echo -e "${Y}    ⚠️  Algumas configurações GCP pendentes${N}"
        echo -e "${Y}  ════════════════════════════════════════════════════════════${N}"
    fi
}

#-------------------------------------------------------------------------------
# CONFIGURAÇÃO DE AMBIENTE
#-------------------------------------------------------------------------------

setup_env_files() {
    section "⚙️  CONFIGURANDO ARQUIVOS DE AMBIENTE"
    
    explain "Arquivos .env contêm configurações locais (senhas, URLs, etc.)"
    explain "Eles NÃO são commitados no git por segurança."
    echo ""
    
    # Backend
    step "1" "Backend (.env)"
    if [[ ! -f "$BACKEND/.env" ]]; then
        if [[ -f "$BACKEND/.env.example" ]]; then
            cp "$BACKEND/.env.example" "$BACKEND/.env"
            ok "Copiado de .env.example"
        else
            cat > "$BACKEND/.env" << 'EOF'
# === Banco de Dados ===
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/crm_juridico

# === Segurança ===
SECRET_KEY=dev-secret-key-change-in-production-minimum-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# === Ambiente ===
ENVIRONMENT=development
DEBUG=true

# === Redis (cache/filas) ===
REDIS_URL=redis://localhost:6379/0

# === GCP (configurar para produção) ===
GCP_PROJECT_ID=
GEMINI_API_KEY=
GCS_BUCKET_DOCUMENTOS=
EOF
            ok "Arquivo .env criado com valores padrão"
        fi
        explain "Edite backend/.env para adicionar chaves de API se necessário"
    else
        info "backend/.env já existe"
    fi
    
    # Frontend
    step "2" "Frontend (.env)"
    if [[ ! -f "$FRONTEND/.env" ]]; then
        if [[ -f "$FRONTEND/.env.example" ]]; then
            cp "$FRONTEND/.env.example" "$FRONTEND/.env"
            ok "Copiado de .env.example"
        else
            cat > "$FRONTEND/.env" << 'EOF'
VITE_API_URL=http://localhost:8000
EOF
            ok "Arquivo .env criado"
        fi
    else
        info "frontend/.env já existe"
    fi
}

#-------------------------------------------------------------------------------
# INFRAESTRUTURA (Docker)
#-------------------------------------------------------------------------------

start_infra() {
    section "🐳 INICIANDO INFRAESTRUTURA"
    
    explain "PostgreSQL: Banco de dados relacional com pgvector (IA)"
    explain "Redis: Cache e filas de tarefas assíncronas"
    echo ""
    
    cd "$ROOT"
    
    step "1" "Parando containers anteriores"
    docker compose down --remove-orphans >> "$LOG" 2>&1 || true
    ok "Containers parados"
    
    step "2" "Iniciando PostgreSQL + Redis"
    wait_msg "Subindo containers"
    if [[ "$VERBOSE" == "true" ]]; then
        docker compose up -d db redis 2>&1 | tee -a "$LOG"
    else
        docker compose up -d db redis >> "$LOG" 2>&1
    fi
    done_msg
    
    step "3" "Aguardando PostgreSQL"
    local attempts=0
    while [[ $attempts -lt 30 ]]; do
        if docker compose exec -T db pg_isready -U postgres >> "$LOG" 2>&1; then
            ok "PostgreSQL pronto!"
            break
        fi
        attempts=$((attempts + 1))
        sleep 1
    done
    if [[ $attempts -eq 30 ]]; then
        err "PostgreSQL timeout"
        return 1
    fi
    
    step "4" "Configurando extensões PostgreSQL"
    explain "vector: Embeddings de IA | uuid-ossp: IDs únicos | pg_trgm: Busca textual"
    for ext in "vector" "uuid-ossp" "pg_trgm"; do
        docker compose exec -T db psql -U postgres -d crm_juridico \
            -c "CREATE EXTENSION IF NOT EXISTS \"$ext\";" >> "$LOG" 2>&1 || true
    done
    ok "Extensões configuradas"
    
    step "5" "Criando banco de testes"
    docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS test_db;" >> "$LOG" 2>&1 || true
    docker compose exec -T db psql -U postgres -c "CREATE DATABASE test_db;" >> "$LOG" 2>&1 || true
    for ext in "vector" "uuid-ossp" "pg_trgm"; do
        docker compose exec -T db psql -U postgres -d test_db \
            -c "CREATE EXTENSION IF NOT EXISTS \"$ext\";" >> "$LOG" 2>&1 || true
    done
    ok "Banco test_db criado"
    
    step "6" "Verificando Redis"
    if docker compose exec -T redis redis-cli ping >> "$LOG" 2>&1; then
        ok "Redis respondendo"
    else
        err "Redis não respondeu"
        return 1
    fi
}

#-------------------------------------------------------------------------------
# BACKEND
#-------------------------------------------------------------------------------

setup_backend() {
    section "🐍 CONFIGURANDO BACKEND"
    
    explain "FastAPI + SQLAlchemy assíncrono + Pydantic v2"
    explain "Especializado em Direito Previdenciário (INSS)"
    echo ""
    
    cd "$BACKEND"
    
    step "1" "Instalando dependências Python"
    explain "Poetry gerencia virtualenv e pacotes automaticamente"
    wait_msg "poetry install"
    if [[ "$VERBOSE" == "true" ]]; then
        poetry install 2>&1 | tee -a "$LOG"
    else
        poetry install >> "$LOG" 2>&1
    fi
    done_msg
    ok "Dependências instaladas"
    
    step "2" "Aplicando migrations"
    explain "Alembic cria/atualiza tabelas no PostgreSQL"
    if poetry run alembic upgrade head >> "$LOG" 2>&1; then
        ok "Banco de dados atualizado"
    else
        warn "Migration falhou (verifique o log)"
    fi
    
    step "3" "Executando testes"
    explain "Pytest valida se o código está funcionando"
    echo ""
    poetry run pytest -v --tb=short 2>&1 | grep -E "(PASSED|FAILED|ERROR|tests/|=====)" || true
    echo ""
    ok "Testes executados"
}

#-------------------------------------------------------------------------------
# FRONTEND
#-------------------------------------------------------------------------------

setup_frontend() {
    section "⚛️  CONFIGURANDO FRONTEND"
    
    explain "React 18 + TypeScript + Vite + TailwindCSS"
    explain "Interface moderna para gestão de processos"
    echo ""
    
    cd "$FRONTEND"
    
    step "1" "Instalando dependências Node.js"
    wait_msg "npm install"
    if [[ "$VERBOSE" == "true" ]]; then
        npm install 2>&1 | tee -a "$LOG"
    else
        npm install >> "$LOG" 2>&1
    fi
    done_msg
    ok "Dependências instaladas"
    
    step "2" "Verificando build"
    explain "Compila TypeScript e verifica erros"
    if npm run build >> "$LOG" 2>&1; then
        ok "Build OK (sem erros TypeScript)"
    else
        warn "Build com warnings (verifique o log)"
    fi
}

#-------------------------------------------------------------------------------
# SERVIÇOS
#-------------------------------------------------------------------------------

check_port() {
    local port=$1
    if has lsof; then
        ! lsof -i :"$port" &>/dev/null
    elif has ss; then
        ! ss -tuln | grep -q ":$port "
    else
        return 0
    fi
}

start_services() {
    section "🚀 INICIANDO SERVIÇOS"
    
    explain "Backend: API REST em http://localhost:${PORTS[backend]}"
    explain "Frontend: Interface em http://localhost:${PORTS[frontend]}"
    echo ""
    
    # Parar anteriores
    step "1" "Limpando processos anteriores"
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 2
    ok "Processos finalizados"
    
    # Verificar portas
    step "2" "Verificando portas"
    for svc in backend frontend; do
        if ! check_port "${PORTS[$svc]}"; then
            err "Porta ${PORTS[$svc]} ($svc) em uso!"
            info "Execute: kill \$(lsof -t -i:${PORTS[$svc]})"
            return 1
        fi
    done
    ok "Portas disponíveis"
    
    # Backend
    step "3" "Iniciando Backend (porta ${PORTS[backend]})"
    cd "$BACKEND"
    nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port "${PORTS[backend]}" --reload >> "$ROOT/.backend.log" 2>&1 &
    sleep 3
    if pgrep -f "uvicorn app.main:app" >/dev/null; then
        ok "Backend rodando"
    else
        err "Falha ao iniciar. Veja: tail -50 $ROOT/.backend.log"
        return 1
    fi
    
    # Frontend
    step "4" "Iniciando Frontend (porta ${PORTS[frontend]})"
    cd "$FRONTEND"
    nohup npm run dev >> "$ROOT/.frontend.log" 2>&1 &
    sleep 3
    if pgrep -f "vite" >/dev/null; then
        ok "Frontend rodando"
    else
        err "Falha ao iniciar. Veja: tail -50 $ROOT/.frontend.log"
        return 1
    fi
}

#-------------------------------------------------------------------------------
# TESTES DE API
#-------------------------------------------------------------------------------

test_api() {
    section "🧪 TESTANDO API"
    
    local url="http://localhost:${PORTS[backend]}"
    
    step "1" "Health Check"
    explain "Verifica se a API está respondendo"
    local health
    health=$(curl -s --max-time 5 "$url/health" 2>/dev/null || true)
    if echo "$health" | grep -q "healthy"; then
        ok "API saudável"
    else
        err "API não respondeu"
        return 1
    fi
    
    step "2" "Documentação OpenAPI"
    explain "Swagger UI para testar endpoints"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url/docs" 2>/dev/null || echo "000")
    if [[ "$http_code" == "200" ]]; then
        ok "Docs disponíveis em $url/docs"
    else
        info "Docs podem estar desabilitados"
    fi
    
    step "3" "Teste de Onboarding"
    explain "Cria escritório + usuário admin de teste"
    local response
    response=$(curl -s --max-time 10 -X POST "$url/api/v1/auth/onboarding" \
        -H "Content-Type: application/json" \
        -d '{"escritorio_nome":"Teste Dev","escritorio_cnpj":"11222333000181","escritorio_email":"teste@dev.com","usuario_nome":"Admin","usuario_email":"admin@dev.com","usuario_password":"Test@123"}' 2>/dev/null || true)
    
    if echo "$response" | grep -q "success.*true"; then
        ok "Onboarding OK"
        
        local token
        token=$(echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$token" ]]; then
            step "4" "Endpoint autenticado (/me)"
            if curl -s --max-time 5 "$url/api/v1/auth/me" -H "Authorization: Bearer $token" | grep -q "admin@dev.com"; then
                ok "Autenticação funcionando"
            fi
        fi
    else
        info "Onboarding já executado ou com erro"
    fi
}

#-------------------------------------------------------------------------------
# STATUS
#-------------------------------------------------------------------------------

show_status() {
    section "📊 STATUS DOS SERVIÇOS"
    
    cd "$ROOT"
    
    # PostgreSQL
    step "1" "PostgreSQL (${PORTS[postgres]})"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "crm_juridico_db"; then
        ok "Rodando"
    else
        err "Parado"
    fi
    
    # Redis
    step "2" "Redis (${PORTS[redis]})"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "crm_juridico_redis"; then
        ok "Rodando"
    else
        err "Parado"
    fi
    
    # Backend
    step "3" "Backend API (${PORTS[backend]})"
    if curl -s --max-time 2 "http://localhost:${PORTS[backend]}/health" 2>/dev/null | grep -q "healthy"; then
        ok "Respondendo"
    elif pgrep -f "uvicorn app.main:app" >/dev/null; then
        warn "Processo ativo mas não responde"
    else
        err "Parado"
    fi
    
    # Frontend
    step "4" "Frontend (${PORTS[frontend]})"
    if curl -s --max-time 2 "http://localhost:${PORTS[frontend]}" >/dev/null 2>&1; then
        ok "Respondendo"
    elif pgrep -f "vite" >/dev/null; then
        warn "Processo ativo mas não responde"
    else
        err "Parado"
    fi
    
    # Celery Worker (opcional)
    step "5" "Celery Worker (opcional)"
    if pgrep -f "celery.*worker" >/dev/null; then
        ok "Worker rodando"
    else
        info "Não iniciado (opcional para dev)"
    fi
    
    echo ""
    echo -e "${C}  ┌─────────────────────────────────────────────────────────────┐${N}"
    echo -e "${C}  │${N}  🚀 API:      ${G}http://localhost:${PORTS[backend]}${N}                     ${C}│${N}"
    echo -e "${C}  │${N}  📚 Docs:     ${G}http://localhost:${PORTS[backend]}/docs${N}                ${C}│${N}"
    echo -e "${C}  │${N}  🎨 Frontend: ${G}http://localhost:${PORTS[frontend]}${N}                     ${C}│${N}"
    echo -e "${C}  └─────────────────────────────────────────────────────────────┘${N}"
}

#-------------------------------------------------------------------------------
# TESTES COMPLETOS
#-------------------------------------------------------------------------------

run_full_tests() {
    section "🔬 TESTES COMPLETOS (Lint + Types + Coverage)"
    
    explain "Executa todas as verificações de qualidade de código"
    echo ""
    
    cd "$BACKEND"
    local all_ok=true
    
    step "1" "Ruff (linter)"
    explain "Verifica estilo e problemas no código"
    if poetry run ruff check . >> "$LOG" 2>&1; then
        ok "Sem problemas"
    else
        warn "Issues encontrados (veja log)"
        all_ok=false
    fi
    
    step "2" "MyPy (type checker)"
    explain "Verifica tipos estáticos"
    if poetry run mypy app --ignore-missing-imports >> "$LOG" 2>&1; then
        ok "Tipos OK"
    else
        warn "Issues de tipos (veja log)"
        all_ok=false
    fi
    
    step "3" "Pytest + Coverage"
    explain "Testes unitários com cobertura de código"
    echo ""
    poetry run pytest -v --cov=app --cov-report=term-missing 2>&1 | grep -E "(PASSED|FAILED|ERROR|TOTAL|tests/|=====)" || true
    
    local cov
    cov=$(poetry run coverage report 2>/dev/null | grep TOTAL | awk '{print $4}' | tr -d '%' || echo "0")
    if [[ -n "$cov" && "$cov" != "0" ]]; then
        if [[ "$cov" -ge 70 ]]; then
            ok "Cobertura: ${cov}% ✓"
        else
            warn "Cobertura: ${cov}% (mínimo: 70%)"
            all_ok=false
        fi
    fi
    
    step "4" "Frontend Build"
    cd "$FRONTEND"
    if npm run build >> "$LOG" 2>&1; then
        ok "TypeScript sem erros"
    else
        warn "Build com problemas"
        all_ok=false
    fi
    
    echo ""
    if [[ "$all_ok" == "true" ]]; then
        echo -e "${G}  ════════════════════════════════════════════════════════════${N}"
        echo -e "${G}    ✅ Tudo OK! Pronto para deploy.${N}"
        echo -e "${G}  ════════════════════════════════════════════════════════════${N}"
    else
        echo -e "${Y}  ════════════════════════════════════════════════════════════${N}"
        echo -e "${Y}    ⚠️  Alguns warnings. Revise antes do deploy.${N}"
        echo -e "${Y}  ════════════════════════════════════════════════════════════${N}"
    fi
}

#-------------------------------------------------------------------------------
# PARAR / LIMPAR
#-------------------------------------------------------------------------------

stop_all() {
    section "🛑 PARANDO SERVIÇOS DO PROJETO"
    
    step "1" "Parando processos (backend + frontend)"
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "celery.*worker" 2>/dev/null || true
    ok "Processos finalizados"
    
    step "2" "Parando containers do projeto"
    cd "$ROOT"
    docker compose down >> "$LOG" 2>&1 || true
    ok "Containers parados"
    
    echo ""
    ok "Serviços do projeto parados!"
}

stop_all_docker() {
    section "🐳 PARANDO TODOS OS CONTAINERS DOCKER"
    
    explain "Para TODOS os containers Docker da máquina (não só do projeto)"
    echo ""
    
    local running_containers
    running_containers=$(docker ps -q 2>/dev/null || true)
    
    if [[ -z "$running_containers" ]]; then
        info "Nenhum container em execução"
        return 0
    fi
    
    # Mostrar containers ativos
    step "1" "Containers em execução:"
    echo ""
    docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" 2>/dev/null || true
    echo ""
    
    if ! confirm "Deseja parar TODOS esses containers?"; then
        info "Operação cancelada."
        return 0
    fi
    
    step "2" "Parando todos os containers"
    docker stop $running_containers >> "$LOG" 2>&1 || true
    ok "Todos os containers parados"
    
    echo ""
    ok "Máquina limpa de containers!"
}

restart_all() {
    section "🔄 REINICIANDO SERVIÇOS"
    
    explain "Parando e reiniciando todos os serviços do projeto..."
    echo ""
    
    # Parar processos
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    cd "$ROOT"
    docker compose down >> "$LOG" 2>&1 || true
    ok "Serviços parados"
    
    # Reiniciar
    start_infra || return 1
    start_services || return 1
    
    echo ""
    ok "Serviços reiniciados!"
    show_status
}

clean_all() {
    section "🧹 LIMPANDO AMBIENTE"
    
    if ! confirm "Isso irá APAGAR todos os dados do banco de dados!"; then
        info "Operação cancelada."
        return 0
    fi
    
    # Parar tudo
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    pkill -f "celery.*worker" 2>/dev/null || true
    ok "Processos finalizados"
    
    cd "$ROOT"
    
    step "2" "Removendo containers e volumes"
    explain "Apagando dados do PostgreSQL e Redis..."
    docker compose down -v >> "$LOG" 2>&1 || true
    ok "Volumes removidos"
    
    step "3" "Removendo logs"
    rm -f "$ROOT/.backend.log" "$ROOT/.frontend.log" "$LOG"
    ok "Logs removidos"
    
    echo ""
    ok "Ambiente limpo!"
}

#-------------------------------------------------------------------------------
# RESUMO FINAL
#-------------------------------------------------------------------------------

print_summary() {
    section "✅ CONFIGURAÇÃO CONCLUÍDA"
    
    echo -e "${C}  ┌─────────────────────────────────────────────────────────────┐${N}"
    echo -e "${C}  │${N}                    ${W}SERVIÇOS ATIVOS${N}                        ${C}│${N}"
    echo -e "${C}  ├─────────────────────────────────────────────────────────────┤${N}"
    echo -e "${C}  │${N}  🗄️  PostgreSQL:  ${G}localhost:${PORTS[postgres]}${N}                       ${C}│${N}"
    echo -e "${C}  │${N}  📦 Redis:       ${G}localhost:${PORTS[redis]}${N}                       ${C}│${N}"
    echo -e "${C}  │${N}  🚀 API:         ${G}http://localhost:${PORTS[backend]}${N}              ${C}│${N}"
    echo -e "${C}  │${N}  📚 Docs:        ${G}http://localhost:${PORTS[backend]}/docs${N}         ${C}│${N}"
    echo -e "${C}  │${N}  🎨 Frontend:    ${G}http://localhost:${PORTS[frontend]}${N}              ${C}│${N}"
    echo -e "${C}  └─────────────────────────────────────────────────────────────┘${N}"
    
    echo ""
    echo -e "${D}  Comandos úteis:${N}"
    echo -e "${D}    tail -f .backend.log           # Logs do backend${N}"
    echo -e "${D}    tail -f .frontend.log          # Logs do frontend${N}"
    echo -e "${D}    ./scripts/dev-setup.sh --stop  # Parar tudo${N}"
    echo ""
    
    show_duration
}

#-------------------------------------------------------------------------------
# MENU INTERATIVO
#-------------------------------------------------------------------------------

show_menu() {
    while true; do
        echo ""
        echo -e "${W}  O que você deseja fazer?${N}"
        echo ""
        echo -e "  ${C}1)${N} Setup completo (recomendado para primeira vez)"
        echo -e "  ${C}2)${N} Apenas verificar pré-requisitos"
        echo -e "  ${C}3)${N} Apenas iniciar infraestrutura (DB + Redis)"
        echo -e "  ${C}4)${N} Apenas configurar backend"
        echo -e "  ${C}5)${N} Apenas configurar frontend"
        echo -e "  ${C}6)${N} Iniciar serviços (backend + frontend)"
        echo -e "  ${C}7)${N} Ver status dos serviços"
        echo -e "  ${C}8)${N} Rodar testes completos (lint + types + coverage)"
        echo -e "  ${C}9)${N} Reiniciar serviços"
        echo -e "  ${C}0)${N} Parar serviços do projeto"
        echo ""
        echo -e "  ${Y}d)${N} Parar TODOS os containers Docker"
        echo -e "  ${Y}g)${N} Validar ambiente GCP (produção)"
        echo -e "  ${Y}c)${N} Limpar ambiente (remove dados)"
        echo -e "  ${C}q)${N} Sair"
        echo ""
        read -rp "  Escolha: " choice
        
        case "$choice" in
            1) run_full_setup ;;
            2) check_prerequisites ;;
            3) start_infra ;;
            4) setup_backend ;;
            5) setup_frontend ;;
            6) start_services ;;
            7) show_status ;;
            8) run_full_tests ;;
            9) restart_all ;;
            0) stop_all ;;
            d|D) stop_all_docker ;;
            g|G) check_gcp_ready ;;
            c|C) clean_all ;;
            q|Q) echo ""; info "Até logo!"; exit 0 ;;
            *) warn "Opção inválida" ;;
        esac
        
        echo ""
        echo -e "${D}Pressione ENTER para voltar ao menu...${N}"
        read -r
    done
}

run_full_setup() {
    check_prerequisites || return 1
    setup_env_files
    start_infra || return 1
    setup_backend
    setup_frontend
    start_services || return 1
    test_api || true
    print_summary
}

#-------------------------------------------------------------------------------
# HELP
#-------------------------------------------------------------------------------

show_help() {
    cat << EOF
CRM Jurídico AI - Setup de Desenvolvimento

Uso: $0 [comando] [opções]

Comandos:
  (nenhum)      Menu interativo
  --auto        Setup completo automático
  --full        Setup + testes completos (lint, types, coverage)
  --check       Verificar pré-requisitos
  --gcp         Validar ambiente GCP (produção)
  --infra       Iniciar PostgreSQL + Redis
  --backend     Configurar backend
  --frontend    Configurar frontend
  --start       Iniciar backend + frontend
  --restart     Reiniciar todos os serviços
  --test        Testar endpoints da API
  --status      Ver status dos serviços
  --stop        Parar serviços do projeto
  --stop-all    Parar TODOS os containers Docker
  --clean       Parar e remover dados
  --help        Esta ajuda

Opções:
  --verbose     Modo detalhado (mostra comandos executados)

Exemplos:
  $0                    # Menu interativo
  $0 --auto             # Setup completo sem interação
  $0 --status           # Ver o que está rodando
  $0 --gcp              # Validar se está pronto para GCP
  $0 --stop-all         # Para TODOS os dockers da máquina
  $0 --auto --verbose   # Setup com output detalhado
EOF
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    # Criar arquivo de log
    : > "$LOG"
    echo "=== Dev Setup Log - $(date) ===" >> "$LOG"
    
    # Processar flag --verbose primeiro
    local args=()
    for arg in "$@"; do
        case "$arg" in
            --verbose|-v) VERBOSE=true ;;
            *) args+=("$arg") ;;
        esac
    done
    set -- "${args[@]+"${args[@]}"}"
    
    # Verificar estrutura (exceto help e stop-all)
    case "${1:-}" in
        --help|-h|--stop-all) ;;
        *) check_structure ;;
    esac
    
    case "${1:-}" in
        --help|-h)    show_help ;;
        --auto|-y)    banner; run_full_setup ;;
        --full)       banner; run_full_setup && run_full_tests ;;
        --check)      banner; check_prerequisites ;;
        --gcp)        banner; check_gcp_ready ;;
        --infra)      banner; start_infra ;;
        --backend)    banner; setup_backend ;;
        --frontend)   banner; setup_frontend ;;
        --start)      banner; start_services ;;
        --restart)    banner; restart_all ;;
        --test)       banner; test_api ;;
        --status)     banner; show_status ;;
        --stop)       banner; stop_all ;;
        --stop-all)   banner; stop_all_docker ;;
        --clean)      banner; clean_all ;;
        "")           banner; show_menu ;;
        *)            echo "Comando desconhecido: $1"; show_help; exit 1 ;;
    esac
}

main "$@"
