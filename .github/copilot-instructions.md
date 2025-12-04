# Copilot Instructions - CRM Jurídico AI

## Visão Geral
CRM especializado em **Direito Previdenciário** (INSS) com IA integrada para escritórios de advocacia. Arquitetura cloud-native na **Google Cloud Platform (GCP)**.

### Stack Principal
| Camada | Tecnologia |
|--------|------------|
| **Backend** | Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) |
| **Frontend** | React 18 + TypeScript + Vite + TailwindCSS |
| **Banco de Dados** | Cloud SQL (PostgreSQL 16) + pgvector |
| **IA/ML** | Vertex AI / Gemini API (extração, embeddings, RAG) |
| **Storage** | Cloud Storage (documentos jurídicos) |
| **Mensageria** | Celery + Redis / Cloud Tasks / Pub/Sub |
| **Cache** | Redis (Memorystore) |
| **Autenticação** | Firebase Auth + JWT local (fallback) |
| **Infra** | Cloud Run (containers) / Secret Manager |

---

## Estrutura Completa do Projeto

```
crm-juridico-ai/
├── .github/
│   └── copilot-instructions.md
├── docker-compose.yml
├── README.md
└── backend/
    ├── Dockerfile
    ├── pyproject.toml
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    │       └── 001_initial.py           # Migration inicial completa
    └── app/
        ├── main.py                       # FastAPI app entry point
        ├── ai/
        │   └── gemini_service.py         # IA: extração, embeddings, RAG
        ├── api/v1/
        │   ├── router.py                 # Agregador de rotas
        │   └── endpoints/
        │       ├── auth.py               # Login, registro, Firebase
        │       ├── clientes.py           # CRUD clientes + documentos
        │       ├── processos.py          # CRUD processos + prazos + andamentos
        │       ├── documentos.py         # Upload, download, processamento IA
        │       ├── notificacoes.py       # Notificações + preferências
        │       ├── honorarios.py         # Contratos + parcelas + dashboard
        │       └── health.py             # Health check
        ├── core/
        │   ├── config.py                 # Settings (Pydantic BaseSettings)
        │   ├── dependencies.py           # DBSession, CurrentUser, etc.
        │   ├── exceptions.py             # CRMException, handlers
        │   ├── firebase_auth.py          # Firebase Admin SDK
        │   ├── logging.py                # structlog JSON
        │   ├── middleware.py             # RequestID, Timing, ErrorHandler
        │   ├── security.py               # JWT, password hashing
        │   └── storage.py                # GCS upload/download/signed URLs
        ├── db/
        │   ├── base.py                   # Base, MultiTenantBase
        │   └── session.py                # AsyncSession factory
        ├── models/
        │   ├── cliente.py                # Cliente (LGPD compliant)
        │   ├── documento.py              # Documento + embeddings
        │   ├── escritorio.py             # Escritório (tenant)
        │   ├── honorario.py              # ContratoHonorario + Parcela
        │   ├── notificacao.py            # Notificacao + Preferencias
        │   ├── processo.py               # Processo + Prazo + Andamento
        │   └── usuario.py                # Usuario + Roles
        ├── repositories/
        │   ├── base.py                   # BaseRepository, MultiTenantRepository
        │   ├── cliente_repository.py
        │   ├── documento_repository.py
        │   ├── escritorio_repository.py
        │   ├── honorario_repository.py
        │   ├── notificacao_repository.py
        │   ├── processo_repository.py
        │   └── usuario_repository.py
        ├── schemas/
        │   ├── base.py                   # APIResponse[T], PaginatedResponse[T]
        │   ├── cliente.py
        │   ├── documento.py
        │   ├── escritorio.py
        │   ├── honorario.py
        │   ├── notificacao.py
        │   ├── processo.py
        │   └── usuario.py
        ├── services/
        │   ├── auth_service.py           # Login, registro, Firebase sync
        │   ├── cliente_service.py
        │   ├── documento_service.py      # Upload + processamento IA
        │   ├── escritorio_service.py
        │   ├── honorario_service.py      # Contratos + parcelas + dashboard
        │   ├── notificacao_service.py    # Push, email, in-app
        │   └── processo_service.py       # Prazos, andamentos, CNJ
        └── workers/
            ├── celery_app.py             # Celery config + beat schedule
            ├── calculation_tasks.py      # Cálculos previdenciários
            ├── document_tasks.py         # OCR, extração, embeddings
            └── notification_tasks.py     # Push, email, verificação prazos
```

