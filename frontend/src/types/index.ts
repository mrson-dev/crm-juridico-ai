// ============================================
// Enums - Domínio Previdenciário
// ============================================

export enum TipoBeneficio {
  APOSENTADORIA_IDADE = 'aposentadoria_idade',
  APOSENTADORIA_TEMPO_CONTRIBUICAO = 'aposentadoria_tempo_contribuicao',
  APOSENTADORIA_ESPECIAL = 'aposentadoria_especial',
  APOSENTADORIA_INVALIDEZ = 'aposentadoria_invalidez',
  AUXILIO_DOENCA = 'auxilio_doenca',
  AUXILIO_ACIDENTE = 'auxilio_acidente',
  BPC_LOAS_IDOSO = 'bpc_loas_idoso',
  BPC_LOAS_DEFICIENTE = 'bpc_loas_deficiente',
  PENSAO_MORTE = 'pensao_morte',
  SALARIO_MATERNIDADE = 'salario_maternidade',
  REVISAO_BENEFICIO = 'revisao_beneficio',
}

export enum FaseProcessual {
  ADMINISTRATIVO = 'administrativo',
  JUDICIAL_PRIMEIRA_INSTANCIA = 'judicial_1a_instancia',
  JUDICIAL_SEGUNDA_INSTANCIA = 'judicial_2a_instancia',
  TRIBUNAL_SUPERIOR = 'tribunal_superior',
  CUMPRIMENTO_SENTENCA = 'cumprimento_sentenca',
  ENCERRADO = 'encerrado',
}

export enum StatusPrazo {
  PENDENTE = 'pendente',
  CONCLUIDO = 'concluido',
  CANCELADO = 'cancelado',
  PERDIDO = 'perdido',
}

export enum TipoDocumento {
  CNIS = 'cnis',
  PPP = 'ppp',
  LAUDO_MEDICO = 'laudo_medico',
  RG = 'rg',
  CPF = 'cpf',
  CNH = 'cnh',
  COMPROVANTE_RESIDENCIA = 'comprovante_residencia',
  CERTIDAO_CASAMENTO = 'certidao_casamento',
  CERTIDAO_NASCIMENTO = 'certidao_nascimento',
  CTPS = 'ctps',
  SENTENCA = 'sentenca',
  PETICAO = 'peticao',
  RECURSO = 'recurso',
  PROCURACAO = 'procuracao',
  OUTROS = 'outros',
}

export enum TipoNotificacao {
  PRAZO_PROXIMO = 'prazo_proximo',
  PRAZO_VENCIDO = 'prazo_vencido',
  DOCUMENTO_PROCESSADO = 'documento_processado',
  ANDAMENTO_PROCESSO = 'andamento_processo',
  PARCELA_VENCENDO = 'parcela_vencendo',
  PARCELA_ATRASADA = 'parcela_atrasada',
  SISTEMA = 'sistema',
}

export enum StatusParcela {
  PENDENTE = 'pendente',
  PAGA = 'paga',
  ATRASADA = 'atrasada',
  CANCELADA = 'cancelada',
}

export enum TipoHonorario {
  CONTRATUAL = 'contratual',
  EXITO = 'exito',
  MISTO = 'misto',
}

export enum RoleUsuario {
  ADMIN = 'admin',
  ADVOGADO = 'advogado',
  SECRETARIA = 'secretaria',
  ESTAGIARIO = 'estagiario',
}

// ============================================
// Interfaces Base
// ============================================

export interface BaseEntity {
  id: string
  created_at: string
  updated_at: string
  is_active: boolean
}

export interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  total: number
  page: number
  page_size: number
  message?: string
}

export interface APIResponse<T> {
  success: boolean
  data: T
  message?: string
}

export interface APIError {
  success: false
  code: string
  message: string
  details?: Record<string, unknown>
}

// ============================================
// Entidades
// ============================================

export interface Usuario extends BaseEntity {
  email: string
  nome: string
  role: RoleUsuario
  firebase_uid?: string
  telefone?: string
  oab_numero?: string
  oab_uf?: string
  avatar_url?: string
  escritorio_id: string
}

export interface Escritorio extends BaseEntity {
  nome: string
  cnpj: string
  endereco?: string
  telefone?: string
  email?: string
  logo_url?: string
}

export interface Cliente extends BaseEntity {
  cpf: string
  nome: string
  email?: string
  telefone?: string
  celular?: string
  data_nascimento?: string
  endereco?: string
  cidade?: string
  uf?: string
  cep?: string
  profissao?: string
  nit?: string
  rg?: string
  estado_civil?: string
  nome_mae?: string
  consentimento_lgpd: boolean
  data_consentimento?: string
  observacoes?: string
  escritorio_id: string
}

export interface Processo extends BaseEntity {
  numero_cnj?: string
  numero_administrativo?: string
  tipo_beneficio: TipoBeneficio
  fase_atual: FaseProcessual
  status: string
  data_entrada: string
  data_protocolo?: string
  vara?: string
  comarca?: string
  valor_causa?: number
  valor_beneficio?: number
  observacoes?: string
  cliente_id: string
  advogado_responsavel_id: string
  escritorio_id: string
  cliente?: Cliente
  advogado_responsavel?: Usuario
  prazos?: Prazo[]
  andamentos?: Andamento[]
}

