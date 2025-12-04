#!/bin/bash

#===============================================================================
#
#   CRM JURÍDICO AI - Assistente de Deploy para Google Cloud Platform
#   
#   Este script guia você passo a passo na configuração e deploy do
#   CRM Jurídico AI no Google Cloud Platform.
#
#   É TOTALMENTE INTERATIVO e DIDÁTICO - explica cada passo!
#
#   Requisitos:
#   - Google Cloud SDK (gcloud) instalado
#   - Docker instalado
#   - Conta Google Cloud com billing habilitado
#
#   Uso: ./scripts/deploy-gcp.sh
#
#===============================================================================

set -eo pipefail

#-------------------------------------------------------------------------------
# CONFIGURAÇÃO DE CORES
#-------------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
UNDERLINE='\033[4m'

#-------------------------------------------------------------------------------
# VARIÁVEIS GLOBAIS
#-------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/.gcp-config"
LOG_FILE="$PROJECT_ROOT/.deploy-gcp.log"

APP_NAME="crm-juridico"
PROJECT_ID=""
REGION=""
ENVIRONMENT=""

#-------------------------------------------------------------------------------
# FUNÇÕES DE INTERFACE
#-------------------------------------------------------------------------------

clear_screen() {
    printf "\033c"
}

# Imprime o banner principal
print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║       ██████╗ ██████╗██████╗     ██████╗ ███████╗██████╗ ██╗  ██████╗   ║
    ║      ██╔════╝██╔════╝██╔══██╗    ██╔══██╗██╔════╝██╔══██╗██║ ██╔═══██╗  ║
    ║      ██║  ███╗██║     ██████╔╝    ██║  ██║█████╗  ██████╔╝██║ ██║   ██║  ║
    ║      ██║   ██║██║     ██╔═══╝     ██║  ██║██╔══╝  ██╔═══╝ ██║ ██║   ██║  ║
    ║      ╚██████╔╝╚██████╗██║         ██████╔╝███████╗██║     ███████████╔╝  ║
    ║       ╚═════╝  ╚═════╝╚═╝         ╚═════╝ ╚══════╝╚═╝     ╚══════╝═══╝   ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo -e "              ${WHITE}CRM Jurídico AI - Assistente de Deploy GCP${NC}"
    echo -e "              ${DIM}Configuração guiada passo a passo${NC}"
    echo ""
}

# Imprime título de seção
print_section() {
    local num="$1"
    local title="$2"
    local desc="$3"
    
    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}  ${WHITE}${BOLD}PASSO $num: $title${NC}"
    echo -e "${PURPLE}╠══════════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${PURPLE}║${NC}  ${DIM}$desc${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Imprime explicação didática
print_explanation() {
    echo -e "${CYAN}  ┌─────────────────────────────────────────────────────────────────────────────┐${NC}"
    while IFS= read -r line; do
        echo -e "${CYAN}  │${NC} $line"
    done
    echo -e "${CYAN}  └─────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

# Indicadores de status
print_checking() { echo -ne "${YELLOW}  ⏳${NC} $1..."; }
print_ok() { echo -e "\r${GREEN}  ✓${NC} $1"; }
print_fail() { echo -e "\r${RED}  ✗${NC} $1"; }
print_skip() { echo -e "\r${GRAY}  ○${NC} $1 ${DIM}(pulado)${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠${NC} $1"; }
print_info() { echo -e "${CYAN}  ℹ${NC} $1"; }
print_step() { echo -e "${BLUE}  ➤${NC} $1"; }
print_substep() { echo -e "${DIM}    └─${NC} $1"; }

# Caixa de destaque
print_box() {
    local title="$1"
    local color="$2"
    shift 2
    local lines=("$@")
    
    echo ""
    echo -e "${color}  ┌─── $title ───${NC}"
    for line in "${lines[@]}"; do
        echo -e "${color}  │${NC} $line"
    done
    echo -e "${color}  └$( printf '─%.0s' {1..70} )${NC}"
    echo ""
}

# Pede confirmação do usuário
ask_confirm() {
    local message="$1"
    local default="${2:-n}"
    
    local prompt="[y/N]"
    [ "$default" = "y" ] && prompt="[Y/n]"
    
    echo ""
    echo -ne "${YELLOW}  ?${NC} $message $prompt "
    read -r response
    
    [ -z "$response" ] && response="$default"
    [[ "$response" =~ ^[Yy]$ ]]
}

# Pede input do usuário
ask_input() {
    local message="$1"
    local default="$2"
    local var_name="$3"
    local validation="$4"
    
    while true; do
        if [ -n "$default" ]; then
            echo -ne "${CYAN}  ?${NC} $message ${DIM}[$default]${NC}: "
        else
            echo -ne "${CYAN}  ?${NC} $message: "
        fi
        
        read -r response
        [ -z "$response" ] && response="$default"
        
        # Validação se especificada
        if [ -n "$validation" ]; then
            case "$validation" in
                "project_id")
                    if [[ "$response" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
                        break
                    else
                        print_warn "ID do projeto deve ter 6-30 caracteres, começar com letra, apenas minúsculas, números e hífens"
                    fi
                    ;;
                "not_empty")
                    if [ -n "$response" ]; then
                        break
                    else
                        print_warn "Este campo é obrigatório"
                    fi
                    ;;
                *)
                    break
                    ;;
            esac
        else
            break
        fi
    done
    
    eval "$var_name='$response'"
}

