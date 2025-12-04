#!/bin/bash

#===============================================================================
#
#   CRM JURÍDICO AI - Deploy & Setup GCP (Interativo)
#   
#   Script completo e INTERATIVO para configurar e fazer deploy no GCP.
#   Guia o usuário passo a passo com menus e validações.
#
#   Uso: ./scripts/deploy-gcp.sh
#
#===============================================================================

set -eo pipefail

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
# VARIÁVEIS GLOBAIS
#-------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_ROOT/.deploy-gcp.log"
CONFIG_FILE="$PROJECT_ROOT/.gcp-config"

# Configurações (serão preenchidas interativamente)
APP_NAME="crm-juridico"
PROJECT_ID=""
REGION=""
ENVIRONMENT=""

#-------------------------------------------------------------------------------
# FUNÇÕES DE UI
#-------------------------------------------------------------------------------

clear_screen() {
    clear
}

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                              ║"
    echo "║      ██████╗  ██████╗██████╗     ██████╗ ███████╗██████╗ ██╗      ██████╗   ║"
    echo "║     ██╔════╝ ██╔════╝██╔══██╗    ██╔══██╗██╔════╝██╔══██╗██║     ██╔═══██╗  ║"
    echo "║     ██║  ███╗██║     ██████╔╝    ██║  ██║█████╗  ██████╔╝██║     ██║   ██║  ║"
    echo "║     ██║   ██║██║     ██╔═══╝     ██║  ██║██╔══╝  ██╔═══╝ ██║     ██║   ██║  ║"
    echo "║     ╚██████╔╝╚██████╗██║         ██████╔╝███████╗██║     ███████╗╚██████╔╝  ║"
    echo "║      ╚═════╝  ╚═════╝╚═╝         ╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ║"
    echo "║                                                                              ║"
    echo -e "║                    ${WHITE}CRM Jurídico AI - Google Cloud Platform${CYAN}                 ║"
    echo "║                                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_header() {
    local title="$1"
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}  ${BOLD}$title${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() { echo -e "${GREEN}  ✓${NC} $1"; }
print_error() { echo -e "${RED}  ✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}  ⚠${NC} $1"; }
print_info() { echo -e "${CYAN}  ℹ${NC} $1"; }
print_step() { echo -e "${BLUE}  ➤${NC} $1"; }

print_box() {
    local message="$1"
    local color="${2:-$WHITE}"
    local len=${#message}
    local border=$(printf '─%.0s' $(seq 1 $((len + 4))))
    
    echo -e "${color}  ┌${border}┐${NC}"
    echo -e "${color}  │  ${message}  │${NC}"
    echo -e "${color}  └${border}┘${NC}"
}

# Função para pedir confirmação
confirm() {
    local message="$1"
    local default="${2:-n}"
    
    if [ "$default" = "y" ]; then
        local prompt="[Y/n]"
    else
        local prompt="[y/N]"
    fi
    
    echo -ne "${YELLOW}  ?${NC} $message $prompt "
    read -r response
    
    if [ -z "$response" ]; then
        response="$default"
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

# Função para pedir input
ask_input() {
    local message="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        echo -ne "${CYAN}  ?${NC} $message ${DIM}[$default]${NC}: "
    else
        echo -ne "${CYAN}  ?${NC} $message: "
    fi
    
    read -r response
    
    if [ -z "$response" ] && [ -n "$default" ]; then
        response="$default"
    fi
    
    eval "$var_name='$response'"
}

# Função para menu de seleção numérico (mais compatível)
select_menu() {
    local title="$1"
    shift
    local options=("$@")
    
    echo ""
    echo -e "${CYAN}  ?${NC} $title"
    echo ""
    
    for i in "${!options[@]}"; do
        local num=$((i + 1))
        echo -e "    ${GREEN}$num)${NC} ${options[$i]}"
    done
    
    echo ""
    echo -ne "    Digite o número da opção: "
    read -r choice
    
    # Validar entrada
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#options[@]} ]; then
        return $((choice - 1))
    else
        echo ""
        print_warning "Opção inválida. Tente novamente."
        select_menu "$title" "${options[@]}"
        return $?
    fi
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

#-------------------------------------------------------------------------------
# FUNÇÕES DE VERIFICAÇÃO
#-------------------------------------------------------------------------------

check_gcloud_installed() {
    if ! command -v gcloud &> /dev/null; then
        return 1
    fi
    return 0
}

check_docker_installed() {
    if ! command -v docker &> /dev/null; then
        return 1
    fi
    return 0
}

check_gcloud_authenticated() {
    local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)
    if [ -z "$account" ]; then
        return 1
    fi
    echo "$account"
    return 0
}

get_current_project() {
    gcloud config get-value project 2>/dev/null | grep -v "^$" || echo ""
}

# Carregar configuração salva
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        return 0
    fi
    return 1
}

# Salvar configuração
save_config() {
    cat > "$CONFIG_FILE" << EOF
# CRM Jurídico - GCP Configuration
# Gerado em: $(date)
PROJECT_ID="$PROJECT_ID"
REGION="$REGION"
ENVIRONMENT="$ENVIRONMENT"
EOF
}

#-------------------------------------------------------------------------------
# WIZARD: VERIFICAÇÃO DE PRÉ-REQUISITOS
#-------------------------------------------------------------------------------

wizard_prerequisites() {
    clear_screen
    print_banner
    print_header "1. VERIFICANDO PRÉ-REQUISITOS"
    
    local all_ok=true
    
    # Verificar gcloud
    print_step "Verificando Google Cloud SDK..."
    if check_gcloud_installed; then
        local gcloud_version=$(gcloud version --format="value(Google Cloud SDK)" 2>/dev/null | head -1)
        print_success "Google Cloud SDK instalado (v$gcloud_version)"
    else
        print_error "Google Cloud SDK não encontrado"
        echo ""
        echo -e "  ${DIM}Instale em: https://cloud.google.com/sdk/docs/install${NC}"
        echo ""
        all_ok=false
    fi
    
    # Verificar Docker
    print_step "Verificando Docker..."
    if check_docker_installed; then
        local docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        print_success "Docker instalado (v$docker_version)"
    else
        print_error "Docker não encontrado"
        echo ""
        echo -e "  ${DIM}Instale em: https://docs.docker.com/get-docker/${NC}"
        echo ""
        all_ok=false
    fi
    
    if [ "$all_ok" = false ]; then
        echo ""
        print_error "Instale os pré-requisitos acima e execute novamente."
        echo ""
        exit 1
    fi
    
    # Verificar autenticação
    print_step "Verificando autenticação GCP..."
    local account=$(check_gcloud_authenticated)
    
    if [ -n "$account" ]; then
        print_success "Autenticado como: $account"
    else
        print_warning "Não autenticado no GCP"
        echo ""
        
        if confirm "Deseja fazer login agora?"; then
            echo ""
            print_info "Abrindo navegador para autenticação..."
            gcloud auth login
            
            account=$(check_gcloud_authenticated)
            if [ -n "$account" ]; then
                print_success "Autenticado como: $account"
            else
                print_error "Falha na autenticação"
                exit 1
            fi
        else
            print_error "Autenticação necessária para continuar"
            exit 1
        fi
    fi
    
    echo ""
    print_success "Todos os pré-requisitos atendidos!"
    echo ""
    
    sleep 1
}

#-------------------------------------------------------------------------------
# WIZARD: CONFIGURAÇÃO DO PROJETO
#-------------------------------------------------------------------------------

wizard_project_config() {
    clear_screen
    print_banner
    print_header "2. CONFIGURAÇÃO DO PROJETO"
    
    # Tentar carregar config salva
    if load_config && [ -n "$PROJECT_ID" ]; then
        echo ""
        print_info "Configuração anterior encontrada:"
        echo ""
        echo -e "    Projeto:   ${GREEN}$PROJECT_ID${NC}"
        echo -e "    Região:    ${GREEN}$REGION${NC}"
        echo -e "    Ambiente:  ${GREEN}$ENVIRONMENT${NC}"
        echo ""
        
        if confirm "Usar esta configuração?" "y"; then
            return 0
        fi
    fi
    
    echo ""
    
    # Listar projetos existentes
    print_step "Buscando projetos GCP..."
    local projects_list=$(gcloud projects list --format="value(projectId)" 2>/dev/null | head -10)
    
    if [ -n "$projects_list" ]; then
        echo ""
        print_info "Projetos disponíveis:"
        echo ""
        
        local i=1
        while IFS= read -r proj; do
            echo -e "    ${GREEN}$i)${NC} $proj"
            ((i++))
        done <<< "$projects_list"
        echo -e "    ${GREEN}$i)${NC} ➕ Criar/usar outro projeto"
        
        echo ""
        echo -ne "    Digite o número do projeto: "
        read -r proj_choice
        
        local proj_count=$(echo "$projects_list" | wc -l)
        
        if [[ "$proj_choice" =~ ^[0-9]+$ ]] && [ "$proj_choice" -ge 1 ] && [ "$proj_choice" -le "$proj_count" ]; then
            PROJECT_ID=$(echo "$projects_list" | sed -n "${proj_choice}p")
        else
            ask_input "Digite o ID do projeto" "crm-juridico" PROJECT_ID
        fi
    else
        ask_input "Digite o ID do projeto GCP" "crm-juridico" PROJECT_ID
    fi
    
    # Configurar projeto
    print_step "Configurando projeto..."
    gcloud config set project "$PROJECT_ID" >> "$LOG_FILE" 2>&1 || true
    print_success "Projeto configurado: $PROJECT_ID"
    
    echo ""
    
    # Selecionar região
    print_info "Selecione a região:"
    
    local regions=(
        "southamerica-east1 (São Paulo, Brasil) ⭐ Recomendado"
        "us-central1 (Iowa, EUA)"
        "us-east1 (Carolina do Sul, EUA)"
        "europe-west1 (Bélgica, Europa)"
        "asia-east1 (Taiwan, Ásia)"
    )
    
    select_menu "Escolha a região:" "${regions[@]}"
    local region_idx=$?
    
    case $region_idx in
        0) REGION="southamerica-east1" ;;
        1) REGION="us-central1" ;;
        2) REGION="us-east1" ;;
        3) REGION="europe-west1" ;;
        4) REGION="asia-east1" ;;
    esac
    
    print_success "Região selecionada: $REGION"
    
    echo ""
    
    # Selecionar ambiente
    local envs=(
        "dev - Desenvolvimento (recursos mínimos, menor custo)"
        "prod - Produção (alta disponibilidade)"
    )
    
    select_menu "Escolha o ambiente:" "${envs[@]}"
    local env_idx=$?
    
    ENVIRONMENT=$([ $env_idx -eq 0 ] && echo "dev" || echo "prod")
    
    print_success "Ambiente selecionado: $ENVIRONMENT"
    
    # Salvar configuração
    save_config
    
    echo ""
    print_success "Configuração salva!"
    echo ""
    
    read -p "  Pressione ENTER para continuar..."
}

