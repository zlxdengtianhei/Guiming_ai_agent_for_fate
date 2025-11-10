'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { TarotLoader } from '@/components/ui/TarotLoader'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-[var(--bg-primary)]">
        <TarotLoader size="lg" />
        <div className="text-[var(--text-primary)]">加载中...</div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return <>{children}</>
}

