// Placeholder - implementar lista de documentos
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Upload } from 'lucide-react'

export function DocumentosPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Documentos</h1>
          <p className="text-muted-foreground">Gerencie documentos com extração por IA</p>
        </div>
        <Button>
          <Upload className="h-4 w-4 mr-2" />
          Upload
        </Button>
      </div>

      <Card>
        <CardContent className="py-12 text-center">
          <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-lg font-medium">Nenhum documento</p>
          <p className="text-muted-foreground mb-4">
            Faça upload de CNIS, PPP e outros documentos
          </p>
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
