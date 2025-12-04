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

# Portas dos serviços
PORT_POSTGRES=5432
PORT_REDIS=6379
PORT_BACKEND=8000
PORT_FRONTEND=5173

# Contadores
STEPS_TOTAL=0
STEPS_PASSED=0
STEPS_FAILED=0
WARNINGS=0
AUTO_MODE=false
FULL_MODE=false

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
# FUNÇÕES DE VERIFICAÇÃO E INSTALAÇÃO
#-------------------------------------------------------------------------------

verify_project_structure() {
    # Verifica se os diretórios necessários existem
    local missing=()
    
    if [ ! -d "$BACKEND_DIR" ]; then
        missing+=("backend/")
    fi
    
    if [ ! -d "$FRONTEND_DIR" ]; then
        missing+=("frontend/")
    fi
    
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        missing+=("docker-compose.yml")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        print_error "Estrutura do projeto incompleta!"
        echo ""
        for item in "${missing[@]}"; do
            echo -e "  ${RED}✗${NC} Faltando: $item"
        done
        echo ""
        print_info "Certifique-se de estar no diretório raiz do projeto CRM Jurídico AI"
        print_info "e que todos os diretórios foram criados."
        exit 1
    fi
}

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

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/debian_version ]; then
        echo "debian"
    elif [ -f /etc/redhat-release ]; then
        echo "rhel"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

install_package() {
    local package="$1"
    local os=$(detect_os)
    
    print_info "Instalando $package..."
    
    case "$os" in
        ubuntu|debian|pop|linuxmint)
            if [ "$EUID" -eq 0 ]; then
                apt-get update -qq >> "$LOG_FILE" 2>&1
                apt-get install -y "$package" >> "$LOG_FILE" 2>&1
            else
                sudo apt-get update -qq >> "$LOG_FILE" 2>&1
                sudo apt-get install -y "$package" >> "$LOG_FILE" 2>&1
            fi
            ;;
        fedora)
            sudo dnf install -y "$package" >> "$LOG_FILE" 2>&1
            ;;
        rhel|centos)
            sudo yum install -y "$package" >> "$LOG_FILE" 2>&1
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm "$package" >> "$LOG_FILE" 2>&1
            ;;
        macos)
            if check_command brew; then
                brew install "$package" >> "$LOG_FILE" 2>&1
            else
                print_error "Homebrew não encontrado. Instale: https://brew.sh"
                return 1
            fi
            ;;
        *)
            print_error "Sistema operacional não suportado para instalação automática"
            return 1
            ;;
    esac
}

install_nodejs() {
    local os=$(detect_os)
    
    print_info "Instalando Node.js v20 LTS..."
    
    case "$os" in
        ubuntu|debian|pop|linuxmint)
            # Usar NodeSource para versão LTS
            if [ "$EUID" -eq 0 ]; then
                curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >> "$LOG_FILE" 2>&1
                apt-get install -y nodejs >> "$LOG_FILE" 2>&1
            else
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - >> "$LOG_FILE" 2>&1
                sudo apt-get install -y nodejs >> "$LOG_FILE" 2>&1
            fi
            ;;
        fedora)
            sudo dnf module install -y nodejs:20 >> "$LOG_FILE" 2>&1
            ;;
        rhel|centos)
            curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash - >> "$LOG_FILE" 2>&1
            sudo yum install -y nodejs >> "$LOG_FILE" 2>&1
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm nodejs npm >> "$LOG_FILE" 2>&1
            ;;
        macos)
            if check_command brew; then
                brew install node@20 >> "$LOG_FILE" 2>&1
            else
                print_error "Homebrew não encontrado. Instale: https://brew.sh"
                return 1
            fi
            ;;
        *)
            print_error "Sistema não suportado. Instale Node.js manualmente: https://nodejs.org"
            return 1
            ;;
    esac
}