#-------------------------------------------------------------------------------
# WIZARD: SETUP INICIAL
#-------------------------------------------------------------------------------

wizard_setup() {
    clear_screen
    print_banner
    print_header "3. SETUP INICIAL DO GCP"
    
    echo ""
    print_info "Este passo irá configurar:"
    echo ""
    echo "    • APIs necessárias (Cloud Run, Storage, etc.)"
    echo "    • Artifact Registry para imagens Docker"
    echo "    • Service Account com permissões"
    echo "    • Secrets para credenciais"
    echo "    • Bucket de armazenamento"
    echo ""
    
    if ! confirm "Continuar com o setup?" "y"; then
        return 0
    fi
    
    echo ""
    
    local total_steps=7
    local current_step=0
    
    # 1. Habilitar APIs
    current_step=$((current_step + 1))
    print_step "[$current_step/$total_steps] Habilitando APIs (pode demorar ~2 min)..."
    
    local apis=(
        "run.googleapis.com"
        "artifactregistry.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "storage.googleapis.com"
        "cloudbuild.googleapis.com"
        "aiplatform.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        gcloud services enable "$api" >> "$LOG_FILE" 2>&1 || true
    done
    
    print_success "APIs habilitadas"
    
    # 2. Criar Artifact Registry
    current_step=$((current_step + 1))
    print_step "[$current_step/$total_steps] Criando Artifact Registry..."
    
    if ! gcloud artifacts repositories describe "$APP_NAME" --location="$REGION" &>/dev/null; then
        gcloud artifacts repositories create "$APP_NAME" \
            --repository-format=docker \
            --location="$REGION" \
            --description="CRM Jurídico AI" >> "$LOG_FILE" 2>&1 || true
    fi
    print_success "Artifact Registry configurado"
    
    # 3. Service Account
    current_step=$((current_step + 1))
    print_step "[$current_step/$total_steps] Configurando Service Account..."
    
    local SA_NAME="${APP_NAME}-cloudrun"
    local SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    if ! gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null 2>&1; then
        gcloud iam service-accounts create "$SA_NAME" \
            --display-name="CRM Jurídico Cloud Run" >> "$LOG_FILE" 2>&1 || true
    fi
    
    local roles=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/storage.objectAdmin"
        "roles/aiplatform.user"
        "roles/logging.logWriter"
    )
    
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="$role" \
            --quiet >> "$LOG_FILE" 2>&1 || true
    done
    
    print_success "Service Account configurado"
    
    # 4. Criar Secrets
    current_step=$((current_step + 1))
    print_step "[$current_step/$total_steps] Criando Secrets..."
    
    local JWT_SECRET=$(openssl rand -hex 32)
    local DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    
    if ! gcloud secrets describe "${APP_NAME}-jwt-secret" &>/dev/null 2>&1; then
        echo "$JWT_SECRET" | gcloud secrets create "${APP_NAME}-jwt-secret" --data-file=- >> "$LOG_FILE" 2>&1 || true
    fi
    
    if ! gcloud secrets describe "${APP_NAME}-db-password" &>/dev/null 2>&1; then
        echo "$DB_PASSWORD" | gcloud secrets create "${APP_NAME}-db-password" --data-file=- >> "$LOG_FILE" 2>&1 || true
    fi
    
    print_success "Secrets criados"
    
    # 5. Bucket
    current_step=$((current_step + 1))
    print_step "[$current_step/$total_steps] Criando Storage Bucket..."
    
    local BUCKET_NAME="${PROJECT_ID}-documentos"
    
    if ! gsutil ls -b "gs://$BUCKET_NAME" &>/dev/null 2>&1; then
        gsutil mb -l "$REGION" "gs://$BUCKET_NAME" >> "$LOG_FILE" 2>&1 || true
        gsutil uniformbucketlevelaccess set on "gs://$BUCKET_NAME" >> "$LOG_FILE" 2>&1 || true
    fi
    
    print_success "Bucket criado: $BUCKET_NAME"
    
    # 6. Docker auth
    current_step=$((current_step + 1))
    print_step "[$current_step/$total_steps] Configurando autenticação Docker..."
    
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >> "$LOG_FILE" 2>&1 || true
    
    print_success "Docker configurado"
    
    # 7. Verificar Gemini API Key
    current_step=$((current_step + 1))
    print_step "[$current_step/$total_steps] Verificando Gemini API Key..."
    
    if ! gcloud secrets describe "${APP_NAME}-gemini-api-key" &>/dev/null 2>&1; then
        print_warning "Secret da Gemini API não encontrado"
        echo ""
        
        if confirm "Você tem uma API Key da Gemini?"; then
            echo ""
            echo -ne "${CYAN}  ?${NC} Cole sua Gemini API Key: "
            read -rs GEMINI_KEY
            echo ""
            
            if [ -n "$GEMINI_KEY" ]; then
                echo "$GEMINI_KEY" | gcloud secrets create "${APP_NAME}-gemini-api-key" --data-file=- >> "$LOG_FILE" 2>&1 || true
                print_success "Gemini API Key salva"
            fi
        else
            print_info "Você pode adicionar depois com:"
            echo -e "    ${DIM}echo 'SUA_KEY' | gcloud secrets create ${APP_NAME}-gemini-api-key --data-file=-${NC}"
        fi
    else
        print_success "Gemini API Key já configurada"
    fi
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ SETUP CONCLUÍDO!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Mostrar credenciais
    print_box "CREDENCIAIS GERADAS - SALVE EM LOCAL SEGURO!" "$YELLOW"
    echo ""
    echo -e "    DB_PASSWORD: ${WHITE}$DB_PASSWORD${NC}"
    echo -e "    JWT_SECRET:  ${WHITE}${JWT_SECRET:0:20}...${NC}"
    echo ""
    
    echo ""
    read -p "  Pressione ENTER para continuar..."
}

