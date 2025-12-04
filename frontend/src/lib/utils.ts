import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow, parseISO, differenceInDays, isAfter, isBefore } from 'date-fns'
import { ptBR } from 'date-fns/locale'

// Merge Tailwind classes
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ============================================
// Formatação de Datas
// ============================================

export function formatDate(date: string | Date, pattern = 'dd/MM/yyyy'): string {
  const parsed = typeof date === 'string' ? parseISO(date) : date
  return format(parsed, pattern, { locale: ptBR })
}

export function formatDateTime(date: string | Date): string {
  return formatDate(date, 'dd/MM/yyyy HH:mm')
}

export function formatRelativeDate(date: string | Date): string {
  const parsed = typeof date === 'string' ? parseISO(date) : date
  return formatDistanceToNow(parsed, { addSuffix: true, locale: ptBR })
}

export function daysUntil(date: string | Date): number {
  const parsed = typeof date === 'string' ? parseISO(date) : date
  return differenceInDays(parsed, new Date())
}

export function isPastDate(date: string | Date): boolean {
  const parsed = typeof date === 'string' ? parseISO(date) : date
  return isBefore(parsed, new Date())
}

export function isFutureDate(date: string | Date): boolean {
  const parsed = typeof date === 'string' ? parseISO(date) : date
  return isAfter(parsed, new Date())
}

// ============================================
// Formatação de Valores
// ============================================

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

export function formatNumber(value: number, decimals = 0): string {
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number, decimals = 1): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100)
}

export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB']
  let unitIndex = 0
  let size = bytes

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`
}

// ============================================
// Formatação de Documentos
// ============================================

export function formatCPF(cpf: string): string {
  const cleaned = cpf.replace(/\D/g, '')
  return cleaned.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
}

export function formatCNPJ(cnpj: string): string {
  const cleaned = cnpj.replace(/\D/g, '')
  return cleaned.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
}

export function formatPhone(phone: string): string {
  const cleaned = phone.replace(/\D/g, '')
  if (cleaned.length === 11) {
    return cleaned.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3')
  }
  return cleaned.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3')
}

export function formatCEP(cep: string): string {
  const cleaned = cep.replace(/\D/g, '')
  return cleaned.replace(/(\d{5})(\d{3})/, '$1-$2')
}

export function formatNumeroCNJ(numero: string): string {
  // Formato: NNNNNNN-DD.AAAA.J.TR.OOOO
  const cleaned = numero.replace(/\D/g, '')
  if (cleaned.length !== 20) return numero
  return cleaned.replace(
    /(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{4})/,
    '$1-$2.$3.$4.$5.$6'
  )
}

// ============================================
// Validações
// ============================================

export function isValidCPF(cpf: string): boolean {
  const cleaned = cpf.replace(/\D/g, '')
  if (cleaned.length !== 11) return false
  if (/^(\d)\1+$/.test(cleaned)) return false

  let sum = 0
  for (let i = 0; i < 9; i++) {
    sum += parseInt(cleaned[i]) * (10 - i)
  }
  let digit = (sum * 10) % 11
  if (digit === 10) digit = 0
  if (digit !== parseInt(cleaned[9])) return false

  sum = 0
  for (let i = 0; i < 10; i++) {
    sum += parseInt(cleaned[i]) * (11 - i)
  }
  digit = (sum * 10) % 11
  if (digit === 10) digit = 0
  return digit === parseInt(cleaned[10])
}

export function isValidCNPJ(cnpj: string): boolean {
  const cleaned = cnpj.replace(/\D/g, '')
  if (cleaned.length !== 14) return false
  if (/^(\d)\1+$/.test(cleaned)) return false

  const weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
  const weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

  let sum = 0
  for (let i = 0; i < 12; i++) {
    sum += parseInt(cleaned[i]) * weights1[i]
  }
  let digit = sum % 11 < 2 ? 0 : 11 - (sum % 11)
  if (digit !== parseInt(cleaned[12])) return false

  sum = 0
  for (let i = 0; i < 13; i++) {
    sum += parseInt(cleaned[i]) * weights2[i]
  }
  digit = sum % 11 < 2 ? 0 : 11 - (sum % 11)
  return digit === parseInt(cleaned[13])
}

export function isValidEmail(email: string): boolean {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return regex.test(email)
}

// ============================================
// Labels para Enums
// ============================================

export const TIPO_BENEFICIO_LABELS: Record<string, string> = {
  aposentadoria_idade: 'Aposentadoria por Idade',
  aposentadoria_tempo_contribuicao: 'Aposentadoria por Tempo de Contribuição',
  aposentadoria_especial: 'Aposentadoria Especial',
  aposentadoria_invalidez: 'Aposentadoria por Invalidez',
  auxilio_doenca: 'Auxílio-Doença',
  auxilio_acidente: 'Auxílio-Acidente',
  bpc_loas_idoso: 'BPC/LOAS - Idoso',
  bpc_loas_deficiente: 'BPC/LOAS - Deficiente',
  pensao_morte: 'Pensão por Morte',
  salario_maternidade: 'Salário Maternidade',
  revisao_beneficio: 'Revisão de Benefício',
}

export const FASE_PROCESSUAL_LABELS: Record<string, string> = {
  administrativo: 'Administrativo',
  judicial_1a_instancia: 'Judicial - 1ª Instância',
  judicial_2a_instancia: 'Judicial - 2ª Instância',
  tribunal_superior: 'Tribunal Superior',
  cumprimento_sentenca: 'Cumprimento de Sentença',
  encerrado: 'Encerrado',
}

export const STATUS_PRAZO_LABELS: Record<string, string> = {
  pendente: 'Pendente',
  concluido: 'Concluído',
  cancelado: 'Cancelado',
  perdido: 'Perdido',
}

export const TIPO_DOCUMENTO_LABELS: Record<string, string> = {
  cnis: 'CNIS',
  ppp: 'PPP',
  laudo_medico: 'Laudo Médico',
  rg: 'RG',
  cpf: 'CPF',
  cnh: 'CNH',
  comprovante_residencia: 'Comprovante de Residência',
  certidao_casamento: 'Certidão de Casamento',
  certidao_nascimento: 'Certidão de Nascimento',
  ctps: 'CTPS',
  sentenca: 'Sentença',
  peticao: 'Petição',
  recurso: 'Recurso',
  procuracao: 'Procuração',
  outros: 'Outros',
}

export const UF_OPTIONS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
]

export const ESTADO_CIVIL_OPTIONS = [
  { value: 'solteiro', label: 'Solteiro(a)' },
  { value: 'casado', label: 'Casado(a)' },
  { value: 'divorciado', label: 'Divorciado(a)' },
  { value: 'viuvo', label: 'Viúvo(a)' },
  { value: 'uniao_estavel', label: 'União Estável' },
]