# Menu de seleção numérico
select_menu() {
    local title="$1"
    shift
    local options=("$@")
    
    echo ""
    echo -e "${WHITE}  $title${NC}"
    echo ""
    
    for i in "${!options[@]}"; do
        echo -e "    ${GREEN}$((i + 1)))${NC} ${options[$i]}"
    done
    
    echo ""
    while true; do
        echo -ne "    Escolha uma opção ${DIM}[1-${#options[@]}]${NC}: "
        read -r choice
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#options[@]} ]; then
            return $((choice - 1))
        else
            print_warn "Opção inválida. Digite um número de 1 a ${#options[@]}"
        fi
    done
}

# Aguarda usuário pressionar ENTER
wait_enter() {
    local message="${1:-Pressione ENTER para continuar...}"
    echo ""
    echo -ne "${DIM}  $message${NC}"
    read -r
}

# Log para arquivo
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

#-------------------------------------------------------------------------------
# FUNÇÕES DE VALIDAÇÃO
#-------------------------------------------------------------------------------

# Verifica se um comando existe
check_command() {
    command -v "$1" &> /dev/null
}

# Verifica versão do comando
get_version() {
    local cmd="$1"
    case "$cmd" in
        gcloud)
            gcloud version 2>/dev/null | grep "Google Cloud SDK" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
            ;;
        docker)
            docker --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

# Valida se projeto existe no GCP
validate_project() {
    local project="$1"
    gcloud projects describe "$project" &>/dev/null 2>&1
}

# Verifica se API está habilitada
check_api_enabled() {
    local api="$1"
    gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"
}

# Verifica se secret existe
check_secret_exists() {
    local secret="$1"
    gcloud secrets describe "$secret" &>/dev/null 2>&1
}

# Verifica se bucket existe
check_bucket_exists() {
    local bucket="$1"
    gsutil ls -b "gs://$bucket" &>/dev/null 2>&1
}

# Verifica se service account existe
check_sa_exists() {
    local sa_email="$1"
    gcloud iam service-accounts describe "$sa_email" &>/dev/null 2>&1
}

# Verifica se artifact registry existe
check_registry_exists() {
    local name="$1"
    local location="$2"
    gcloud artifacts repositories describe "$name" --location="$location" &>/dev/null 2>&1
}

# Verifica se Cloud Run service existe
check_service_exists() {
    local name="$1"
    local region="$2"
    gcloud run services describe "$name" --region="$region" &>/dev/null 2>&1
}

#-------------------------------------------------------------------------------
# FUNÇÕES DE CONFIGURAÇÃO
#-------------------------------------------------------------------------------

# Carrega configuração salva
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        return 0
    fi
    return 1
}

# Salva configuração
save_config() {
    cat > "$CONFIG_FILE" << EOF
# Configuração do Deploy GCP - CRM Jurídico AI
# Gerado em: $(date)
# NÃO edite manualmente!

PROJECT_ID="$PROJECT_ID"
REGION="$REGION"
ENVIRONMENT="$ENVIRONMENT"
EOF
    log "Configuração salva em $CONFIG_FILE"
}

#-------------------------------------------------------------------------------
# PASSO 1: VERIFICAR PRÉ-REQUISITOS
#-------------------------------------------------------------------------------

step_prerequisites() {
    clear_screen
    print_banner
    
    print_section "1" "VERIFICAÇÃO DE PRÉ-REQUISITOS" \
        "Vamos verificar se você tem tudo necessário para o deploy"
    
    print_explanation << 'EOF'
  Para fazer deploy no Google Cloud, você precisa de:
  
  1. Google Cloud SDK (gcloud) - Ferramenta de linha de comando do GCP
  2. Docker - Para construir as imagens dos containers
  3. Conta GCP autenticada - Com permissões de administrador
  4. Billing habilitado - Para criar recursos pagos
EOF
    
    local all_ok=true
    local issues=()
    
    # Verificar gcloud
    print_checking "Verificando Google Cloud SDK"
    if check_command gcloud; then
        local version=$(get_version gcloud)
        print_ok "Google Cloud SDK v$version instalado"
        log "gcloud version: $version"
    else
        print_fail "Google Cloud SDK NÃO encontrado"
        issues+=("Instale o Google Cloud SDK: https://cloud.google.com/sdk/docs/install")
        all_ok=false
    fi
    
    # Verificar Docker
    print_checking "Verificando Docker"
    if check_command docker; then
        local version=$(get_version docker)
        print_ok "Docker v$version instalado"
        log "docker version: $version"
        
        # Verificar se Docker está rodando
        print_checking "Verificando se Docker está ativo"
        if docker info &>/dev/null; then
            print_ok "Docker está rodando"
        else
            print_fail "Docker instalado mas não está rodando"
            issues+=("Inicie o Docker: sudo systemctl start docker")
            all_ok=false
        fi
    else
        print_fail "Docker NÃO encontrado"
        issues+=("Instale o Docker: https://docs.docker.com/get-docker/")
        all_ok=false
    fi
    
    # Verificar autenticação GCP
    if [ "$all_ok" = true ]; then
        print_checking "Verificando autenticação no GCP"
        local account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
        
        if [ -n "$account" ]; then
            print_ok "Autenticado como: $account"
            log "Authenticated as: $account"
        else
            print_warn "Não autenticado no Google Cloud"
            echo ""
            
            print_explanation << 'EOF'
  Você precisa fazer login na sua conta Google Cloud.
  Uma janela do navegador será aberta para autenticação.
EOF
            
            if ask_confirm "Fazer login agora?"; then
                echo ""
                print_step "Abrindo navegador para autenticação..."
                
                if gcloud auth login 2>&1 | tee -a "$LOG_FILE"; then
                    account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
                    if [ -n "$account" ]; then
                        print_ok "Login realizado com sucesso!"
                        print_substep "Conta: $account"
                    else
                        print_fail "Falha no login"
                        all_ok=false
                    fi
                else
                    print_fail "Erro durante autenticação"
                    all_ok=false
                fi
            else
                issues+=("Faça login: gcloud auth login")
                all_ok=false
            fi
        fi
    fi
    
    # Mostrar problemas encontrados
    if [ "$all_ok" = false ]; then
        echo ""
        print_box "AÇÕES NECESSÁRIAS" "$RED" "${issues[@]}"
        echo ""
        print_fail "Corrija os problemas acima e execute novamente."
        exit 1
    fi
    
    echo ""
    print_box "PRÉ-REQUISITOS" "$GREEN" \
        "✓ Todos os pré-requisitos foram verificados!" \
        "  Você está pronto para configurar o projeto."
    
    wait_enter
}

