#!/bin/bash
# ============================================
# Script de Deploy Manual para GCP
# ============================================
# Use este script para deploy manual sem CI/CD
#
# Uso: ./scripts/deploy.sh <ENVIRONMENT>
# Exemplo: ./scripts/deploy.sh prod

set -euo pipefail

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuração
ENVIRONMENT=${1:-"dev"}
REGION=${REGION:-"southamerica-east1"}
PROJECT_ID=$(gcloud config get-value project)
APP_NAME="crm-juridico"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  CRM Jurídico - Deploy Manual${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Timestamp: $TIMESTAMP"
echo ""

# ============================================
# Verificar pré-requisitos
# ============================================
echo -e "${YELLOW}[1/6] Verificando pré-requisitos...${NC}"

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Erro: PROJECT_ID não configurado${NC}"
    echo "Execute: gcloud config set project SEU_PROJETO"
    exit 1
fi

# Verificar se está na raiz do projeto
if [ ! -f "cloudbuild.yaml" ]; then
    echo -e "${RED}Erro: Execute este script na raiz do projeto${NC}"
    exit 1
fi

echo "  ✓ Pré-requisitos OK"

# ============================================
# Build Backend
# ============================================
echo -e "${YELLOW}[2/6] Building Backend...${NC}"

docker build \
    -t gcr.io/$PROJECT_ID/${APP_NAME}-api:$TIMESTAMP \
    -t gcr.io/$PROJECT_ID/${APP_NAME}-api:latest \
    ./backend

echo "  ✓ Backend build completo"

# ============================================
# Build Frontend
# ============================================
echo -e "${YELLOW}[3/6] Building Frontend...${NC}"

# Criar .env.production para o frontend
cat > frontend/.env.production << EOF
VITE_API_URL=https://${APP_NAME}-api-$(echo $PROJECT_ID | tr -d '-' | head -c 8)-${REGION:0:2}.a.run.app
VITE_ENVIRONMENT=$ENVIRONMENT
EOF

docker build \
    -t gcr.io/$PROJECT_ID/${APP_NAME}-frontend:$TIMESTAMP \
    -t gcr.io/$PROJECT_ID/${APP_NAME}-frontend:latest \
    ./frontend

echo "  ✓ Frontend build completo"

# ============================================
# Push Images
# ============================================
echo -e "${YELLOW}[4/6] Pushing images...${NC}"

docker push gcr.io/$PROJECT_ID/${APP_NAME}-api:$TIMESTAMP
docker push gcr.io/$PROJECT_ID/${APP_NAME}-api:latest
docker push gcr.io/$PROJECT_ID/${APP_NAME}-frontend:$TIMESTAMP
docker push gcr.io/$PROJECT_ID/${APP_NAME}-frontend:latest

echo "  ✓ Images pushed"

# ============================================
# Deploy API
# ============================================
echo -e "${YELLOW}[5/6] Deploying API...${NC}"

gcloud run deploy ${APP_NAME}-api \
    --image gcr.io/$PROJECT_ID/${APP_NAME}-api:$TIMESTAMP \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --service-account ${APP_NAME}-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-secrets "SECRET_KEY=${APP_NAME}-jwt-secret:latest,GEMINI_API_KEY=${APP_NAME}-gemini-api-key:latest" \
    --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=$ENVIRONMENT,GCS_BUCKET_DOCUMENTOS=${PROJECT_ID}-documentos" \
    --vpc-connector ${APP_NAME}-connector \
    --vpc-egress private-ranges-only \
    --min-instances $([ "$ENVIRONMENT" = "prod" ] && echo "1" || echo "0") \
    --max-instances $([ "$ENVIRONMENT" = "prod" ] && echo "10" || echo "2") \
    --memory $([ "$ENVIRONMENT" = "prod" ] && echo "2Gi" || echo "512Mi") \
    --cpu $([ "$ENVIRONMENT" = "prod" ] && echo "2" || echo "1") \
    --timeout 300

API_URL=$(gcloud run services describe ${APP_NAME}-api --region $REGION --format 'value(status.url)')
echo "  ✓ API deployed: $API_URL"

# ============================================
# Deploy Frontend
# ============================================
echo -e "${YELLOW}[6/6] Deploying Frontend...${NC}"

gcloud run deploy ${APP_NAME}-frontend \
    --image gcr.io/$PROJECT_ID/${APP_NAME}-frontend:$TIMESTAMP \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "VITE_API_URL=$API_URL" \
    --min-instances $([ "$ENVIRONMENT" = "prod" ] && echo "1" || echo "0") \
    --max-instances $([ "$ENVIRONMENT" = "prod" ] && echo "5" || echo "2") \
    --memory 256Mi \
    --cpu 1

FRONTEND_URL=$(gcloud run services describe ${APP_NAME}-frontend --region $REGION --format 'value(status.url)')
echo "  ✓ Frontend deployed: $FRONTEND_URL"

# ============================================
# Deploy Worker (opcional)
# ============================================
read -p "Deseja fazer deploy do Celery Worker? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deploying Worker...${NC}"
    
    gcloud run deploy ${APP_NAME}-worker \
        --image gcr.io/$PROJECT_ID/${APP_NAME}-api:$TIMESTAMP \
        --region $REGION \
        --platform managed \
        --no-allow-unauthenticated \
        --service-account ${APP_NAME}-cloudrun@${PROJECT_ID}.iam.gserviceaccount.com \
        --set-secrets "SECRET_KEY=${APP_NAME}-jwt-secret:latest,GEMINI_API_KEY=${APP_NAME}-gemini-api-key:latest" \
        --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID,ENVIRONMENT=$ENVIRONMENT" \
        --vpc-connector ${APP_NAME}-connector \
        --vpc-egress private-ranges-only \
        --command "celery,-A,app.workers.celery_app,worker,--loglevel=info" \
        --no-cpu-throttling \
        --min-instances 0 \
        --max-instances $([ "$ENVIRONMENT" = "prod" ] && echo "5" || echo "1") \
        --memory $([ "$ENVIRONMENT" = "prod" ] && echo "2Gi" || echo "1Gi")
    
    echo "  ✓ Worker deployed"
fi

# ============================================
# Resumo
# ============================================
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Deploy Concluído!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "URLs:"
echo "  API:      $API_URL"
echo "  Frontend: $FRONTEND_URL"
echo "  Docs:     $API_URL/api/v1/docs"
echo ""
echo "Verificar logs:"
echo "  gcloud run services logs read ${APP_NAME}-api --region $REGION"
echo ""
