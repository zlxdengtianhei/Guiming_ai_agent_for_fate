'use client'

import { useState, useEffect } from 'react'
import { Badge } from '@/components/ui/Badge'
import { useLanguage } from '@/contexts/LanguageContext'

interface CardData {
  card_id: string
  card_name_en: string
  card_name_cn?: string
  position: string
  position_order: number
  is_reversed: boolean
  image_url?: string
}

interface CardModalProps {
  cards: CardData[]
  currentIndex: number
  onClose: () => void
  onNavigate: (index: number) => void
}

export function CardModal({ cards, currentIndex, onClose, onNavigate }: CardModalProps) {
  const { t } = useLanguage()
  const [touchStart, setTouchStart] = useState<number | null>(null)
  const [touchEnd, setTouchEnd] = useState<number | null>(null)

  const sortedCards = [...cards].sort((a, b) => a.position_order - b.position_order)
  const currentCard = sortedCards[currentIndex]

  // 处理键盘导航
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
        onNavigate(currentIndex - 1)
      } else if (e.key === 'ArrowRight' && currentIndex < sortedCards.length - 1) {
        onNavigate(currentIndex + 1)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentIndex, sortedCards.length, onClose, onNavigate])

  // 处理触摸滑动
  const minSwipeDistance = 50

  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null)
    setTouchStart(e.targetTouches[0].clientX)
  }

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX)
  }

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return

    const distance = touchStart - touchEnd
    const isLeftSwipe = distance > minSwipeDistance
    const isRightSwipe = distance < -minSwipeDistance

    if (isLeftSwipe && currentIndex < sortedCards.length - 1) {
      onNavigate(currentIndex + 1)
    }
    if (isRightSwipe && currentIndex > 0) {
      onNavigate(currentIndex - 1)
    }
  }

  if (!currentCard) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
    >
      <div
        className="relative max-w-2xl w-full mx-4 bg-[var(--bg-secondary)] rounded-lg border-2 border-purple-500/50 p-6 max-h-[90vh] overflow-y-auto scrollbar-custom"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-2xl"
          aria-label="Close"
        >
          ✕
        </button>

        {/* 卡牌图片 */}
        <div className="flex justify-center mb-6">
          <div className="w-64 h-96 bg-[var(--bg-tertiary)] rounded-lg border-2 border-purple-500/30 overflow-hidden">
            {currentCard.image_url ? (
              <img
                src={currentCard.image_url}
                alt={currentCard.card_name_en}
                className={`w-full h-full object-cover ${currentCard.is_reversed ? 'rotate-180' : ''}`}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center p-4">
                <p className="text-lg text-[var(--text-secondary)] text-center break-words">
                  {currentCard.card_name_cn || currentCard.card_name_en}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* 卡牌信息 */}
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center gap-2">
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">
              {currentCard.card_name_cn || currentCard.card_name_en}
            </h2>
            {currentCard.is_reversed && (
              <Badge variant="error" size="sm">
                {t('reversed')}
              </Badge>
            )}
          </div>

          <div>
            <Badge variant="mystical" size="md">
              {t('position')}: {currentCard.position}
            </Badge>
          </div>

          {/* 导航指示器 */}
          <div className="flex items-center justify-center gap-4 mt-6">
            <button
              onClick={() => currentIndex > 0 && onNavigate(currentIndex - 1)}
              disabled={currentIndex === 0}
              className="px-4 py-2 bg-[var(--bg-tertiary)] rounded-lg border border-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-tertiary)]/80 transition-colors"
            >
              ← {t('previous') || '上一张'}
            </button>
            <span className="text-[var(--text-secondary)]">
              {currentIndex + 1} / {sortedCards.length}
            </span>
            <button
              onClick={() => currentIndex < sortedCards.length - 1 && onNavigate(currentIndex + 1)}
              disabled={currentIndex === sortedCards.length - 1}
              className="px-4 py-2 bg-[var(--bg-tertiary)] rounded-lg border border-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[var(--bg-tertiary)]/80 transition-colors"
            >
              {t('next') || '下一张'} →
            </button>
          </div>

          {/* 滑动提示 */}
          <p className="text-xs text-[var(--text-muted)] mt-4">
            {t('swipeHint') || '左右滑动或使用键盘方向键切换卡牌'}
          </p>
        </div>
      </div>
    </div>
  )
}




