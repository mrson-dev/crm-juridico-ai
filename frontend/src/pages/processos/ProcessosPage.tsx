// Placeholder - implementar lista de processos
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Briefcase, Plus } from 'lucide-react'

export function ProcessosPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Processos</h1>
          <p className="text-muted-foreground">Gerencie seus processos previdenciários</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Novo Processo
        </Button>
      </div>

      <Card>
        <CardContent className="py-12 text-center">
          <Briefcase className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Nenhum processo cadastrado</p>
          <p className="text-muted-foreground mb-4">
            Cadastre seu primeiro processo para começar
          </p>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Novo Processo
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
