#!/bin/bash

#===============================================================================
#
#   CRM JURÍDICO AI - Deploy & Setup GCP Unificado
#   
#   Script completo para configurar e fazer deploy no Google Cloud Platform.
#   Combina setup inicial + deploy em um único script inteligente.
#
#   Uso: ./scripts/deploy-gcp.sh [comando] [opções]
#
#   Comandos:
#     setup       - Configuração inicial do projeto GCP (executar uma vez)
#     deploy      - Deploy da aplicação (dev ou prod)
#     status      - Verificar status dos serviços
#     logs        - Ver logs dos serviços
#     destroy     - Remover recursos (cuidado!)
#
#   Exemplos:
#     ./scripts/deploy-gcp.sh setup my-project-id
#     ./scripts/deploy-gcp.sh deploy dev
#     ./scripts/deploy-gcp.sh deploy prod
#     ./scripts/deploy-gcp.sh status
#     ./scripts/deploy-gcp.sh logs api
#
#===============================================================================

set -euo pipefail

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

# Configurações padrão
APP_NAME="crm-juridico"
REGION="${GCP_REGION:-southamerica-east1}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

#-------------------------------------------------------------------------------
# FUNÇÕES DE UI
#-------------------------------------------------------------------------------

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

print_section() {
    local title="$1"
    echo ""
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}  ${BOLD}$title${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_step() {
    local num="$1"
    local msg="$2"
    echo -e "${BLUE}  [$num]${NC} $msg"
}

print_success() {
    echo -e "${GREEN}  ✓${NC} $1"
}

print_error() {
    echo -e "${RED}  ✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}  ⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}  ℹ${NC} $1"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

#-------------------------------------------------------------------------------
# FUNÇÕES DE VERIFICAÇÃO
#-------------------------------------------------------------------------------

check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI não encontrado"
        echo ""
        echo "Instale o Google Cloud SDK:"
        echo "  https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker não encontrado"
        exit 1
    fi
}

check_authenticated() {
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        print_error "Não autenticado no GCP"
        echo ""
        echo "Execute: gcloud auth login"
        exit 1
    fi
}

get_project_id() {
    local project_id=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$project_id" ] || [ "$project_id" = "(unset)" ]; then
        print_error "PROJECT_ID não configurado"
        echo ""
        echo "Execute: gcloud config set project SEU_PROJETO"
        exit 1
    fi
    echo "$project_id"
}

#-------------------------------------------------------------------------------
# COMANDO: SETUP
#-------------------------------------------------------------------------------

cmd_setup() {
    local PROJECT_ID="${1:-}"
    
    if [ -z "$PROJECT_ID" ]; then
        echo "Uso: $0 setup <PROJECT_ID> [REGION]"
        echo ""
        echo "Exemplo: $0 setup meu-projeto-crm southamerica-east1"
        exit 1
    fi
    
    REGION="${2:-$REGION}"
    
    print_banner
    print_section "SETUP INICIAL DO PROJETO GCP"
    
    echo "  Projeto: $PROJECT_ID"
    echo "  Região:  $REGION"
    echo "  App:     $APP_NAME"
    echo ""
    
    read -p "  Continuar? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelado."
        exit 0
    fi
    
    # 1. Configurar projeto
    print_step "1/8" "Configurando projeto..."
    gcloud config set project "$PROJECT_ID" >> "$LOG_FILE" 2>&1
    print_success "Projeto configurado"
    
    # 2. Habilitar APIs
    print_step "2/8" "Habilitando APIs (pode demorar)..."
    local apis=(
        "run.googleapis.com"
        "artifactregistry.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "redis.googleapis.com"
        "vpcaccess.googleapis.com"
        "compute.googleapis.com"
        "servicenetworking.googleapis.com"
        "aiplatform.googleapis.com"
        "storage.googleapis.com"
        "cloudbuild.googleapis.com"
        "cloudscheduler.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        gcloud services enable "$api" >> "$LOG_FILE" 2>&1 || true
    done
    print_success "APIs habilitadas"
    
    # 3. Criar Artifact Registry
    print_step "3/8" "Criando Artifact Registry..."
    if ! gcloud artifacts repositories describe "$APP_NAME" --location="$REGION" &>/dev/null; then
        gcloud artifacts repositories create "$APP_NAME" \
            --repository-format=docker \
            --location="$REGION" \
            --description="CRM Jurídico AI Docker images" >> "$LOG_FILE" 2>&1
        print_success "Artifact Registry criado"
    else
        print_info "Artifact Registry já existe"
    fi
    
    # 4. Criar Service Account
    print_step "4/8" "Criando Service Account..."
    local SA_NAME="${APP_NAME}-cloudrun"
    local SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    if ! gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
        gcloud iam service-accounts create "$SA_NAME" \
            --display-name="CRM Jurídico Cloud Run" >> "$LOG_FILE" 2>&1
    fi
    
    # Permissões
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
    print_success "Service Account configurado"
    
    # 5. Criar Secrets
    print_step "5/8" "Criando Secrets..."
    local JWT_SECRET=$(openssl rand -hex 32)
    local DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    
    create_secret() {
        local name=$1
        local value=$2
        if ! gcloud secrets describe "$name" &>/dev/null; then
            echo "$value" | gcloud secrets create "$name" --data-file=- >> "$LOG_FILE" 2>&1
            echo "    - $name criado"
        fi
    }
    
    create_secret "${APP_NAME}-jwt-secret" "$JWT_SECRET"
    create_secret "${APP_NAME}-db-password" "$DB_PASSWORD"
    print_success "Secrets criados"
    
    # 6. Criar Bucket
    print_step "6/8" "Criando Cloud Storage Bucket..."
    local BUCKET_NAME="${PROJECT_ID}-documentos"
    
    if ! gsutil ls -b "gs://$BUCKET_NAME" &>/dev/null; then
        gsutil mb -l "$REGION" "gs://$BUCKET_NAME" >> "$LOG_FILE" 2>&1
        gsutil uniformbucketlevelaccess set on "gs://$BUCKET_NAME" >> "$LOG_FILE" 2>&1
        print_success "Bucket criado: $BUCKET_NAME"
    else
        print_info "Bucket já existe"
    fi
    
    # 7. Configurar Docker auth
    print_step "7/8" "Configurando autenticação Docker..."
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >> "$LOG_FILE" 2>&1
    print_success "Docker configurado para Artifact Registry"
    
    # 8. Resumo
    print_step "8/8" "Finalizando..."
    
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ SETUP CONCLUÍDO!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}  ⚠️  AÇÕES MANUAIS NECESSÁRIAS:${NC}"
    echo ""
    echo "  1. Criar secret da Gemini API:"
    echo -e "     ${DIM}echo 'SUA_API_KEY' | gcloud secrets create ${APP_NAME}-gemini-api-key --data-file=-${NC}"
    echo ""
    echo "  2. Configurar Cloud SQL (via Terraform ou Console):"
    echo -e "     ${DIM}cd infra/terraform && terraform apply${NC}"
    echo ""
    echo "  3. Fazer o primeiro deploy:"
    echo -e "     ${DIM}./scripts/deploy-gcp.sh deploy dev${NC}"
    echo ""
    echo -e "${CYAN}  Credenciais geradas (SALVE EM LOCAL SEGURO!):${NC}"
    echo "    DB_PASSWORD: $DB_PASSWORD"
    echo "    JWT_SECRET:  $JWT_SECRET"
    echo ""
}

#-------------------------------------------------------------------------------
# COMANDO: DEPLOY
#-------------------------------------------------------------------------------

cmd_deploy() {
    local ENVIRONMENT="${1:-dev}"
    
    print_banner
    
    check_gcloud
    check_docker
    check_authenticated
    
    local PROJECT_ID=$(get_project_id)
    local REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}"
    
    print_section "DEPLOY - $ENVIRONMENT"
    
    echo "  Projeto:    $PROJECT_ID"
    echo "  Região:     $REGION"
    echo "  Ambiente:   $ENVIRONMENT"
    echo "  Registry:   $REGISTRY"
    echo "  Timestamp:  $TIMESTAMP"
    echo ""
    
    # Verificar se está na raiz do projeto
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        print_error "Execute este script na raiz do projeto"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    
    # 1. Build Backend
    print_step "1/6" "Building Backend..."
    docker build \
        -t "${REGISTRY}/api:${TIMESTAMP}" \
        -t "${REGISTRY}/api:latest" \
        ./backend >> "$LOG_FILE" 2>&1
    print_success "Backend build completo"
    
    # 2. Build Frontend
    print_step "2/6" "Building Frontend..."
    
    # Criar .env.production temporário
    cat > frontend/.env.production << EOF
VITE_API_URL=https://${APP_NAME}-api-${PROJECT_ID:0:10}-${REGION:0:2}.a.run.app
VITE_ENVIRONMENT=$ENVIRONMENT
EOF
    
    docker build \
        -t "${REGISTRY}/frontend:${TIMESTAMP}" \
        -t "${REGISTRY}/frontend:latest" \
        ./frontend >> "$LOG_FILE" 2>&1
    print_success "Frontend build completo"
    
    # 3. Push Images
    print_step "3/6" "Pushing images para Artifact Registry..."
    docker push "${REGISTRY}/api:${TIMESTAMP}" >> "$LOG_FILE" 2>&1
    docker push "${REGISTRY}/api:latest" >> "$LOG_FILE" 2>&1
    docker push "${REGISTRY}/frontend:${TIMESTAMP}" >> "$LOG_FILE" 2>&1
    docker push "${REGISTRY}/frontend:latest" >> "$LOG_FILE" 2>&1
    print_success "Images enviadas"
    
    # 4. Deploy API
    print_step "4/6" "Deploying API no Cloud Run..."
    
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
    
    gcloud run deploy "${APP_NAME}-api" \
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
        --timeout 300 >> "$LOG_FILE" 2>&1
    
    local API_URL=$(gcloud run services describe "${APP_NAME}-api" --region "$REGION" --format 'value(status.url)')
    print_success "API deployed: $API_URL"
    
    # 5. Deploy Frontend
    print_step "5/6" "Deploying Frontend no Cloud Run..."
    
    gcloud run deploy "${APP_NAME}-frontend" \
        --image "${REGISTRY}/frontend:${TIMESTAMP}" \
        --region "$REGION" \
        --platform managed \
        --allow-unauthenticated \
        --set-env-vars "VITE_API_URL=$API_URL" \
        --min-instances "$min_instances" \
        --max-instances $([ "$ENVIRONMENT" = "prod" ] && echo "5" || echo "2") \
        --memory 256Mi \
        --cpu 1 >> "$LOG_FILE" 2>&1
    
    local FRONTEND_URL=$(gcloud run services describe "${APP_NAME}-frontend" --region "$REGION" --format 'value(status.url)')
    print_success "Frontend deployed: $FRONTEND_URL"
    
    # 6. Opcional: Worker
    print_step "6/6" "Worker Celery..."
    
    read -p "  Deseja fazer deploy do Celery Worker? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud run deploy "${APP_NAME}-worker" \
            --image "${REGISTRY}/api:${TIMESTAMP}" \
            --region "$REGION" \
            --platform managed \
            --no-allow-unauthenticated \
            --service-account "${APP_NAME}-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com" \
            --set-secrets "SECRET_KEY=${APP_NAME}-jwt-secret:latest" \
            --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=$ENVIRONMENT" \
            --command "celery,-A,app.workers.celery_app,worker,--loglevel=info" \
            --no-cpu-throttling \
            --min-instances 0 \
            --max-instances $([ "$ENVIRONMENT" = "prod" ] && echo "5" || echo "1") \
            --memory $([ "$ENVIRONMENT" = "prod" ] && echo "2Gi" || echo "1Gi") >> "$LOG_FILE" 2>&1
        print_success "Worker deployed"
    else
        print_info "Worker pulado"
    fi
    
    # Resumo
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ DEPLOY CONCLUÍDO!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  URLs:"
    echo -e "    Frontend: ${GREEN}$FRONTEND_URL${NC}"
    echo -e "    API:      ${GREEN}$API_URL${NC}"
    echo -e "    Docs:     ${GREEN}$API_URL/docs${NC}"
    echo ""
    echo "  Ver logs:"
    echo "    gcloud run services logs read ${APP_NAME}-api --region $REGION"
    echo ""
}

