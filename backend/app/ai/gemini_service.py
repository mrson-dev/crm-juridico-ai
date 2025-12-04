"""
Serviço de integração com Gemini para extração de documentos.

Responsável por:
- Extração de dados de documentos de identificação (RG, CNH, CPF)
- OCR de imagens e PDFs
- Análise de documentos previdenciários (CNIS, PPP)
- Geração de embeddings para busca semântica
- Análise e geração de petições
"""

import base64
import json
from datetime import date
from pathlib import Path
from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.schemas.cliente import ClienteFromDocumentAI

logger = structlog.get_logger()


class GeminiService:
    """
    Serviço de integração com Google Gemini API.
    
    Uso:
        service = GeminiService()
        dados = await service.extract_identity_document(file_path)
    """
    
    def __init__(self):
        self._model_name = settings.GEMINI_MODEL
        self._embedding_model = "models/text-embedding-004"
        self._client = None
        self._embedding_client = None
    
    def _get_client(self):
        """Inicializa cliente Gemini sob demanda."""
        if self._client is None:
            import google.generativeai as genai
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._client = genai.GenerativeModel(self._model_name)
        return self._client
    
    def _get_embedding_model(self):
        """Inicializa modelo de embedding sob demanda."""
        if self._embedding_client is None:
            import google.generativeai as genai
            
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._embedding_client = genai
        return self._embedding_client
    
    def _encode_file_to_base64(self, file_path: str) -> tuple[str, str]:
        """Codifica arquivo para base64 e detecta mime type."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        mime_types = {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        
        mime_type = mime_types.get(suffix, "application/octet-stream")
        
        with open(file_path, "rb") as f:
            content = base64.standard_b64encode(f.read()).decode("utf-8")
        
        return content, mime_type
    
    def _encode_bytes_to_base64(self, content: bytes, mime_type: str) -> str:
        """Codifica bytes para base64."""
        return base64.standard_b64encode(content).decode("utf-8")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def extract_identity_document(
        self,
        file_path_or_content: str | bytes,
        mime_type: str = None,
    ) -> ClienteFromDocumentAI:
        """
        Extrai dados de documento de identificação (RG, CNH, CPF).
        
        Args:
            file_path_or_content: Caminho para o arquivo ou bytes do conteúdo
            mime_type: Tipo MIME (obrigatório se passar bytes)
        
        Returns:
            ClienteFromDocumentAI com dados extraídos
        """
        logger.info("Iniciando extração de documento de identidade")
        
        prompt = """Analise este documento de identificação brasileiro (RG, CNH ou CPF) e extraia os dados em formato JSON.

Extraia APENAS os campos que conseguir identificar claramente no documento:
- nome: Nome completo
- cpf: CPF no formato XXX.XXX.XXX-XX
- rg: Número do RG
- rg_orgao_emissor: Órgão emissor do RG (SSP, DETRAN, etc)
- rg_data_emissao: Data de emissão do RG (formato YYYY-MM-DD)
- data_nascimento: Data de nascimento (formato YYYY-MM-DD)
- sexo: M ou F
- nome_mae: Nome da mãe
- nome_pai: Nome do pai
- naturalidade: Cidade/Estado de nascimento

Para CNH, também extraia:
- cnh_numero: Número da CNH
- cnh_categoria: Categoria (A, B, AB, etc)
- cnh_validade: Data de validade (formato YYYY-MM-DD)

Responda APENAS com o JSON, sem explicações. Use null para campos não encontrados.
Adicione um campo "confidence" de 0 a 1 indicando a confiança geral da extração.
Adicione um campo "fields_to_review" listando campos que podem precisar de revisão manual.

