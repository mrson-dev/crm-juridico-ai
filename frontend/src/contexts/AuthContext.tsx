import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  auth,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as firebaseSignOut,
  sendPasswordResetEmail,
  onAuthStateChanged,
  signInWithPopup,
  googleProvider,
  isFirebaseConfigured,
  type FirebaseUser,
} from '@/lib/firebase'
import api from '@/lib/api'
import type { Usuario, LoginCredentials, RegisterData, AuthTokens } from '@/types'

interface AuthContextType {
  user: Usuario | null
  firebaseUser: FirebaseUser | null
  loading: boolean
  error: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  loginWithGoogle: () => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => Promise<void>
  resetPassword: (email: string) => Promise<void>
  clearError: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Usuario | null>(null)
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  // Carrega usuário do backend com token
  const loadUser = useCallback(async (token: string) => {
    try {
      localStorage.setItem('access_token', token)
      const response = await api.get('/auth/me')
      setUser(response.data.data)
    } catch (err) {
      console.error('Erro ao carregar usuário:', err)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setUser(null)
    }
  }, [])

  // Monitora estado do Firebase Auth
  useEffect(() => {
    if (!auth || !isFirebaseConfigured()) {
      // Fallback para JWT local se Firebase não configurado
      const token = localStorage.getItem('access_token')
      if (token) {
        loadUser(token).finally(() => setLoading(false))
      } else {
        setLoading(false)
      }
      return
    }

    const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
      setFirebaseUser(fbUser)
      if (fbUser) {
        try {
          const idToken = await fbUser.getIdToken()
          // Sincroniza com backend
          const response = await api.post('/auth/login/firebase', {
            firebase_token: idToken,
          })
          const { user: userData, tokens } = response.data.data
          localStorage.setItem('access_token', tokens.access_token)
          localStorage.setItem('refresh_token', tokens.refresh_token)
          setUser(userData)
        } catch (err) {
          console.error('Erro ao sincronizar com backend:', err)
          setError('Erro ao autenticar. Tente novamente.')
        }
      } else {
        setUser(null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
      setLoading(false)
    })

    return () => unsubscribe()
  }, [loadUser])

  // Login com email/senha
  const login = useCallback(async (credentials: LoginCredentials) => {
    setLoading(true)
    setError(null)

    try {
      if (auth && isFirebaseConfigured()) {
        // Login via Firebase
        await signInWithEmailAndPassword(auth, credentials.email, credentials.password)
      } else {
        // Login via JWT local
        const response = await api.post('/auth/login', credentials)
        const { user: userData, tokens }: { user: Usuario; tokens: AuthTokens } = response.data.data
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        setUser(userData)
      }
      navigate('/dashboard')
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Credenciais inválidas'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [navigate])

  // Login com Google
  const loginWithGoogle = useCallback(async () => {
    if (!auth || !isFirebaseConfigured()) {
      setError('Login com Google não disponível')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await signInWithPopup(auth, googleProvider)
      navigate('/dashboard')
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao fazer login com Google'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [navigate])

  // Registro
  const register = useCallback(async (data: RegisterData) => {
    setLoading(true)
    setError(null)

    try {
      if (auth && isFirebaseConfigured()) {
        // Cria usuário no Firebase
        const credential = await createUserWithEmailAndPassword(auth, data.email, data.password)
        const idToken = await credential.user.getIdToken()

        // Registra no backend
        await api.post('/auth/register/firebase', {
          firebase_token: idToken,
          nome: data.nome,
          telefone: data.telefone,
          oab_numero: data.oab_numero,
          oab_uf: data.oab_uf,
        })
      } else {
        // Registro via JWT local
        const response = await api.post('/auth/register', data)
        const { user: userData, tokens }: { user: Usuario; tokens: AuthTokens } = response.data.data
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        setUser(userData)
      }
      navigate('/dashboard')
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao criar conta'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [navigate])

  // Logout
  const logout = useCallback(async () => {
    setLoading(true)
    try {
      if (auth && isFirebaseConfigured()) {
        await firebaseSignOut(auth)
      }
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setUser(null)
      setFirebaseUser(null)
      navigate('/login')
    } catch (err) {
      console.error('Erro ao fazer logout:', err)
    } finally {
      setLoading(false)
    }
  }, [navigate])

  // Reset de senha
  const resetPassword = useCallback(async (email: string) => {
    setError(null)
    try {
      if (auth && isFirebaseConfigured()) {
        await sendPasswordResetEmail(auth, email)
      } else {
        await api.post('/auth/forgot-password', { email })
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Erro ao enviar email de recuperação'
      setError(errorMessage)
      throw err
    }
  }, [])

  // Limpa erro
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const value: AuthContextType = {
    user,
    firebaseUser,
    loading,
    error,
    login,
    loginWithGoogle,
    register,
    logout,
    resetPassword,
    clearError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
