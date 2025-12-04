import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Search, User, Phone, Mail, FileText, Eye } from 'lucide-react'
import { formatCPF, formatPhone, isValidCPF } from '@/lib/utils'
import type { Cliente, ClienteCreate, PaginatedResponse } from '@/types'

const clienteSchema = z.object({
  cpf: z.string().length(11, 'CPF deve ter 11 dígitos').refine(isValidCPF, 'CPF inválido'),
  nome: z.string().min(3, 'Nome deve ter pelo menos 3 caracteres'),
  email: z.string().email('Email inválido').optional().or(z.literal('')),
  telefone: z.string().optional(),
  celular: z.string().optional(),
  consentimento_lgpd: z.boolean().default(true),
})

type ClienteForm = z.infer<typeof clienteSchema>

export function ClientesPage() {
  const [search, setSearch] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ClienteForm>({
    resolver: zodResolver(clienteSchema),
    defaultValues: { consentimento_lgpd: true },
  })

  const { data, isLoading } = useQuery<PaginatedResponse<Cliente>>({
    queryKey: ['clientes', search],
    queryFn: async () => {
      const params = search ? `?search=${encodeURIComponent(search)}` : ''
      const response = await api.get(`/clientes${params}`)
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: (data: ClienteCreate) => api.post('/clientes', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      setDialogOpen(false)
      reset()
      toast({ title: 'Cliente criado!', variant: 'success' })
    },
    onError: () => {
      toast({ title: 'Erro ao criar cliente', variant: 'destructive' })
    },
  })

  const onSubmit = (data: ClienteForm) => {
    createMutation.mutate({
      ...data,
      email: data.email || undefined,
    })
  }

  const clientes = data?.data || []

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Clientes</h1>
          <p className="text-muted-foreground">
            {data?.total || 0} cliente(s) cadastrado(s)
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Novo Cliente
        </Button>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar por nome ou CPF..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">Carregando...</div>
      ) : clientes.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <User className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-lg font-medium">Nenhum cliente encontrado</p>
            <p className="text-muted-foreground mb-4">
              {search ? 'Tente outro termo de busca' : 'Cadastre seu primeiro cliente'}
            </p>
            {!search && (
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Novo Cliente
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {clientes.map((cliente) => (
            <Card key={cliente.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate">{cliente.nome}</p>
                    <p className="text-sm font-normal text-muted-foreground">
                      {formatCPF(cliente.cpf)}
                    </p>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {cliente.email && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Mail className="h-4 w-4" />
                    <span className="truncate">{cliente.email}</span>
                  </div>
                )}
                {(cliente.telefone || cliente.celular) && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Phone className="h-4 w-4" />
                    <span>{formatPhone(cliente.celular || cliente.telefone || '')}</span>
                  </div>
                )}
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" className="flex-1" asChild>
                    <Link to={`/clientes/${cliente.id}`}>
                      <Eye className="h-4 w-4 mr-1" />
                      Ver
                    </Link>
                  </Button>
                  <Button variant="outline" size="sm" className="flex-1" asChild>
                    <Link to={`/processos?cliente=${cliente.id}`}>
                      <FileText className="h-4 w-4 mr-1" />
                      Processos
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Novo Cliente</DialogTitle>
            <DialogDescription>
              Preencha os dados do cliente. CPF e nome são obrigatórios.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="cpf" required>CPF</Label>
                <Input
                  id="cpf"
                  placeholder="00000000000"
                  maxLength={11}
                  {...register('cpf')}
                  error={errors.cpf?.message}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nome" required>Nome</Label>
                <Input
                  id="nome"
                  placeholder="Nome completo"
                  {...register('nome')}
                  error={errors.nome?.message}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="email@exemplo.com"
                {...register('email')}
                error={errors.email?.message}
              />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="telefone">Telefone</Label>
                <Input
                  id="telefone"
                  placeholder="(00) 0000-0000"
                  {...register('telefone')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="celular">Celular</Label>
                <Input
                  id="celular"
                  placeholder="(00) 00000-0000"
                  {...register('celular')}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancelar
              </Button>
              <Button type="submit" loading={createMutation.isPending}>
                Criar Cliente
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