Exemplo de resposta:
{
  "nome": "JOÃO DA SILVA",
  "cpf": "123.456.789-00",
  "data_nascimento": "1985-03-15",
  "confidence": 0.85,
  "fields_to_review": ["rg_data_emissao"]
}"""
        
        try:
            if isinstance(file_path_or_content, bytes):
                content = self._encode_bytes_to_base64(file_path_or_content, mime_type)
            else:
                content, mime_type = self._encode_file_to_base64(file_path_or_content)
            
            client = self._get_client()
            
            response = await client.generate_content_async(
                [
                    {"mime_type": mime_type, "data": content},
                    prompt,
                ],
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            
            result_text = response.text.strip()
            result_data = json.loads(result_text)
            
            for campo in ["data_nascimento", "rg_data_emissao", "cnh_validade"]:
                if result_data.get(campo):
                    try:
                        result_data[campo] = date.fromisoformat(result_data[campo])
                    except (ValueError, TypeError):
                        result_data[campo] = None
            
            logger.info(
                "Extração concluída",
                confidence=result_data.get("confidence"),
                campos_extraidos=len([v for v in result_data.values() if v]),
            )
            
            return ClienteFromDocumentAI(**result_data)
            
        except json.JSONDecodeError as e:
            logger.error("Erro ao parsear resposta da IA", error=str(e))
            return ClienteFromDocumentAI(
                confidence=0.0,
                fields_to_review=["all"],
            )
        except Exception as e:
            logger.error("Erro na extração de documento", error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def extract_cnis(
        self,
        file_path_or_content: str | bytes,
        mime_type: str = None,
    ) -> dict[str, Any]:
        """
        Extrai dados do CNIS (Cadastro Nacional de Informações Sociais).
        
        Retorna vínculos empregatícios e contribuições.
        """
        logger.info("Iniciando extração de CNIS")
        
        prompt = """Analise este CNIS (Cadastro Nacional de Informações Sociais) e extraia os dados em formato JSON.

Extraia:
- nit: Número de Identificação do Trabalhador
- nome: Nome do segurado
- data_nascimento: Data de nascimento (YYYY-MM-DD)
- nome_mae: Nome da mãe

- vinculos: Lista de vínculos empregatícios, cada um com:
  - empregador: Nome do empregador
  - cnpj: CNPJ do empregador (se disponível)
  - data_inicio: Data de início (YYYY-MM-DD)
  - data_fim: Data de fim (YYYY-MM-DD), null se ativo
  - tipo: CLT, contribuinte_individual, etc
  - ultima_remuneracao: Último salário registrado

- contribuicoes: Lista de contribuições, cada uma com:
  - competencia: Mês/Ano (YYYY-MM)
  - valor: Valor da contribuição
  - tipo: Tipo de contribuição

- tempo_contribuicao_total_dias: Total de dias de contribuição calculado
- indicadores_especiais: Lista de períodos com atividade especial, se houver

Responda APENAS com o JSON válido."""
        
        try:
            if isinstance(file_path_or_content, bytes):
                content = self._encode_bytes_to_base64(file_path_or_content, mime_type)
            else:
                content, mime_type = self._encode_file_to_base64(file_path_or_content)
            
            client = self._get_client()
            
            response = await client.generate_content_async(
                [
                    {"mime_type": mime_type, "data": content},
                    prompt,
                ],
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            
            result = json.loads(response.text.strip())
            logger.info(
                "Extração de CNIS concluída",
                vinculos=len(result.get("vinculos", [])),
            )
            return result
            
        except Exception as e:
            logger.error("Erro na extração de CNIS", error=str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def analyze_ppp(
        self,
        file_path_or_content: str | bytes,
        mime_type: str = None,
    ) -> dict[str, Any]:
        """
        Analisa PPP (Perfil Profissiográfico Previdenciário).
        
        Identifica exposição a agentes nocivos para aposentadoria especial.
        """
        logger.info("Iniciando análise de PPP")
        
        prompt = """Analise este PPP (Perfil Profissiográfico Previdenciário) e extraia os dados em formato JSON.

Foque especialmente em:
- dados_empresa: Nome, CNPJ, CNAE
- dados_trabalhador: Nome, CPF, data_nascimento, data_admissao
- cargo: Cargo/função exercida
- setor: Setor de trabalho
- descricao_atividades: Descrição das atividades