#-------------------------------------------------------------------------------
# WIZARD: DEPLOY
#-------------------------------------------------------------------------------

wizard_deploy() {
    clear_screen
    print_banner
    print_header "4. DEPLOY DA APLICAÇÃO"
    
    local REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}"
    local TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    
    echo ""
    print_info "Configuração do deploy:"
    echo ""
    echo -e "    Projeto:   ${GREEN}$PROJECT_ID${NC}"
    echo -e "    Região:    ${GREEN}$REGION${NC}"
    echo -e "    Ambiente:  ${GREEN}$ENVIRONMENT${NC}"
    echo -e "    Registry:  ${GREEN}$REGISTRY${NC}"
    echo ""
    
    if ! confirm "Iniciar deploy?" "y"; then
        return 0
    fi
    
    echo ""
    
    cd "$PROJECT_ROOT"
    
    local total_steps=5
    local current_step=0
    
    # 1. Build Backend
    current_step=$((current_step + 1))
    echo ""
    print_step "[$current_step/$total_steps] Building Backend..."
    print_info "Isso pode demorar alguns minutos na primeira vez..."
    echo ""
    
    if docker build \
        -t "${REGISTRY}/api:${TIMESTAMP}" \
        -t "${REGISTRY}/api:latest" \
        ./backend >> "$LOG_FILE" 2>&1; then
        print_success "Backend build completo"
    else
        print_error "Falha no build do backend. Verifique $LOG_FILE"
        return 1
    fi
    
    # 2. Build Frontend
    current_step=$((current_step + 1))
    echo ""
    print_step "[$current_step/$total_steps] Building Frontend..."
    
    # Criar .env.production
    cat > frontend/.env.production << EOF
