"""
Tasks de cálculos previdenciários.

Tarefas assíncronas para cálculos complexos de benefícios INSS.
"""

import structlog
from celery import shared_task
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.core.config import settings

logger = structlog.get_logger()


async def get_async_session():
    """Cria sessão async para uso nas tasks."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session()


# Constantes previdenciárias
IDADE_MINIMA_HOMEM = 65
IDADE_MINIMA_MULHER = 62
TEMPO_CONTRIBUICAO_HOMEM = 35
TEMPO_CONTRIBUICAO_MULHER = 30
CARENCIA_MINIMA = 180  # meses (15 anos)

# Fator previdenciário (simplificado)
EXPECTATIVA_VIDA = {
    60: 21.0, 61: 20.3, 62: 19.6, 63: 18.9, 64: 18.3,
    65: 17.6, 66: 17.0, 67: 16.4, 68: 15.8, 69: 15.2,
    70: 14.6, 71: 14.0, 72: 13.5, 73: 12.9, 74: 12.4,
    75: 11.9, 76: 11.4, 77: 10.9, 78: 10.4, 79: 10.0,
    80: 9.5,
}


def calcular_idade(data_nascimento: date, data_referencia: date = None) -> int:
    """Calcula idade em anos completos."""
    if data_referencia is None:
        data_referencia = date.today()
    
    idade = data_referencia.year - data_nascimento.year
    
    # Ajusta se ainda não fez aniversário
    if (data_referencia.month, data_referencia.day) < (data_nascimento.month, data_nascimento.day):
        idade -= 1
    
    return idade


def calcular_tempo_contribuicao(vinculos: list[dict]) -> dict:
    """
    Calcula tempo total de contribuição.
    
    Retorna:
        - anos: tempo em anos
        - meses: meses restantes
        - dias: dias restantes
        - total_dias: total em dias
    """
    total_dias = 0
    
    for vinculo in vinculos:
        data_inicio = vinculo.get("data_inicio")
        data_fim = vinculo.get("data_fim") or date.today()
        
        if isinstance(data_inicio, str):
            data_inicio = datetime.fromisoformat(data_inicio).date()
        if isinstance(data_fim, str):
            data_fim = datetime.fromisoformat(data_fim).date()
        
        dias = (data_fim - data_inicio).days
        total_dias += max(0, dias)
    
    anos = total_dias // 365
    resto = total_dias % 365
    meses = resto // 30
    dias = resto % 30
    
    return {
        "anos": anos,
        "meses": meses,
        "dias": dias,
        "total_dias": total_dias,
        "total_meses": total_dias // 30,
    }


def calcular_fator_previdenciario(
    tempo_contribuicao_meses: int,
    idade: int,
    expectativa_sobrevida: float,
    aliquota: float = 0.31,
) -> float:
    """
    Calcula fator previdenciário (reforma de 2019 não usa mais, mas útil para revisões).
    
    f = (Tc x a / Es) x (1 + (Id + Tc x a) / 100)
    
    Tc = tempo de contribuição
    a = alíquota (0.31)
    Es = expectativa de sobrevida
    Id = idade
    """
    tc = tempo_contribuicao_meses / 12  # Converte para anos
    
    fator = (tc * aliquota / expectativa_sobrevida) * (1 + (idade + tc * aliquota) / 100)
    
    return round(fator, 4)


def calcular_media_salarial(contribuicoes: list[dict], percentual: float = 0.8) -> Decimal:
    """
    Calcula média salarial para aposentadoria.
    
    Regra atual (EC 103/2019): 60% da média + 2% por ano que exceder 15/20 anos.
    Regra anterior: média dos 80% maiores salários.
    """
    if not contribuicoes:
        return Decimal("0")
    
    # Ordena por valor e pega os maiores
    valores = sorted([c.get("valor", 0) for c in contribuicoes], reverse=True)
    
    # Pega o percentual dos maiores (padrão 80%)
    quantidade = int(len(valores) * percentual)
    maiores = valores[:max(1, quantidade)]
    
    media = sum(maiores) / len(maiores)
    
    return Decimal(str(round(media, 2)))


@shared_task(bind=True)
def calcular_tempo_contribuicao_task(
    self,
    cliente_id: str,
    escritorio_id: str,
):
    """
    Calcula tempo de contribuição completo do cliente.
    
    Usa dados do CNIS e vínculos cadastrados.
    """
    import asyncio
    from uuid import UUID
    
    async def _calculate():
        session = await get_async_session()
        
        try:
            # TODO: Buscar vínculos do cliente no banco
            # Por hora, retorna estrutura de exemplo
            
            vinculos = []  # Seria buscado do banco
            
            resultado = calcular_tempo_contribuicao(vinculos)
            
            logger.info(
                "Tempo de contribuição calculado",
                cliente_id=cliente_id,
                **resultado,
            )
            
            return resultado
            
        finally:
            await session.close()
    
    return asyncio.run(_calculate())


@shared_task(bind=True)
def simular_aposentadoria_task(
    self,
    cliente_id: str,
    escritorio_id: str,
    data_nascimento: str,
    sexo: str,
    vinculos: list[dict],
    contribuicoes: list[dict] = None,
):
    """
    Simula cenários de aposentadoria para o cliente.
    
    Retorna análise completa com diferentes regras:
    - Regra de transição por idade
    - Regra de transição por pontos
    - Regra de transição por pedágio
    - Aposentadoria especial (se aplicável)
    """
    import asyncio
    
    async def _simulate():
        data_nasc = datetime.fromisoformat(data_nascimento).date()
        idade = calcular_idade(data_nasc)
        tempo = calcular_tempo_contribuicao(vinculos)
        
        # Determina requisitos por sexo
        idade_minima = IDADE_MINIMA_HOMEM if sexo.upper() == "M" else IDADE_MINIMA_MULHER
        tempo_minimo = TEMPO_CONTRIBUICAO_HOMEM if sexo.upper() == "M" else TEMPO_CONTRIBUICAO_MULHER
        
        # Análise de cada regra
        resultados = {
            "cliente_id": cliente_id,
            "data_calculo": date.today().isoformat(),
            "idade_atual": idade,
            "tempo_contribuicao": tempo,
            "regras": [],
        }
        
        # 1. Regra por idade mínima
        regra_idade = {
            "nome": "Aposentadoria por Idade",
            "requisitos": {
                "idade_minima": idade_minima,
                "carencia_meses": CARENCIA_MINIMA,
            },
            "situacao_atual": {
                "idade": idade,
                "carencia_cumprida": tempo["total_meses"] >= CARENCIA_MINIMA,
            },
        }
        
        if idade >= idade_minima and tempo["total_meses"] >= CARENCIA_MINIMA:
            regra_idade["status"] = "APTO"
            regra_idade["data_possivel"] = date.today().isoformat()
        else:
            regra_idade["status"] = "NAO_APTO"
            # Calcula quando atinge
            anos_faltantes = max(0, idade_minima - idade)
            data_possivel = date.today() + timedelta(days=anos_faltantes * 365)
            regra_idade["data_possivel"] = data_possivel.isoformat()
            regra_idade["tempo_faltante"] = f"{anos_faltantes} ano(s)"
        
        resultados["regras"].append(regra_idade)
        
        # 2. Regra por tempo de contribuição (transição)
        regra_tempo = {
            "nome": "Aposentadoria por Tempo de Contribuição",
            "requisitos": {
                "tempo_minimo_anos": tempo_minimo,
                "idade_minima": 60 if sexo.upper() == "M" else 57,  # Regra de transição
            },
            "situacao_atual": {
                "tempo_anos": tempo["anos"],
                "idade": idade,
            },
        }
        
        idade_min_transicao = 60 if sexo.upper() == "M" else 57
        if tempo["anos"] >= tempo_minimo and idade >= idade_min_transicao:
            regra_tempo["status"] = "APTO"
            regra_tempo["data_possivel"] = date.today().isoformat()
        else:
            regra_tempo["status"] = "NAO_APTO"
            anos_contrib_faltante = max(0, tempo_minimo - tempo["anos"])
            anos_idade_faltante = max(0, idade_min_transicao - idade)
            anos_faltantes = max(anos_contrib_faltante, anos_idade_faltante)
            
            data_possivel = date.today() + timedelta(days=anos_faltantes * 365)
            regra_tempo["data_possivel"] = data_possivel.isoformat()
        
        resultados["regras"].append(regra_tempo)
        
        # 3. Regra de pontos
        pontos_atuais = idade + tempo["anos"]
        pontos_necessarios = 100 if sexo.upper() == "M" else 90  # 2024
        
        regra_pontos = {
            "nome": "Regra de Pontos",
            "requisitos": {
                "pontos_minimos": pontos_necessarios,
                "tempo_minimo_anos": tempo_minimo,
            },
            "situacao_atual": {
                "pontos": pontos_atuais,
                "tempo_anos": tempo["anos"],
            },
        }
        
        if pontos_atuais >= pontos_necessarios and tempo["anos"] >= tempo_minimo:
            regra_pontos["status"] = "APTO"
            regra_pontos["data_possivel"] = date.today().isoformat()
        else:
            regra_pontos["status"] = "NAO_APTO"
            pontos_faltantes = pontos_necessarios - pontos_atuais
            # A cada ano que passa, ganha 2 pontos (1 de idade + 1 de contribuição)
            anos_faltantes = (pontos_faltantes + 1) // 2
            data_possivel = date.today() + timedelta(days=max(0, anos_faltantes) * 365)
            regra_pontos["data_possivel"] = data_possivel.isoformat()
        
        resultados["regras"].append(regra_pontos)
        
        # 4. Cálculo estimado do valor
        if contribuicoes:
            media = calcular_media_salarial(contribuicoes)
            
            # Coeficiente: 60% + 2% por ano acima de 15/20 anos
            anos_base = 20 if sexo.upper() == "M" else 15
            anos_excedentes = max(0, tempo["anos"] - anos_base)
            coeficiente = Decimal("0.6") + (Decimal("0.02") * anos_excedentes)
            coeficiente = min(coeficiente, Decimal("1.0"))  # Máximo 100%
            
            valor_estimado = media * coeficiente
            
            resultados["estimativa_valor"] = {
                "media_salarial": str(media),
                "coeficiente": str(coeficiente),
                "valor_estimado": str(valor_estimado),
            }
        
        logger.info(
            "Simulação de aposentadoria calculada",
            cliente_id=cliente_id,
            regras_analisadas=len(resultados["regras"]),
        )
        
        return resultados
    
    return asyncio.run(_simulate())


@shared_task(bind=True)
def calcular_revisao_beneficio_task(
    self,
    processo_id: str,
    escritorio_id: str,
    tipo_revisao: str,
    contribuicoes: list[dict],
    rmi_atual: str,
    dib: str,  # Data de início do benefício
):
    """
    Calcula potencial de revisão de benefício.
    
    Tipos de revisão:
    - BURACO_NEGRO: benefícios entre 05/10/1988 e 05/04/1991
    - TETO_REVISAO: benefícios limitados pelo teto
    - VIDA_TODA: inclusão de todos os salários (não só após 07/1994)
    - MELHOR_BENEFICIO: revisão do art. 29 II
    """
    import asyncio
    
    async def _calculate_revision():
        rmi = Decimal(rmi_atual)
        data_dib = datetime.fromisoformat(dib).date()
        
        resultado = {
            "processo_id": processo_id,
            "tipo_revisao": tipo_revisao,
            "rmi_atual": str(rmi),
            "dib": dib,
            "viabilidade": "ANALISAR",
            "observacoes": [],
        }
        
        if tipo_revisao == "VIDA_TODA":
            # Calcula média com todos os salários vs apenas pós-1994
            if contribuicoes:
                # Separa contribuições antes e depois de jul/1994
                data_corte = date(1994, 7, 1)
                
                todas = [c.get("valor", 0) for c in contribuicoes]
                pos_1994 = [
                    c.get("valor", 0) for c in contribuicoes
                    if datetime.fromisoformat(c.get("competencia", "1990-01-01")).date() >= data_corte
                ]
                
                media_todas = sum(todas) / len(todas) if todas else 0
                media_pos_1994 = sum(pos_1994) / len(pos_1994) if pos_1994 else 0
                
                if media_todas > media_pos_1994:
                    diferenca_percentual = ((media_todas - media_pos_1994) / media_pos_1994) * 100
                    resultado["viabilidade"] = "FAVORAVEL"
                    resultado["diferenca_percentual"] = f"{diferenca_percentual:.2f}%"
                    resultado["media_vida_toda"] = str(round(media_todas, 2))
                    resultado["media_pos_1994"] = str(round(media_pos_1994, 2))
                    resultado["observacoes"].append(
                        f"Revisão pode aumentar benefício em aproximadamente {diferenca_percentual:.1f}%"
                    )
                else:
                    resultado["viabilidade"] = "DESFAVORAVEL"
                    resultado["observacoes"].append(
                        "Média pós-1994 é mais favorável ao segurado"
                    )
        
        elif tipo_revisao == "BURACO_NEGRO":
            # Verifica se DIB está no período
            inicio_buraco = date(1988, 10, 5)
            fim_buraco = date(1991, 4, 5)
            
            if inicio_buraco <= data_dib <= fim_buraco:
                resultado["viabilidade"] = "POSSIVEL"
                resultado["observacoes"].append(
                    "Benefício concedido no período do 'buraco negro'"
                )
            else:
                resultado["viabilidade"] = "NAO_APLICAVEL"
                resultado["observacoes"].append(
                    "DIB fora do período do buraco negro"
                )
        
        elif tipo_revisao == "TETO_REVISAO":
            # Verifica se benefício foi limitado pelo teto
            # Simplificação - em produção, verificar EC 20/1998 e EC 41/2003
            resultado["observacoes"].append(
                "Analisar se houve limitação pelo teto nas ECs 20/1998 ou 41/2003"
            )
            resultado["viabilidade"] = "ANALISAR"
        
        logger.info(
            "Cálculo de revisão concluído",
            processo_id=processo_id,
            tipo_revisao=tipo_revisao,
            viabilidade=resultado["viabilidade"],
        )
        
        return resultado
    
    return asyncio.run(_calculate_revision())


@shared_task
def calcular_atrasados_task(
    processo_id: str,
    escritorio_id: str,
    valor_mensal: str,
    data_inicio: str,
    data_fim: str = None,
    juros_mora: bool = True,
    correcao_monetaria: bool = True,
):
    """
    Calcula valores atrasados (parcelas retroativas).
    
    Útil para estimar valores em ações de concessão/revisão.
    """
    valor = Decimal(valor_mensal)
    inicio = datetime.fromisoformat(data_inicio).date()
    fim = datetime.fromisoformat(data_fim).date() if data_fim else date.today()
    
    # Calcula número de meses
    meses = (fim.year - inicio.year) * 12 + (fim.month - inicio.month)
    
    # Valor base
    total_base = valor * meses
    
    # Correção monetária (simplificado - INPC)
    # Em produção, usar índices reais
    taxa_correcao_anual = Decimal("0.05")  # 5% ao ano aproximado
    anos = meses / 12
    correcao = total_base * (taxa_correcao_anual * Decimal(str(anos))) if correcao_monetaria else Decimal("0")
    
    # Juros de mora (1% ao mês, limitado)
    taxa_juros_mes = Decimal("0.01")
    juros = total_base * (taxa_juros_mes * meses) if juros_mora else Decimal("0")
    juros = min(juros, total_base)  # Limita a 100%
    
    total = total_base + correcao + juros
    
    resultado = {
        "processo_id": processo_id,
        "periodo": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "meses": meses,
        },
        "valores": {
            "valor_mensal": str(valor),
            "total_base": str(total_base),
            "correcao_monetaria": str(correcao),
            "juros_mora": str(juros),
            "total_estimado": str(total),
        },
        "observacao": "Valores estimados. Cálculo definitivo depende de índices oficiais.",
    }
    
    logger.info(
        "Cálculo de atrasados concluído",
        processo_id=processo_id,
        meses=meses,
        total_estimado=str(total),
    )
    
    return resultado