#-------------------------------------------------------------------------------
# COMANDO: STATUS
#-------------------------------------------------------------------------------

cmd_status() {
    print_banner
    
    check_gcloud
    check_authenticated
    
    local PROJECT_ID=$(get_project_id)
    
    print_section "STATUS DOS SERVIÇOS"
    
    echo "  Projeto: $PROJECT_ID"
    echo "  Região:  $REGION"
    echo ""
    
    echo -e "${BLUE}  Cloud Run Services:${NC}"
    gcloud run services list --region "$REGION" --format="table(SERVICE,REGION,URL,LAST_DEPLOYED_BY)" 2>/dev/null || echo "  Nenhum serviço encontrado"
    
    echo ""
    echo -e "${BLUE}  Artifact Registry Images:${NC}"
    gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}" \
        --format="table(IMAGE,DIGEST,CREATE_TIME)" 2>/dev/null | head -10 || echo "  Nenhuma imagem encontrada"
    
    echo ""
    echo -e "${BLUE}  Secrets:${NC}"
    gcloud secrets list --format="table(NAME,CREATED)" 2>/dev/null | grep "$APP_NAME" || echo "  Nenhum secret encontrado"
    
    echo ""
}

#-------------------------------------------------------------------------------
# COMANDO: LOGS
#-------------------------------------------------------------------------------