VITE_API_URL=https://${APP_NAME}-api-${REGION:0:2}.a.run.app
VITE_ENVIRONMENT=$ENVIRONMENT
EOF
    
    if docker build \
        -t "${REGISTRY}/frontend:${TIMESTAMP}" \
        -t "${REGISTRY}/frontend:latest" \
        ./frontend >> "$LOG_FILE" 2>&1; then
        print_success "Frontend build completo"
    else
        print_error "Falha no build do frontend. Verifique $LOG_FILE"
        return 1
    fi
    
    # 3. Push Images
    current_step=$((current_step + 1))
    echo ""
    print_step "[$current_step/$total_steps] Enviando imagens para o cloud..."
    
    docker push "${REGISTRY}/api:${TIMESTAMP}" >> "$LOG_FILE" 2>&1 || true
    docker push "${REGISTRY}/api:latest" >> "$LOG_FILE" 2>&1 || true
    docker push "${REGISTRY}/frontend:${TIMESTAMP}" >> "$LOG_FILE" 2>&1 || true
    docker push "${REGISTRY}/frontend:latest" >> "$LOG_FILE" 2>&1 || true
    
    print_success "Imagens enviadas"
    
    # 4. Deploy API
    current_step=$((current_step + 1))
    echo ""
    print_step "[$current_step/$total_steps] Deployando API no Cloud Run..."
    
    local min_instances=0
    local max_instances=2
    local memory="512Mi"
    local cpu="1"
    
    if [ "$ENVIRONMENT" = "prod" ]; then
        min_instances=1
        max_instances=10
        memory="2Gi"
        cpu="2"
    fi
    
    if gcloud run deploy "${APP_NAME}-api" \
        --image "${REGISTRY}/api:${TIMESTAMP}" \
        --region "$REGION" \
        --platform managed \
        --allow-unauthenticated \
        --service-account "${APP_NAME}-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com" \
        --set-secrets "SECRET_KEY=${APP_NAME}-jwt-secret:latest" \
        --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=$ENVIRONMENT,GCS_BUCKET_DOCUMENTOS=${PROJECT_ID}-documentos" \
        --min-instances "$min_instances" \
        --max-instances "$max_instances" \
        --memory "$memory" \
        --cpu "$cpu" \
        --timeout 300 >> "$LOG_FILE" 2>&1; then
        
        local API_URL=$(gcloud run services describe "${APP_NAME}-api" --region "$REGION" --format 'value(status.url)')
        print_success "API deployed: $API_URL"
    else
        print_error "Falha no deploy da API"
        return 1
    fi
    
    # 5. Deploy Frontend
    current_step=$((current_step + 1))
    echo ""
    print_step "[$current_step/$total_steps] Deployando Frontend no Cloud Run..."
    
    local frontend_max=$([ "$ENVIRONMENT" = "prod" ] && echo "5" || echo "2")
    
    if gcloud run deploy "${APP_NAME}-frontend" \
        --image "${REGISTRY}/frontend:${TIMESTAMP}" \
        --region "$REGION" \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "VITE_API_URL=$API_URL" \
        --min-instances "$min_instances" \
        --max-instances "$frontend_max" \
        --memory 256Mi \
        --cpu 1 >> "$LOG_FILE" 2>&1; then
        
        local FRONTEND_URL=$(gcloud run services describe "${APP_NAME}-frontend" --region "$REGION" --format 'value(status.url)')
        print_success "Frontend deployed: $FRONTEND_URL"
    else
        print_error "Falha no deploy do frontend"
        return 1
    fi
    
    # Resultado final
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  🎉 DEPLOY CONCLUÍDO COM SUCESSO!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${WHITE}URLs da aplicação:${NC}"
    echo ""
    echo -e "    🌐 Frontend: ${GREEN}$FRONTEND_URL${NC}"
    echo -e "    🔧 API:      ${GREEN}$API_URL${NC}"
    echo -e "    📚 Docs:     ${GREEN}$API_URL/docs${NC}"
    echo ""
    
    echo ""
    read -p "  Pressione ENTER para voltar ao menu..."
}