---

## Arquitetura em Camadas

### Fluxo de Dados
```
Request → Middleware → Endpoint → Service → Repository → Model → Database
                         ↓
                    GeminiService (IA)
                         ↓
                    Celery Workers (async)
```

### Camadas e Responsabilidades

| Camada | Responsabilidade | Exemplo |
|--------|------------------|---------|
| **Endpoints** | Validação HTTP, serialização | `processos.py` |
| **Services** | Regras de negócio, orquestração | `ProcessoService` |
| **Repositories** | Queries, isolamento multi-tenant | `ProcessoRepository` |
| **Models** | Estrutura de dados, relacionamentos | `Processo`, `Prazo` |
| **Workers** | Tarefas assíncronas | `document_tasks.py` |

---

## Padrões Obrigatórios

### Multi-tenancy (CRÍTICO)
Todas as entidades de negócio são isoladas por `escritorio_id`:

```python
# models/ - Sempre herdar de MultiTenantBase
class Cliente(MultiTenantBase):
    __tablename__ = "clientes"
    # escritorio_id é herdado automaticamente

# services/ - Sempre receber escritorio_id no construtor
class ClienteService:
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        self._repo = ClienteRepository(db, escritorio_id)

# repositories/ - MultiTenantRepository filtra automaticamente
class ClienteRepository(MultiTenantRepository[Cliente]):
    def __init__(self, db: AsyncSession, escritorio_id: UUID):
        super().__init__(Cliente, db, escritorio_id)
```

### Responses Padronizadas
```python
from app.schemas.base import APIResponse, PaginatedResponse

# Sucesso simples
return APIResponse(success=True, data=ClienteResponse.model_validate(cliente))

# Lista paginada
return PaginatedResponse(
    success=True,
    data=[ClienteResponse.model_validate(c) for c in clientes],
    total=total,
    page=page,
    page_size=page_size
)

# Erro
raise CRMException(code="CLIENTE_NOT_FOUND", message="Cliente não encontrado", status_code=404)
```

### Dependency Injection
```python
from app.core.dependencies import DBSession, CurrentUser, CurrentEscritorio

@router.get("")
async def listar(
    db: DBSession,
    current_user: CurrentUser,
    escritorio_id: CurrentEscritorio
):
    service = ClienteService(db, escritorio_id)
    return await service.listar()
```

---

## API Endpoints

### Autenticação (`/api/v1/auth`)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/login` | Login com email/senha (JWT) |
| POST | `/login/firebase` | Login com Firebase token |
| POST | `/register` | Registro local |
| POST | `/register/firebase` | Registro via Firebase |
| GET | `/me` | Usuário atual |
| PUT | `/me` | Atualizar perfil |
| POST | `/change-password` | Alterar senha |

### Clientes (`/api/v1/clientes`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Listar clientes (paginado) |
| POST | `/` | Criar cliente |
| GET | `/{id}` | Buscar por ID |
| PUT | `/{id}` | Atualizar cliente |
| DELETE | `/{id}` | Soft delete |
| GET | `/search` | Busca por CPF/nome |
| POST | `/{id}/documentos` | Upload de documento |

### Processos (`/api/v1/processos`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Listar processos |
| POST | `/` | Criar processo |
| GET | `/{id}` | Buscar por ID |
| PUT | `/{id}` | Atualizar processo |
| GET | `/prazos/proximos` | Prazos próximos (7 dias) |
| POST | `/{id}/prazos` | Adicionar prazo |
| POST | `/{id}/andamentos` | Adicionar andamento |
| POST | `/prazos/{id}/concluir` | Marcar prazo concluído |