cmd_logs() {
    local SERVICE="${1:-api}"
    
    check_gcloud
    check_authenticated
    
    local PROJECT_ID=$(get_project_id)
    local SERVICE_NAME="${APP_NAME}-${SERVICE}"
    
    echo "Mostrando logs de: $SERVICE_NAME"
    echo "Pressione Ctrl+C para sair"
    echo ""
    
    gcloud run services logs read "$SERVICE_NAME" --region "$REGION" --limit 100
}

#-------------------------------------------------------------------------------
# COMANDO: DESTROY
#-------------------------------------------------------------------------------

cmd_destroy() {
    print_banner
    
    check_gcloud
    check_authenticated
    
    local PROJECT_ID=$(get_project_id)
    
    print_section "⚠️  DESTRUIR RECURSOS"
    
    echo -e "${RED}  ATENÇÃO: Esta ação irá remover todos os recursos do CRM Jurídico no GCP!${NC}"
    echo ""
    echo "  Recursos que serão removidos:"
    echo "    - Cloud Run services (api, frontend, worker)"
    echo "    - Artifact Registry images"
    echo "    - Secrets"
    echo ""
    
    read -p "  Digite 'DESTRUIR' para confirmar: " confirm
    
    if [ "$confirm" != "DESTRUIR" ]; then
        echo "Cancelado."
        exit 0
    fi
    
    echo ""
    
    # Remover Cloud Run services
    print_step "1/3" "Removendo Cloud Run services..."
    for service in api frontend worker; do
        gcloud run services delete "${APP_NAME}-${service}" --region "$REGION" --quiet 2>/dev/null || true
    done
    print_success "Services removidos"
    
    # Remover imagens do Artifact Registry
    print_step "2/3" "Removendo imagens do Artifact Registry..."
    gcloud artifacts repositories delete "$APP_NAME" --location="$REGION" --quiet 2>/dev/null || true
    print_success "Imagens removidas"
    
    # Remover secrets
    print_step "3/3" "Removendo Secrets..."
    for secret in jwt-secret db-password gemini-api-key; do
        gcloud secrets delete "${APP_NAME}-${secret}" --quiet 2>/dev/null || true
    done
    print_success "Secrets removidos"
    
    echo ""
    echo -e "${GREEN}  ✅ Recursos removidos com sucesso${NC}"
    echo ""
    echo -e "${YELLOW}  Nota: Bucket de storage e Cloud SQL não foram removidos.${NC}"
    echo "  Remova manualmente se necessário:"
    echo "    gsutil rm -r gs://${PROJECT_ID}-documentos"
    echo ""
}