#-------------------------------------------------------------------------------
# WIZARD: STATUS
#-------------------------------------------------------------------------------

wizard_status() {
    clear_screen
    print_banner
    print_header "STATUS DOS SERVIÇOS"
    
    echo ""
    print_info "Buscando informações..."
    echo ""
    
    # Cloud Run Services
    echo -e "${BLUE}  Cloud Run Services:${NC}"
    echo ""
    
    gcloud run services list --region "$REGION" \
        --format="table(SERVICE,REGION,URL)" 2>/dev/null \
        | sed 's/^/    /' || echo "    Nenhum serviço encontrado"
    
    echo ""
    
    # Últimas imagens
    echo -e "${BLUE}  Últimas Imagens:${NC}"
    echo ""
    
    gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}" \
        --format="table(IMAGE,CREATE_TIME)" \
        --sort-by="~CREATE_TIME" \
        --limit=5 2>/dev/null \
        | sed 's/^/    /' || echo "    Nenhuma imagem encontrada"
    
    echo ""
    read -p "  Pressione ENTER para voltar ao menu..."
}

#-------------------------------------------------------------------------------
# WIZARD: LOGS
#-------------------------------------------------------------------------------

wizard_logs() {
    clear_screen
    print_banner
    print_header "VISUALIZAR LOGS"
    
    echo ""
    
    local services=(
        "api - Logs da API Backend"
        "frontend - Logs do Frontend"
        "worker - Logs do Celery Worker"
        "← Voltar ao menu"
    )
    
    select_menu "Qual serviço deseja ver?" "${services[@]}"
    local idx=$?
    
    if [ $idx -eq 3 ]; then
        return 0
    fi
    
    local service_names=("api" "frontend" "worker")
    local service="${service_names[$idx]}"
    
    echo ""
    print_info "Mostrando últimos logs de ${APP_NAME}-${service}"
    print_info "Pressione Ctrl+C para sair"
    echo ""
    
    gcloud run services logs read "${APP_NAME}-${service}" \
        --region "$REGION" \
        --limit 50 2>/dev/null || print_warning "Serviço não encontrado ou sem logs"
    
    echo ""
    read -p "  Pressione ENTER para voltar..."
}