- exposicao_agentes_nocivos: Lista de agentes nocivos, cada um com:
  - agente: Nome do agente (ruído, calor, agentes químicos, etc)
  - codigo: Código do agente nocivo
  - intensidade: Intensidade/concentração
  - tecnica_utilizada: Metodologia de medição
  - periodo_inicio: Data início exposição
  - periodo_fim: Data fim exposição
  - epi_eficaz: Se EPI elimina/neutraliza (true/false)

- conclusao_especial: Análise se o período pode ser considerado especial para aposentadoria
- fundamento_legal: Base legal aplicável (Decreto 3048, etc)

Responda APENAS com o JSON válido."""
        
        try:
            if isinstance(file_path_or_content, bytes):
                content = self._encode_bytes_to_base64(file_path_or_content, mime_type)
            else:
                content, mime_type = self._encode_file_to_base64(file_path_or_content)
            
            client = self._get_client()
            
            response = await client.generate_content_async(
                [
                    {"mime_type": mime_type, "data": content},
                    prompt,
                ],
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            
            result = json.loads(response.text.strip())
            logger.info(
                "Análise de PPP concluída",
                agentes_nocivos=len(result.get("exposicao_agentes_nocivos", [])),
            )
            return result
            
        except Exception as e:
            logger.error("Erro na análise de PPP", error=str(e))
            raise
    
    async def summarize_document(
        self,
        file_path_or_content: str | bytes,
        mime_type: str = None,
    ) -> str:
        """Gera resumo de documento jurídico."""
        logger.info("Gerando resumo de documento")
        
        prompt = """Analise este documento jurídico e gere um resumo estruturado em português.

O resumo deve conter:
1. TIPO DE DOCUMENTO: (petição inicial, sentença, acórdão, etc)
2. PARTES: Autor(es) e Réu(s)
3. OBJETO: O que está sendo discutido/pedido
4. PRINCIPAIS ARGUMENTOS: Resumo dos argumentos apresentados
5. DECISÃO (se aplicável): Resultado/decisão do documento
6. PRAZOS (se mencionados): Datas e prazos relevantes
7. PRÓXIMOS PASSOS: Ações necessárias após este documento

Seja conciso mas completo."""
        
        try:
            if isinstance(file_path_or_content, bytes):
                content = self._encode_bytes_to_base64(file_path_or_content, mime_type)
            else:
                content, mime_type = self._encode_file_to_base64(file_path_or_content)
            
            client = self._get_client()
            
            response = await client.generate_content_async(
                [
                    {"mime_type": mime_type, "data": content},
                    prompt,
                ],
                generation_config={"temperature": 0.3},
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error("Erro ao gerar resumo", error=str(e))
            raise
    
    # === NOVOS MÉTODOS ===
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_embedding(self, text: str) -> list[float]:
        """
        Gera embedding vetorial para texto.
        
        Útil para busca semântica em documentos e processos.
        """
        try:
            genai = self._get_embedding_model()
            
            result = genai.embed_content(
                model=self._embedding_model,
                content=text,
                task_type="retrieval_document",
            )
            
            return result["embedding"]
            
        except Exception as e:
            logger.error("Erro ao gerar embedding", error=str(e))
            raise
    
    async def generate_query_embedding(self, query: str) -> list[float]:
        """
        Gera embedding para query de busca.
        
        Otimizado para busca semântica.
        """
        try:
            genai = self._get_embedding_model()
            
            result = genai.embed_content(
                model=self._embedding_model,
                content=query,
                task_type="retrieval_query",
            )
            
            return result["embedding"]
            
        except Exception as e:
            logger.error("Erro ao gerar embedding de query", error=str(e))
            raise
    
    async def analyze_sentenca(
        self,
        file_path_or_content: str | bytes,
        mime_type: str = None,
    ) -> dict[str, Any]:
        """
        Analisa sentença judicial para extração estruturada.
        
        Identifica dispositivo, fundamentação, prazos e valores.
        """
        logger.info("Analisando sentença")
        
        prompt = """Analise esta sentença judicial e extraia os dados em formato JSON.