install_docker() {
    local os=$(detect_os)
    
    print_info "Instalando Docker..."
    
    # Linux Mint usa repositório Ubuntu
    local docker_os="$os"
    if [ "$os" = "linuxmint" ]; then
        docker_os="ubuntu"
    fi
    
    case "$os" in
        ubuntu|debian|pop|linuxmint)
            # Instalar Docker oficial
            if [ "$EUID" -eq 0 ]; then
                apt-get update -qq >> "$LOG_FILE" 2>&1
                apt-get install -y ca-certificates curl gnupg >> "$LOG_FILE" 2>&1
                install -m 0755 -d /etc/apt/keyrings
                curl -fsSL https://download.docker.com/linux/$docker_os/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg >> "$LOG_FILE" 2>&1
                chmod a+r /etc/apt/keyrings/docker.gpg
                # Obter codename correto (Linux Mint usa base Ubuntu)
                local codename
                if [ "$os" = "linuxmint" ]; then
                    codename=$(grep UBUNTU_CODENAME /etc/os-release | cut -d= -f2)
                else
                    codename=$(. /etc/os-release && echo "$VERSION_CODENAME")
                fi
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$docker_os $codename stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
                apt-get update -qq >> "$LOG_FILE" 2>&1
                apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >> "$LOG_FILE" 2>&1
            else
                curl -fsSL https://get.docker.com | sudo sh >> "$LOG_FILE" 2>&1
                sudo usermod -aG docker $USER
                print_warning "Você precisará fazer logout/login para usar Docker sem sudo"
            fi
            ;;
        macos)
            print_error "No macOS, instale Docker Desktop: https://www.docker.com/products/docker-desktop"
            return 1
            ;;
        *)
            print_error "Sistema não suportado. Instale Docker manualmente: https://docs.docker.com/get-docker/"
            return 1
            ;;
    esac
}