#-------------------------------------------------------------------------------
# WIZARD: DESTROY
#-------------------------------------------------------------------------------

wizard_destroy() {
    clear_screen
    print_banner
    print_header "⚠️  REMOVER RECURSOS"
    
    echo ""
    echo -e "${RED}  ╔════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}  ║                           ATENÇÃO!                                     ║${NC}"
    echo -e "${RED}  ║                                                                        ║${NC}"
    echo -e "${RED}  ║   Esta ação irá REMOVER PERMANENTEMENTE todos os recursos do          ║${NC}"
    echo -e "${RED}  ║   CRM Jurídico no Google Cloud Platform.                              ║${NC}"
    echo -e "${RED}  ║                                                                        ║${NC}"
    echo -e "${RED}  ╚════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -ne "${YELLOW}  ?${NC} Digite ${RED}DESTRUIR${NC} para confirmar: "
    read -r confirm_text
    
    if [ "$confirm_text" != "DESTRUIR" ]; then
        print_info "Operação cancelada"
        sleep 1
        return 0
    fi
    
    echo ""
    
    # Remover services
    print_step "Removendo Cloud Run services..."
    for service in api frontend worker; do
        gcloud run services delete "${APP_NAME}-${service}" --region "$REGION" --quiet 2>/dev/null || true
    done
    print_success "Services removidos"
    
    # Remover imagens
    print_step "Removendo Artifact Registry..."
    gcloud artifacts repositories delete "$APP_NAME" --location="$REGION" --quiet 2>/dev/null || true
    print_success "Registry removido"
    
    # Remover secrets
    print_step "Removendo Secrets..."
    for secret in jwt-secret db-password gemini-api-key; do
        gcloud secrets delete "${APP_NAME}-${secret}" --quiet 2>/dev/null || true
    done
    print_success "Secrets removidos"
    
    # Remover config local
    rm -f "$CONFIG_FILE"
    
    echo ""
    print_success "Todos os recursos foram removidos!"
    echo ""
    
    print_warning "O bucket de storage NÃO foi removido para preservar documentos."
    echo -e "    ${DIM}Para remover: gsutil rm -r gs://${PROJECT_ID}-documentos${NC}"
    echo ""
    
    read -p "  Pressione ENTER para sair..."
}

