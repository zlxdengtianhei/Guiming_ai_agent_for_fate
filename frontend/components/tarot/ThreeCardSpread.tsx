'use client'

import { useEffect, useMemo, useState } from 'react'
import { Badge } from '@/components/ui/Badge'
import { useLanguage } from '@/contexts/LanguageContext'
import { CardImage } from './CardImage'

interface CardData {
  card_id: string
  card_name_en: string
  card_name_cn?: string
  position: string
  position_order: number
  is_reversed: boolean
  image_url?: string
}

interface ThreeCardSpreadProps {
  cards: CardData[]
  positions: string[]
  onCardClick?: (index: number) => void
}

export function ThreeCardSpread({ cards, positions, onCardClick }: ThreeCardSpreadProps) {
  const { t } = useLanguage()
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [userInteracted, setUserInteracted] = useState(false)

  const sortedCards = useMemo(
    () => [...cards].sort((a, b) => a.position_order - b.position_order),
    [cards]
  )
  const cardsKey = useMemo(
    () => sortedCards.map((card) => card.card_id).join('|'),
    [sortedCards]
  )

  useEffect(() => {
    setUserInteracted(false)
  }, [cardsKey])

  useEffect(() => {
    if (userInteracted) {
      return
    }

    if (sortedCards.length === 0) {
      setSelectedIndex(0)
      return
    }

    if (sortedCards.length === 1) {
      setSelectedIndex(0)
      return
    }

    const preferredIndex = Math.min(1, sortedCards.length - 1)
    setSelectedIndex(preferredIndex)
  }, [cardsKey, sortedCards.length, userInteracted])

  const handleCardClick = (index: number) => {
    setUserInteracted(true)
    setSelectedIndex(index)
    if (onCardClick) {
      const sortedCard = sortedCards[index]
      const originalIndex = cards.findIndex(c => c.card_id === sortedCard.card_id)
      onCardClick(originalIndex >= 0 ? originalIndex : index)
    }
  }

  return (
    <div className="w-full flex flex-col items-center">
      <div 
        className="relative rounded-lg p-4 border border-purple-500/20 w-full max-w-3xl mx-auto overflow-hidden"
      >
        <div className="absolute inset-0 bg-[var(--bg-secondary)]/60 backdrop-blur-[1px]"></div>
        
        <div className="relative z-10 flex gap-6 overflow-x-auto pb-2 scrollbar-custom justify-center">
          {sortedCards.map((card, index) => {
            return (
              <div
                key={card.card_id}
                className={`group relative flex-shrink-0 cursor-pointer transition-all duration-300 flex flex-col items-center ${
                  index === selectedIndex ? 'scale-105 opacity-100' : 'opacity-70 hover:opacity-90'
                }`}
                onClick={() => handleCardClick(index)}
              >
                <div className="relative w-48 h-36">
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/30 via-transparent to-amber-400/25 opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-sm" />
                  <div className="relative z-10 w-full h-full rounded-2xl border-t border-b border-l border-r border-purple-400/40 bg-[var(--bg-tertiary)]/85 backdrop-blur-sm shadow-[0_15px_35px_rgba(15,23,42,0.55)] overflow-hidden">
                    {card.image_url ? (
                      <CardImage
                        imageUrl={card.image_url}
                        alt={card.card_name_en}
                        isReversed={card.is_reversed}
                        containerClassName="scale-105"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center p-3">
                        <p className="text-xs text-[var(--text-secondary)] text-center break-words line-clamp-2">
                          {card.card_name_cn || card.card_name_en}
                        </p>
                        {card.is_reversed && (
                          <Badge variant="error" size="sm" className="mt-1">
                            {t('reversed')}
                          </Badge>
                        )}
                      </div>
                    )}
                    <div className="absolute inset-x-2 bottom-2 rounded-xl bg-[var(--bg-primary)]/70 border border-purple-400/30 px-2 py-1 text-center text-[10px] text-[var(--text-secondary)] uppercase tracking-widest">
                      {positions[index] || card.position}
                    </div>
                  </div>
                </div>
                <div className="mt-2 text-center w-full px-2">
                  <p className="text-sm font-semibold text-[var(--text-primary)] line-clamp-1">
                    {card.card_name_cn || card.card_name_en}
                  </p>
                  {card.is_reversed && (
                    <span className="mt-1 inline-block text-[11px] text-red-300/80">
                      {t('reversed')}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <p className="text-xs text-[var(--text-muted)] text-center mt-1">
        {t('swipeHint') || '点击卡牌查看详情，左右滑动切换'}
      </p>
    </div>
  )
}
