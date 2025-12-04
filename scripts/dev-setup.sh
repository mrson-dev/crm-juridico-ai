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

set -e

#-------------------------------------------------------------------------------
# CONFIGURAÇÃO
#-------------------------------------------------------------------------------

# Cores
R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m'
P='\033[0;35m' C='\033[0;36m' W='\033[1;37m' D='\033[2m' N='\033[0m'

# Diretórios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
LOG="$ROOT/.dev-setup.log"

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

#-------------------------------------------------------------------------------
# FUNÇÕES DE UI
#-------------------------------------------------------------------------------

banner() {
    clear
    echo -e "${C}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║     ██████╗██████╗ ███╗   ███╗         ██╗██╗   ██╗██████╗ ██╗██████╗       ║
║    ██╔════╝██╔══██╗████╗ ████║         ██║██║   ██║██╔══██╗██║██╔══██╗      ║
║    ██║     ██████╔╝██╔████╔██║         ██║██║   ██║██████╔╝██║██║  ██║      ║
║    ██║     ██╔══██╗██║╚██╔╝██║    ██   ██║██║   ██║██╔══██╗██║██║  ██║      ║
║    ╚██████╗██║  ██║██║ ╚═╝ ██║    ╚█████╔╝╚██████╔╝██║  ██║██║██████╔╝      ║
║     ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝     ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${N}"
}

# Mensagens padronizadas
ok()    { echo -e "${G}  ✓${N} $1"; }
err()   { echo -e "${R}  ✗${N} $1"; }
warn()  { echo -e "${Y}  ⚠${N} $1"; }
info()  { echo -e "${C}  ℹ${N} $1"; }
step()  { echo -e "${B}  [$1]${N} $2"; }
wait_msg() { echo -ne "${Y}  ⏳${N} $1..."; }
done_msg() { echo -e " ${G}OK${N}"; }

section() {
    echo ""
    echo -e "${P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo -e "${P}  $1${N}"
    echo -e "${P}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo ""
}

explain() {
    echo -e "${D}      $1${N}"
}

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# Verificação de comando
has() { command -v "$1" &>/dev/null; }

# Comparação de versão (retorna 0 se $1 >= $2)
ver_gte() { printf '%s\n%s\n' "$2" "$1" | sort -V -C; }

#-------------------------------------------------------------------------------
# DETECÇÃO DE SISTEMA
#-------------------------------------------------------------------------------

