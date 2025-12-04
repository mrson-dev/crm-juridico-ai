// Placeholder - implementar prazos
import { Card, CardContent } from '@/components/ui/card'
import { Calendar } from 'lucide-react'

export function PrazosPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Prazos</h1>
        <p className="text-muted-foreground">Acompanhe prazos processuais</p>
      </div>

      <Card>
        <CardContent className="py-12 text-center">
          <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Nenhum prazo pendente</p>
          <p className="text-muted-foreground">
            Todos os prazos estão em dia!
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
