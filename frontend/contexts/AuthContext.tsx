'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authAPI, userAPI, UserProfile } from '@/lib/api'

interface AuthContextType {
  user: { id: string; email: string } | null
  profile: UserProfile | null
  loading: boolean
  signin: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  signout: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<{ id: string; email: string } | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user is logged in
    const checkAuth = async () => {
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
        const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null
        
        // 检查是否30天未使用
        const lastActivity = typeof window !== 'undefined' ? localStorage.getItem('last_activity') : null
        if (lastActivity) {
          const daysSinceLastActivity = (Date.now() - parseInt(lastActivity)) / (1000 * 60 * 60 * 24)
          if (daysSinceLastActivity > 30) {
            // 30天未使用，清除token
            if (typeof window !== 'undefined') {
              localStorage.removeItem('access_token')
              localStorage.removeItem('refresh_token')
              localStorage.removeItem('user_id')
              localStorage.removeItem('user_email')
              localStorage.removeItem('last_activity')
            }
            setUser(null)
            setProfile(null)
            setLoading(false)
            return
          }
        }

        // 如果有token或refreshToken，尝试获取用户信息
        // axios拦截器会自动处理token刷新
        if (token || refreshToken) {
          try {
            // getMe()会通过axios拦截器自动处理token刷新
            const userData = await authAPI.getMe()
            setUser(userData)
            
            // Try to load profile
            try {
              const profileData = await userAPI.getProfile()
              setProfile(profileData)
            } catch (error) {
              // Profile doesn't exist yet, that's okay
              setProfile(null)
            }
          } catch (error: any) {
            // 如果getMe()失败（包括拦截器刷新失败），清除token
            console.error('[AuthContext] Failed to get user info:', {
              status: error?.response?.status,
              message: error?.message,
              data: error?.response?.data
            })
            
            // 清除所有token
            if (typeof window !== 'undefined') {
              localStorage.removeItem('access_token')
              localStorage.removeItem('refresh_token')
              localStorage.removeItem('user_id')
              localStorage.removeItem('user_email')
              localStorage.removeItem('last_activity')
            }
            setUser(null)
            setProfile(null)
          }
        } else {
          console.log('[AuthContext] No tokens found, user not authenticated')
          setUser(null)
          setProfile(null)
        }
      } catch (error) {
        // Not authenticated
        console.error('[AuthContext] Auth check error:', error)
        setUser(null)
        setProfile(null)
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
    
    // 监听认证状态变化事件（用于邮箱确认后的状态刷新）
    const handleAuthStateChange = () => {
      checkAuth()
    }
    window.addEventListener('authStateChanged', handleAuthStateChange)
    
    return () => {
      window.removeEventListener('authStateChanged', handleAuthStateChange)
    }
  }, [])

  const signin = async (email: string, password: string) => {
    const response = await authAPI.signin({ email, password })
    // Token is already saved in api.ts signin function
    setUser({ id: response.user_id, email: response.email })
    
    // Try to load profile
    try {
      const profileData = await userAPI.getProfile()
      setProfile(profileData)
    } catch (error) {
      setProfile(null)
    }
  }

  const signup = async (email: string, password: string) => {
    const response = await authAPI.signup({ email, password })
    
    // 如果需要邮箱确认，不自动登录
    if (response.requires_email_confirmation) {
      // 使用自定义错误类，避免在控制台显示为错误
      const confirmationError: any = new Error('EMAIL_CONFIRMATION_REQUIRED')
      confirmationError.isConfirmationRequired = true
      throw confirmationError
    }
    
    // 如果不需要邮箱确认，自动登录
    await signin(email, password)
  }

  const signout = async () => {
    await authAPI.signout()
    setUser(null)
    setProfile(null)
  }

  const refreshProfile = async () => {
    if (!user) return
    try {
      const profileData = await userAPI.getProfile()
      setProfile(profileData)
    } catch (error) {
      setProfile(null)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        loading,
        signin,
        signup,
        signout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

