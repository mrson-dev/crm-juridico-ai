import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingScreen } from '@/components/ui/loading-screen'
import {
  ArrowLeft,
  User,
  Mail,
  Phone,
  MapPin,
  Calendar,
  FileText,
  Briefcase,
  Edit,
} from 'lucide-react'
import { formatCPF, formatPhone, formatDate } from '@/lib/utils'
import type { Cliente, Processo } from '@/types'

export function ClienteDetalhePage() {
  const { id } = useParams<{ id: string }>()

  const { data: cliente, isLoading } = useQuery<Cliente>({
    queryKey: ['cliente', id],
    queryFn: async () => {
      const response = await api.get(`/clientes/${id}`)
      return response.data.data
    },
  })

  const { data: processos } = useQuery<Processo[]>({
    queryKey: ['processos', 'cliente', id],
    queryFn: async () => {
      const response = await api.get(`/processos?cliente_id=${id}`)
      return response.data.data
    },
    enabled: !!id,
  })

  if (isLoading) {
    return <LoadingScreen message="Carregando cliente..." />
  }

  if (!cliente) {
    return (
      <div className="text-center py-12">
        <p className="text-lg text-muted-foreground">Cliente não encontrado</p>
        <Button asChild className="mt-4">
          <Link to="/clientes">Voltar</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/clientes">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{cliente.nome}</h1>
          <p className="text-muted-foreground">{formatCPF(cliente.cpf)}</p>
        </div>
        <Button variant="outline">
          <Edit className="h-4 w-4 mr-2" />
          Editar
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Dados Pessoais
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-sm text-muted-foreground">CPF</p>
                <p className="font-medium">{formatCPF(cliente.cpf)}</p>
              </div>
              {cliente.rg && (
                <div>
                  <p className="text-sm text-muted-foreground">RG</p>
                  <p className="font-medium">{cliente.rg}</p>
                </div>
              )}
              {cliente.data_nascimento && (
                <div>
                  <p className="text-sm text-muted-foreground">Data de Nascimento</p>
                  <p className="font-medium">{formatDate(cliente.data_nascimento)}</p>
                </div>
              )}
              {cliente.estado_civil && (
                <div>
                  <p className="text-sm text-muted-foreground">Estado Civil</p>
                  <p className="font-medium capitalize">{cliente.estado_civil}</p>
                </div>
              )}
              {cliente.profissao && (
                <div>
                  <p className="text-sm text-muted-foreground">Profissão</p>
                  <p className="font-medium">{cliente.profissao}</p>
                </div>
              )}
              {cliente.nit && (
                <div>
                  <p className="text-sm text-muted-foreground">NIT/PIS</p>
                  <p className="font-medium">{cliente.nit}</p>
                </div>
              )}
              {cliente.nome_mae && (
                <div className="sm:col-span-2">
                  <p className="text-sm text-muted-foreground">Nome da Mãe</p>
                  <p className="font-medium">{cliente.nome_mae}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Phone className="h-5 w-5" />
                Contato
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2">
              {cliente.email && (
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Email</p>
                    <p className="font-medium">{cliente.email}</p>
                  </div>
                </div>
              )}
              {cliente.telefone && (
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Telefone</p>
                    <p className="font-medium">{formatPhone(cliente.telefone)}</p>
                  </div>
                </div>
              )}
              {cliente.celular && (
                <div className="flex items-center gap-2">
                  <Phone className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm text-muted-foreground">Celular</p>
                    <p className="font-medium">{formatPhone(cliente.celular)}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {(cliente.endereco || cliente.cidade) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5" />
                  Endereço
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="font-medium">
                  {cliente.endereco}
                  {cliente.cidade && ` - ${cliente.cidade}`}
                  {cliente.uf && `/${cliente.uf}`}
                  {cliente.cep && ` - CEP: ${cliente.cep}`}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="h-5 w-5" />
                Processos
              </CardTitle>
              <Button size="sm" asChild>
                <Link to={`/processos?cliente=${id}`}>Ver todos</Link>
              </Button>
            </CardHeader>
            <CardContent>
              {processos && processos.length > 0 ? (
                <div className="space-y-2">
                  {processos.slice(0, 5).map((processo) => (
                    <Link
                      key={processo.id}
                      to={`/processos/${processo.id}`}
                      className="block p-3 rounded-lg border hover:bg-accent transition-colors"
                    >
                      <p className="font-medium text-sm">
                        {processo.numero_cnj || processo.numero_administrativo || 'Sem número'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {processo.tipo_beneficio}
                      </p>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Nenhum processo
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Documentos
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full" asChild>
                <Link to={`/documentos?cliente=${id}`}>
                  Ver documentos
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Informações
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Cadastrado em</span>
                <span>{formatDate(cliente.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">LGPD</span>
                <span className={cliente.consentimento_lgpd ? 'text-green-600' : 'text-red-600'}>
                  {cliente.consentimento_lgpd ? 'Consentido' : 'Pendente'}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