Extraia:
- numero_processo: Número do processo
- vara: Vara/Juízo
- juiz: Nome do juiz
- data_sentenca: Data da sentença (YYYY-MM-DD)
- tipo_acao: Tipo de ação (concessão, revisão, etc)

- partes:
  - autor: Nome do autor
  - reu: Nome do réu (geralmente INSS)

- pedidos: Lista de pedidos feitos
- decisao:
  - resultado: PROCEDENTE, IMPROCEDENTE, PARCIALMENTE_PROCEDENTE
  - beneficio_concedido: Tipo de benefício (se procedente)
  - dib: Data de início do benefício (YYYY-MM-DD)
  - rmi: Valor do benefício (se mencionado)
  - atrasados: Se há condenação em atrasados

- fundamentos: Principais fundamentos da decisão
- honorarios:
  - tipo: SUCUMBENCIA ou outro
  - percentual: Percentual de honorários

- recursos:
  - prazo_recurso: Prazo para recurso em dias
  - data_limite_recurso: Data limite (YYYY-MM-DD)

- observacoes: Outras informações relevantes

Responda APENAS com JSON válido."""
        
        try:
            if isinstance(file_path_or_content, bytes):
                content = self._encode_bytes_to_base64(file_path_or_content, mime_type)
            else:
                content, mime_type = self._encode_file_to_base64(file_path_or_content)
            
            client = self._get_client()
            
            response = await client.generate_content_async(
                [
                    {"mime_type": mime_type, "data": content},
                    prompt,
                ],
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            
            result = json.loads(response.text.strip())
            logger.info(
                "Análise de sentença concluída",
                resultado=result.get("decisao", {}).get("resultado"),
            )
            return result
            
        except Exception as e:
            logger.error("Erro na análise de sentença", error=str(e))
            raise
    
    async def generate_peticao_minuta(
        self,
        tipo_peticao: str,
        dados_cliente: dict,
        dados_processo: dict,
        contexto_adicional: str = None,
    ) -> str:
        """
        Gera minuta de petição com base nos dados do processo.
        
        Tipos suportados:
        - PETICAO_INICIAL: Petição inicial de benefício
        - RECURSO_ADMINISTRATIVO: Recurso ao CRPS
        - RECURSO_JEF: Recurso Inominado
        - CUMPRIMENTO_SENTENCA: Início de cumprimento
        """
        logger.info("Gerando minuta de petição", tipo=tipo_peticao)
        
        prompts = {
            "PETICAO_INICIAL": """Gere uma petição inicial previdenciária com os seguintes dados:

Dados do Cliente:
{dados_cliente}

Dados do Processo:
{dados_processo}

Contexto adicional:
{contexto}

A petição deve seguir o modelo padrão brasileiro, incluindo:
1. Endereçamento ao juízo
2. Qualificação das partes
3. Dos fatos
4. Do direito (fundamentos legais)
5. Dos pedidos
6. Do valor da causa
7. Requerimentos finais

Use linguagem jurídica formal. Cite dispositivos legais pertinentes (Lei 8.213/91, Decreto 3.048/99, etc).
""",
            "RECURSO_ADMINISTRATIVO": """Gere um recurso administrativo ao CRPS com os seguintes dados:

Dados do Cliente:
{dados_cliente}

Dados do Processo:
{dados_processo}

Motivo do indeferimento:
{contexto}

O recurso deve incluir:
1. Endereçamento à Junta de Recursos
2. Número do benefício e dados do segurado
3. Do cabimento e tempestividade
4. Dos fatos
5. Das razões do recurso
6. Dos pedidos
7. Documentos anexos