#-------------------------------------------------------------------------------
# MENU PRINCIPAL
#-------------------------------------------------------------------------------

main_menu() {
    while true; do
        clear_screen
        print_banner
        
        # Mostrar config atual se existir
        if [ -n "$PROJECT_ID" ]; then
            echo -e "  ${DIM}Projeto: $PROJECT_ID | Região: $REGION | Ambiente: $ENVIRONMENT${NC}"
        fi
        
        echo ""
        echo -e "${WHITE}  O que você deseja fazer?${NC}"
        echo ""
        
        local options=(
            "🚀 Setup Inicial - Configurar projeto GCP pela primeira vez"
            "📦 Deploy - Fazer deploy da aplicação"
            "📊 Status - Ver status dos serviços"
            "📋 Logs - Visualizar logs"
            "⚙️  Reconfigurar - Alterar projeto/região/ambiente"
            "🗑️  Remover Recursos - Destruir todos os recursos"
            "❌ Sair"
        )
        
        select_menu "Selecione uma opção:" "${options[@]}"
        local choice=$?
        
        case $choice in
            0) # Setup
                wizard_prerequisites
                wizard_project_config
                wizard_setup
                ;;
            1) # Deploy
                if [ -z "$PROJECT_ID" ]; then
                    wizard_prerequisites
                    wizard_project_config
                fi
                wizard_deploy
                ;;
            2) # Status
                if [ -z "$PROJECT_ID" ]; then
                    print_error "Configure o projeto primeiro"
                    sleep 1
                else
                    wizard_status
                fi
                ;;
            3) # Logs
                if [ -z "$PROJECT_ID" ]; then
                    print_error "Configure o projeto primeiro"
                    sleep 1
                else
                    wizard_logs
                fi
                ;;
            4) # Reconfigurar
                wizard_project_config
                ;;
            5) # Destroy
                if [ -z "$PROJECT_ID" ]; then
                    print_error "Configure o projeto primeiro"
                    sleep 1
                else
                    wizard_destroy
                fi
                ;;
            6) # Sair
                clear_screen
                echo ""
                print_info "Até logo! 👋"
                echo ""
                exit 0
                ;;
        esac
    done
}