export interface Prazo extends BaseEntity {
  descricao: string
  data_fatal: string
  data_alerta?: string
  status: StatusPrazo
  observacoes?: string
  processo_id: string
  responsavel_id: string
  processo?: Processo
  responsavel?: Usuario
}

export interface Andamento extends BaseEntity {
  data: string
  descricao: string
  tipo?: string
  publico: boolean
  processo_id: string
  usuario_id: string
  processo?: Processo
  usuario?: Usuario
}

export interface Documento extends BaseEntity {
  nome: string
  tipo: TipoDocumento
  mime_type: string
  tamanho: number
  gcs_path: string
  gcs_url?: string
  hash_arquivo?: string
  processado_ia: boolean
  dados_extraidos?: Record<string, unknown>
  texto_ocr?: string
  cliente_id?: string
  processo_id?: string
  escritorio_id: string
  cliente?: Cliente
  processo?: Processo
}

export interface Notificacao extends BaseEntity {
  tipo: TipoNotificacao
  titulo: string
  mensagem: string
  lida: boolean
  data_leitura?: string
  link?: string
  dados?: Record<string, unknown>
  usuario_id: string
  escritorio_id: string
}

export interface PreferenciasNotificacao {
  id: string
  usuario_id: string
  email_prazo_proximo: boolean
  email_prazo_vencido: boolean
  email_andamento: boolean
  email_financeiro: boolean
  push_prazo_proximo: boolean
  push_prazo_vencido: boolean
  push_andamento: boolean
  push_financeiro: boolean
  antecedencia_prazo_dias: number
}

export interface ContratoHonorario extends BaseEntity {
  numero: string
  tipo: TipoHonorario
  valor_total: number
  percentual_exito?: number
  data_assinatura: string
  data_vencimento?: string
  observacoes?: string
  processo_id: string
  cliente_id: string
  escritorio_id: string
  processo?: Processo
  cliente?: Cliente
  parcelas?: ParcelaHonorario[]
}

export interface ParcelaHonorario extends BaseEntity {
  numero: number
  valor: number
  data_vencimento: string
  data_pagamento?: string
  status: StatusParcela
  forma_pagamento?: string
  comprovante_url?: string
  observacoes?: string
  contrato_id: string
  contrato?: ContratoHonorario
}

// ============================================
// DTOs - Create/Update
// ============================================

export interface ClienteCreate {
  cpf: string
  nome: string
  email?: string
  telefone?: string
  celular?: string
  data_nascimento?: string
  endereco?: string
  cidade?: string
  uf?: string
  cep?: string
  profissao?: string
  nit?: string
  rg?: string
  estado_civil?: string
  nome_mae?: string
  consentimento_lgpd: boolean
  observacoes?: string
}

export interface ClienteUpdate extends Partial<ClienteCreate> {}

export interface ProcessoCreate {
  numero_cnj?: string
  numero_administrativo?: string
  tipo_beneficio: TipoBeneficio
  fase_atual?: FaseProcessual
  data_entrada?: string
  data_protocolo?: string
  vara?: string
  comarca?: string
  valor_causa?: number
  valor_beneficio?: number
  observacoes?: string
  cliente_id: string
  advogado_responsavel_id?: string
}

export interface ProcessoUpdate extends Partial<ProcessoCreate> {}

export interface PrazoCreate {
  descricao: string
  data_fatal: string
  data_alerta?: string
  observacoes?: string
  responsavel_id?: string
}

export interface AndamentoCreate {
  data?: string
  descricao: string
  tipo?: string
  publico?: boolean
}

export interface ContratoHonorarioCreate {
  tipo: TipoHonorario
  valor_total: number
  percentual_exito?: number
  data_assinatura?: string
  data_vencimento?: string
  observacoes?: string
  processo_id: string
  cliente_id: string
  numero_parcelas?: number
}

export interface PagamentoCreate {
  data_pagamento?: string
  forma_pagamento?: string
  observacoes?: string
}

// ============================================
// Auth
// ============================================

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  nome: string
  telefone?: string
  oab_numero?: string
  oab_uf?: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AuthUser {
  user: Usuario
  tokens: AuthTokens
}

// ============================================
// Dashboard
// ============================================

export interface DashboardStats {
  total_clientes: number
  total_processos: number
  processos_ativos: number
  prazos_proximos: number
  prazos_vencidos: number
  valor_honorarios_pendente: number
  valor_honorarios_recebido: number
}

export interface DashboardFinanceiro {
  receita_mes: number
  receita_ano: number
  pendente_mes: number
  parcelas_atrasadas: number
  valor_atrasado: number
  previsao_proximos_30_dias: number
}

export interface ProcessosPorFase {
  fase: FaseProcessual
  quantidade: number
}

export interface ProcessosPorBeneficio {
  tipo: TipoBeneficio
  quantidade: number
}
