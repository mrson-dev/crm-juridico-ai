#!/bin/bash
# ============================================
# Script de Setup Inicial do GCP
# ============================================
# Execute este script uma vez para configurar
# o projeto GCP antes do primeiro deploy.
#
# Uso: ./scripts/gcp-setup.sh <PROJECT_ID>

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar argumento
if [ -z "${1:-}" ]; then
    echo -e "${RED}Erro: PROJECT_ID não informado${NC}"
    echo "Uso: $0 <PROJECT_ID>"
    exit 1
fi

PROJECT_ID=$1
REGION=${2:-"southamerica-east1"}
APP_NAME="crm-juridico"

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  CRM Jurídico - Setup GCP${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# ============================================
# 1. Configurar projeto
# ============================================
echo -e "${YELLOW}[1/8] Configurando projeto...${NC}"
gcloud config set project $PROJECT_ID

# ============================================
# 2. Habilitar APIs necessárias
# ============================================
echo -e "${YELLOW}[2/8] Habilitando APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com \
    redis.googleapis.com \
    vpcaccess.googleapis.com \
    compute.googleapis.com \
    servicenetworking.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    cloudtasks.googleapis.com \
    pubsub.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    firebaseauth.googleapis.com

# ============================================
# 3. Criar Service Account
# ============================================
echo -e "${YELLOW}[3/8] Criando Service Account...${NC}"
SA_NAME="${APP_NAME}-cloudrun"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
    gcloud iam service-accounts create $SA_NAME \
        --display-name="CRM Jurídico Cloud Run"
fi

# Permissões
ROLES=(
    "roles/cloudsql.client"
    "roles/secretmanager.secretAccessor"
    "roles/storage.objectAdmin"
    "roles/aiplatform.user"
    "roles/cloudtasks.enqueuer"
    "roles/pubsub.publisher"
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role" \
        --quiet
done

# ============================================
# 4. Criar Secrets
# ============================================
echo -e "${YELLOW}[4/8] Criando Secrets...${NC}"

# Gerar valores se não existirem
JWT_SECRET=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)

create_secret() {
    local name=$1
    local value=$2
    
    if ! gcloud secrets describe $name &>/dev/null; then
        echo "$value" | gcloud secrets create $name --data-file=-
        echo "  ✓ Secret $name criado"
    else
        echo "  - Secret $name já existe"
    fi
}

create_secret "${APP_NAME}-jwt-secret" "$JWT_SECRET"
create_secret "${APP_NAME}-db-password" "$DB_PASSWORD"

echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE: Crie manualmente o secret da Gemini API:${NC}"
echo "  gcloud secrets create ${APP_NAME}-gemini-api-key --data-file=-"
echo "  (Cole sua API key e pressione Ctrl+D)"
echo ""

# ============================================
# 5. Criar Bucket de Storage
# ============================================
echo -e "${YELLOW}[5/8] Criando Cloud Storage Bucket...${NC}"
BUCKET_NAME="${PROJECT_ID}-documentos"

if ! gsutil ls -b gs://$BUCKET_NAME &>/dev/null; then
    gsutil mb -l $REGION gs://$BUCKET_NAME
    gsutil uniformbucketlevelaccess set on gs://$BUCKET_NAME
    echo "  ✓ Bucket criado: $BUCKET_NAME"
else
    echo "  - Bucket já existe: $BUCKET_NAME"
fi

# ============================================
# 6. Configurar Cloud Build
# ============================================
echo -e "${YELLOW}[6/8] Configurando Cloud Build...${NC}"

# Permissões para Cloud Build SA
CLOUDBUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/run.admin" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUDBUILD_SA}" \
    --role="roles/iam.serviceAccountUser" \
    --quiet

# ============================================
# 7. Criar VPC e Connector
# ============================================
echo -e "${YELLOW}[7/8] Verificando VPC...${NC}"
echo "  ℹ️  VPC e Cloud SQL serão criados via Terraform"
echo "  Execute: cd infra/terraform && terraform apply"

# ============================================
# 8. Resumo
# ============================================
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Setup Concluído!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Próximos passos:"
echo ""
echo "1. Criar secret da Gemini API:"
echo "   echo 'SUA_API_KEY' | gcloud secrets create ${APP_NAME}-gemini-api-key --data-file=-"
echo ""
echo "2. Configurar Terraform:"
echo "   cd infra/terraform"
echo "   cp terraform.tfvars.example terraform.tfvars"
echo "   # Editar terraform.tfvars com seus valores"
echo "   terraform init"
echo "   terraform plan"
echo "   terraform apply"
echo ""
echo "3. Deploy manual (primeiro deploy):"
echo "   gcloud builds submit --config=cloudbuild.yaml"
echo ""
echo "4. Configurar trigger automático:"
echo "   gcloud builds triggers create github \\"
echo "     --repo-name=crm-juridico-ai \\"
echo "     --repo-owner=SEU_USUARIO \\"
echo "     --branch-pattern='^main$' \\"
echo "     --build-config=cloudbuild.yaml"
echo ""
echo -e "${YELLOW}Credenciais geradas (salve em local seguro!):${NC}"
echo "  DB_PASSWORD: $DB_PASSWORD"
echo "  JWT_SECRET: $JWT_SECRET"
echo ""
