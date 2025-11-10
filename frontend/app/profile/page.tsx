'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguage } from '@/contexts/LanguageContext'
import { userAPI, UserProfileCreate } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Sidebar } from '@/components/Sidebar'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Container } from '@/components/ui/Container'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { TarotLoader } from '@/components/ui/TarotLoader'

export default function ProfilePage() {
  const { user, profile, refreshProfile } = useAuth()
  const { t, setLanguage } = useLanguage()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [formData, setFormData] = useState<UserProfileCreate>({
    age: undefined,
    gender: '',
    zodiac_sign: '',
    personality_type: '',
    preferred_source: 'pkt',
    preferred_spread: '',
    language: 'zh',
    significator_priority: 'question_first',
    interpretation_model: 'gpt4omini',
  })

  useEffect(() => {
    if (profile) {
      setFormData({
        age: profile.age,
        gender: profile.gender || '',
        zodiac_sign: profile.zodiac_sign || '',
        personality_type: profile.personality_type || '',
        preferred_source: profile.preferred_source || 'pkt',
        preferred_spread: profile.preferred_spread || '',
        language: profile.language || 'zh',
        significator_priority: profile.significator_priority || 'question_first',
        interpretation_model: profile.interpretation_model || 'gpt4omini',
      })
    }
  }, [profile])

  const handleChange = (field: keyof UserProfileCreate, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
    setError('')
    setSuccess('')
    
    if (field === 'language' && (value === 'zh' || value === 'en')) {
      setLanguage(value)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')

    try {
      if (profile) {
        await userAPI.updateProfile(formData)
        setSuccess(t('profileSaved'))
      } else {
        await userAPI.createProfile(formData)
        setSuccess(t('profileCreated'))
      }
      await refreshProfile()
      if (formData.language === 'zh' || formData.language === 'en') {
        setLanguage(formData.language)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || t('saveFailed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ProtectedRoute>
      <Sidebar>
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center py-12">
        <Container size="lg" className="w-full">
          <Card variant="mystical" glowColor="purple" className="w-full max-w-3xl">
            <CardHeader className="text-center">
              <CardTitle className="text-3xl font-bold bg-gradient-to-r from-purple-300 via-amber-300 to-purple-300 bg-clip-text text-transparent">
                {t('profilePage')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-8">
                {/* Basic Info */}
                <div>
                  <h2 className="text-xl font-semibold mb-4 text-[var(--text-primary)] border-b border-purple-500/30 pb-2">
                    {t('basicInfo')}
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('age')}
                      </label>
                      <Input
                        type="number"
                        value={formData.age || ''}
                        onChange={(e) => handleChange('age', e.target.value ? parseInt(e.target.value) : undefined)}
                        placeholder={t('enterAge')}
                        variant="mystical"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('gender')}
                      </label>
                      <select
                        value={formData.gender || ''}
                        onChange={(e) => handleChange('gender', e.target.value || undefined)}
                        className="w-full px-4 py-2 bg-[var(--bg-secondary)] border border-amber-500/30 rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-200"
                      >
                        <option value="">{t('selectGender')}</option>
                        <option value="male">{t('male')}</option>
                        <option value="female">{t('female')}</option>
                        <option value="other">{t('other')}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('zodiacSign')}
                      </label>
                      <Input
                        value={formData.zodiac_sign || ''}
                        onChange={(e) => handleChange('zodiac_sign', e.target.value || undefined)}
                        placeholder={t('enterZodiac')}
                        variant="mystical"
                      />
                    </div>
                  </div>
                </div>

                {/* Tarot Preferences */}
                <div>
                  <h2 className="text-xl font-semibold mb-4 text-[var(--text-primary)] border-b border-purple-500/30 pb-2">
                    {t('tarotPreferences')}
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('personalityType')}
                      </label>
                      <select
                        value={formData.personality_type || ''}
                        onChange={(e) => handleChange('personality_type', e.target.value || undefined)}
                        className="w-full px-4 py-2 bg-[var(--bg-secondary)] border border-amber-500/30 rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-200"
                      >
                        <option value="">{t('selectPersonality')}</option>
                        <option value="wands">{t('wands')}</option>
                        <option value="cups">{t('cups')}</option>
                        <option value="swords">{t('swords')}</option>
                        <option value="pentacles">{t('pentacles')}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('significatorPriority')}
                      </label>
                      <select
                        value={formData.significator_priority || 'question_first'}
                        onChange={(e) => handleChange('significator_priority', e.target.value)}
                        className="w-full px-4 py-2 bg-[var(--bg-secondary)] border border-amber-500/30 rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-200"
                      >
                        <option value="question_first">{t('significatorPriorityQuestionFirst')}</option>
                        <option value="personality_first">{t('significatorPriorityPersonalityFirst')}</option>
                        <option value="zodiac_first">{t('significatorPriorityZodiacFirst')}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('preferredSource')}
                      </label>
                      <select
                        value={formData.preferred_source || 'pkt'}
                        onChange={(e) => handleChange('preferred_source', e.target.value)}
                        className="w-full px-4 py-2 bg-[var(--bg-secondary)] border border-amber-500/30 rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-200"
                      >
                        <option value="pkt">{t('pkt')}</option>
                        <option value="78degrees">{t('degrees78')}</option>
                        <option value="both">{t('both')}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('preferredSpread')}
                      </label>
                      <select
                        value={formData.preferred_spread || ''}
                        onChange={(e) => handleChange('preferred_spread', e.target.value || undefined)}
                        className="w-full px-4 py-2 bg-[var(--bg-secondary)] border border-amber-500/30 rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-200"
                      >
                        <option value="">{t('auto')}</option>
                        <option value="three_card">{t('threeCardOption')}</option>
                        <option value="celtic_cross">{t('celticCrossOption')}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('languagePreference')}
                      </label>
                      <select
                        value={formData.language || 'zh'}
                        onChange={(e) => handleChange('language', e.target.value)}
                        className="w-full px-4 py-2 bg-[var(--bg-secondary)] border border-amber-500/30 rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-200"
                      >
                        <option value="zh">{t('chinese')}</option>
                        <option value="en">{t('english')}</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                        {t('interpretationModel')}
                      </label>
                      <select
                        value={formData.interpretation_model || 'gpt4omini'}
                        onChange={(e) => handleChange('interpretation_model', e.target.value || 'gpt4omini')}
                        className="w-full px-4 py-2 bg-[var(--bg-secondary)] border border-amber-500/30 rounded-lg text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-200"
                      >
                        <option value="gpt4omini">{t('interpretationModelGpt4omini')}</option>
                        <option value="deepseek">{t('interpretationModelDeepseek')}</option>
                        <option value="gemini_2.5_pro">{t('interpretationModelGemini')}</option>
                      </select>
                      <p className="mt-1 text-xs text-[var(--text-muted)]">
                        {t('interpretationModelDescription')}
                      </p>
                    </div>
                  </div>
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

                <Button type="submit" variant="mystical" size="lg" className="w-full" disabled={saving}>
                  {saving ? (
                    <div className="flex items-center justify-center gap-2">
                      <TarotLoader size="sm" />
                      <span>{t('saving')}</span>
                    </div>
                  ) : (
                    t('saveProfile')
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>
        </Container>
      </div>
    </Sidebar>
    </ProtectedRoute>
  )
}