#-------------------------------------------------------------------------------
# PROCESSAMENTO DE ARGUMENTOS
#-------------------------------------------------------------------------------

show_help() {
    echo "CRM Jurídico AI - Deploy GCP (Interativo)"
    echo ""
    echo "Uso: $0 [comando]"
    echo ""
    echo "Sem argumentos: abre o menu interativo"
    echo ""
    echo "Comandos rápidos:"
    echo "  setup     Executar setup inicial"
    echo "  deploy    Fazer deploy direto"
    echo "  status    Ver status dos serviços"
    echo "  logs      Ver logs"
    echo "  help      Mostrar esta ajuda"
    echo ""
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    # Inicializar log
    echo "=== Deploy GCP Log - $(date) ===" > "$LOG_FILE"
    
    # Carregar config se existir
    load_config || true
    
    # Processar argumentos
    case "${1:-}" in
        setup)
            wizard_prerequisites
            wizard_project_config
            wizard_setup
            ;;
        deploy)
            if [ -z "$PROJECT_ID" ]; then
                wizard_prerequisites
                wizard_project_config
            fi
            wizard_deploy
            ;;
        status)
            if [ -z "$PROJECT_ID" ]; then
                print_error "Execute ./scripts/deploy-gcp.sh primeiro para configurar"
                exit 1
            fi
            wizard_status
            ;;
        logs)
            if [ -z "$PROJECT_ID" ]; then
                print_error "Execute ./scripts/deploy-gcp.sh primeiro para configurar"
                exit 1
            fi
            wizard_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            main_menu
            ;;
        *)
            echo "Comando desconhecido: $1"
            show_help
            exit 1
            ;;
    esac
}

# Capturar Ctrl+C
trap 'echo ""; print_info "Operação cancelada"; exit 0' INT

main "$@"