Cite jurisprudência do CRPS quando pertinente.
""",
        }
        
        template = prompts.get(tipo_peticao, prompts["PETICAO_INICIAL"])
        
        prompt = template.format(
            dados_cliente=json.dumps(dados_cliente, ensure_ascii=False, indent=2),
            dados_processo=json.dumps(dados_processo, ensure_ascii=False, indent=2),
            contexto=contexto_adicional or "Não informado",
        )
        
        try:
            client = self._get_client()
            
            response = await client.generate_content_async(
                prompt,
                generation_config={"temperature": 0.4},
            )
            
            logger.info("Minuta gerada com sucesso", tipo=tipo_peticao)
            return response.text.strip()
            
        except Exception as e:
            logger.error("Erro ao gerar minuta", error=str(e))
            raise
    
    async def analisar_viabilidade_acao(
        self,
        dados_cliente: dict,
        tipo_beneficio: str,
        documentos_disponiveis: list[str],
    ) -> dict[str, Any]:
        """
        Analisa viabilidade de ajuizamento de ação previdenciária.
        
        Retorna análise de riscos e recomendações.
        """
        logger.info("Analisando viabilidade de ação", tipo=tipo_beneficio)
        
        prompt = f"""Analise a viabilidade de ajuizamento de ação previdenciária para {tipo_beneficio}.

Dados do Cliente:
{json.dumps(dados_cliente, ensure_ascii=False, indent=2)}

Documentos Disponíveis:
{json.dumps(documentos_disponiveis, ensure_ascii=False)}

Forneça análise em JSON com:
- viabilidade: ALTA, MEDIA, BAIXA
- pontos_fortes: Lista de pontos favoráveis ao cliente
- pontos_fracos: Lista de pontos desfavoráveis
- documentos_faltantes: Documentos necessários que não foram apresentados
- riscos: Lista de riscos identificados
- recomendacoes: Ações recomendadas antes do ajuizamento
- probabilidade_sucesso_percentual: Estimativa de 0 a 100
- observacoes: Considerações adicionais

Considere a jurisprudência do TRF e TNU sobre o tema."""
        
        try:
            client = self._get_client()
            
            response = await client.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            )
            
            result = json.loads(response.text.strip())
            logger.info(
                "Análise de viabilidade concluída",
                viabilidade=result.get("viabilidade"),
            )
            return result
            
        except Exception as e:
            logger.error("Erro na análise de viabilidade", error=str(e))
            raise
    
    async def classificar_documento(
        self,
        file_path_or_content: str | bytes,
        mime_type: str = None,
    ) -> dict[str, Any]:
        """
        Classifica automaticamente tipo de documento jurídico/previdenciário.
        
        Útil para organização automática de uploads.
        """
        logger.info("Classificando documento")
        
        prompt = """Analise este documento e classifique-o. Responda em JSON:

{
  "tipo_documento": "RG|CNH|CPF|CNIS|PPP|CTPS|LAUDO_MEDICO|PETICAO|SENTENCA|ACORDAO|CARTA_BENEFICIO|COMPROVANTE_RESIDENCIA|PROCURACAO|OUTRO",
  "subtipo": "descrição mais específica se houver",
  "confidence": 0.0 a 1.0,
  "campos_identificados": ["lista de campos visíveis"],
  "qualidade_documento": "BOA|MEDIA|RUIM",
  "observacoes": "qualquer observação relevante"
}

Responda APENAS com JSON válido."""
        
        try:
            if isinstance(file_path_or_content, bytes):
                content = self._encode_bytes_to_base64(file_path_or_content, mime_type)
            else:
                content, mime_type = self._encode_file_to_base64(file_path_or_content)
            
            client = self._get_client()
            
            response = await client.generate_content_async(
                [
                    {"mime_type": mime_type, "data": content},
                    prompt,
                ],
                generation_config={
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )
            
            result = json.loads(response.text.strip())
            logger.info(
                "Documento classificado",
                tipo=result.get("tipo_documento"),
                confidence=result.get("confidence"),
            )
            return result
            
        except Exception as e:
            logger.error("Erro na classificação de documento", error=str(e))
            raise


# Singleton para uso global
gemini_service = GeminiService()