#-------------------------------------------------------------------------------
# PASSO 2: CONFIGURAR PROJETO
#-------------------------------------------------------------------------------

step_configure_project() {
    clear_screen
    print_banner
    
    print_section "2" "CONFIGURAÇÃO DO PROJETO" \
        "Vamos definir o projeto GCP, região e ambiente"
    
    # Verificar configuração existente
    if load_config && [ -n "$PROJECT_ID" ]; then
        print_box "CONFIGURAÇÃO ENCONTRADA" "$CYAN" \
            "Projeto:  $PROJECT_ID" \
            "Região:   $REGION" \
            "Ambiente: $ENVIRONMENT"
        
        if ask_confirm "Usar esta configuração?" "y"; then
            return 0
        fi
    fi
    
    # PROJETO
    print_explanation << 'EOF'
  Um PROJETO GCP é um container para todos os seus recursos.
  
  - Se você já tem um projeto, pode selecioná-lo
  - Se não tem, podemos criar um novo
  
  O ID do projeto deve ser único globalmente e ter entre 6-30 caracteres.
  Exemplo: meu-crm-juridico, advocacia-silva-crm
EOF
    
    # Listar projetos existentes
    print_step "Buscando seus projetos GCP..."
    local projects=$(gcloud projects list --format="value(projectId)" 2>/dev/null | head -10)
    
    if [ -n "$projects" ]; then
        echo ""
        print_info "Projetos encontrados na sua conta:"
        echo ""
        
        local proj_array=()
        local i=1
        while IFS= read -r proj; do
            echo -e "    ${GREEN}$i)${NC} $proj"
            proj_array+=("$proj")
            ((i++))
        done <<< "$projects"
        echo -e "    ${GREEN}$i)${NC} ${WHITE}Criar/usar outro projeto${NC}"
        
        echo ""
        echo -ne "    Escolha uma opção: "
        read -r proj_choice
        
        if [[ "$proj_choice" =~ ^[0-9]+$ ]] && [ "$proj_choice" -ge 1 ] && [ "$proj_choice" -lt "$i" ]; then
            PROJECT_ID="${proj_array[$((proj_choice - 1))]}"
            print_ok "Projeto selecionado: $PROJECT_ID"
        else
            ask_input "Digite o ID do projeto" "crm-juridico-$(date +%Y)" PROJECT_ID "project_id"
        fi
    else
        print_info "Nenhum projeto encontrado. Vamos criar um novo."
        ask_input "Digite o ID do novo projeto" "crm-juridico-$(date +%Y)" PROJECT_ID "project_id"
    fi
    
    # Validar/criar projeto
    print_checking "Verificando projeto $PROJECT_ID"
    if validate_project "$PROJECT_ID"; then
        print_ok "Projeto existe"
    else
        print_warn "Projeto não encontrado"
        
        if ask_confirm "Deseja criar o projeto '$PROJECT_ID'?"; then
            print_step "Criando projeto..."
            if gcloud projects create "$PROJECT_ID" --name="CRM Jurídico AI" 2>&1 | tee -a "$LOG_FILE"; then
                print_ok "Projeto criado com sucesso!"
            else
                print_fail "Erro ao criar projeto. Verifique se o ID é único."
                exit 1
            fi
        else
            print_fail "Projeto necessário para continuar."
            exit 1
        fi
    fi
    
    # Configurar projeto como padrão
    print_step "Configurando projeto como padrão..."
    gcloud config set project "$PROJECT_ID" >> "$LOG_FILE" 2>&1
    print_ok "Projeto configurado: $PROJECT_ID"
    
    echo ""
    
    # REGIÃO
    print_explanation << 'EOF'
  A REGIÃO determina onde seus servidores estarão fisicamente.
  
  Escolha a região mais próxima dos seus usuários para menor latência.
  
  Para Brasil, recomendamos: southamerica-east1 (São Paulo)
EOF
    
    local regions=(
        "southamerica-east1  │ São Paulo, Brasil ⭐ RECOMENDADO"
        "us-central1         │ Iowa, EUA (baixo custo)"
        "us-east1            │ Carolina do Sul, EUA"
        "europe-west1        │ Bélgica, Europa"
        "asia-east1          │ Taiwan, Ásia"
    )
    
    select_menu "Escolha a região para seus servidores:" "${regions[@]}"
    local region_idx=$?
    
    case $region_idx in
        0) REGION="southamerica-east1" ;;
        1) REGION="us-central1" ;;
        2) REGION="us-east1" ;;
        3) REGION="europe-west1" ;;
        4) REGION="asia-east1" ;;
    esac
    
    print_ok "Região selecionada: $REGION"
    
    echo ""
    
    # AMBIENTE
    print_explanation << 'EOF'
  O AMBIENTE define os recursos alocados:
  
  DESENVOLVIMENTO (dev):
    - Recursos mínimos (menor custo ~$20-50/mês)
    - Escala para zero quando inativo
    - Ideal para testes
  
  PRODUÇÃO (prod):
    - Recursos maiores para performance
    - Sempre ligado (maior disponibilidade)
    - Mais memória e CPU (~$100-300/mês)
