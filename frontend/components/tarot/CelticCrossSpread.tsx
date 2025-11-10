'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { useLanguage } from '@/contexts/LanguageContext'
import { TranslationKey } from '@/lib/i18n'
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

interface CelticCrossSpreadProps {
  cards: CardData[]
  onCardClick?: (index: number) => void
}

// 凯尔特十字布局位置映射
// 中心十字 (The Cross): 前6张牌
// 权杖/高塔 (The Staff/Tower): 后4张牌，垂直排列在右侧
const positionLabelMap: Record<string, TranslationKey> = {
  'cover': 'situation',
  'crossing': 'challenge',
  'basis': 'past',
  'behind': 'past',
  'crowned': 'goal',
  'before': 'future',
  'self': 'attitude',
  'environment': 'environment',
  'hopes_and_fears': 'hope',
  'outcome': 'outcome',
}

export function CelticCrossSpread({ cards, onCardClick }: CelticCrossSpreadProps) {
  const { t } = useLanguage()
  const [isExpanded, setIsExpanded] = useState(false)
  const [selectedCard, setSelectedCard] = useState<CardData | null>(null)

  const sortedCards = [...cards].sort((a, b) => a.position_order - b.position_order)
  const cardMap = new Map(sortedCards.map(card => [card.position_order, card]))

  const handleCardClick = (card: CardData) => {
    setSelectedCard(card)
    setIsExpanded(true)
    if (onCardClick) {
      // 找到原始cards数组中的索引
      const originalIndex = cards.findIndex(c => c.card_id === card.card_id)
      if (originalIndex >= 0) {
        onCardClick(originalIndex)
      }
    }
  }

  const handleCloseExpanded = () => {
    setIsExpanded(false)
    setSelectedCard(null)
  }

  const getPositionLabelKey = (position: string): TranslationKey | undefined => {
    return positionLabelMap[position]
  }

  // 中心十字的6张牌
  const crossCards = sortedCards.slice(0, 6)
  // 权杖的4张牌
  const staffCards = sortedCards.slice(6, 10)

  return (
    <div className="w-full flex flex-col items-center">
      {/* 卡牌展示区域 */}
      <div
        className="relative bg-[var(--bg-secondary)] rounded-lg p-6 border border-purple-500/20 cursor-pointer min-h-[500px] w-full max-w-5xl mx-auto"
        onClick={() => !isExpanded && setIsExpanded(true)}
      >
        {/* 紧凑视图 - 显示所有卡牌（图像只显示中间1/3） */}
        {!isExpanded ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center justify-center gap-4 flex-wrap">
              {sortedCards.map((card) => {
                const labelKey = getPositionLabelKey(card.position)
                const label = labelKey ? t(labelKey) : card.position
                return (
                  <CardItem
                    key={card.card_id}
                    card={card}
                    label={label}
                    reversedLabel={t('reversed')}
                    onClick={(e) => {
                      e.stopPropagation()
                      handleCardClick(card)
                    }}
                  />
                )
              })}
            </div>
          </div>
        ) : (
          /* 展开视图 */
          <div className="space-y-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-[var(--text-primary)] text-center flex-1">
                {t('celticCrossSpread') || '凯尔特十字占卜'}
              </h3>
              <button
                onClick={handleCloseExpanded}
                className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              >
                ✕
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 justify-items-center">
              {sortedCards.map((card) => {
                const positionLabelKey = getPositionLabelKey(card.position)
                const positionLabel = positionLabelKey ? t(positionLabelKey) : card.position
                return (
                  <div
                    key={card.card_id}
                    className={`cursor-pointer transition-all hover:scale-105 flex flex-col items-center gap-2 ${
                      selectedCard?.card_id === card.card_id ? 'ring-2 ring-purple-500/80 rounded-xl p-2' : ''
                    }`}
                    onClick={() => {
                      setSelectedCard(card)
                      if (onCardClick) {
                        const originalIndex = cards.findIndex(c => c.card_id === card.card_id)
                        if (originalIndex >= 0) {
                          onCardClick(originalIndex)
                        }
                      }
                    }}
                  >
                    <div className="relative w-full h-32">
                      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/30 via-transparent to-amber-400/20 opacity-0 hover:opacity-100 transition-opacity duration-300 blur-sm" />
                      <div className="relative z-10 w-full h-full rounded-2xl border border-purple-400/35 bg-[var(--bg-tertiary)]/85 backdrop-blur-sm overflow-hidden shadow-[0_15px_35px_rgba(15,23,42,0.5)]">
                        {card.image_url ? (
                          <CardImage
                            imageUrl={card.image_url}
                            alt={card.card_name_en}
                            isReversed={card.is_reversed}
                            containerClassName="scale-105"
                          />
                        ) : (
                          <div className="h-full flex items-center justify-center p-3">
                            <p className="text-sm text-[var(--text-secondary)] text-center break-words line-clamp-2">
                              {card.card_name_cn || card.card_name_en}
                            </p>
                          </div>
                        )}
                        <div className="absolute inset-x-2 bottom-2 rounded-xl bg-[var(--bg-primary)]/75 border border-purple-400/30 px-2 py-1 text-center text-[11px] text-[var(--text-secondary)] uppercase tracking-wider">
                          {positionLabel}
                        </div>
                      </div>
                    </div>
                    <p className="text-sm font-semibold text-[var(--text-primary)] text-center line-clamp-1 w-full">
                      {card.card_name_cn || card.card_name_en}
                    </p>
                    <div className="flex items-center justify-center gap-2">
                      <Badge variant="mystical" size="sm">
                        {positionLabel}
                      </Badge>
                      {card.is_reversed && (
                        <Badge variant="error" size="sm">
                          {t('reversed')}
                        </Badge>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
            {selectedCard && (
              <div className="mt-4 pt-4 border-t border-purple-500/20 text-center">
                <h4 className="text-lg font-semibold text-[var(--text-primary)] mb-2">
                  {selectedCard.card_name_cn || selectedCard.card_name_en}
                </h4>
                <p className="text-sm text-[var(--text-secondary)]">
                  {t('position')}: {selectedCard.position}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
      {!isExpanded && (
        <p className="text-xs text-[var(--text-muted)] text-center mt-2">
          {t('clickToExpand') || '点击查看完整牌阵'}
        </p>
      )}
    </div>
  )
}

// 卡牌项组件
function CardItem({
  card,
  label,
  reversedLabel,
  onClick,
  className = '',
}: {
  card: CardData
  label: string
  reversedLabel: string
  onClick: (e: React.MouseEvent) => void
  className?: string
}) {
  return (
    <div
      className={`group flex flex-col items-center cursor-pointer hover:scale-105 transition-transform duration-300 ${className}`}
      onClick={onClick}
    >
      <div className="relative w-28 h-24">
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/30 via-transparent to-amber-400/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-sm" />
        <div className="relative z-10 w-full h-full rounded-2xl border border-purple-400/35 bg-[var(--bg-tertiary)]/85 backdrop-blur-sm overflow-hidden shadow-[0_12px_30px_rgba(15,23,42,0.5)]">
          {card.image_url ? (
            <CardImage
              imageUrl={card.image_url}
              alt={card.card_name_en}
              isReversed={card.is_reversed}
              containerClassName="scale-105"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center p-2">
              <p className="text-[10px] text-[var(--text-secondary)] text-center break-words line-clamp-2">
                {card.card_name_cn || card.card_name_en}
              </p>
            </div>
          )}
          <div className="absolute inset-x-1 bottom-1 rounded-lg bg-[var(--bg-primary)]/70 border border-purple-400/30 px-1.5 py-0.5 text-center text-[9px] text-[var(--text-secondary)] uppercase tracking-widest">
            {label}
          </div>
        </div>
      </div>
      <p className="mt-2 text-[11px] text-[var(--text-primary)] font-medium text-center max-w-[90px] line-clamp-1">
        {card.card_name_cn || card.card_name_en}
      </p>
      {card.is_reversed && (
        <span className="text-[10px] text-red-300/80 mt-1">
          {reversedLabel}
        </span>
      )}
    </div>
  )
}
