import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Users,
  Briefcase,
  Calendar,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  Clock,
  FileText,
  Plus,
  ArrowRight,
} from 'lucide-react'
import { formatCurrency, formatDate, daysUntil, TIPO_BENEFICIO_LABELS, FASE_PROCESSUAL_LABELS } from '@/lib/utils'
import type { DashboardStats, Prazo, Processo } from '@/types'

export function DashboardPage() {
  // Busca estatísticas
  const { data: stats, isLoading: loadingStats } = useQuery<DashboardStats>({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      const response = await api.get('/dashboard/stats')
      return response.data.data
    },
  })

  // Busca prazos próximos
  const { data: prazosProximos } = useQuery<Prazo[]>({
    queryKey: ['prazos', 'proximos'],
    queryFn: async () => {
      const response = await api.get('/processos/prazos/proximos')
      return response.data.data
    },
  })

  // Busca processos recentes
  const { data: processosRecentes } = useQuery<Processo[]>({
    queryKey: ['processos', 'recentes'],
    queryFn: async () => {
      const response = await api.get('/processos?page_size=5')
      return response.data.data
    },
  })

  const statCards = [
    {
      title: 'Clientes',
      value: stats?.total_clientes || 0,
      icon: Users,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      href: '/clientes',
    },
    {
      title: 'Processos Ativos',
      value: stats?.processos_ativos || 0,
      icon: Briefcase,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      href: '/processos',
    },
    {
      title: 'Prazos Próximos',
      value: stats?.prazos_proximos || 0,
      icon: Calendar,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      href: '/prazos',
    },
    {
      title: 'Honorários Pendentes',
      value: formatCurrency(stats?.valor_honorarios_pendente || 0),
      icon: DollarSign,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      href: '/honorarios',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Visão geral do seu escritório
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild>
            <Link to="/clientes">
              <Plus className="h-4 w-4 mr-2" />
              Novo Cliente
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link to="/processos">
              <Plus className="h-4 w-4 mr-2" />
              Novo Processo
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Link key={stat.title} to={stat.href}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">
                      {stat.title}
                    </p>
                    <p className="text-2xl font-bold mt-1">
                      {loadingStats ? '...' : stat.value}
                    </p>
                  </div>
                  <div className={`p-3 rounded-full ${stat.bgColor}`}>
                    <stat.icon className={`h-6 w-6 ${stat.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Alertas de Prazos */}
      {(stats?.prazos_vencidos ?? 0) > 0 && (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              <div className="flex-1">
                <p className="font-medium text-destructive">
                  {stats?.prazos_vencidos} prazo(s) vencido(s)!
                </p>
                <p className="text-sm text-muted-foreground">
                  Verifique imediatamente os prazos vencidos
                </p>
              </div>
              <Button variant="destructive" size="sm" asChild>
                <Link to="/prazos">Ver prazos</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Prazos Próximos */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Prazos Próximos
              </CardTitle>
              <CardDescription>Próximos 7 dias</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/prazos">
                Ver todos
                <ArrowRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {prazosProximos && prazosProximos.length > 0 ? (
                prazosProximos.slice(0, 5).map((prazo) => {
                  const dias = daysUntil(prazo.data_fatal)
                  const isUrgente = dias <= 2
                  
                  return (
                    <div
                      key={prazo.id}
                      className={`flex items-center justify-between p-3 rounded-lg border ${
                        isUrgente ? 'border-destructive bg-destructive/5' : ''
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{prazo.descricao}</p>
                        <p className="text-sm text-muted-foreground">
                          {prazo.processo?.numero_cnj || 'Processo sem número'}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className={`text-sm font-medium ${isUrgente ? 'text-destructive' : ''}`}>
                          {formatDate(prazo.data_fatal)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {dias === 0 ? 'Hoje!' : dias === 1 ? 'Amanhã' : `${dias} dias`}
                        </p>
                      </div>
                    </div>
                  )
                })
              ) : (
                <p className="text-center text-muted-foreground py-4">
                  Nenhum prazo nos próximos 7 dias
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Processos Recentes */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Processos Recentes
              </CardTitle>
              <CardDescription>Últimos processos cadastrados</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/processos">
                Ver todos
                <ArrowRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {processosRecentes && processosRecentes.length > 0 ? (
                processosRecentes.map((processo) => (
                  <Link
                    key={processo.id}
                    to={`/processos/${processo.id}`}
                    className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">
                        {processo.cliente?.nome || 'Cliente não identificado'}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {TIPO_BENEFICIO_LABELS[processo.tipo_beneficio] || processo.tipo_beneficio}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                        {FASE_PROCESSUAL_LABELS[processo.fase_atual] || processo.fase_atual}
                      </span>
                    </div>
                  </Link>
                ))
              ) : (
                <p className="text-center text-muted-foreground py-4">
                  Nenhum processo cadastrado
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Resumo Financeiro */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Resumo Financeiro
          </CardTitle>
          <CardDescription>Visão geral dos honorários</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 rounded-lg bg-green-50 dark:bg-green-950">
              <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                Recebido
              </p>
              <p className="text-2xl font-bold text-green-700 dark:text-green-300">
                {formatCurrency(stats?.valor_honorarios_recebido || 0)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-orange-50 dark:bg-orange-950">
              <p className="text-sm text-orange-600 dark:text-orange-400 font-medium">
                Pendente
              </p>
              <p className="text-2xl font-bold text-orange-700 dark:text-orange-300">
                {formatCurrency(stats?.valor_honorarios_pendente || 0)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950">
              <p className="text-sm text-blue-600 dark:text-blue-400 font-medium">
                Total
              </p>
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {formatCurrency(
                  (stats?.valor_honorarios_recebido || 0) +
                  (stats?.valor_honorarios_pendente || 0)
                )}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