EOF
    
    local envs=(
        "dev  │ Desenvolvimento (menor custo, escala para zero)"
        "prod │ Produção (alta disponibilidade, mais recursos)"
    )
    
    select_menu "Escolha o ambiente:" "${envs[@]}"
    ENVIRONMENT=$([ $? -eq 0 ] && echo "dev" || echo "prod")
    
    print_ok "Ambiente selecionado: $ENVIRONMENT"
    
    # Salvar configuração
    save_config
    
    echo ""
    print_box "CONFIGURAÇÃO SALVA" "$GREEN" \
        "Projeto:  $PROJECT_ID" \
        "Região:   $REGION" \
        "Ambiente: $ENVIRONMENT" \
        "" \
        "Estas configurações foram salvas em .gcp-config"
    
    wait_enter
}

#-------------------------------------------------------------------------------
# PASSO 3: HABILITAR APIs
#-------------------------------------------------------------------------------

step_enable_apis() {
    clear_screen
    print_banner
    
    print_section "3" "HABILITANDO APIs DO GOOGLE CLOUD" \
        "Ativando os serviços necessários no GCP"
    
    print_explanation << 'EOF'
  O Google Cloud tem centenas de serviços (APIs).
  Precisamos habilitar apenas os que vamos usar:
  
  • Cloud Run        - Executa os containers da aplicação
  • Artifact Registry - Armazena as imagens Docker
  • Secret Manager   - Guarda senhas e chaves de forma segura
  • Cloud Storage    - Armazena arquivos (documentos dos clientes)
  • Cloud SQL        - Banco de dados PostgreSQL
  • AI Platform      - Acesso ao Gemini AI
  • Cloud Build      - Compila o código automaticamente
  
  Este processo pode demorar 2-3 minutos na primeira vez.
EOF
    
    if ! ask_confirm "Habilitar as APIs necessárias?" "y"; then
        print_skip "APIs não habilitadas"
        return 0
    fi
    
    echo ""
    
    local apis=(
        "run.googleapis.com:Cloud Run"
        "artifactregistry.googleapis.com:Artifact Registry"
        "secretmanager.googleapis.com:Secret Manager"
        "storage.googleapis.com:Cloud Storage"
        "sqladmin.googleapis.com:Cloud SQL Admin"
        "aiplatform.googleapis.com:Vertex AI"
        "cloudbuild.googleapis.com:Cloud Build"
    )
    
    local total=${#apis[@]}
    local current=0
    local enabled=0
    local already=0
    
    for api_item in "${apis[@]}"; do
        IFS=':' read -r api name <<< "$api_item"
        ((current++))
        
        print_checking "[$current/$total] $name"
        
        if check_api_enabled "$api"; then
            print_ok "$name (já habilitada)"
            ((already++))
        else
            if gcloud services enable "$api" >> "$LOG_FILE" 2>&1; then
                print_ok "$name"
                ((enabled++))
            else
                print_fail "$name - Erro ao habilitar"
                log "ERROR: Failed to enable $api"
            fi
        fi
    done
    
    echo ""
    print_box "RESULTADO" "$GREEN" \
        "APIs habilitadas: $enabled" \
        "Já estavam ativas: $already" \
        "Total verificadas: $total"
    
    wait_enter
}

#-------------------------------------------------------------------------------
# PASSO 4: CRIAR INFRAESTRUTURA
#-------------------------------------------------------------------------------

step_create_infrastructure() {
    clear_screen
    print_banner
    
    print_section "4" "CRIANDO INFRAESTRUTURA" \
        "Configurando os recursos necessários no GCP"
    
    print_explanation << 'EOF'
  Vamos criar os seguintes recursos:
  
  1. ARTIFACT REGISTRY
     Repositório para armazenar as imagens Docker dos seus containers.
     Funciona como um "Docker Hub privado" no GCP.
  
  2. SERVICE ACCOUNT
     Uma "conta de serviço" com permissões específicas.
     Os containers usarão esta conta para acessar recursos.
  
  3. SECRETS
     Senhas e chaves armazenadas de forma segura.
     JWT Secret, senha do banco, chave da Gemini AI.
  
  4. STORAGE BUCKET
     Armazenamento de arquivos (documentos dos clientes).
     Similar ao Amazon S3.
EOF
    
    if ! ask_confirm "Criar a infraestrutura?" "y"; then
        return 0
    fi
    
    echo ""
    local SA_EMAIL="${APP_NAME}-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com"
    local BUCKET_NAME="${PROJECT_ID}-documentos"
    
    # 4.1 Artifact Registry
    echo -e "${WHITE}  4.1 ARTIFACT REGISTRY${NC}"
    print_checking "Verificando Artifact Registry"
    
    if check_registry_exists "$APP_NAME" "$REGION"; then
        print_ok "Artifact Registry já existe"
    else
        print_step "Criando Artifact Registry '$APP_NAME'..."
        if gcloud artifacts repositories create "$APP_NAME" \
            --repository-format=docker \
            --location="$REGION" \
            --description="CRM Jurídico AI - Docker Images" >> "$LOG_FILE" 2>&1; then
            print_ok "Artifact Registry criado"
        else
            print_fail "Erro ao criar Artifact Registry"
        fi
    fi
    
    # Configurar Docker auth
    print_step "Configurando autenticação Docker..."
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >> "$LOG_FILE" 2>&1
    print_ok "Docker configurado para Artifact Registry"
    
    echo ""
    
    # 4.2 Service Account
    echo -e "${WHITE}  4.2 SERVICE ACCOUNT${NC}"
    print_checking "Verificando Service Account"
    
    if check_sa_exists "$SA_EMAIL"; then
        print_ok "Service Account já existe"
    else
        print_step "Criando Service Account..."
        if gcloud iam service-accounts create "${APP_NAME}-cloudrun" \
            --display-name="CRM Jurídico - Cloud Run" \
            --description="Service Account para os containers do CRM Jurídico" >> "$LOG_FILE" 2>&1; then
            print_ok "Service Account criado: $SA_EMAIL"
        else
            print_fail "Erro ao criar Service Account"
        fi
    fi
    
    # Atribuir permissões
    print_step "Configurando permissões..."
    local roles=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/storage.objectAdmin"
        "roles/aiplatform.user"
        "roles/logging.logWriter"
        "roles/monitoring.metricWriter"
    )
    
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="$role" \
            --quiet >> "$LOG_FILE" 2>&1 || true
    done
    print_ok "Permissões configuradas"
    
    echo ""
    
    # 4.3 Secrets
    echo -e "${WHITE}  4.3 SECRETS (Credenciais Seguras)${NC}"
    
    # JWT Secret
    print_checking "Verificando JWT Secret"
    if check_secret_exists "${APP_NAME}-jwt-secret"; then
        print_ok "JWT Secret já existe"
    else
        local JWT_SECRET=$(openssl rand -hex 32)
        print_step "Criando JWT Secret..."
        echo "$JWT_SECRET" | gcloud secrets create "${APP_NAME}-jwt-secret" \
            --data-file=- \
            --labels="app=${APP_NAME},type=jwt" >> "$LOG_FILE" 2>&1
        print_ok "JWT Secret criado"
        print_substep "Valor: ${JWT_SECRET:0:16}... (salvo no Secret Manager)"
    fi
    
    # DB Password
    print_checking "Verificando DB Password"
    if check_secret_exists "${APP_NAME}-db-password"; then
        print_ok "DB Password já existe"
    else
        local DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
        print_step "Criando senha do banco..."
        echo "$DB_PASSWORD" | gcloud secrets create "${APP_NAME}-db-password" \
            --data-file=- \
            --labels="app=${APP_NAME},type=database" >> "$LOG_FILE" 2>&1
        print_ok "DB Password criado"
        
        # Mostrar para o usuário salvar
        echo ""
        print_box "IMPORTANTE - SALVE ESTA SENHA!" "$YELLOW" \
            "Senha do Banco de Dados: $DB_PASSWORD" \
            "" \
            "Você precisará desta senha para configurar o Cloud SQL."
    fi
    
    # Gemini API Key
    print_checking "Verificando Gemini API Key"
    if check_secret_exists "${APP_NAME}-gemini-api-key"; then
        print_ok "Gemini API Key já existe"
    else
        print_warn "Gemini API Key não configurada"
        echo ""
        
        print_explanation << 'EOF'
  A GEMINI API KEY é necessária para:
  - Extração automática de dados de documentos (OCR inteligente)
  - Análise de CNIS e PPP
  - Geração de petições
  - Busca semântica
  
  Para obter sua chave:
  1. Acesse: https://aistudio.google.com/apikey
  2. Clique em "Create API Key"
  3. Selecione seu projeto ou crie um novo
  4. Copie a chave gerada
EOF
        
        if ask_confirm "Você tem uma Gemini API Key para configurar agora?"; then
            echo ""
            echo -ne "${CYAN}  ?${NC} Cole sua Gemini API Key: "
            read -rs GEMINI_KEY
            echo ""
            
            if [ -n "$GEMINI_KEY" ] && [ ${#GEMINI_KEY} -gt 20 ]; then
                print_step "Salvando Gemini API Key..."
                echo "$GEMINI_KEY" | gcloud secrets create "${APP_NAME}-gemini-api-key" \
                    --data-file=- \
                    --labels="app=${APP_NAME},type=api-key" >> "$LOG_FILE" 2>&1
                print_ok "Gemini API Key salva"
            else
                print_warn "Chave inválida ou vazia"
            fi
        else
            print_info "Você pode adicionar depois com:"
            echo -e "    ${DIM}echo 'SUA_KEY' | gcloud secrets create ${APP_NAME}-gemini-api-key --data-file=-${NC}"
        fi
    fi
    
    echo ""
    
    # 4.4 Storage Bucket
    echo -e "${WHITE}  4.4 STORAGE BUCKET${NC}"
    print_checking "Verificando Storage Bucket"
    
    if check_bucket_exists "$BUCKET_NAME"; then
        print_ok "Bucket já existe: $BUCKET_NAME"
    else
        print_step "Criando bucket para documentos..."
        if gsutil mb -l "$REGION" -b on "gs://$BUCKET_NAME" >> "$LOG_FILE" 2>&1; then
            # Configurar acesso uniforme
            gsutil uniformbucketlevelaccess set on "gs://$BUCKET_NAME" >> "$LOG_FILE" 2>&1
            print_ok "Bucket criado: $BUCKET_NAME"
        else
            print_fail "Erro ao criar bucket"
        fi
    fi
    
    echo ""
    print_box "INFRAESTRUTURA PRONTA" "$GREEN" \
        "✓ Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}" \
        "✓ Service Account: $SA_EMAIL" \
        "✓ Secrets: JWT, DB Password configurados" \
        "✓ Storage Bucket: gs://$BUCKET_NAME"
    
    wait_enter
}

#-------------------------------------------------------------------------------
# PASSO 5: BUILD E DEPLOY
#-------------------------------------------------------------------------------

step_build_and_deploy() {
    clear_screen
    print_banner
    
    print_section "5" "BUILD E DEPLOY" \
        "Construindo e publicando a aplicação"
    
    local REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}"
    local TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    
    print_explanation << 'EOF'
  Agora vamos:
  
  1. CONSTRUIR as imagens Docker (Backend e Frontend)
  2. ENVIAR as imagens para o Artifact Registry
  3. FAZER DEPLOY no Cloud Run
  
  O Cloud Run é um serviço serverless que:
  - Escala automaticamente conforme demanda
  - Cobra apenas pelo tempo de execução
  - Gerencia certificados SSL automaticamente
EOF
    
    print_box "CONFIGURAÇÃO DO DEPLOY" "$CYAN" \
        "Projeto:  $PROJECT_ID" \
        "Região:   $REGION" \
        "Ambiente: $ENVIRONMENT" \
        "Registry: $REGISTRY"
    
    if ! ask_confirm "Iniciar o build e deploy?" "y"; then
        return 0
    fi
    
    echo ""
    cd "$PROJECT_ROOT"
    
    # 5.1 Build Backend
    echo -e "${WHITE}  5.1 BUILD DO BACKEND${NC}"
    print_step "Construindo imagem do Backend (Python/FastAPI)..."
    print_info "Isso pode demorar 3-5 minutos na primeira vez..."
    echo ""
    
    if docker build \
        -t "${REGISTRY}/api:${TIMESTAMP}" \
        -t "${REGISTRY}/api:latest" \
        -f backend/Dockerfile \
        ./backend 2>&1 | tee -a "$LOG_FILE" | grep -E "^(Step|Successfully|CACHED)"; then
        echo ""
        print_ok "Backend build concluído"
    else
        print_fail "Erro no build do backend"
        print_info "Verifique o log: $LOG_FILE"
        return 1
    fi
    
    echo ""
    
    # 5.2 Build Frontend
    echo -e "${WHITE}  5.2 BUILD DO FRONTEND${NC}"
    
    # Criar .env.production
    cat > frontend/.env.production << EOF
VITE_API_URL=https://${APP_NAME}-api-${REGION:0:2}.a.run.app
VITE_ENVIRONMENT=$ENVIRONMENT
EOF
    
    print_step "Construindo imagem do Frontend (React/TypeScript)..."
    echo ""
    
    if docker build \
        -t "${REGISTRY}/frontend:${TIMESTAMP}" \
        -t "${REGISTRY}/frontend:latest" \
        -f frontend/Dockerfile \
        ./frontend 2>&1 | tee -a "$LOG_FILE" | grep -E "^(Step|Successfully|CACHED)"; then
        echo ""
        print_ok "Frontend build concluído"
    else
        print_fail "Erro no build do frontend"
        return 1
    fi
    
    echo ""
    
    # 5.3 Push Images
    echo -e "${WHITE}  5.3 ENVIANDO IMAGENS PARA O CLOUD${NC}"
    print_step "Enviando imagens para Artifact Registry..."
    
    docker push "${REGISTRY}/api:${TIMESTAMP}" >> "$LOG_FILE" 2>&1 &
    local pid1=$!
    docker push "${REGISTRY}/frontend:${TIMESTAMP}" >> "$LOG_FILE" 2>&1 &
    local pid2=$!
    
    # Mostrar progresso
    echo -ne "    Enviando API..."
    wait $pid1 && echo -e " ${GREEN}✓${NC}" || echo -e " ${RED}✗${NC}"
    echo -ne "    Enviando Frontend..."
    wait $pid2 && echo -e " ${GREEN}✓${NC}" || echo -e " ${RED}✗${NC}"
    
    # Push latest tags
    docker push "${REGISTRY}/api:latest" >> "$LOG_FILE" 2>&1
    docker push "${REGISTRY}/frontend:latest" >> "$LOG_FILE" 2>&1
    
    print_ok "Imagens enviadas"
    
    echo ""
    
    # 5.4 Deploy API
    echo -e "${WHITE}  5.4 DEPLOY DA API${NC}"
    
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
    
    print_step "Fazendo deploy da API no Cloud Run..."
    print_substep "Instâncias: $min_instances - $max_instances"
    print_substep "Memória: $memory | CPU: $cpu"
    
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
        --timeout 300 \
        --quiet >> "$LOG_FILE" 2>&1; then
        
        local API_URL=$(gcloud run services describe "${APP_NAME}-api" --region "$REGION" --format 'value(status.url)')
        print_ok "API deployed!"
        print_substep "URL: $API_URL"
    else
        print_fail "Erro no deploy da API"
        return 1
    fi
    
    echo ""
    
    # 5.5 Deploy Frontend
    echo -e "${WHITE}  5.5 DEPLOY DO FRONTEND${NC}"
    
    print_step "Fazendo deploy do Frontend no Cloud Run..."
    
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
        --cpu 1 \
        --quiet >> "$LOG_FILE" 2>&1; then
        
        local FRONTEND_URL=$(gcloud run services describe "${APP_NAME}-frontend" --region "$REGION" --format 'value(status.url)')
        print_ok "Frontend deployed!"
        print_substep "URL: $FRONTEND_URL"
    else
        print_fail "Erro no deploy do frontend"
        return 1
    fi
    
    echo ""
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                              ║${NC}"
    echo -e "${GREEN}║                    🎉 DEPLOY CONCLUÍDO COM SUCESSO! 🎉                       ║${NC}"
    echo -e "${GREEN}║                                                                              ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${WHITE}Sua aplicação está no ar!${NC}"
    echo ""
    echo -e "  🌐 ${BOLD}Frontend:${NC} ${GREEN}$FRONTEND_URL${NC}"
    echo -e "  🔧 ${BOLD}API:${NC}      ${GREEN}$API_URL${NC}"
    echo -e "  📚 ${BOLD}Docs:${NC}     ${GREEN}$API_URL/docs${NC}"
    echo ""
    
    if ask_confirm "Abrir o frontend no navegador?"; then
        if check_command xdg-open; then
            xdg-open "$FRONTEND_URL" 2>/dev/null &
        elif check_command open; then
            open "$FRONTEND_URL" 2>/dev/null &
        fi
    fi
    
    wait_enter
}

#-------------------------------------------------------------------------------
# PASSO 6: STATUS E MONITORAMENTO
#-------------------------------------------------------------------------------

step_status() {
    clear_screen
    print_banner
    
    print_section "6" "STATUS DOS SERVIÇOS" \
        "Verificando o estado atual da aplicação"
    
    if [ -z "$PROJECT_ID" ] && ! load_config; then
        print_fail "Nenhuma configuração encontrada"
        print_info "Execute o setup primeiro"
        wait_enter
        return 1
    fi
    
    echo ""
    echo -e "${WHITE}  CLOUD RUN SERVICES${NC}"
    echo ""
    
    # Verificar API
    print_checking "API Backend"
    if check_service_exists "${APP_NAME}-api" "$REGION"; then
        local api_url=$(gcloud run services describe "${APP_NAME}-api" --region "$REGION" --format 'value(status.url)' 2>/dev/null)
        print_ok "API Online"
        print_substep "URL: $api_url"
        
        # Testar health
        print_checking "Health check da API"
        if curl -s --max-time 10 "$api_url/health" | grep -q "healthy"; then
            print_ok "API respondendo corretamente"
        else
            print_warn "API pode estar iniciando..."
        fi
    else
        print_skip "API não deployada"
    fi
    
    # Verificar Frontend
    print_checking "Frontend"
    if check_service_exists "${APP_NAME}-frontend" "$REGION"; then
        local frontend_url=$(gcloud run services describe "${APP_NAME}-frontend" --region "$REGION" --format 'value(status.url)' 2>/dev/null)
        print_ok "Frontend Online"
        print_substep "URL: $frontend_url"
    else
        print_skip "Frontend não deployado"
    fi
    
    echo ""
    echo -e "${WHITE}  RECURSOS${NC}"
    echo ""
    
    # Artifact Registry
    print_checking "Artifact Registry"
    if check_registry_exists "$APP_NAME" "$REGION"; then
        print_ok "Artifact Registry configurado"
    else
        print_skip "Não configurado"
    fi
    
    # Storage
    print_checking "Storage Bucket"
    if check_bucket_exists "${PROJECT_ID}-documentos"; then
        print_ok "Bucket configurado"
    else
        print_skip "Não configurado"
    fi
    
    # Secrets
    print_checking "Secrets"
    local secrets_ok=0
    check_secret_exists "${APP_NAME}-jwt-secret" && ((secrets_ok++))
    check_secret_exists "${APP_NAME}-db-password" && ((secrets_ok++))
    check_secret_exists "${APP_NAME}-gemini-api-key" && ((secrets_ok++))
    print_ok "$secrets_ok/3 secrets configurados"
    
    echo ""
    wait_enter
}

#-------------------------------------------------------------------------------
# PASSO 7: LOGS
#-------------------------------------------------------------------------------

step_logs() {
    clear_screen
    print_banner
    
    print_section "7" "VISUALIZAR LOGS" \
        "Acompanhe os logs da aplicação em tempo real"
    
    if [ -z "$PROJECT_ID" ] && ! load_config; then
        print_fail "Nenhuma configuração encontrada"
        wait_enter
        return 1
    fi
    
    local services=(
        "api      │ Backend (FastAPI)"
        "frontend │ Frontend (React)"
        "← Voltar"
    )
    
    select_menu "Qual serviço deseja monitorar?" "${services[@]}"
    local choice=$?
    
    [ $choice -eq 2 ] && return 0
    
    local service_name=$([ $choice -eq 0 ] && echo "api" || echo "frontend")
    
    echo ""
    print_info "Mostrando últimos 50 logs de ${APP_NAME}-${service_name}"
    print_info "Pressione Ctrl+C para sair"
    echo ""
    echo -e "${DIM}────────────────────────────────────────────────────────────────────────────────${NC}"
    
    gcloud run services logs read "${APP_NAME}-${service_name}" \
        --region "$REGION" \
        --limit 50 2>/dev/null || print_warn "Nenhum log encontrado"
    
    wait_enter
}

#-------------------------------------------------------------------------------
# PASSO 8: DESTRUIR
#-------------------------------------------------------------------------------

step_destroy() {
    clear_screen
    print_banner
    
    print_section "8" "REMOVER RECURSOS" \
        "Remove todos os recursos criados no GCP"
    
    if [ -z "$PROJECT_ID" ] && ! load_config; then
        print_fail "Nenhuma configuração encontrada"
        wait_enter
        return 1
    fi
    
    echo ""
    echo -e "${RED}  ╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}  ║                         ⚠️  ATENÇÃO - PERIGO! ⚠️                            ║${NC}"
    echo -e "${RED}  ╠════════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${RED}  ║                                                                            ║${NC}"
    echo -e "${RED}  ║   Esta ação irá REMOVER PERMANENTEMENTE os seguintes recursos:            ║${NC}"
    echo -e "${RED}  ║                                                                            ║${NC}"
    echo -e "${RED}  ║   • Cloud Run Services (api, frontend)                                    ║${NC}"
    echo -e "${RED}  ║   • Artifact Registry (todas as imagens Docker)                          ║${NC}"
    echo -e "${RED}  ║   • Secrets (jwt-secret, db-password, gemini-api-key)                     ║${NC}"
    echo -e "${RED}  ║                                                                            ║${NC}"
    echo -e "${RED}  ║   O Storage Bucket NÃO será removido para preservar documentos.          ║${NC}"
    echo -e "${RED}  ║                                                                            ║${NC}"
    echo -e "${RED}  ╚════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -ne "${YELLOW}  ?${NC} Digite ${RED}${BOLD}DESTRUIR${NC} para confirmar: "
    read -r confirm_text
    
    if [ "$confirm_text" != "DESTRUIR" ]; then
        print_info "Operação cancelada"
        wait_enter
        return 0
    fi
    
    echo ""
    
    # Remover services
    print_step "Removendo Cloud Run Services..."
    for service in api frontend worker; do
        print_checking "${APP_NAME}-${service}"
        if gcloud run services delete "${APP_NAME}-${service}" --region "$REGION" --quiet 2>/dev/null; then
            print_ok "Removido"
        else
            print_skip "Não encontrado"
        fi
    done
    
    # Remover Artifact Registry
    print_step "Removendo Artifact Registry..."
    if gcloud artifacts repositories delete "$APP_NAME" --location="$REGION" --quiet 2>/dev/null; then
        print_ok "Registry removido"
    else
        print_skip "Registry não encontrado"
    fi
    
    # Remover Secrets
    print_step "Removendo Secrets..."
    for secret in jwt-secret db-password gemini-api-key; do
        if gcloud secrets delete "${APP_NAME}-${secret}" --quiet 2>/dev/null; then
            print_ok "${APP_NAME}-${secret} removido"
        fi
    done
    
    # Remover config local
    rm -f "$CONFIG_FILE"
    PROJECT_ID=""
    REGION=""
    ENVIRONMENT=""
    
    echo ""
    print_ok "Recursos removidos com sucesso"
    echo ""
    print_info "O bucket de documentos foi preservado."
    print_info "Para removê-lo: gsutil rm -r gs://${PROJECT_ID}-documentos"
    
    wait_enter
}

#-------------------------------------------------------------------------------
# MENU PRINCIPAL
#-------------------------------------------------------------------------------

main_menu() {
    while true; do
        clear_screen
        print_banner
        
        # Mostrar config atual
        if [ -n "$PROJECT_ID" ]; then
            echo -e "  ${DIM}Projeto: $PROJECT_ID │ Região: $REGION │ Ambiente: $ENVIRONMENT${NC}"
            echo ""
        fi
        
        echo -e "${WHITE}  ┌─────────────────────────────────────────────────────────────────────────────┐${NC}"
        echo -e "${WHITE}  │                        O QUE VOCÊ DESEJA FAZER?                            │${NC}"
        echo -e "${WHITE}  └─────────────────────────────────────────────────────────────────────────────┘${NC}"
        echo ""
        
        local options=(
            "🚀 Setup Completo      │ Configurar tudo do zero (primeira vez)"
            "📦 Apenas Deploy       │ Fazer deploy (já configurado)"
            "📊 Ver Status          │ Verificar estado dos serviços"
            "📋 Ver Logs            │ Acompanhar logs da aplicação"
            "⚙️  Reconfigurar        │ Alterar projeto/região/ambiente"
            "🗑️  Remover Recursos    │ Destruir tudo no GCP"
            "❌ Sair"
        )
        
        select_menu "" "${options[@]}"
        local choice=$?
        
        case $choice in
            0) # Setup Completo
                step_prerequisites
                step_configure_project
                step_enable_apis
                step_create_infrastructure
                step_build_and_deploy
                ;;
            1) # Apenas Deploy
                if [ -z "$PROJECT_ID" ]; then
                    step_prerequisites
                    step_configure_project
                fi
                step_build_and_deploy
                ;;
            2) # Status
                step_status
                ;;
            3) # Logs
                step_logs
                ;;
            4) # Reconfigurar
                step_configure_project
                ;;
            5) # Destruir
                step_destroy
                ;;
            6) # Sair
                clear_screen
                echo ""
                print_info "Até logo! 👋"
                echo ""
                echo -e "  ${DIM}Dúvidas? Consulte a documentação em docs/DEPLOY.md${NC}"
                echo ""
                exit 0
                ;;
        esac
    done
}

