'use client'

import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/Button'
import { Sidebar } from '@/components/Sidebar'
import { useLanguage } from '@/contexts/LanguageContext'
import { Container } from '@/components/ui/Container'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card'

export default function SpreadSelectionPage() {
  const router = useRouter()
  const { t } = useLanguage()

  const handleSpreadSelect = (spreadType: 'three_card' | 'celtic_cross') => {
    router.push(`/?spread=${spreadType}`)
  }

  const handleInfoClick = () => {
    alert(`${t('threeCardInfo')}\n\n${t('celticCrossInfo')}`)
  }

  return (
    <Sidebar>
      <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center py-12">
        <Container size="lg" className="w-full">
          <div className="flex flex-col items-center space-y-8">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-amber-300 via-purple-300 to-amber-300 bg-clip-text text-transparent text-center mb-4">
              {t('spreadSelection')}
            </h1>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-4xl">
              {/* Three Card Spread */}
              <Card
                variant="glow"
                glowColor="gold"
                className="cursor-pointer hover:scale-105 transition-transform duration-300"
                onClick={() => handleSpreadSelect('three_card')}
              >
                <CardHeader>
                  <CardTitle className="text-2xl font-bold">
                    {t('threeCardSpread')}
                  </CardTitle>
                  <CardDescription>
                    {t('threeCardDescription')}
                  </CardDescription>
                </CardHeader>
                <CardFooter>
                  <Button variant="gold" className="w-full">
                    {t('selectThisMethod')}
                  </Button>
                </CardFooter>
              </Card>

              {/* Celtic Cross Spread */}
              <Card
                variant="glow"
                glowColor="purple"
                className="cursor-pointer hover:scale-105 transition-transform duration-300"
                onClick={() => handleSpreadSelect('celtic_cross')}
              >
                <CardHeader>
                  <CardTitle className="text-2xl font-bold">
                    {t('celticCrossSpread')}
                  </CardTitle>
                  <CardDescription>
                    {t('celticCrossDescription')}
                  </CardDescription>
                </CardHeader>
                <CardFooter>
                  <Button variant="mystical" className="w-full">
                    {t('selectThisMethod')}
                  </Button>
                </CardFooter>
              </Card>
            </div>

            {/* Info button */}
            <div className="pt-6">
              <Button variant="outline" onClick={handleInfoClick}>
                {t('learnMore')}
              </Button>
            </div>
          </div>
        </Container>
      </div>
    </Sidebar>
  )
}

