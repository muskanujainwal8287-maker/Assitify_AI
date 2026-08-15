import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { TOKEN_KEY, USER_KEY, authApi } from '../lib/api.ts'
import type { User, UserLoginRequest, UserRegisterRequest, UserUpdateRequest } from '../types/api.ts'

type AuthContextValue = {
  token: string | null
  user: User | null
  ready: boolean
  login: (payload: UserLoginRequest) => Promise<void>
  register: (payload: UserRegisterRequest) => Promise<void>
  updateProfile: (payload: UserUpdateRequest) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function persistSession(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  const logout = useCallback(() => {
    clearSession()
    setToken(null)
    setUser(null)
  }, [])

  const applyAuth = useCallback((accessToken: string, nextUser: User) => {
    persistSession(accessToken, nextUser)
    setToken(accessToken)
    setUser(nextUser)
  }, [])

  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    const rawUser = localStorage.getItem(USER_KEY)
    if (!storedToken) {
      setReady(true)
      return
    }
    if (rawUser) {
      try {
        setUser(JSON.parse(rawUser) as User)
        setToken(storedToken)
      } catch {
        clearSession()
        setReady(true)
        return
      }
    }
    authApi
      .me()
      .then((nextUser) => applyAuth(storedToken, nextUser))
      .catch(() => logout())
      .finally(() => setReady(true))
  }, [applyAuth, logout])

  useEffect(() => {
    const onUnauthorized = () => logout()
    window.addEventListener('assitify:unauthorized', onUnauthorized)
    return () => window.removeEventListener('assitify:unauthorized', onUnauthorized)
  }, [logout])

  const login = useCallback(
    async (payload: UserLoginRequest) => {
      const result = await authApi.login(payload)
      applyAuth(result.access_token, result.user)
    },
    [applyAuth],
  )

  const register = useCallback(
    async (payload: UserRegisterRequest) => {
      const result = await authApi.register(payload)
      applyAuth(result.access_token, result.user)
    },
    [applyAuth],
  )

  const updateProfile = useCallback(async (payload: UserUpdateRequest) => {
    const nextUser = await authApi.updateMe(payload)
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
    setUser(nextUser)
    return nextUser
  }, [])

  const value = useMemo(
    () => ({ token, user, ready, login, register, updateProfile, logout }),
    [token, user, ready, login, register, updateProfile, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
