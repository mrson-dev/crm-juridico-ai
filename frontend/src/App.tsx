import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'

// Layouts
import { DashboardLayout } from './layouts/DashboardLayout'
import { AuthLayout } from './layouts/AuthLayout'

// Pages - Auth
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'
import { ForgotPasswordPage } from './pages/auth/ForgotPasswordPage'

// Pages - Dashboard
import { DashboardPage } from './pages/dashboard/DashboardPage'
import { ClientesPage } from './pages/clientes/ClientesPage'
import { ClienteDetalhePage } from './pages/clientes/ClienteDetalhePage'
import { ProcessosPage } from './pages/processos/ProcessosPage'
import { ProcessoDetalhePage } from './pages/processos/ProcessoDetalhePage'
import { DocumentosPage } from './pages/documentos/DocumentosPage'
import { HonorariosPage } from './pages/honorarios/HonorariosPage'
import { NotificacoesPage } from './pages/notificacoes/NotificacoesPage'
import { ConfiguracoesPage } from './pages/configuracoes/ConfiguracoesPage'
import { PrazosPage } from './pages/prazos/PrazosPage'

// Loading component
import { LoadingScreen } from './components/ui/loading-screen'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <LoadingScreen />
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <LoadingScreen />
  }

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route element={<AuthLayout />}>
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <PublicRoute>
              <ForgotPasswordPage />
            </PublicRoute>
          }
        />
      </Route>

      {/* Protected routes */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/clientes" element={<ClientesPage />} />
        <Route path="/clientes/:id" element={<ClienteDetalhePage />} />
        <Route path="/processos" element={<ProcessosPage />} />
        <Route path="/processos/:id" element={<ProcessoDetalhePage />} />
        <Route path="/documentos" element={<DocumentosPage />} />
        <Route path="/honorarios" element={<HonorariosPage />} />
        <Route path="/notificacoes" element={<NotificacoesPage />} />
        <Route path="/prazos" element={<PrazosPage />} />
        <Route path="/configuracoes" element={<ConfiguracoesPage />} />
      </Route>

      {/* Redirect root to dashboard or login */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default App