### Documentos (`/api/v1/documentos`)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/upload` | Upload para GCS |
| GET | `/{id}/download` | Download (URL assinada) |
| POST | `/{id}/processar-ia` | Processar com Gemini |
| POST | `/extract-identity` | Extrair RG/CNH/CPF |
| POST | `/extract-cnis` | Extrair vínculos CNIS |
| POST | `/analyze-ppp` | Analisar PPP (especial) |

### Notificações (`/api/v1/notificacoes`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Listar notificações |
| GET | `/stats` | Estatísticas (não lidas) |
| POST | `/{id}/lida` | Marcar como lida |
| GET | `/preferencias` | Preferências do usuário |
| PUT | `/preferencias` | Atualizar preferências |

### Honorários (`/api/v1/honorarios`)
| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/contratos` | Listar contratos |
| POST | `/contratos` | Criar contrato |
| GET | `/contratos/{id}` | Buscar contrato |
| POST | `/parcelas/{id}/pagamento` | Registrar pagamento |
| GET | `/dashboard` | Dashboard financeiro |
| GET | `/parcelas/atrasadas` | Parcelas em atraso |

---

## Integração IA (GeminiService)

### Métodos Implementados

```python
from app.ai.gemini_service import GeminiService

gemini = GeminiService()

# Extração de documentos
dados_rg = await gemini.extract_identity_document(image_bytes, "image/jpeg")
dados_cnis = await gemini.extract_cnis(pdf_bytes)
dados_ppp = await gemini.analyze_ppp(pdf_bytes)

# Resumo estruturado
resumo = await gemini.summarize_document(pdf_bytes, "sentença judicial")

# Embeddings para busca semântica (768 dimensões)
embedding = await gemini.generate_embeddings("texto do documento")

# RAG - Resposta baseada em contexto
resposta = await gemini.answer_question(
    question="Qual o tempo de contribuição?",
    context_documents=["doc1...", "doc2..."]
)

# Geração de petições
peticao = await gemini.generate_legal_document(
    tipo="recurso_inss",
    dados_cliente={"nome": "...", "cpf": "..."},
    dados_processo={"numero": "...", "tipo_beneficio": "..."}
)
```

### Tipos de Documento Suportados
- **Identidade**: RG, CNH, CPF → dados pessoais
- **CNIS**: Extrato previdenciário → vínculos e contribuições
- **PPP**: Perfil Profissiográfico → agentes nocivos
- **Sentença**: Decisão judicial → resumo estruturado
- **Petição**: Geração automática → recursos, iniciais

---

## Workers (Celery Tasks)

### Configuração
```python
# celery_app.py
celery_app = Celery("crm_juridico")
celery_app.conf.broker_url = settings.REDIS_URL
celery_app.conf.beat_schedule = {
    "check-prazos-every-30-min": {
        "task": "app.workers.notification_tasks.check_upcoming_deadlines",
        "schedule": 1800.0,
    },
    "send-notifications-every-5-min": {
        "task": "app.workers.notification_tasks.send_batch_notifications",
        "schedule": 300.0,
    },
}
```

### Tasks Disponíveis

| Task | Módulo | Descrição |
|------|--------|-----------|
| `process_document_ocr` | document_tasks | OCR via Gemini |
| `extract_document_data` | document_tasks | Extração estruturada |
| `generate_document_embeddings` | document_tasks | Vetorização pgvector |
| `send_push_notification` | notification_tasks | Firebase Cloud Messaging |
| `send_email_notification` | notification_tasks | SendGrid/SES |
| `check_upcoming_deadlines` | notification_tasks | Verificar prazos |
| `calculate_tempo_contribuicao` | calculation_tasks | Tempo de contribuição |
| `simulate_aposentadoria` | calculation_tasks | Simulação de benefício |
| `calculate_rmi` | calculation_tasks | Renda Mensal Inicial |

### Executar Workers
```bash
# Worker principal
celery -A app.workers.celery_app worker --loglevel=info

# Beat scheduler (periodic tasks)
celery -A app.workers.celery_app beat --loglevel=info

# Flower (monitoramento)
celery -A app.workers.celery_app flower --port=5555
```

---

## Domínio Previdenciário

### Entidades e Relacionamentos

```
Escritorio (tenant)
    ├── Usuario (advogados, secretários)
    ├── Cliente (segurados INSS)
    │   ├── Documento (CNIS, PPP, laudos)
    │   └── Processo
    │       ├── Prazo (datas fatais ⚠️)
    │       ├── Andamento (movimentações)
    │       └── ContratoHonorario
    │           └── ParcelaHonorario
    └── Notificacao
