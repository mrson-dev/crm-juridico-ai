# Deploy no Google Cloud Platform

Este guia detalha como fazer o deploy do CRM Jurídico AI no GCP.

## 📋 Pré-requisitos

### Ferramentas Necessárias
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- [Terraform](https://www.terraform.io/downloads) >= 1.5.0
- [Docker](https://docs.docker.com/get-docker/)
- Conta GCP com billing ativado

### Credenciais Necessárias
- `GCP_PROJECT_ID`: ID do projeto GCP
- `GEMINI_API_KEY`: Chave da API Gemini ([obter aqui](https://aistudio.google.com/))

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Load Balancer                      │
├─────────────────────────────────────────────────────────────┤
│   Cloud Run          Cloud Run          Cloud Run           │
│   (API FastAPI)      (Frontend)         (Celery Worker)     │
├─────────────────────────────────────────────────────────────┤
│   Cloud SQL          Memorystore        Cloud Storage       │
│   (PostgreSQL 16     (Redis 7)          (Documentos)        │
│    + pgvector)                                              │
├─────────────────────────────────────────────────────────────┤
│              Secret Manager + Vertex AI/Gemini              │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Deploy Rápido (Opção 1: Scripts)

### 1. Setup Inicial

```bash
# Clone o repositório
git clone https://github.com/mrson-dev/crm-juridico-ai
cd crm-juridico-ai

# Execute o setup (uma vez)
./scripts/gcp-setup.sh SEU_PROJECT_ID
```

### 2. Configurar Gemini API Key

```bash
echo "SUA_GEMINI_API_KEY" | gcloud secrets create crm-juridico-gemini-api-key --data-file=-
```

### 3. Aplicar Infraestrutura (Terraform)

```bash
cd infra/terraform

# Criar arquivo de variáveis
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars com seus valores

# Inicializar e aplicar
terraform init
terraform plan
terraform apply
```

### 4. Deploy das Aplicações

```bash
cd ../..
./scripts/deploy.sh prod
```

## 🔧 Deploy Detalhado (Opção 2: Manual)

### Passo 1: Criar Projeto GCP

```bash
# Criar projeto
gcloud projects create crm-juridico-prod --name="CRM Jurídico"

# Definir projeto padrão
gcloud config set project crm-juridico-prod

# Habilitar billing (necessário via Console)
```

### Passo 2: Habilitar APIs

```bash
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
    cloudbuild.googleapis.com
```

### Passo 3: Criar VPC e Subnet

```bash
# VPC
gcloud compute networks create crm-juridico-vpc --subnet-mode=custom

# Subnet
gcloud compute networks subnets create crm-juridico-subnet \
    --network=crm-juridico-vpc \
    --region=southamerica-east1 \
    --range=10.0.0.0/24

# VPC Connector para Cloud Run
gcloud compute networks vpc-access connectors create crm-juridico-connector \
    --region=southamerica-east1 \
    --network=crm-juridico-vpc \
    --range=10.8.0.0/28
```

### Passo 4: Criar Cloud SQL

```bash
# Alocar IP privado
gcloud compute addresses create crm-juridico-private-ip \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --network=crm-juridico-vpc

# Conectar VPC ao serviço
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=crm-juridico-private-ip \
    --network=crm-juridico-vpc

# Criar instância PostgreSQL
gcloud sql instances create crm-juridico-db \
    --database-version=POSTGRES_16 \
    --tier=db-custom-2-4096 \
    --region=southamerica-east1 \
    --network=crm-juridico-vpc \
    --no-assign-ip \
    --database-flags=cloudsql.enable_pgvector=on

# Criar database
gcloud sql databases create crm_juridico --instance=crm-juridico-db

# Criar usuário
gcloud sql users create crm_app \
    --instance=crm-juridico-db \
    --password="SENHA_FORTE_AQUI"
```

### Passo 5: Criar Redis (Memorystore)

```bash
gcloud redis instances create crm-juridico-redis \
    --size=1 \
    --region=southamerica-east1 \
    --network=crm-juridico-vpc \
    --redis-version=redis_7_0
```

### Passo 6: Criar Secrets

```bash
# JWT Secret
openssl rand -hex 32 | gcloud secrets create crm-juridico-jwt-secret --data-file=-

# DB Password
echo "SENHA_DO_BANCO" | gcloud secrets create crm-juridico-db-password --data-file=-

# Gemini API Key
echo "SUA_API_KEY" | gcloud secrets create crm-juridico-gemini-api-key --data-file=-
```

### Passo 7: Criar Storage Bucket

```bash
gsutil mb -l southamerica-east1 gs://crm-juridico-prod-documentos
gsutil uniformbucketlevelaccess set on gs://crm-juridico-prod-documentos
```

### Passo 8: Criar Service Account

```bash
# Criar SA
gcloud iam service-accounts create crm-juridico-cloudrun \
    --display-name="CRM Jurídico Cloud Run"

# Permissões
for role in roles/cloudsql.client roles/secretmanager.secretAccessor \
    roles/storage.objectAdmin roles/aiplatform.user; do
    gcloud projects add-iam-policy-binding crm-juridico-prod \
        --member="serviceAccount:crm-juridico-cloudrun@crm-juridico-prod.iam.gserviceaccount.com" \
        --role="$role"
done
```

### Passo 9: Build e Push das Imagens

```bash
# Configurar Docker para GCR
gcloud auth configure-docker gcr.io

# Build Backend
docker build -t gcr.io/crm-juridico-prod/crm-juridico-api:latest ./backend
docker push gcr.io/crm-juridico-prod/crm-juridico-api:latest

# Build Frontend
docker build -t gcr.io/crm-juridico-prod/crm-juridico-frontend:latest ./frontend
docker push gcr.io/crm-juridico-prod/crm-juridico-frontend:latest
```

### Passo 10: Deploy Cloud Run

```bash
# Obter IPs
DB_IP=$(gcloud sql instances describe crm-juridico-db --format='value(ipAddresses[0].ipAddress)')
REDIS_IP=$(gcloud redis instances describe crm-juridico-redis --region=southamerica-east1 --format='value(host)')

# Deploy API
gcloud run deploy crm-juridico-api \
    --image gcr.io/crm-juridico-prod/crm-juridico-api:latest \
    --region southamerica-east1 \
    --platform managed \
    --allow-unauthenticated \
    --service-account crm-juridico-cloudrun@crm-juridico-prod.iam.gserviceaccount.com \
    --set-secrets "SECRET_KEY=crm-juridico-jwt-secret:latest,GEMINI_API_KEY=crm-juridico-gemini-api-key:latest" \
    --set-env-vars "DATABASE_URL=postgresql+asyncpg://crm_app:SENHA@${DB_IP}:5432/crm_juridico" \
    --set-env-vars "REDIS_URL=redis://${REDIS_IP}:6379/0" \
    --set-env-vars "GCP_PROJECT_ID=crm-juridico-prod" \
    --set-env-vars "GCS_BUCKET_DOCUMENTOS=crm-juridico-prod-documentos" \
    --vpc-connector crm-juridico-connector \
    --vpc-egress private-ranges-only \
    --min-instances 1 \
    --max-instances 10 \
    --memory 2Gi

# Obter URL da API
API_URL=$(gcloud run services describe crm-juridico-api --region=southamerica-east1 --format='value(status.url)')

# Deploy Frontend
gcloud run deploy crm-juridico-frontend \
    --image gcr.io/crm-juridico-prod/crm-juridico-frontend:latest \
    --region southamerica-east1 \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "VITE_API_URL=$API_URL" \
    --min-instances 1 \
    --memory 256Mi
```

## 🔄 CI/CD Automático

### Opção A: GitHub Actions

1. Configurar secrets no GitHub:
   - `GCP_PROJECT_ID`
   - `WIF_PROVIDER` (Workload Identity)
   - `WIF_SERVICE_ACCOUNT`

2. Push para `main` aciona deploy automático

### Opção B: Cloud Build

```bash
# Criar trigger
gcloud builds triggers create github \
    --repo-name=crm-juridico-ai \
    --repo-owner=SEU_USUARIO \
    --branch-pattern='^main$' \
    --build-config=cloudbuild.yaml
```

## 💰 Estimativa de Custos (Mensal)

| Recurso | Especificação | Custo Estimado |
|---------|---------------|----------------|
| Cloud SQL | db-custom-2-4096, HA | ~$150 |
| Cloud Run (API) | 2 vCPU, 2GB, min 1 | ~$50 |
| Cloud Run (Frontend) | 1 vCPU, 256MB, min 1 | ~$15 |
| Cloud Run (Worker) | 2 vCPU, 2GB, min 0 | ~$30 |
| Memorystore | 1GB Basic | ~$35 |
| Cloud Storage | 50GB | ~$1 |
| Gemini API | ~100k tokens/dia | ~$20 |
| **Total Estimado** | | **~$300/mês** |

> Para ambiente dev, usar instâncias menores reduz para ~$80/mês

## 🔒 Segurança

### Checklist de Segurança
- [ ] Secrets no Secret Manager (nunca em env vars)
- [ ] VPC privada para DB e Redis
- [ ] Service Account com permissões mínimas
- [ ] Cloud Armor para WAF (opcional)
- [ ] IAP para acesso administrativo (opcional)
- [ ] Audit logs habilitados

### Workload Identity Federation (Recomendado)

```bash
# Criar pool
gcloud iam workload-identity-pools create github-pool \
    --location="global"

# Criar provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location="global" \
    --workload-identity-pool="github-pool" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository"

# Permitir GitHub Actions usar SA
gcloud iam service-accounts add-iam-policy-binding \
    crm-juridico-cloudrun@crm-juridico-prod.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/SEU_USUARIO/crm-juridico-ai"
```

## 🐛 Troubleshooting

### Erro de conexão com DB
```bash
# Verificar conectividade
gcloud sql connect crm-juridico-db --user=crm_app

# Verificar VPC connector
gcloud compute networks vpc-access connectors describe crm-juridico-connector --region=southamerica-east1
```

### Logs do Cloud Run
```bash
# API
gcloud run services logs read crm-juridico-api --region=southamerica-east1 --limit=100

# Em tempo real
gcloud run services logs tail crm-juridico-api --region=southamerica-east1
```

### Erro de permissão
```bash
# Verificar permissões da SA
gcloud projects get-iam-policy crm-juridico-prod \
    --filter="bindings.members:crm-juridico-cloudrun" \
    --format="table(bindings.role)"
```

## 📚 Referências

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
