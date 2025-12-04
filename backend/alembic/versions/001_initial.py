"""
Initial migration - CRM Jurídico AI

Revision ID: 001
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensão pgvector para embeddings
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # ========================
    # ENUMS (valores exatos do Python Enum)
    # ========================
    
    # UserRole - valores em lowercase como definido no Enum Python
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'advogado', 'estagiario', 'secretaria', 'financeiro')")
    
    # TipoPessoa
    op.execute("CREATE TYPE tipopessoa AS ENUM ('fisica', 'juridica')")
    
    # EstadoCivil
    op.execute("CREATE TYPE estadocivil AS ENUM ('solteiro', 'casado', 'divorciado', 'viuvo', 'uniao_estavel')")
    
    # TipoBeneficio
    op.execute("""CREATE TYPE tipobeneficio AS ENUM (
        'aposentadoria_idade', 'aposentadoria_tempo_contribuicao', 'aposentadoria_especial',
        'aposentadoria_rural', 'aposentadoria_invalidez', 'aposentadoria_programada',
        'auxilio_doenca', 'auxilio_acidente', 'bpc_loas_idoso', 'bpc_loas_deficiencia',
        'pensao_morte', 'auxilio_reclusao', 'salario_maternidade', 'revisao_beneficio', 'outros'
    )""")
    
    # FaseProcessual
    op.execute("""CREATE TYPE faseprocessual AS ENUM (
        'requerimento_administrativo', 'recurso_administrativo',
        'inicial_protocolada', 'citacao', 'contestacao', 'pericia_agendada',
        'pericia_realizada', 'alegacoes_finais', 'sentenca',
        'recurso_inss', 'contrarrazoes', 'tribunal', 'acordao',
        'execucao', 'rpv_precatorio', 'arquivado', 'transitado_julgado'
    )""")
    
    # StatusPrazo
    op.execute("CREATE TYPE statusprazo AS ENUM ('pendente', 'em_andamento', 'cumprido', 'perdido', 'cancelado')")
    
    # TipoPrazo
    op.execute("""CREATE TYPE tipoprazo AS ENUM (
        'contestacao', 'recurso', 'manifestacao', 'pericia',
        'audiencia', 'cumprimento_sentenca', 'juntada_documentos', 'outros'
    )""")
    
    # TipoDocumento
    op.execute("""CREATE TYPE tipodocumento AS ENUM (
        'rg', 'cpf', 'cnh', 'certidao_nascimento', 'certidao_casamento',
        'titulo_eleitor', 'comprovante_residencia',
        'cnis', 'ppp', 'ctps', 'carta_concessao', 'carta_indeferimento',
        'laudo_medico', 'atestado', 'exame', 'receituario',
        'peticao_inicial', 'contestacao', 'recurso', 'sentenca', 'acordao', 'mandado',
        'procuracao', 'contrato_honorarios', 'comprovante_pagamento', 'outros'
    )""")
    
    # StatusProcessamentoIA
    op.execute("CREATE TYPE statusprocessamentoia AS ENUM ('pendente', 'processando', 'concluido', 'erro')")
    
    # TipoHonorario
    op.execute("CREATE TYPE tipohonorario AS ENUM ('fixo', 'parcelado', 'exito', 'misto', 'hora')")
    
    # StatusContrato
    op.execute("CREATE TYPE statuscontrato AS ENUM ('rascunho', 'ativo', 'suspenso', 'cancelado', 'concluido')")
    
    # StatusParcela
    op.execute("CREATE TYPE statusparcela AS ENUM ('pendente', 'pago', 'atrasado', 'cancelado')")
    
    # FormaPagamento
    op.execute("CREATE TYPE formapagamento AS ENUM ('dinheiro', 'pix', 'transferencia', 'cartao_credito', 'cartao_debito', 'boleto', 'cheque')")
    
    # TipoNotificacao
    op.execute("""CREATE TYPE tiponotificacao AS ENUM (
        'prazo_vencendo', 'prazo_hoje', 'prazo_vencido',
        'novo_andamento', 'mudanca_fase', 'documento_processado',
        'sistema', 'alerta'
    )""")
    
    # CanalNotificacao
    op.execute("CREATE TYPE canalnotificacao AS ENUM ('push', 'email', 'sms', 'in_app')")
    
    # StatusNotificacao
    op.execute("CREATE TYPE statusnotificacao AS ENUM ('pendente', 'enviada', 'lida', 'falha')")
    
    # ========================
    # TABELA: escritorios (tenant principal)
    # ========================
    op.create_table(
        "escritorios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Dados básicos
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("razao_social", sa.String(255), nullable=True),
        sa.Column("cnpj", sa.String(18), nullable=True, unique=True),
        sa.Column("oab_sociedade", sa.String(20), nullable=True),
        # Contato
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("telefone", sa.String(20), nullable=True),
        # Endereço
        sa.Column("endereco", sa.Text(), nullable=True),
        sa.Column("cidade", sa.String(100), nullable=True),
        sa.Column("estado", sa.String(2), nullable=True),
        sa.Column("cep", sa.String(10), nullable=True),
        # Configurações
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("logo_path", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # ========================
    # TABELA: usuarios
    # ========================
    op.create_table(
        "usuarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Firebase Auth
        sa.Column("firebase_uid", sa.String(128), nullable=True, unique=True),
        # Autenticação local
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        # Dados pessoais
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cpf", sa.String(14), nullable=True, unique=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("avatar_path", sa.String(500), nullable=True),
        # Dados profissionais (advogados)
        sa.Column("oab_numero", sa.String(20), nullable=True),
        sa.Column("oab_estado", sa.String(2), nullable=True),
        # Controle de acesso - usar o tipo enum PostgreSQL criado acima
        sa.Column("role", postgresql.ENUM('admin', 'advogado', 'estagiario', 'secretaria', 'financeiro', name='userrole', create_type=False), nullable=False, server_default="advogado"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        # Preferências (JSON em texto)
        sa.Column("preferences", sa.Text(), nullable=True, comment="JSON com preferências do usuário"),
        # Relacionamento com escritório
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"])
    op.create_index("ix_usuarios_firebase_uid", "usuarios", ["firebase_uid"])
    op.create_index("ix_usuarios_escritorio_id", "usuarios", ["escritorio_id"])
    
    # ========================
    # TABELA: clientes
    # ========================
    op.create_table(
        "clientes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Tipo de pessoa
        sa.Column("tipo_pessoa", postgresql.ENUM('fisica', 'juridica', name='tipopessoa', create_type=False), nullable=False, server_default="fisica"),
        # Identificação
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("cpf", sa.String(14), nullable=True),
        sa.Column("rg", sa.String(20), nullable=True),
        sa.Column("rg_orgao_emissor", sa.String(20), nullable=True),
        sa.Column("rg_data_emissao", sa.Date(), nullable=True),
        # Pessoa jurídica
        sa.Column("cnpj", sa.String(18), nullable=True),
        sa.Column("razao_social", sa.String(255), nullable=True),
        # Dados pessoais
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("sexo", sa.String(1), nullable=True),
        sa.Column("estado_civil", postgresql.ENUM('solteiro', 'casado', 'divorciado', 'viuvo', 'uniao_estavel', name='estadocivil', create_type=False), nullable=True),
        sa.Column("profissao", sa.String(100), nullable=True),
        sa.Column("nacionalidade", sa.String(50), nullable=True, server_default="Brasileira"),
        sa.Column("naturalidade", sa.String(100), nullable=True),
        # Filiação
        sa.Column("nome_mae", sa.String(255), nullable=True),
        sa.Column("nome_pai", sa.String(255), nullable=True),
        # Contato
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("telefone", sa.String(20), nullable=True),
        sa.Column("telefone_secundario", sa.String(20), nullable=True),
        # Endereço
        sa.Column("cep", sa.String(10), nullable=True),
        sa.Column("logradouro", sa.String(255), nullable=True),
        sa.Column("numero", sa.String(20), nullable=True),
        sa.Column("complemento", sa.String(100), nullable=True),
        sa.Column("bairro", sa.String(100), nullable=True),
        sa.Column("cidade", sa.String(100), nullable=True),
        sa.Column("estado", sa.String(2), nullable=True),
        # Dados previdenciários
        sa.Column("nit_pis_pasep", sa.String(20), nullable=True),
        sa.Column("ctps_numero", sa.String(20), nullable=True),
        sa.Column("ctps_serie", sa.String(10), nullable=True),
        sa.Column("ctps_estado", sa.String(2), nullable=True),
        # Dados bancários
        sa.Column("banco", sa.String(100), nullable=True),
        sa.Column("agencia", sa.String(20), nullable=True),
        sa.Column("conta", sa.String(30), nullable=True),
        sa.Column("tipo_conta", sa.String(20), nullable=True),
        # Observações
        sa.Column("observacoes", sa.Text(), nullable=True),
        # Status e LGPD
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("consentimento_lgpd", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("data_consentimento", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
    )
    op.create_index("ix_clientes_nome", "clientes", ["nome"])
    op.create_index("ix_clientes_cpf", "clientes", ["cpf"])
    op.create_index("ix_clientes_escritorio_id", "clientes", ["escritorio_id"])
    
    # ========================
    # TABELA: processos
    # ========================
    op.create_table(
        "processos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Identificação do processo
        sa.Column("numero_cnj", sa.String(25), nullable=True, unique=True, comment="Formato: NNNNNNN-DD.AAAA.J.TR.OOOO"),
        sa.Column("numero_administrativo", sa.String(30), nullable=True, comment="Número do requerimento no INSS"),
        # Tipo de benefício
        sa.Column("tipo_beneficio", postgresql.ENUM(
            'aposentadoria_idade', 'aposentadoria_tempo_contribuicao', 'aposentadoria_especial',
            'aposentadoria_rural', 'aposentadoria_invalidez', 'aposentadoria_programada',
            'auxilio_doenca', 'auxilio_acidente', 'bpc_loas_idoso', 'bpc_loas_deficiencia',
            'pensao_morte', 'auxilio_reclusao', 'salario_maternidade', 'revisao_beneficio', 'outros',
            name='tipobeneficio', create_type=False
        ), nullable=False),
        # Fase atual
        sa.Column("fase", postgresql.ENUM(
            'requerimento_administrativo', 'recurso_administrativo',
            'inicial_protocolada', 'citacao', 'contestacao', 'pericia_agendada',
            'pericia_realizada', 'alegacoes_finais', 'sentenca',
            'recurso_inss', 'contrarrazoes', 'tribunal', 'acordao',
            'execucao', 'rpv_precatorio', 'arquivado', 'transitado_julgado',
            name='faseprocessual', create_type=False
        ), nullable=False, server_default="requerimento_administrativo"),
        # Localização (judicial)
        sa.Column("tribunal", sa.String(20), nullable=True),
        sa.Column("vara", sa.String(100), nullable=True),
        sa.Column("comarca", sa.String(100), nullable=True),
        # Localização (administrativo)
        sa.Column("agencia_inss", sa.String(100), nullable=True),
        # Datas importantes
        sa.Column("data_entrada", sa.Date(), nullable=False),
        sa.Column("data_distribuicao", sa.Date(), nullable=True),
        sa.Column("data_citacao", sa.Date(), nullable=True),
        sa.Column("data_sentenca", sa.Date(), nullable=True),
        sa.Column("data_transito", sa.Date(), nullable=True),
        # Valores
        sa.Column("valor_causa", sa.Float(), nullable=True),
        sa.Column("valor_condenacao", sa.Float(), nullable=True),
        # Descrição
        sa.Column("objeto", sa.Text(), nullable=True, comment="Descrição do pedido"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("resultado", sa.String(50), nullable=True, comment="procedente, improcedente, acordo, desistencia"),
        # Relacionamentos
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("advogado_responsavel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["advogado_responsavel_id"], ["usuarios.id"]),
    )
    op.create_index("ix_processos_numero_cnj", "processos", ["numero_cnj"])
    op.create_index("ix_processos_numero_administrativo", "processos", ["numero_administrativo"])
    op.create_index("ix_processos_escritorio_id", "processos", ["escritorio_id"])
    op.create_index("ix_processos_cliente_id", "processos", ["cliente_id"])
    
    # ========================
    # TABELA: prazos
    # ========================
    op.create_table(
        "prazos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Vinculação ao processo
        sa.Column("processo_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Dados do prazo
        sa.Column("tipo", postgresql.ENUM(
            'contestacao', 'recurso', 'manifestacao', 'pericia',
            'audiencia', 'cumprimento_sentenca', 'juntada_documentos', 'outros',
            name='tipoprazo', create_type=False
        ), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=False),
        # Datas
        sa.Column("data_fatal", sa.Date(), nullable=False, comment="Data limite para cumprimento"),
        sa.Column("data_inicio", sa.Date(), nullable=True, comment="Data de início da contagem"),
        sa.Column("dias_prazo", sa.Integer(), nullable=True),
        # Status
        sa.Column("status", postgresql.ENUM('pendente', 'em_andamento', 'cumprido', 'perdido', 'cancelado', name='statusprazo', create_type=False), nullable=False, server_default="pendente"),
        # Controle de cumprimento
        sa.Column("data_cumprimento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cumprido_por_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Notificações
        sa.Column("notificacao_enviada", sa.Boolean(), nullable=False, server_default="false"),
        # Observações
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["processo_id"], ["processos.id"]),
        sa.ForeignKeyConstraint(["cumprido_por_id"], ["usuarios.id"]),
    )
    op.create_index("ix_prazos_data_fatal", "prazos", ["data_fatal"])
    op.create_index("ix_prazos_status", "prazos", ["status"])
    op.create_index("ix_prazos_processo_id", "prazos", ["processo_id"])
    op.create_index("ix_prazos_escritorio_id", "prazos", ["escritorio_id"])
    
    # ========================
    # TABELA: andamentos
    # ========================
    op.create_table(
        "andamentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Vinculação ao processo
        sa.Column("processo_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Dados do andamento
        sa.Column("data", sa.DateTime(timezone=True), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        # Origem
        sa.Column("fonte", sa.String(50), nullable=True, comment="manual, pje, esaj, push"),
        # Flags
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("gera_prazo", sa.Boolean(), nullable=False, server_default="false"),
        # Quem registrou
        sa.Column("registrado_por_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["processo_id"], ["processos.id"]),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["usuarios.id"]),
    )
    op.create_index("ix_andamentos_data", "andamentos", ["data"])
    op.create_index("ix_andamentos_processo_id", "andamentos", ["processo_id"])
    op.create_index("ix_andamentos_escritorio_id", "andamentos", ["escritorio_id"])
    
    # ========================
    # TABELA: documentos
    # ========================
    op.create_table(
        "documentos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Identificação do documento
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("tipo", postgresql.ENUM(
            'rg', 'cpf', 'cnh', 'certidao_nascimento', 'certidao_casamento',
            'titulo_eleitor', 'comprovante_residencia',
            'cnis', 'ppp', 'ctps', 'carta_concessao', 'carta_indeferimento',
            'laudo_medico', 'atestado', 'exame', 'receituario',
            'peticao_inicial', 'contestacao', 'recurso', 'sentenca', 'acordao', 'mandado',
            'procuracao', 'contrato_honorarios', 'comprovante_pagamento', 'outros',
            name='tipodocumento', create_type=False
        ), nullable=False, server_default="outros"),
        sa.Column("descricao", sa.Text(), nullable=True),
        # Armazenamento
        sa.Column("gcs_bucket", sa.String(255), nullable=False),
        sa.Column("gcs_path", sa.String(500), nullable=False, unique=True),
        # Metadados do arquivo
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
        sa.Column("hash_sha256", sa.String(64), nullable=True),
        # Versionamento
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("documento_original_id", postgresql.UUID(as_uuid=True), nullable=True, comment="ID do documento original se esta for uma versão"),
        # Processamento de IA
        sa.Column("status_ia", postgresql.ENUM('pendente', 'processando', 'concluido', 'erro', name='statusprocessamentoia', create_type=False), nullable=False, server_default="pendente"),
        sa.Column("dados_extraidos", sa.Text(), nullable=True, comment="JSON com dados extraídos pela IA"),
        sa.Column("resumo_ia", sa.Text(), nullable=True, comment="Resumo gerado pela IA"),
        sa.Column("processado_em", sa.DateTime(timezone=True), nullable=True),
        # Vinculações
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("processo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["documento_original_id"], ["documentos.id"]),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["processo_id"], ["processos.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["usuarios.id"]),
    )
    op.create_index("ix_documentos_cliente_id", "documentos", ["cliente_id"])
    op.create_index("ix_documentos_processo_id", "documentos", ["processo_id"])
    op.create_index("ix_documentos_escritorio_id", "documentos", ["escritorio_id"])
    
    # ========================
    # TABELA: contratos_honorario
    # ========================
    op.create_table(
        "contratos_honorario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Vinculações
        sa.Column("cliente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processo_id", postgresql.UUID(as_uuid=True), nullable=True, comment="Processo específico (se aplicável)"),
        sa.Column("advogado_responsavel_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Tipo e status
        sa.Column("tipo", postgresql.ENUM('fixo', 'parcelado', 'exito', 'misto', 'hora', name='tipohonorario', create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM('rascunho', 'ativo', 'suspenso', 'cancelado', 'concluido', name='statuscontrato', create_type=False), nullable=False, server_default="rascunho"),
        # Valores
        sa.Column("valor_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("valor_entrada", sa.Numeric(12, 2), nullable=True, comment="Valor de entrada (para tipo MISTO)"),
        sa.Column("percentual_exito", sa.Numeric(5, 2), nullable=True, comment="Percentual sobre êxito (ex: 30.00 = 30%)"),
        sa.Column("valor_hora", sa.Numeric(10, 2), nullable=True, comment="Valor por hora (para tipo HORA)"),
        # Parcelamento
        sa.Column("numero_parcelas", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("dia_vencimento", sa.Integer(), nullable=True, comment="Dia do mês para vencimento das parcelas"),
        # Datas
        sa.Column("data_assinatura", sa.Date(), nullable=True),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=True),
        # Documento do contrato
        sa.Column("documento_path", sa.String(500), nullable=True, comment="Path do contrato assinado no GCS"),
        # Observações
        sa.Column("descricao_servicos", sa.Text(), nullable=True, comment="Descrição dos serviços contratados"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["processo_id"], ["processos.id"]),
        sa.ForeignKeyConstraint(["advogado_responsavel_id"], ["usuarios.id"]),
    )
    op.create_index("ix_contratos_honorario_cliente_id", "contratos_honorario", ["cliente_id"])
    op.create_index("ix_contratos_honorario_processo_id", "contratos_honorario", ["processo_id"])
    op.create_index("ix_contratos_honorario_status", "contratos_honorario", ["status"])
    op.create_index("ix_contratos_honorario_escritorio_id", "contratos_honorario", ["escritorio_id"])
    
    # ========================
    # TABELA: parcelas_honorario
    # ========================
    op.create_table(
        "parcelas_honorario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Vinculação ao contrato
        sa.Column("contrato_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Identificação
        sa.Column("numero_parcela", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(255), nullable=True),
        # Valores
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("valor_pago", sa.Numeric(12, 2), nullable=True),
        # Datas
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        # Status
        sa.Column("status", postgresql.ENUM('pendente', 'pago', 'atrasado', 'cancelado', name='statusparcela', create_type=False), nullable=False, server_default="pendente"),
        sa.Column("forma_pagamento", postgresql.ENUM('dinheiro', 'pix', 'transferencia', 'cartao_credito', 'cartao_debito', 'boleto', 'cheque', name='formapagamento', create_type=False), nullable=True),
        # Comprovante
        sa.Column("comprovante_path", sa.String(500), nullable=True),
        # Observações
        sa.Column("observacoes", sa.Text(), nullable=True),
        # Quem registrou
        sa.Column("registrado_por_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["contrato_id"], ["contratos_honorario.id"]),
        sa.ForeignKeyConstraint(["registrado_por_id"], ["usuarios.id"]),
    )
    op.create_index("ix_parcelas_honorario_contrato_id", "parcelas_honorario", ["contrato_id"])
    op.create_index("ix_parcelas_honorario_data_vencimento", "parcelas_honorario", ["data_vencimento"])
    op.create_index("ix_parcelas_honorario_status", "parcelas_honorario", ["status"])
    op.create_index("ix_parcelas_honorario_escritorio_id", "parcelas_honorario", ["escritorio_id"])
    
    # ========================
    # TABELA: notificacoes
    # ========================
    op.create_table(
        "notificacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Tipo e conteúdo
        sa.Column("tipo", postgresql.ENUM(
            'prazo_vencendo', 'prazo_hoje', 'prazo_vencido',
            'novo_andamento', 'mudanca_fase', 'documento_processado',
            'sistema', 'alerta',
            name='tiponotificacao', create_type=False
        ), nullable=False),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("mensagem", sa.Text(), nullable=False),
        # Canal e status
        sa.Column("canal", postgresql.ENUM('push', 'email', 'sms', 'in_app', name='canalnotificacao', create_type=False), nullable=False, server_default="in_app"),
        sa.Column("status", postgresql.ENUM('pendente', 'enviada', 'lida', 'falha', name='statusnotificacao', create_type=False), nullable=False, server_default="pendente"),
        # Datas
        sa.Column("agendada_para", sa.DateTime(timezone=True), nullable=True, comment="Data/hora agendada para envio"),
        sa.Column("enviada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lida_em", sa.DateTime(timezone=True), nullable=True),
        # Tentativas
        sa.Column("tentativas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("erro_envio", sa.Text(), nullable=True),
        # Links
        sa.Column("action_url", sa.String(500), nullable=True, comment="URL para ação ao clicar na notificação"),
        # Vinculações
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False, comment="Destinatário da notificação"),
        sa.Column("prazo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("processo_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("andamento_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["prazo_id"], ["prazos.id"]),
        sa.ForeignKeyConstraint(["processo_id"], ["processos.id"]),
        sa.ForeignKeyConstraint(["andamento_id"], ["andamentos.id"]),
    )
    op.create_index("ix_notificacoes_tipo", "notificacoes", ["tipo"])
    op.create_index("ix_notificacoes_status", "notificacoes", ["status"])
    op.create_index("ix_notificacoes_agendada_para", "notificacoes", ["agendada_para"])
    op.create_index("ix_notificacoes_usuario_id", "notificacoes", ["usuario_id"])
    op.create_index("ix_notificacoes_prazo_id", "notificacoes", ["prazo_id"])
    op.create_index("ix_notificacoes_processo_id", "notificacoes", ["processo_id"])
    op.create_index("ix_notificacoes_escritorio_id", "notificacoes", ["escritorio_id"])
    
    # ========================
    # TABELA: preferencias_notificacao
    # ========================
    op.create_table(
        "preferencias_notificacao",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("escritorio_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Usuário
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Canais habilitados
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default="false"),
        # Tipos habilitados
        sa.Column("prazo_vencendo_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("prazo_hoje_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("prazo_vencido_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("novo_andamento_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("mudanca_fase_enabled", sa.Boolean(), nullable=False, server_default="true"),
        # FCM token
        sa.Column("fcm_token", sa.String(500), nullable=True, comment="Firebase Cloud Messaging token"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["escritorio_id"], ["escritorios.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
    )
    op.create_index("ix_preferencias_notificacao_usuario_id", "preferencias_notificacao", ["usuario_id"])
    op.create_index("ix_preferencias_notificacao_escritorio_id", "preferencias_notificacao", ["escritorio_id"])


def downgrade() -> None:
    # Dropar tabelas em ordem reversa (respeitar FKs)
    op.drop_table("preferencias_notificacao")
    op.drop_table("notificacoes")
    op.drop_table("parcelas_honorario")
    op.drop_table("contratos_honorario")
    op.drop_table("documentos")
    op.drop_table("andamentos")
    op.drop_table("prazos")
    op.drop_table("processos")
    op.drop_table("clientes")
    op.drop_table("usuarios")
    op.drop_table("escritorios")
    
    # Dropar enums
    op.execute("DROP TYPE IF EXISTS tiponotificacao")
    op.execute("DROP TYPE IF EXISTS canalnotificacao")
    op.execute("DROP TYPE IF EXISTS statusnotificacao")
    op.execute("DROP TYPE IF EXISTS statusparcela")
    op.execute("DROP TYPE IF EXISTS formapagamento")
    op.execute("DROP TYPE IF EXISTS statuscontrato")
    op.execute("DROP TYPE IF EXISTS tipohonorario")
    op.execute("DROP TYPE IF EXISTS statusprocessamentoia")
    op.execute("DROP TYPE IF EXISTS tipodocumento")
    op.execute("DROP TYPE IF EXISTS statusprazo")
    op.execute("DROP TYPE IF EXISTS tipoprazo")
    op.execute("DROP TYPE IF EXISTS faseprocessual")
    op.execute("DROP TYPE IF EXISTS tipobeneficio")
    op.execute("DROP TYPE IF EXISTS estadocivil")
    op.execute("DROP TYPE IF EXISTS tipopessoa")
    op.execute("DROP TYPE IF EXISTS userrole")
    
    # Dropar extensão
    op.execute("DROP EXTENSION IF EXISTS vector")