```

### Enums Principais

```python
# TipoBeneficio
APOSENTADORIA_IDADE = "aposentadoria_idade"
APOSENTADORIA_TEMPO_CONTRIBUICAO = "aposentadoria_tempo_contribuicao"
APOSENTADORIA_ESPECIAL = "aposentadoria_especial"
APOSENTADORIA_INVALIDEZ = "aposentadoria_invalidez"
AUXILIO_DOENCA = "auxilio_doenca"
AUXILIO_ACIDENTE = "auxilio_acidente"
BPC_LOAS_IDOSO = "bpc_loas_idoso"
BPC_LOAS_DEFICIENTE = "bpc_loas_deficiente"
PENSAO_MORTE = "pensao_morte"
SALARIO_MATERNIDADE = "salario_maternidade"
REVISAO_BENEFICIO = "revisao_beneficio"

# FaseProcessual
ADMINISTRATIVO = "administrativo"
JUDICIAL_PRIMEIRA_INSTANCIA = "judicial_1a_instancia"
JUDICIAL_SEGUNDA_INSTANCIA = "judicial_2a_instancia"
TRIBUNAL_SUPERIOR = "tribunal_superior"
CUMPRIMENTO_SENTENCA = "cumprimento_sentenca"
ENCERRADO = "encerrado"

# StatusPrazo
PENDENTE = "pendente"
CONCLUIDO = "concluido"
CANCELADO = "cancelado"
PERDIDO = "perdido"
```

### Validações de Domínio

```python
# CPF (11 dígitos)
cpf: str = Field(..., pattern=r"^\d{11}$")

# CNPJ (14 dígitos)
cnpj: str = Field(..., pattern=r"^\d{14}$")