#-------------------------------------------------------------------------------
# HELP
#-------------------------------------------------------------------------------

show_help() {
    echo "CRM Jurídico AI - Assistente de Deploy GCP"
    echo ""
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos:"
    echo "  (nenhum)  Abre o menu interativo (recomendado)"
    echo "  setup     Executa o setup completo"
    echo "  deploy    Faz apenas o deploy"
    echo "  status    Mostra o status dos serviços"
    echo "  logs      Mostra os logs"
    echo "  help      Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  ./scripts/deploy-gcp.sh          # Menu interativo"
    echo "  ./scripts/deploy-gcp.sh setup    # Setup direto"
    echo "  ./scripts/deploy-gcp.sh deploy   # Deploy direto"
    echo ""
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    # Criar arquivo de log
    echo "=== Deploy GCP - $(date) ===" > "$LOG_FILE"
    
    # Carregar configuração existente
    load_config 2>/dev/null || true
    
    # Processar argumentos
    case "${1:-}" in
        setup)
            step_prerequisites
            step_configure_project
            step_enable_apis
            step_create_infrastructure
            step_build_and_deploy
            ;;
        deploy)
            if [ -z "$PROJECT_ID" ]; then
                step_prerequisites
                step_configure_project
            fi
            step_build_and_deploy
            ;;
        status)
            step_status
            ;;
        logs)
            step_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            main_menu
            ;;
        *)
            echo "Comando desconhecido: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Capturar Ctrl+C graciosamente
trap 'echo ""; print_info "Operação cancelada pelo usuário"; exit 0' INT

# Executar
main "$@"