detect_os() {
    if [[ -f /etc/os-release ]]; then
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
    local os=$(detect_os)
    
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
    local os=$(detect_os)
    local docker_os="$os"
    [[ "$os" == "linuxmint" ]] && docker_os="ubuntu"
    
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
    local os=$(detect_os)
    
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
    
    local os=$(detect_os)
    info "Sistema: $os"
    explain "Verificando ferramentas necessárias para desenvolvimento..."
    echo ""
    
    local all_ok=true
    
    # Docker
    step "1" "Docker (containerização)"
    explain "Necessário para PostgreSQL, Redis e deploy"
    if has docker; then
        local v=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        ok "Docker $v instalado"
    else
        warn "Docker não encontrado. Instalando..."
        install_docker && ok "Docker instalado" || { err "Falha na instalação"; all_ok=false; }
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
        local v=$(python3 --version | grep -oE '[0-9]+\.[0-9]+')
        if ver_gte "$v" "${MIN_VERSIONS[python]}"; then
            ok "Python $v instalado"
        else
            err "Python $v muito antigo (mínimo: ${MIN_VERSIONS[python]})"
            all_ok=false
        fi
    else
        warn "Python não encontrado. Instalando..."
        pkg_install python3 && ok "Python instalado" || { err "Falha"; all_ok=false; }
    fi
    
    # Poetry
    step "4" "Poetry (gerenciador de pacotes Python)"
    explain "Gerencia dependências e virtualenv do backend"
    if has poetry; then
        ok "Poetry instalado"
    else
        warn "Poetry não encontrado. Instalando..."
        install_poetry && ok "Poetry instalado" || { err "Falha"; all_ok=false; }
    fi
    
    # Node.js
    step "5" "Node.js 18+ (frontend)"
    explain "Runtime do React/Vite"
    if has node; then
        local v=$(node --version | grep -oE '[0-9]+' | head -1)
        if ver_gte "$v" "${MIN_VERSIONS[node]}"; then
            ok "Node.js v$v instalado"
        else
            warn "Node.js v$v antigo. Atualizando..."
            install_node && ok "Node.js atualizado" || warn "Atualize manualmente"
        fi
    else
        warn "Node.js não encontrado. Instalando v20..."
        install_node && ok "Node.js instalado" || { err "Falha"; all_ok=false; }
    fi
    
    # Git
    step "6" "Git (controle de versão)"
    explain "Necessário para commits e deploy"
    if has git; then
        ok "Git instalado"
    else
        warn "Git não encontrado. Instalando..."
        pkg_install git && ok "Git instalado" || { err "Falha"; all_ok=false; }
    fi
    
    # Ferramentas opcionais
    step "7" "Ferramentas auxiliares (curl, jq)"
    explain "Úteis para testes de API e debug"
    has curl && ok "curl disponível" || { pkg_install curl; }
    has jq && ok "jq disponível" || { pkg_install jq 2>/dev/null || info "jq não instalado (opcional)"; }
    
    echo ""
    if [[ "$all_ok" == "false" ]]; then
        err "Alguns requisitos falharam. Corrija e execute novamente."
        exit 1
    fi
    ok "Todos os pré-requisitos OK!"
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

# === GCP (opcional em dev) ===
GCP_PROJECT_ID=
GEMINI_API_KEY=
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
    docker compose up -d db redis >> "$LOG" 2>&1
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
    [[ $attempts -eq 30 ]] && { err "PostgreSQL timeout"; exit 1; }
    
    step "4" "Configurando extensões PostgreSQL"
    explain "vector: Embeddings de IA | uuid-ossp: IDs únicos | pg_trgm: Busca textual"
    for ext in "vector" "\"uuid-ossp\"" "pg_trgm"; do
        docker compose exec -T db psql -U postgres -d crm_juridico \
            -c "CREATE EXTENSION IF NOT EXISTS $ext;" >> "$LOG" 2>&1 || true
    done
    ok "Extensões configuradas"
    
    step "5" "Criando banco de testes"
    docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS test_db;" >> "$LOG" 2>&1 || true
    docker compose exec -T db psql -U postgres -c "CREATE DATABASE test_db;" >> "$LOG" 2>&1
    for ext in "vector" "\"uuid-ossp\"" "pg_trgm"; do
        docker compose exec -T db psql -U postgres -d test_db \
            -c "CREATE EXTENSION IF NOT EXISTS $ext;" >> "$LOG" 2>&1 || true
    done
    ok "Banco test_db criado"
    
    step "6" "Verificando Redis"
    if docker compose exec -T redis redis-cli ping >> "$LOG" 2>&1; then
        ok "Redis respondendo"
    else
        err "Redis não respondeu"
        exit 1
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
    poetry install >> "$LOG" 2>&1
    done_msg
    ok "Dependências instaladas"
    
    step "2" "Aplicando migrations"
    explain "Alembic cria/atualiza tabelas no PostgreSQL"
    poetry run alembic upgrade head >> "$LOG" 2>&1
    ok "Banco de dados atualizado"
    
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
    npm install >> "$LOG" 2>&1
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
    local health=$(curl -s "$url/health" 2>/dev/null)
    if echo "$health" | grep -q "healthy"; then
        ok "API saudável"
    else
        err "API não respondeu"
        return 1
    fi
    
    step "2" "Documentação OpenAPI"
    explain "Swagger UI para testar endpoints"
    if curl -s -o /dev/null -w "%{http_code}" "$url/docs" 2>/dev/null | grep -q "200"; then
        ok "Docs disponíveis em $url/docs"
    else
        info "Docs podem estar desabilitados"
    fi
    
    step "3" "Teste de Onboarding"
    explain "Cria escritório + usuário admin de teste"
    local response=$(curl -s -X POST "$url/api/v1/auth/onboarding" \
        -H "Content-Type: application/json" \
        -d '{"escritorio_nome":"Teste Dev","escritorio_cnpj":"11222333000181","escritorio_email":"teste@dev.com","usuario_nome":"Admin","usuario_email":"admin@dev.com","usuario_password":"Test@123"}' 2>/dev/null)
    
    if echo "$response" | grep -q "success.*true"; then
        ok "Onboarding OK"
        
        local token=$(echo "$response" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
        if [[ -n "$token" ]]; then
            step "4" "Endpoint autenticado (/me)"
            if curl -s "$url/api/v1/auth/me" -H "Authorization: Bearer $token" | grep -q "admin@dev.com"; then
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
    if docker compose ps 2>/dev/null | grep -q "crm_juridico_db.*Up"; then
        ok "Rodando"
    else
        err "Parado"
    fi
    
    # Redis
    step "2" "Redis (${PORTS[redis]})"
    if docker compose ps 2>/dev/null | grep -q "crm_juridico_redis.*Up"; then
        ok "Rodando"
    else
        err "Parado"
    fi
    
    # Backend
    step "3" "Backend API (${PORTS[backend]})"
    if curl -s "http://localhost:${PORTS[backend]}/health" 2>/dev/null | grep -q "healthy"; then
        ok "Respondendo"
    elif pgrep -f "uvicorn app.main:app" >/dev/null; then
        warn "Processo ativo mas não responde"
    else
        err "Parado"
    fi
    
    # Frontend
    step "4" "Frontend (${PORTS[frontend]})"
    if curl -s "http://localhost:${PORTS[frontend]}" >/dev/null 2>&1; then
        ok "Respondendo"
    elif pgrep -f "vite" >/dev/null; then
        warn "Processo ativo mas não responde"
    else
        err "Parado"
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
    
    local cov=$(poetry run coverage report 2>/dev/null | grep TOTAL | awk '{print $4}' | tr -d '%')
    if [[ -n "$cov" ]]; then
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
    section "🛑 PARANDO SERVIÇOS"
    
    step "1" "Parando processos"
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    ok "Processos finalizados"
    
    step "2" "Parando containers"
    cd "$ROOT"
    docker compose down >> "$LOG" 2>&1 || true
    ok "Containers parados"
    
    echo ""
    ok "Tudo parado!"
}

clean_all() {
    section "🧹 LIMPANDO AMBIENTE"
    
    stop_all
    
    step "3" "Removendo volumes Docker"
    explain "Isso apaga todos os dados do banco!"
    docker compose down -v >> "$LOG" 2>&1 || true
    ok "Volumes removidos"
    
    step "4" "Removendo logs"
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
    echo -e "${D}    tail -f .backend.log     # Logs do backend${N}"
    echo -e "${D}    tail -f .frontend.log    # Logs do frontend${N}"
    echo -e "${D}    ./scripts/dev-setup.sh --stop   # Parar tudo${N}"
    echo ""
}

#-------------------------------------------------------------------------------
# MENU INTERATIVO
#-------------------------------------------------------------------------------

show_menu() {
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
    echo -e "  ${C}9)${N} Parar todos os serviços"
    echo -e "  ${C}0)${N} Limpar ambiente (remove dados)"
    echo -e "  ${C}q)${N} Sair"
    echo ""
    read -p "  Escolha [1-9, 0, q]: " choice
    
    case "$choice" in
        1) run_full_setup ;;
        2) check_prerequisites ;;
        3) start_infra ;;
        4) setup_backend ;;
        5) setup_frontend ;;
        6) start_services ;;
        7) show_status ;;
        8) run_full_tests ;;
        9) stop_all ;;
        0) clean_all ;;
        q|Q) echo ""; info "Até logo!"; exit 0 ;;
        *) warn "Opção inválida"; show_menu ;;
    esac
}