# Número CNJ (padrão único nacional)
numero_cnj: str = Field(..., pattern=r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")
# Exemplo: 1234567-89.2024.8.26.0100

# NIT/PIS (11 dígitos)
nit: str = Field(..., pattern=r"^\d{11}$")
```

---

## Convenções de Código

| Aspecto | Convenção | Exemplo |
|---------|-----------|---------|
| **Código** | Inglês | `get_cliente_by_cpf()` |
| **Documentação** | Português BR | `"""Busca cliente por CPF."""` |
| **Domínio jurídico** | Português | `numero_cnj`, `data_fatal` |
| **Schemas** | Sufixos padrão | `Create`, `Update`, `Response` |
| **Imports** | Absolutos | `from app.services import ClienteService` |

### Nomenclatura de Arquivos
- Models: singular (`cliente.py`)
- Schemas: singular (`cliente.py`)
- Repositories: singular + sufixo (`cliente_repository.py`)
- Services: singular + sufixo (`cliente_service.py`)
- Endpoints: plural (`clientes.py`)

---

## Comandos de Desenvolvimento

### Ambiente Local

```bash
# Subir infraestrutura (PostgreSQL pgvector + Redis)
docker-compose up -d

# Backend
cd backend
poetry install
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload --port 8000

# Celery workers
poetry run celery -A app.workers.celery_app worker --loglevel=info
poetry run celery -A app.workers.celery_app beat --loglevel=info

# Testes
poetry run pytest --cov=app --cov-report=html
poetry run pytest -x -v  # modo debug

# Lint e type check
poetry run ruff check . --fix
poetry run mypy .
```

### Migrations

```bash
# Criar nova migration
poetry run alembic revision --autogenerate -m "add_nova_tabela"

# Aplicar migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1

# Ver histórico
poetry run alembic history
```

---

## Segurança

### Multi-tenancy
- ✅ Isolamento por `escritorio_id` em **todas** as queries
- ✅ `MultiTenantRepository` filtra automaticamente
- ✅ Validação no endpoint via `CurrentEscritorio`

### LGPD
- ✅ `consentimento_lgpd` + `data_consentimento` obrigatórios em Cliente
- ✅ Soft delete com `is_active` (nunca hard delete)
- ✅ Logs de acesso a dados sensíveis

### Autenticação
- ✅ Firebase Auth (produção) + JWT local (desenvolvimento)
- ✅ Refresh tokens com rotação
- ✅ Rate limiting por IP/usuário

### Secrets
- ✅ Secret Manager para credenciais
- ✅ Nunca commitar `.env` ou secrets
- ✅ Variáveis de ambiente validadas no startup

---

## Infraestrutura GCP (Produção)

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Armor + IAP                        │
│                  (WAF, DDoS, Autenticação)                  │
├─────────────────────────────────────────────────────────────┤
│                      Cloud Load Balancer                    │
├─────────────────────────────────────────────────────────────┤
│   Cloud Run          Cloud Run          Cloud Run           │
│   (API FastAPI)      (Celery Worker)    (Celery Beat)       │
├─────────────────────────────────────────────────────────────┤
│   Cloud SQL          Memorystore        Cloud Storage       │
│   (PostgreSQL        (Redis)            (Documentos         │
│    + pgvector)                          Jurídicos)          │
├─────────────────────────────────────────────────────────────┤
│              Vertex AI / Gemini API                         │
│   (OCR, Extração, Embeddings 768d, RAG, Document Gen)       │
├─────────────────────────────────────────────────────────────┤
│   Cloud Tasks        Pub/Sub            Cloud Scheduler     │
│   (Async Jobs)       (Eventos)          (Cron Jobs)         │
├─────────────────────────────────────────────────────────────┤
│   Firebase Auth      Cloud Logging      Secret Manager      │
│   (Autenticação)     (Observability)    (Credentials)       │
└─────────────────────────────────────────────────────────────┘
```

### Variáveis de Ambiente

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/crm_juridico

# GCP
GCP_PROJECT_ID=crm-juridico-prod
GCS_BUCKET_DOCUMENTOS=crm-juridico-docs-prod
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# AI
GEMINI_API_KEY=...                    # ou usar ADC (Application Default Credentials)
GEMINI_MODEL=gemini-1.5-pro

# Cache/Queue
REDIS_URL=redis://10.0.0.1:6379/0

# Auth
SECRET_KEY=...                        # JWT signing key (256 bits)
FIREBASE_PROJECT_ID=crm-juridico-prod
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-adminsdk.json

# Email (opcional)
SENDGRID_API_KEY=...
FROM_EMAIL=noreply@crm-juridico.com.br

# Environment
ENVIRONMENT=production                # development, staging, production
LOG_LEVEL=INFO
```

---

## Checklist para Novas Features

### Novo Model
- [ ] Criar em `models/` herdando `MultiTenantBase`
- [ ] Adicionar relacionamentos (FK, backref)
- [ ] Exportar em `models/__init__.py`
- [ ] Criar migration com `alembic revision --autogenerate`

### Novo Schema
- [ ] Criar em `schemas/` com `Create`, `Update`, `Response`
- [ ] Usar `BaseSchema` como base
- [ ] Adicionar validações (Field, validator)
- [ ] Exportar em `schemas/__init__.py`

### Novo Repository
- [ ] Criar em `repositories/` herdando `MultiTenantRepository`
- [ ] Implementar métodos específicos de query
- [ ] Exportar em `repositories/__init__.py`

### Novo Service
- [ ] Criar em `services/` recebendo `db` e `escritorio_id`
- [ ] Injetar repository no construtor
- [ ] Implementar regras de negócio
- [ ] Exportar em `services/__init__.py`

### Novo Endpoint
- [ ] Criar em `api/v1/endpoints/`
- [ ] Usar `DBSession`, `CurrentUser`, `CurrentEscritorio`
- [ ] Retornar `APIResponse[T]` ou `PaginatedResponse[T]`
- [ ] Adicionar router em `api/v1/router.py`
- [ ] Documentar com docstrings (OpenAPI)

### Nova Task (Celery)
- [ ] Criar em `workers/`
- [ ] Decorar com `@celery_app.task`
- [ ] Adicionar ao beat_schedule se periódica
- [ ] Testar isoladamente antes de deploy

