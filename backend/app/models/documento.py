"""
Modelo de Documento.

Armazena metadados de documentos salvos no Cloud Storage.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import MultiTenantBase, PgEnum


class TipoDocumento(str, enum.Enum):
    """Tipos de documentos do sistema."""
    
    # Identificação pessoal
    RG = "rg"
    CPF = "cpf"
    CNH = "cnh"
    CERTIDAO_NASCIMENTO = "certidao_nascimento"
    CERTIDAO_CASAMENTO = "certidao_casamento"
    TITULO_ELEITOR = "titulo_eleitor"
    COMPROVANTE_RESIDENCIA = "comprovante_residencia"
    
    # Documentos previdenciários
    CNIS = "cnis"  # Cadastro Nacional de Informações Sociais
    PPP = "ppp"  # Perfil Profissiográfico Previdenciário
    CTPS = "ctps"  # Carteira de Trabalho
    CARTA_CONCESSAO = "carta_concessao"
    CARTA_INDEFERIMENTO = "carta_indeferimento"
    
    # Documentos médicos
    LAUDO_MEDICO = "laudo_medico"
    ATESTADO = "atestado"
    EXAME = "exame"
    RECEITUARIO = "receituario"
    
    # Peças processuais
    PETICAO_INICIAL = "peticao_inicial"
    CONTESTACAO = "contestacao"
    RECURSO = "recurso"
    SENTENCA = "sentenca"
    ACORDAO = "acordao"
    MANDADO = "mandado"
    
    # Outros
    PROCURACAO = "procuracao"
    CONTRATO_HONORARIOS = "contrato_honorarios"
    COMPROVANTE_PAGAMENTO = "comprovante_pagamento"
    OUTROS = "outros"


class CategoriaDocumento(str, enum.Enum):
    """Categorias de documentos para agrupamento."""
    
    IDENTIFICACAO = "identificacao"
    PREVIDENCIARIO = "previdenciario"
    MEDICO = "medico"
    PROCESSUAL = "processual"
    FINANCEIRO = "financeiro"
    OUTROS = "outros"


class StatusProcessamentoIA(str, enum.Enum):
    """Status do processamento de IA do documento."""
    
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    CONCLUIDO = "concluido"
    ERRO = "erro"


# Alias para compatibilidade
StatusIA = StatusProcessamentoIA


class Documento(MultiTenantBase):
    """
    Metadados de documento armazenado no Cloud Storage.
    
    O arquivo em si é armazenado no GCS, aqui apenas os metadados.
    """
    
    __tablename__ = "documentos"
    
    # Identificação do documento
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[TipoDocumento] = mapped_column(
        PgEnum(TipoDocumento),
        default=TipoDocumento.OUTROS,
    )
    descricao: Mapped[str | None] = mapped_column(Text)
    
    # Armazenamento
    gcs_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    gcs_path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    
    # Metadados do arquivo
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    
    # Versionamento
    versao: Mapped[int] = mapped_column(Integer, default=1)
    documento_original_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documentos.id"),
        comment="ID do documento original se esta for uma versão",
    )
    
    # Processamento de IA
    status_ia: Mapped[StatusProcessamentoIA] = mapped_column(
        PgEnum(StatusProcessamentoIA),
        default=StatusProcessamentoIA.PENDENTE,
    )
    dados_extraidos: Mapped[str | None] = mapped_column(
        Text,
        comment="JSON com dados extraídos pela IA",
    )
    resumo_ia: Mapped[str | None] = mapped_column(
        Text,
        comment="Resumo gerado pela IA",
    )
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Vinculações (pode pertencer a cliente e/ou processo)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clientes.id"),
        index=True,
    )
    
    processo_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("processos.id"),
        index=True,
    )
    
    # Quem fez upload
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
    )
    
    # Relacionamentos
    cliente: Mapped["Cliente"] = relationship(  # noqa: F821
        "Cliente",
        back_populates="documentos",
    )
    
    processo: Mapped["Processo"] = relationship(  # noqa: F821
        "Processo",
        back_populates="documentos",
    )
    
    uploaded_by: Mapped["Usuario"] = relationship(  # noqa: F821
        "Usuario",
        foreign_keys=[uploaded_by_id],
    )
    
    versoes: Mapped[list["Documento"]] = relationship(
        "Documento",
        remote_side="Documento.documento_original_id",
        lazy="selectin",
    )
    
    @property
    def url_assinada(self) -> str | None:
        """URL assinada é gerada sob demanda pelo service."""
        # Isso é apenas um placeholder - a URL real é gerada pelo StorageService
        return None
    
    @property
    def is_processado(self) -> bool:
        """Verifica se documento foi processado pela IA."""
        return self.status_ia == StatusProcessamentoIA.CONCLUIDO
    
    def __repr__(self) -> str:
        return f"<Documento(id={self.id}, nome='{self.nome}', tipo={self.tipo.value})>"
