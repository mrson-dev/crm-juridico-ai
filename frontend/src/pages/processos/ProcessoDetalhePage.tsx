// Placeholder - implementar detalhes do processo
import { useParams, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'

export function ProcessoDetalhePage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/processos">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-bold">Detalhes do Processo</h1>
          <p className="text-muted-foreground">ID: {id}</p>
        </div>
      </div>

      <p className="text-muted-foreground">Página em desenvolvimento...</p>
    </div>
  )
}
