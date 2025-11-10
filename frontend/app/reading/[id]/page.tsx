'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguage } from '@/contexts/LanguageContext'
import { tarotAPI, TarotReadingResponse } from '@/lib/api'
import { Sidebar } from '@/components/Sidebar'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Container } from '@/components/ui/Container'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import { ThreeCardSpread } from '@/components/tarot/ThreeCardSpread'
import { CelticCrossSpread } from '@/components/tarot/CelticCrossSpread'
import { CardModal } from '@/components/tarot/CardModal'
import { TextModal } from '@/components/tarot/TextModal'
import { TarotLoader } from '@/components/ui/TarotLoader'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface CardData {
  card_id: string
  card_name_en: string
  card_name_cn?: string
  position: string
  position_order: number
  is_reversed: boolean
  image_url?: string
}

export default function ReadingDetailPage() {
  const params = useParams()
  const router = useRouter()
  const readingId = params.id as string
  
  const [reading, setReading] = useState<TarotReadingResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCardIndex, setSelectedCardIndex] = useState<number | null>(null)
  const [scrollPosition, setScrollPosition] = useState(0)
  const [isImageryExpanded, setIsImageryExpanded] = useState(false)
  const [isImageryModalOpen, setIsImageryModalOpen] = useState(false)
  const [isInterpretationExpanded, setIsInterpretationExpanded] = useState(false)
  const [isInterpretationModalOpen, setIsInterpretationModalOpen] = useState(false)
  
  const { user } = useAuth()
  const { t } = useLanguage()

  useEffect(() => {
    if (readingId) {
      loadReading()
    }
  }, [readingId])

  const loadReading = async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await tarotAPI.getReading(readingId)
      setReading(result)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || t('readingNotFound') || '占卜记录未找到')
    } finally {
      setLoading(false)
    }
  }

  const handleCardClick = (index: number) => {
    setScrollPosition(window.scrollY || document.documentElement.scrollTop)
    setSelectedCardIndex(index)
  }

  const handleCardModalClose = () => {
    setSelectedCardIndex(null)
    setTimeout(() => {
      window.scrollTo({
        top: scrollPosition,
        behavior: 'instant'
      })
    }, 0)
  }

  const handleCardModalNavigate = (index: number) => {
    setSelectedCardIndex(index)
  }

  if (loading) {
    return (
      <ProtectedRoute>
        <Sidebar>
          <div className="min-h-screen bg-[var(--bg-primary)] flex flex-col items-center justify-center">
            <Container size="lg" className="flex flex-col items-center justify-center text-center gap-6">
              <TarotLoader size="lg" className="mx-auto" />
              <p className="text-lg text-[var(--text-primary)]">{t('loading') || '加载中...'}</p>
            </Container>
          </div>
        </Sidebar>
      </ProtectedRoute>
    )
  }

  if (error || !reading) {
    return (
      <ProtectedRoute>
        <Sidebar>
          <div className="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center py-12">
            <Container size="lg" className="w-full">
              <Alert variant="error" className="w-full">
                {error || t('readingNotFound') || '占卜记录未找到'}
              </Alert>
              <div className="mt-4 text-center">
                <Button variant="outline" onClick={() => router.push('/')}>
                  {t('backToHome') || '返回首页'}
                </Button>
              </div>
            </Container>
          </div>
        </Sidebar>
      </ProtectedRoute>
    )
  }

  // 转换卡牌数据格式
  // 后端返回的cards数组，每个card包含：card_id, card_name_en, card_name_cn, position, position_order, is_reversed, image_url
  const cards: CardData[] = (reading.cards || reading.selected_cards || []).map((card: any) => ({
    card_id: card.card_id || card.id || '',
    card_name_en: card.card_name_en || card.name || '',
    card_name_cn: card.card_name_cn || '',
    position: card.position || '',
    position_order: card.position_order || 0,
    is_reversed: card.is_reversed || false,
    image_url: card.image_url || '',
  })).sort((a, b) => a.position_order - b.position_order)  // 按位置顺序排序

  const spreadType = reading.spread_type === 'celtic_cross' ? 'celtic_cross' : 'three_card'
  const threeCardPositions = [t('past'), t('present'), t('future')]

  // 获取解读文本
  const interpretationText = typeof reading.interpretation === 'string' 
    ? reading.interpretation 
    : reading.interpretation?.final_interpretation || ''

  // 获取意象描述
  const imageryText = reading.imagery_description || ''

  return (
    <ProtectedRoute>
      <Sidebar>
        <div className="min-h-screen bg-[var(--bg-primary)] py-8">
          <Container size="lg" className="w-full space-y-6">
            {/* 返回按钮 */}
            <div className="mb-4">
              <Button variant="outline" onClick={() => router.push('/')}>
                ← {t('backToHome') || '返回首页'}
              </Button>
            </div>

            {/* 问题显示 */}
            <Card variant="mystical" glowColor="gold" className="w-full">
              <CardHeader>
                <CardTitle className="text-2xl">{t('question') || '问题'}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-lg text-[var(--text-primary)]">{reading.question}</p>
              </CardContent>
            </Card>

            {/* 卡牌展示 */}
            {cards.length > 0 && (
              <Card variant="glow" glowColor="purple" className="w-full relative overflow-hidden" style={{
                backgroundImage: 'url(/database/images/background/backgroud.png)',
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat',
              }}>
                <div className="absolute inset-0 bg-[var(--bg-secondary)]/70 backdrop-blur-[1px]"></div>
                <div className="relative z-10">
                  <CardHeader className="text-center">
                    <CardTitle className="text-2xl">{t('selectedCards') || '抽取的卡牌'}</CardTitle>
                  </CardHeader>
                  <CardContent className="flex justify-center">
                  {spreadType === 'three_card' ? (
                    <ThreeCardSpread 
                      cards={cards} 
                      positions={threeCardPositions}
                      onCardClick={handleCardClick}
                    />
                  ) : (
                    <CelticCrossSpread 
                      cards={cards}
                      onCardClick={handleCardClick}
                    />
                  )}
                </CardContent>
                </div>
              </Card>
            )}

            {/* 意象描述 */}
            {imageryText && (
              <Card 
                variant="glow" 
                glowColor="gold" 
                className="w-full cursor-pointer transition-all hover:border-gold-500/50 relative overflow-hidden !bg-transparent"
                style={{
                  backgroundImage: `url('/database/images/background/backgroud1.png')`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  backgroundRepeat: 'no-repeat',
                }}
                onClick={() => setIsImageryModalOpen(true)}
              >
                <div className="absolute inset-0 bg-[var(--bg-secondary)]/70 backdrop-blur-[1px]"></div>
                <div className="relative z-10">
                  <CardHeader>
                    <CardTitle className="text-xl">{t('imageryDescription') || '意象描述'}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="prose prose-invert max-w-none">
                      <p className="text-[var(--text-primary)] whitespace-pre-wrap break-words line-clamp-3">
                        {imageryText}
                      </p>
                    </div>
                    <Button variant="outline" size="sm" className="mt-4">
                      {t('viewFull') || '查看完整内容'}
                    </Button>
                  </CardContent>
                </div>
              </Card>
            )}

            {/* 最终解读 */}
            {interpretationText && (
              <Card 
                variant="glow" 
                glowColor="purple" 
                className="w-full relative overflow-hidden !bg-transparent"
                style={{
                  backgroundImage: `url('/database/images/background/backgroud3.png')`,
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  backgroundRepeat: 'no-repeat',
                }}
              >
                <div className="absolute inset-0 bg-[var(--bg-secondary)]/70 backdrop-blur-[1px]"></div>
                <div className="relative z-10">
                  <CardHeader>
                    <CardTitle className="text-2xl">{t('interpretation') || '占卜解读'}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div 
                      className="prose prose-invert max-w-none text-[var(--text-primary)]"
                      style={{ maxHeight: '600px', overflowY: 'auto' }}
                    >
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {interpretationText}
                      </ReactMarkdown>
                    </div>
                  </CardContent>
                </div>
              </Card>
            )}

            {/* 卡牌放大模态框 */}
            {selectedCardIndex !== null && cards.length > 0 && (
              <CardModal
                cards={cards}
                currentIndex={selectedCardIndex}
                onClose={handleCardModalClose}
                onNavigate={handleCardModalNavigate}
              />
            )}

            {/* 意象描述模态框 */}
            {isImageryModalOpen && imageryText && (
              <TextModal
                title={t('imageryDescription') || '意象描述'}
                text={imageryText}
                onClose={() => setIsImageryModalOpen(false)}
              />
            )}

            {/* 解读模态框 */}
            {isInterpretationModalOpen && interpretationText && (
              <TextModal
                title={t('interpretation') || '占卜解读'}
                text={interpretationText}
                onClose={() => setIsInterpretationModalOpen(false)}
              />
            )}
          </Container>
        </div>
      </Sidebar>
    </ProtectedRoute>
  )
}

