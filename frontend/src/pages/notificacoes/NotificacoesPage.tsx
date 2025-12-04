// Placeholder - implementar notificações
import { Card, CardContent } from '@/components/ui/card'
import { Bell } from 'lucide-react'

export function NotificacoesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Notificações</h1>
        <p className="text-muted-foreground">Acompanhe alertas e atualizações</p>
      </div>

      <Card>
        <CardContent className="py-12 text-center">
          <Bell className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Nenhuma notificação</p>
          <p className="text-muted-foreground">
            Você está em dia com tudo!
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
