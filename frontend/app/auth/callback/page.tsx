'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLanguage } from '@/contexts/LanguageContext'
import { Button } from '@/components/ui/Button'
import { TarotLoader } from '@/components/ui/TarotLoader'

export default function AuthCallbackPage() {
  const router = useRouter()
  const { t } = useLanguage()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const handleCallback = async () => {
      // Supabase 回调参数在 hash (#) 中，不在 query string (?)
      // 需要解析 window.location.hash
      const hash = typeof window !== 'undefined' ? window.location.hash : ''
      
      // 解析 hash 参数
      const params = new URLSearchParams(hash.substring(1)) // 去掉开头的 #
      
      const error = params.get('error')
      const errorDescription = params.get('error_description')
      const accessToken = params.get('access_token')
      const refreshToken = params.get('refresh_token')
      const type = params.get('type') // 'signup' or 'recovery'
      const expiresAt = params.get('expires_at')
      const expiresIn = params.get('expires_in')

      console.log('Auth callback params:', { error, accessToken: accessToken ? 'present' : 'missing', refreshToken: refreshToken ? 'present' : 'missing', type })

      if (error) {
        // 处理错误情况
        setStatus('error')
        
        if (error === 'access_denied') {
          if (errorDescription?.includes('expired')) {
            setMessage('邮箱确认链接已过期，请重新发送确认邮件。')
          } else {
            setMessage('邮箱确认失败，请重试。')
          }
        } else {
          setMessage(errorDescription || '邮箱确认过程中出现错误。')
        }
      } else if (accessToken && refreshToken) {
        // 确认成功，保存 token 并跳转
        try {
          localStorage.setItem('access_token', accessToken)
          localStorage.setItem('refresh_token', refreshToken)
          
          // 记录最后一次使用时间
          localStorage.setItem('last_activity', Date.now().toString())
          
          // 保存其他有用的信息
          if (expiresAt) {
            localStorage.setItem('token_expires_at', expiresAt)
          }
          if (expiresIn) {
            localStorage.setItem('token_expires_in', expiresIn)
          }
          
          setStatus('success')
          setMessage('邮箱确认成功！正在跳转...')
          
          // 刷新用户状态
          window.dispatchEvent(new Event('authStateChanged'))
          
          // 延迟跳转，让用户看到成功消息
          setTimeout(() => {
            router.push('/')
          }, 2000)
        } catch (err) {
          console.error('Error saving tokens:', err)
          setStatus('error')
          setMessage('保存登录信息失败，请重新登录。')
        }
      } else {
        // 没有 token，可能是其他类型的回调
        setStatus('error')
        setMessage('无效的确认链接。请检查链接是否完整。')
      }
    }

    handleCallback()
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)] px-4">
      <div className="w-full max-w-md">
        <div className="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-8 shadow-lg text-center">
          {status === 'loading' && (
            <>
              <div className="mb-4">
                <TarotLoader size="lg" />
              </div>
              <h1 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">
                正在处理邮箱确认...
              </h1>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="mb-4">
                <svg
                  className="mx-auto h-12 w-12 text-green-500"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
              <h1 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">
                邮箱确认成功！
              </h1>
              <p className="text-[var(--text-secondary)] mb-6 break-words">
                {message}
              </p>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="mb-4">
                <svg
                  className="mx-auto h-12 w-12 text-red-500"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path d="M6 18L18 6M6 6l12 12"></path>
                </svg>
              </div>
              <h1 className="text-2xl font-bold mb-4 text-[var(--text-primary)]">
                邮箱确认失败
              </h1>
              <p className="text-[var(--text-secondary)] mb-6 break-words">
                {message}
              </p>
              <div className="space-y-3">
                <Button
                  onClick={() => router.push('/login')}
                  className="w-full"
                >
                  返回登录页面
                </Button>
                <Button
                  variant="outline"
                  onClick={() => router.push('/login?resend=true')}
                  className="w-full"
                >
                  重新发送确认邮件
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

