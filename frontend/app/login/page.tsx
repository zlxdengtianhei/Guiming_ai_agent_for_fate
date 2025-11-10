'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguage } from '@/contexts/LanguageContext'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { authAPI } from '@/lib/api'
import { Container } from '@/components/ui/Container'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { TarotLoader } from '@/components/ui/TarotLoader'

export default function LoginPage() {
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [resendingConfirmation, setResendingConfirmation] = useState(false)
  const [showEmailConfirmation, setShowEmailConfirmation] = useState(false)
  const { signin, signup } = useAuth()
  const { t } = useLanguage()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setShowEmailConfirmation(false)
    setLoading(true)

    try {
      if (isSignUp) {
        await signup(email, password)
        router.push('/')
      } else {
        await signin(email, password)
        router.push('/')
      }
    } catch (err: any) {
      if (err.message === 'EMAIL_CONFIRMATION_REQUIRED' || err.isConfirmationRequired) {
        setShowEmailConfirmation(true)
        setSuccess(t('emailConfirmationRequired'))
        console.log('Registration successful, email confirmation required')
      } else {
        console.error('Auth error:', err)
        const errorMessage = err.response?.data?.detail || 
                            err.message || 
                            err.toString() || 
                            t('operationFailed')
        setError(errorMessage)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleResendConfirmation = async () => {
    if (!email) {
      setError(t('enterEmail'))
      return
    }

    setResendingConfirmation(true)
    setError('')
    setSuccess('')

    try {
      const response = await authAPI.resendConfirmation({ email, password: password || 'dummy' })
      setSuccess(response.message || t('emailConfirmationSent'))
      console.log('Resend confirmation success:', response)
      setTimeout(() => {
        setSuccess('')
      }, 5000)
    } catch (err: any) {
      console.error('Resend confirmation error:', err)
      const errorMessage = err.response?.data?.detail || 
                          err.message || 
                          t('operationFailed')
      setError(errorMessage)
      
      if (errorMessage.includes('already confirmed') || errorMessage.includes('已确认')) {
        setTimeout(() => {
          setIsSignUp(false)
          setError('')
        }, 3000)
      }
    } finally {
      setResendingConfirmation(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)] px-4 py-12">
      <Container size="sm" className="w-full">
        <Card variant="mystical" glowColor="purple" className="w-full">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold bg-gradient-to-r from-purple-300 via-amber-300 to-purple-300 bg-clip-text text-transparent">
              {isSignUp ? t('signup') : t('login')}
            </CardTitle>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="email" className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                  {t('email')}
                </label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value)
                    setShowEmailConfirmation(false)
                  }}
                  placeholder={t('enterEmail')}
                  required
                  disabled={loading || resendingConfirmation}
                  variant="mystical"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                  {t('password')}
                </label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    setShowEmailConfirmation(false)
                  }}
                  placeholder={t('enterPassword')}
                  required
                  disabled={loading || resendingConfirmation}
                  minLength={6}
                  variant="mystical"
                />
              </div>

              {error && (
                <Alert variant="error">
                  {error}
                </Alert>
              )}

              {success && (
                <Alert variant="success">
                  {success}
                </Alert>
              )}

              {showEmailConfirmation && (
                <Alert variant="mystical" className="space-y-3">
                  <p className="break-words">{t('confirmationEmailSent')}</p>
                  <div className="pt-2 border-t border-purple-500/30">
                    <p className="text-xs mb-2 text-purple-300">{t('didntReceiveEmail')}</p>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleResendConfirmation}
                      disabled={resendingConfirmation || !email}
                      className="w-full"
                    >
                      {resendingConfirmation ? (
                        <div className="flex items-center justify-center gap-2">
                          <TarotLoader size="sm" />
                          <span>{t('resendingConfirmation')}</span>
                        </div>
                      ) : (
                        t('resendConfirmation')
                      )}
                    </Button>
                  </div>
                </Alert>
              )}

              <Button
                type="submit"
                variant="mystical"
                size="lg"
                className="w-full"
                disabled={loading || !email || !password || resendingConfirmation}
              >
                {loading ? (
                  <div className="flex items-center justify-center gap-2">
                    <TarotLoader size="sm" />
                    <span>{t('processing')}</span>
                  </div>
                ) : (
                  isSignUp ? t('signup') : t('login')
                )}
              </Button>
            </form>

            <div className="mt-6 text-center">
              <button
                type="button"
                onClick={() => {
                  setIsSignUp(!isSignUp)
                  setError('')
                  setSuccess('')
                  setShowEmailConfirmation(false)
                }}
                className="text-[var(--accent-purple-light)] hover:text-[var(--accent-purple)] text-sm transition-colors break-words"
              >
                {isSignUp ? t('alreadyHaveAccount') : t('noAccount')}
              </button>
            </div>
          </CardContent>
        </Card>
      </Container>
    </div>
  )
}

