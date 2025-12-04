"""
Modelos SQLAlchemy do CRM Jurídico.

Importa todos os modelos para garantir que são registrados no metadata.
"""

from app.models.cliente import Cliente, EstadoCivil, TipoPessoa
from app.models.documento import Documento, StatusProcessamentoIA, TipoDocumento
from app.models.escritorio import Escritorio
from app.models.honorario import (
    ContratoHonorario,
    FormaPagamento,
    ParcelaHonorario,
    StatusContrato,
    StatusParcela,
    TipoHonorario,
)
from app.models.notificacao import (
    CanalNotificacao,
    Notificacao,
    PreferenciaNotificacao,
    StatusNotificacao,
    TipoNotificacao,
)
from app.models.processo import (
    Andamento,
    FaseProcessual,
    Prazo,
    Processo,
    StatusPrazo,
    TipoBeneficio,
    TipoPrazo,
)
from app.models.usuario import Usuario, UserRole

__all__ = [
    # Escritório e Usuário
    "Escritorio",
    "Usuario",
    "UserRole",
    # Cliente
    "Cliente",
    "TipoPessoa",
    "EstadoCivil",
    # Processo
    "Processo",
    "Prazo",
    "Andamento",
    "TipoBeneficio",
    "FaseProcessual",
    "StatusPrazo",
    "TipoPrazo",
    # Documento
    "Documento",
    "TipoDocumento",
    "StatusProcessamentoIA",
    # Honorários
    "ContratoHonorario",
    "ParcelaHonorario",
    "TipoHonorario",
    "StatusContrato",
    "StatusParcela",
    "FormaPagamento",
    # Notificações
    "Notificacao",
    "PreferenciaNotificacao",
    "TipoNotificacao",
    "CanalNotificacao",
    "StatusNotificacao",
]
