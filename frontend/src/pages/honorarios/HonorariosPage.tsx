// Placeholder - implementar honorários
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DollarSign, Plus } from 'lucide-react'

export function HonorariosPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Honorários</h1>
          <p className="text-muted-foreground">Contratos e controle financeiro</p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Novo Contrato
        </Button>
      </div>

      <Card>
        <CardContent className="py-12 text-center">
          <DollarSign className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Nenhum contrato</p>
          <p className="text-muted-foreground mb-4">
            Cadastre contratos de honorários
          </p>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Novo Contrato
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