run_full_setup() {
    check_prerequisites
    setup_env_files
    start_infra
    setup_backend
    setup_frontend
    start_services
    test_api
    print_summary
}

#-------------------------------------------------------------------------------
# HELP
#-------------------------------------------------------------------------------

show_help() {
    cat << EOF
CRM Jurídico AI - Setup de Desenvolvimento

Uso: $0 [comando]

Comandos:
  (nenhum)    Menu interativo
  --auto      Setup completo automático
  --full      Setup + testes completos (lint, types, coverage)
  --check     Verificar pré-requisitos
  --infra     Iniciar PostgreSQL + Redis
  --backend   Configurar backend
  --frontend  Configurar frontend
  --start     Iniciar backend + frontend
  --test      Testar endpoints da API
  --status    Ver status dos serviços
  --stop      Parar todos os serviços
  --clean     Parar e remover dados
  --help      Esta ajuda

Exemplos:
  $0              # Menu interativo
  $0 --auto       # Setup completo sem interação
  $0 --status     # Ver o que está rodando
EOF
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    echo "=== Dev Setup Log - $(date) ===" > "$LOG"
    
    # Verificar estrutura (exceto help)
    [[ "${1:-}" != "--help" && "${1:-}" != "-h" ]] && check_structure
    
    case "${1:-}" in
        --help|-h)   show_help ;;
        --auto|-y)   banner; run_full_setup ;;
        --full)      banner; run_full_setup; run_full_tests ;;
        --check)     banner; check_prerequisites ;;
        --infra)     banner; start_infra ;;
        --backend)   banner; setup_backend ;;
        --frontend)  banner; setup_frontend ;;
        --start)     banner; start_services ;;
        --test)      banner; test_api ;;
        --status)    banner; show_status ;;
        --stop)      banner; stop_all ;;
        --clean)     banner; clean_all ;;
        "")          banner; show_menu ;;
        *)           echo "Comando desconhecido: $1"; show_help; exit 1 ;;
    esac
}

main "$@"
