'use client'

import { Suspense, useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { tarotAPI, TarotReadingResponse } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguage } from '@/contexts/LanguageContext'
import { Sidebar } from '@/components/Sidebar'
import { Container } from '@/components/ui/Container'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { TarotLoader } from '@/components/ui/TarotLoader'

function ManualInputPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const spreadType = searchParams.get('spread') || 'three_card'
  const { profile } = useAuth()
  const { t } = useLanguage()

  const [cards, setCards] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [reading, setReading] = useState<TarotReadingResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const cardCount = spreadType === 'three_card' ? 3 : 10
    setCards(new Array(cardCount).fill(''))
  }, [spreadType])

  const handleCardChange = (index: number, value: string) => {
    const newCards = [...cards]
    newCards[index] = value
    setCards(newCards)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (cards.some(card => !card.trim())) {
      setError(t('pleaseFillAllCards'))
      return
    }

    setLoading(true)
    setError(null)

    try {
      const question = spreadType === 'three_card' 
        ? t('threeCardManual')
        : t('celticCrossManual')
      
      const result = await tarotAPI.createReading({
        question,
        user_selected_spread: spreadType,
        source_page: 'manual-input',
        user_profile: profile ? {
          age: profile.age,
          gender: profile.gender,
          zodiac_sign: profile.zodiac_sign,
          personality_type: profile.personality_type,
          preferred_source: profile.preferred_source,
          preferred_spread: profile.preferred_spread,
          language: profile.language,
          significator_priority: profile.significator_priority,
          interpretation_model: profile.interpretation_model,
        } : undefined,
      })
      
      setReading(result)
      window.dispatchEvent(new Event('readingCreated'))
    } catch (err: any) {
      setError(err.response?.data?.detail || t('readingFailed'))
    } finally {
      setLoading(false)
    }
  }

  const cardPositions = spreadType === 'three_card' 
    ? [t('past'), t('present'), t('future')]
    : [t('situation'), t('challenge'), t('past'), t('future'), t('goal'), t('recent'), t('attitude'), t('environment'), t('hope'), t('outcome')]

  return (
    <Sidebar>
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center py-12">
        <Container size="lg" className="w-full">
          <div className="flex flex-col items-center space-y-8">
            <Card variant="mystical" glowColor="purple" className="w-full max-w-3xl">
              <CardHeader className="text-center">
                <CardTitle className="text-3xl font-bold bg-gradient-to-r from-purple-300 via-amber-300 to-purple-300 bg-clip-text text-transparent">
                  {t('manualInputTitle')}
                </CardTitle>
                <CardDescription className="text-lg">
                  {spreadType === 'three_card' ? t('threeCardManual') : t('celticCrossManual')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="space-y-4">
                    <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-4">
                      {t('enterCardNames')}
                    </h3>
                    {cards.map((card, index) => (
                      <div key={index}>
                        <label className="block text-sm font-medium mb-2 text-[var(--text-secondary)]">
                          <Badge variant="mystical" size="sm" className="mr-2">
                            {index + 1}/{cards.length}
                          </Badge>
                          {cardPositions[index]}
                        </label>
                        <Input
                          value={card}
                          onChange={(e) => handleCardChange(index, e.target.value)}
                          placeholder="e.g., The Fool, The Magician..."
                          disabled={loading}
                          variant="mystical"
                        />
                      </div>
                    ))}
                  </div>

                  {error && (
                    <Alert variant="error">
                      {error}
                    </Alert>
                  )}

                  <Button
                    type="submit"
                    variant="mystical"
                    size="lg"
                    className="w-full"
                    disabled={loading || cards.some(card => !card.trim())}
                  >
                    {loading ? (
                      <div className="flex items-center justify-center gap-2">
                        <TarotLoader size="sm" />
                        <span>{t('processing')}</span>
                      </div>
                    ) : (
                      t('getInterpretation')
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Reading result */}
            {reading && (
              <Card variant="glow" glowColor="purple" className="w-full max-w-4xl">
                <CardHeader>
                  <CardTitle className="text-2xl">{t('readingResult')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="bg-[var(--bg-primary)] rounded-lg p-4 border border-purple-500/20">
                    <p className="text-[var(--text-primary)] whitespace-pre-wrap break-words leading-relaxed">
                      {typeof reading.interpretation === 'string' 
                        ? reading.interpretation 
                        : reading.interpretation?.final_interpretation || JSON.stringify(reading.interpretation, null, 2)}
                    </p>
                  </div>
                  {reading.cards.length > 0 && (
                    <div>
                      <h3 className="text-xl font-semibold mb-4 text-[var(--text-primary)]">{t('cards')}</h3>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {reading.cards.map((card, index) => (
                          <Card
                            key={index}
                            variant="glow"
                            glowColor={index % 2 === 0 ? 'gold' : 'purple'}
                            className="p-4"
                          >
                            <p className="font-semibold text-[var(--text-primary)] break-words mb-2">{card.name}</p>
                            {card.position && (
                              <Badge variant="mystical" size="sm" className="mb-2">
                                {card.position}
                              </Badge>
                            )}
                            {card.is_reversed && (
                              <Badge variant="error" size="sm">
                                {t('reversed')}
                              </Badge>
                            )}
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </Container>
      </div>
    </Sidebar>
  )
}

export default function ManualInputPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
          <TarotLoader size="lg" />
        </div>
      }
    >
      <ManualInputPageContent />
    </Suspense>
  )
}