check_prerequisites() {
    print_section "1. VERIFICANDO PRÉ-REQUISITOS"
    
    local all_ok=true
    local os=$(detect_os)
    print_info "Sistema detectado: $os"
    echo ""
    
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
        print_warning "Docker não encontrado. Tentando instalar..."
        if install_docker; then
            print_success "Docker instalado com sucesso"
        else
            print_error "Falha ao instalar Docker. Instale manualmente: https://docs.docker.com/get-docker/"
            all_ok=false
        fi
    fi
    
    # Docker Compose
    print_step "1.2" "Verificando Docker Compose..."
    if docker compose version &> /dev/null; then
        local compose_version=$(docker compose version --short 2>/dev/null || echo "v2+")
        print_success "Docker Compose $compose_version instalado"
    elif check_command docker-compose; then
        print_success "Docker Compose (legacy) instalado"
    else
        print_warning "Docker Compose vem incluído no Docker moderno"
        if check_command docker; then
            print_info "Tente: docker compose version"
        fi
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
        print_warning "Python não encontrado. Tentando instalar..."
        if install_package python3; then
            print_success "Python instalado"
        else
            print_error "Falha ao instalar Python"
            all_ok=false
        fi
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
        # Adicionar ao .bashrc se não estiver
        if ! grep -q 'poetry' ~/.bashrc 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        fi
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
            print_warning "Node.js v$node_version é antigo. Atualizando para v20 LTS..."
            if install_nodejs; then
                hash -r  # Refresh PATH
                print_success "Node.js atualizado"
            else
                print_warning "Não foi possível atualizar Node.js automaticamente"
            fi
        fi
    else
        print_warning "Node.js não encontrado. Instalando v20 LTS..."
        if install_nodejs; then
            hash -r  # Refresh PATH
            if check_command node; then
                local node_version=$(node --version | grep -oE '[0-9]+' | head -1)
                print_success "Node.js v$node_version instalado"
            else
                print_error "Node.js instalado mas não encontrado no PATH"
                print_info "Tente abrir um novo terminal e executar novamente"
                all_ok=false
            fi
        else
            print_error "Falha ao instalar Node.js. Instale manualmente: https://nodejs.org/"
            all_ok=false
        fi
    fi
    
    # npm (vem com Node.js)
    print_step "1.6" "Verificando npm..."
    if check_command npm; then
        local npm_version=$(npm --version)
        print_success "npm $npm_version instalado"
    else
        if check_command node; then
            print_warning "npm não encontrado. Tentando instalar..."
            install_package npm >> "$LOG_FILE" 2>&1 || true
            if check_command npm; then
                print_success "npm instalado"
            else
                print_error "npm não encontrado (deveria vir com Node.js)"
                all_ok=false
            fi
        else
            print_error "npm requer Node.js"
            all_ok=false
        fi
    fi
    
    # Git
    print_step "1.7" "Verificando Git..."
    if check_command git; then
        local git_version=$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        print_success "Git $git_version instalado"
    else
        print_warning "Git não encontrado. Instalando..."
        if install_package git; then
            print_success "Git instalado"
        else
            print_error "Falha ao instalar Git"
            all_ok=false
        fi
    fi
    
    # curl
    print_step "1.8" "Verificando curl..."
    if check_command curl; then
        print_success "curl instalado"
    else
        print_warning "curl não encontrado. Instalando..."
        if install_package curl; then
            print_success "curl instalado"
        else
            print_error "Falha ao instalar curl"
            all_ok=false
        fi
    fi
    
    # jq (opcional mas útil - instalar automaticamente)
    print_step "1.9" "Verificando jq..."
    if check_command jq; then
        print_success "jq instalado"
    else
        print_info "jq não encontrado. Instalando (opcional)..."
        if install_package jq >> "$LOG_FILE" 2>&1; then
            print_success "jq instalado"
        else
            print_warning "jq não instalado (opcional, usado para formatar JSON)"
        fi
    fi
    
    echo ""
    if [ "$all_ok" = false ]; then
        print_error "Alguns pré-requisitos não foram atendidos."
        print_info "Tente abrir um novo terminal e executar novamente."
        print_info "Ou instale manualmente os pacotes que falharam."
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
        attempt=$((attempt + 1))
        sleep 1
        echo -ne "${YELLOW}  ⏳${NC} Tentativa $attempt/$max_attempts...\r"
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL não iniciou a tempo"
        exit 1
    fi
    
    # Criar extensões PostgreSQL
    print_step "3.4" "Configurando extensões PostgreSQL..."
    docker compose exec -T db psql -U postgres -d crm_juridico -c "CREATE EXTENSION IF NOT EXISTS vector;" >> "$LOG_FILE" 2>&1 || true
    docker compose exec -T db psql -U postgres -d crm_juridico -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" >> "$LOG_FILE" 2>&1 || true
    docker compose exec -T db psql -U postgres -d crm_juridico -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" >> "$LOG_FILE" 2>&1 || true
    print_success "Extensões configuradas (vector, uuid-ossp, pg_trgm)"
    
    # Criar banco de testes
    print_step "3.5" "Criando banco de dados de testes..."
    docker compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS test_db;" >> "$LOG_FILE" 2>&1 || true
    docker compose exec -T db psql -U postgres -c "CREATE DATABASE test_db;" >> "$LOG_FILE" 2>&1
    docker compose exec -T db psql -U postgres -d test_db -c "CREATE EXTENSION IF NOT EXISTS vector;" >> "$LOG_FILE" 2>&1 || true
    docker compose exec -T db psql -U postgres -d test_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" >> "$LOG_FILE" 2>&1 || true
    docker compose exec -T db psql -U postgres -d test_db -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" >> "$LOG_FILE" 2>&1 || true
    print_success "Banco de testes criado com extensões"
    
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

check_port_available() {
    local port=$1
    if command -v lsof &> /dev/null; then
        ! lsof -i :$port &> /dev/null
    elif command -v netstat &> /dev/null; then
        ! netstat -tuln | grep -q ":$port "
    else
        # Assume disponível se não puder verificar
        return 0
    fi
}

start_services() {
    print_section "6. INICIANDO SERVIÇOS"
    
    # Matar processos anteriores
    print_step "6.0" "Parando processos anteriores..."
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 2
    print_success "Processos anteriores finalizados"
    
    # Verificar portas
    print_step "6.1" "Verificando disponibilidade de portas..."
    local ports_ok=true
    
    if ! check_port_available $PORT_BACKEND; then
        print_error "Porta $PORT_BACKEND (Backend) já está em uso!"
        print_info "Execute: lsof -i :$PORT_BACKEND  ou  kill \$(lsof -t -i:$PORT_BACKEND)"
        ports_ok=false
    fi
    
    if ! check_port_available $PORT_FRONTEND; then
        print_error "Porta $PORT_FRONTEND (Frontend) já está em uso!"
        print_info "Execute: lsof -i :$PORT_FRONTEND  ou  kill \$(lsof -t -i:$PORT_FRONTEND)"
        ports_ok=false
    fi
    
    if [ "$ports_ok" = false ]; then
        print_error "Libere as portas e execute novamente"
        return 1
    fi
    print_success "Portas disponíveis"
    
    # Iniciar Backend
    print_step "6.2" "Iniciando API Backend (porta $PORT_BACKEND)..."
    cd "$BACKEND_DIR"
    nohup poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT_BACKEND --reload >> "$PROJECT_ROOT/.backend.log" 2>&1 &
    local backend_pid=$!
    sleep 3
    
    if kill -0 $backend_pid 2>/dev/null; then
        print_success "Backend iniciado (PID: $backend_pid)"
    else
        print_error "Falha ao iniciar backend. Verifique .backend.log"
        print_info "Comando: tail -50 $PROJECT_ROOT/.backend.log"
    fi
    
    # Iniciar Frontend
    print_step "6.3" "Iniciando Frontend (porta $PORT_FRONTEND)..."
    cd "$FRONTEND_DIR"
    nohup npm run dev >> "$PROJECT_ROOT/.frontend.log" 2>&1 &
    local frontend_pid=$!
    sleep 3
    
    if kill -0 $frontend_pid 2>/dev/null; then
        print_success "Frontend iniciado (PID: $frontend_pid)"
    else
        print_error "Falha ao iniciar frontend. Verifique .frontend.log"
        print_info "Comando: tail -50 $PROJECT_ROOT/.frontend.log"
    fi
    
    # Aguardar serviços
    print_step "6.4" "Aguardando serviços estarem prontos..."
    sleep 5
}

test_api_endpoints() {
    print_section "7. TESTANDO ENDPOINTS DA API"
    
    local api_url="http://localhost:$PORT_BACKEND"
    
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
    # CNPJ válido para testes: 11222333000181 (dígitos verificadores corretos)
    local onboarding_response=$(curl -s -X POST "$api_url/api/v1/auth/onboarding" \
        -H "Content-Type: application/json" \
        -d '{
            "escritorio_nome": "Advocacia Teste Dev",
            "escritorio_cnpj": "11222333000181",
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
            # CPF válido para testes: 52998224725 (dígitos verificadores corretos)
            local cliente_response=$(curl -s -X POST "$api_url/api/v1/clientes" \
                -H "Authorization: Bearer $token" \
                -H "Content-Type: application/json" \
                -d '{
                    "tipo_pessoa": "fisica",
                    "nome": "Cliente Teste Dev",
                    "cpf": "52998224725",
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
    echo -e "${CYAN}  │${NC}  🗄️  PostgreSQL:     ${GREEN}localhost:$PORT_POSTGRES${NC}                                   ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  📦 Redis:          ${GREEN}localhost:$PORT_REDIS${NC}                                   ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  🚀 API Backend:    ${GREEN}http://localhost:$PORT_BACKEND${NC}                            ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  📚 API Docs:       ${GREEN}http://localhost:$PORT_BACKEND/docs${NC}                       ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  🎨 Frontend:       ${GREEN}http://localhost:$PORT_FRONTEND${NC}                            ${CYAN}│${NC}"
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
    echo "  --auto, -y      Execução automática sem prompts (instala tudo)"
    echo "  --full          Execução completa com lint, types e cobertura"
    echo "  --check         Apenas verifica pré-requisitos"
    echo "  --infra         Apenas inicia infraestrutura (DB + Redis)"
    echo "  --backend       Apenas configura backend"
    echo "  --frontend      Apenas configura frontend"
    echo "  --test          Apenas testa endpoints"
    echo "  --stop          Para todos os serviços"
    echo "  --clean         Para e remove todos os dados"
    echo "  --status        Mostra status dos serviços"
    echo ""
    echo "Sem argumentos: executa configuração completa (interativo)"
    echo ""
    echo "Exemplos:"
    echo "  $0              # Interativo, pede confirmação"
    echo "  $0 --auto       # Automático, instala tudo sem perguntar"
    echo "  $0 --full       # Completo com lint, types e cobertura"
    echo "  $0 --check      # Apenas verifica (e instala) dependências"
    echo "  $0 --status     # Verifica se serviços estão rodando"
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

show_status() {
    print_section "STATUS DOS SERVIÇOS"
    
    echo ""
    
    # PostgreSQL
    print_step "1" "PostgreSQL (porta $PORT_POSTGRES)..."
    if docker compose ps 2>/dev/null | grep -q "crm_juridico_db.*Up"; then
        print_success "PostgreSQL está rodando"
    else
        print_error "PostgreSQL não está rodando"
    fi
    
    # Redis
    print_step "2" "Redis (porta $PORT_REDIS)..."
    if docker compose ps 2>/dev/null | grep -q "crm_juridico_redis.*Up"; then
        print_success "Redis está rodando"
    else
        print_error "Redis não está rodando"
    fi
    
    # Backend
    print_step "3" "Backend API (porta $PORT_BACKEND)..."
    if curl -s "http://localhost:$PORT_BACKEND/health" 2>/dev/null | grep -q "healthy"; then
        print_success "Backend está respondendo"
    elif pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
        print_warning "Backend está rodando mas não respondendo"
    else
        print_error "Backend não está rodando"
    fi
    
    # Frontend
    print_step "4" "Frontend (porta $PORT_FRONTEND)..."
    if curl -s "http://localhost:$PORT_FRONTEND" > /dev/null 2>&1; then
        print_success "Frontend está respondendo"
    elif pgrep -f "vite" > /dev/null 2>&1; then
        print_warning "Frontend está rodando mas não respondendo"
    else
        print_error "Frontend não está rodando"
    fi
    
    echo ""
    echo -e "${CYAN}  ┌────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}  │                              URLS DOS SERVIÇOS                         │${NC}"
    echo -e "${CYAN}  ├────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}  │${NC}  🚀 API:      ${GREEN}http://localhost:$PORT_BACKEND${NC}                                  ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  📚 Docs:     ${GREEN}http://localhost:$PORT_BACKEND/docs${NC}                             ${CYAN}│${NC}"
    echo -e "${CYAN}  │${NC}  🎨 Frontend: ${GREEN}http://localhost:$PORT_FRONTEND${NC}                                  ${CYAN}│${NC}"
    echo -e "${CYAN}  └────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

run_full_tests() {
    print_section "EXECUÇÃO COMPLETA (LINT + TYPES + TESTES + COBERTURA)"
    
    local all_passed=true
    
    cd "$BACKEND_DIR"
    
    # Lint com Ruff
    print_step "1" "Executando Ruff (linter)..."
    if poetry run ruff check . >> "$LOG_FILE" 2>&1; then
        print_success "Ruff: Nenhum problema encontrado"
    else
        print_warning "Ruff: Alguns problemas encontrados (verifique log)"
        all_passed=false
    fi
    
    # Type checking com MyPy
    print_step "2" "Executando MyPy (type checker)..."
    if poetry run mypy app --ignore-missing-imports >> "$LOG_FILE" 2>&1; then
        print_success "MyPy: Tipos OK"
    else
        print_warning "MyPy: Alguns problemas de tipos (verifique log)"
        all_passed=false
    fi
    
    # Testes com cobertura
    print_step "3" "Executando testes com cobertura..."
    echo ""
    if poetry run pytest -v --cov=app --cov-report=term-missing --cov-report=html 2>&1 | tee -a "$LOG_FILE" | grep -E "^(tests/|PASSED|FAILED|ERROR|=====|TOTAL|Name)"; then
        echo ""
        print_success "Testes executados"
    else
        echo ""
        print_error "Alguns testes falharam"
        all_passed=false
    fi
    
    # Verificar cobertura mínima
    print_step "4" "Verificando cobertura mínima (70%)..."
    local coverage=$(poetry run coverage report 2>/dev/null | grep TOTAL | awk '{print $4}' | tr -d '%')
    if [ -n "$coverage" ] && [ "$coverage" -ge 70 ]; then
        print_success "Cobertura: ${coverage}% (acima de 70%)"
    elif [ -n "$coverage" ]; then
        print_warning "Cobertura: ${coverage}% (abaixo de 70%)"
        all_passed=false
    else
        print_info "Não foi possível verificar cobertura"
    fi
    
    # Frontend lint
    print_step "5" "Verificando Frontend (TypeScript)..."
    cd "$FRONTEND_DIR"
    if npm run build >> "$LOG_FILE" 2>&1; then
        print_success "Frontend: Build OK (sem erros TypeScript)"
    else
        print_warning "Frontend: Build com problemas"
        all_passed=false
    fi
    
    echo ""
    if [ "$all_passed" = true ]; then
        echo -e "${GREEN}  ════════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}    ✅ Todos os testes passaram! Pronto para deploy.${NC}"
        echo -e "${GREEN}  ════════════════════════════════════════════════════════════════════════${NC}"
    else
        echo -e "${YELLOW}  ════════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}    ⚠️  Alguns testes têm warnings. Revise antes do deploy.${NC}"
        echo -e "${YELLOW}  ════════════════════════════════════════════════════════════════════════${NC}"
    fi
    echo ""
    print_info "Relatório de cobertura HTML: backend/htmlcov/index.html"
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    # Inicializar log
    echo "=== Dev Setup Log - $(date) ===" > "$LOG_FILE"
    
    # Verificar estrutura do projeto (exceto para help)
    if [ "${1:-}" != "--help" ] && [ "${1:-}" != "-h" ]; then
        verify_project_structure
    fi
    
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --auto|-y)
            # Modo automático - executa tudo sem prompts
            AUTO_MODE=true
            print_banner
            check_prerequisites
            setup_environment_files
            start_infrastructure
            setup_backend
            setup_frontend
            start_services
            test_api_endpoints
            print_summary
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
        --status)
            print_banner
            cd "$PROJECT_ROOT"
            show_status
            ;;
        --full)
            # Modo completo - lint, types, cobertura
            FULL_MODE=true
            print_banner
            check_prerequisites
            setup_environment_files
            start_infrastructure
            setup_backend
            setup_frontend
            run_full_tests
            ;;
        "")
            # Execução completa interativa
            print_banner
            
            echo -e "${WHITE}  Este script irá:${NC}"
            echo -e "${DIM}    1. Verificar e instalar pré-requisitos (Docker, Python, Node.js, etc.)${NC}"
            echo -e "${DIM}    2. Configurar arquivos de ambiente (.env)${NC}"
            echo -e "${DIM}    3. Iniciar infraestrutura (PostgreSQL, Redis)${NC}"
            echo -e "${DIM}    4. Configurar e testar backend (FastAPI)${NC}"
            echo -e "${DIM}    5. Configurar e testar frontend (React)${NC}"
            echo -e "${DIM}    6. Iniciar todos os serviços${NC}"
            echo -e "${DIM}    7. Testar endpoints da API${NC}"
            echo ""
            echo -e "${CYAN}  💡 Dica: Use ${WHITE}--auto${CYAN} para execução sem prompts${NC}"
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
