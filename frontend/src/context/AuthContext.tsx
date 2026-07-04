import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { postLogin } from '../api/auth'

interface AuthState {
  token: string | null
  role: string | null
  username: string | null
  isAuthenticated: boolean
  login: (
    username: string,
    role: 'bank_officer' | 'underwriter' | 'admin',
  ) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem('fs_token'),
  )
  const [role, setRole] = useState<string | null>(
    () => localStorage.getItem('fs_role'),
  )
  const [username, setUsername] = useState<string | null>(
    () => localStorage.getItem('fs_username'),
  )

  const login = useCallback(
    async (
      uname: string,
      urole: 'bank_officer' | 'underwriter' | 'admin',
    ) => {
      const resp = await postLogin(uname, urole)
      localStorage.setItem('fs_token', resp.access_token)
      localStorage.setItem('fs_role', resp.role)
      localStorage.setItem('fs_username', uname)
      setToken(resp.access_token)
      setRole(resp.role)
      setUsername(uname)
    },
    [],
  )

  const logout = useCallback(() => {
    localStorage.removeItem('fs_token')
    localStorage.removeItem('fs_role')
    localStorage.removeItem('fs_username')
    setToken(null)
    setRole(null)
    setUsername(null)
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      token,
      role,
      username,
      isAuthenticated: !!token,
      login,
      logout,
    }),
    [token, role, username, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
