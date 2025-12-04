import { Outlet } from 'react-router-dom'
import { Scale } from 'lucide-react'

export function AuthLayout() {
  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-juridico-600 to-juridico-900 p-12 flex-col justify-between">
        <div className="flex items-center gap-3">
          <Scale className="h-10 w-10 text-white" />
          <span className="text-2xl font-bold text-white">CRM Jurídico AI</span>
        </div>
        
        <div className="space-y-6">
          <h1 className="text-4xl font-bold text-white leading-tight">
            Gerencie seu escritório de<br />
            <span className="text-juridico-200">Direito Previdenciário</span><br />
            com Inteligência Artificial
          </h1>
          <p className="text-lg text-juridico-100 max-w-md">
            Automatize a extração de documentos CNIS, PPP e laudos. 
            Gerencie prazos, processos e honorários em um só lugar.
          </p>
        </div>

        <div className="flex items-center gap-8">
          <div className="text-center">
            <p className="text-3xl font-bold text-white">+50%</p>
            <p className="text-sm text-juridico-200">Produtividade</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-white">-80%</p>
            <p className="text-sm text-juridico-200">Tempo em OCR</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-white">0</p>
            <p className="text-sm text-juridico-200">Prazos Perdidos</p>
          </div>
        </div>
      </div>

      {/* Right side - Auth forms */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center justify-center gap-3 mb-8">
            <Scale className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold">CRM Jurídico AI</span>
          </div>
          
          <Outlet />
        </div>
      </div>
    </div>
  )
}