#-------------------------------------------------------------------------------
# HELP
#-------------------------------------------------------------------------------

show_help() {
    echo "CRM Jurídico AI - Deploy GCP"
    echo ""
    echo "Uso: $0 <comando> [argumentos]"
    echo ""
    echo "Comandos:"
    echo "  setup <PROJECT_ID> [REGION]   Configuração inicial do projeto GCP"
    echo "  deploy <dev|prod>             Deploy da aplicação"
    echo "  status                        Ver status dos serviços"
    echo "  logs <api|frontend|worker>    Ver logs de um serviço"
    echo "  destroy                       Remover todos os recursos (CUIDADO!)"
    echo ""
    echo "Exemplos:"
    echo "  $0 setup meu-projeto-crm"
    echo "  $0 setup meu-projeto-crm us-central1"
    echo "  $0 deploy dev"
    echo "  $0 deploy prod"
    echo "  $0 status"
    echo "  $0 logs api"
    echo ""
    echo "Variáveis de ambiente:"
    echo "  GCP_REGION    Região do GCP (padrão: southamerica-east1)"
    echo ""
}

#-------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------

main() {
    # Inicializar log
    echo "=== Deploy GCP Log - $(date) ===" > "$LOG_FILE"
    
    local cmd="${1:-help}"
    shift || true
    
    case "$cmd" in
        setup)
            check_gcloud
            check_authenticated
            cmd_setup "$@"
            ;;
        deploy)
            cmd_deploy "$@"
            ;;
        status)
            cmd_status
            ;;
        logs)
            cmd_logs "$@"
            ;;
        destroy)
            cmd_destroy
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "Comando desconhecido: $cmd"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
