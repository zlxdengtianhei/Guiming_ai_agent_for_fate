'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguage } from '@/contexts/LanguageContext'
import { tarotAPI } from '@/lib/api'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Textarea'
import { Sidebar } from '@/components/Sidebar'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Container } from '@/components/ui/Container'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Alert } from '@/components/ui/Alert'
import { ThreeCardSpread } from '@/components/tarot/ThreeCardSpread'
import { CelticCrossSpread } from '@/components/tarot/CelticCrossSpread'
import { CardModal } from '@/components/tarot/CardModal'
import { TextModal } from '@/components/tarot/TextModal'
import { TarotLoader } from '@/components/ui/TarotLoader'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type ReadingStep = 
  | 'idle'
  | 'question_analysis'
  | 'cards_selected'
  | 'pattern_analyzed'
  | 'rag_retrieved'
  | 'imagery_generated'
  | 'interpretation_started'
  | 'interpretation_streaming'
  | 'complete'

interface CardData {
  card_id: string
  card_name_en: string
  card_name_cn?: string
  position: string
  position_order: number
  is_reversed: boolean
  image_url?: string
}

export default function HomePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const selectedSpread = searchParams.get('spread') as 'three_card' | 'celtic_cross' | null
  
  const [question, setQuestion] = useState('')
  const [currentStep, setCurrentStep] = useState<ReadingStep>('idle')
  const [error, setError] = useState<string | null>(null)
  const [cards, setCards] = useState<CardData[]>([])
  const [displayedCards, setDisplayedCards] = useState<CardData[]>([]) // 渐进式显示的卡牌
  const [spreadType, setSpreadType] = useState<'three_card' | 'celtic_cross'>('three_card')
  const [readingId, setReadingId] = useState<string | null>(null) // 保存占卜ID，用于跳转
  const [imageryDescription, setImageryDescription] = useState<string>('') // 直接存储流式文本
  const [interpretationDisplay, setInterpretationDisplay] = useState<string>('') // 逐步展示的流式文本
  const [isImageryExpanded, setIsImageryExpanded] = useState(false)
  const [isImageryModalOpen, setIsImageryModalOpen] = useState(false)
  const [isInterpretationExpanded, setIsInterpretationExpanded] = useState(false)
  const [isInterpretationModalOpen, setIsInterpretationModalOpen] = useState(false)
  const [hasUserInteracted, setHasUserInteracted] = useState(false)
  const [selectedCardIndex, setSelectedCardIndex] = useState<number | null>(null)
  const [scrollPosition, setScrollPosition] = useState(0) // 保存滚动位置
  const [userHasScrolled, setUserHasScrolled] = useState(false) // 用户是否手动滚动
  const [showImageryBox, setShowImageryBox] = useState(false) // 控制意象描述框显示
  const [showInterpretationBox, setShowInterpretationBox] = useState(false) // 控制最终解读框显示
  const [allCardsDisplayed, setAllCardsDisplayed] = useState(false) // 所有卡牌是否已显示
  const [showTarotExplanation, setShowTarotExplanation] = useState(false)
  
  const { user, profile } = useAuth()
  const { t } = useLanguage()
  const interpretationEndRef = useRef<HTMLDivElement>(null)
  const interpretationBoxRef = useRef<HTMLDivElement>(null)
  const lastScrollTopRef = useRef<number>(0)
  const interpretationBufferRef = useRef<string>('')
  const typingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const startInterpretationTyping = useCallback(() => {
    if (typingIntervalRef.current) {
      return
    }

    typingIntervalRef.current = setInterval(() => {
      if (interpretationBufferRef.current.length === 0) {
        if (typingIntervalRef.current) {
          clearInterval(typingIntervalRef.current)
          typingIntervalRef.current = null
        }
        return
      }

      const nextChunk = interpretationBufferRef.current.slice(0, 5)
      interpretationBufferRef.current = interpretationBufferRef.current.slice(nextChunk.length)
      setInterpretationDisplay((prev) => prev + nextChunk)
    }, 50) // 20字每秒 = 每50ms输出5个字
  }, [])

  useEffect(() => {
    return () => {
      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current)
      }
    }
  }, [])

  // 检测用户是否手动滚动了解读文本框
  const handleInterpretationScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget
    const isAtBottom = Math.abs(target.scrollHeight - target.scrollTop - target.clientHeight) < 10
    
    // 如果用户向上滚动（不在底部），标记为已手动滚动
    if (!isAtBottom && target.scrollTop < lastScrollTopRef.current) {
      setUserHasScrolled(true)
    }
    
    // 如果用户滚动到底部，重置手动滚动标记
    if (isAtBottom) {
      setUserHasScrolled(false)
    }
    
    lastScrollTopRef.current = target.scrollTop
  }

  // 自动滚动到解读文本底部（仅在用户未手动滚动且正在流式输出时）
  useEffect(() => {
    if (currentStep === 'interpretation_streaming' && !userHasScrolled && interpretationBoxRef.current) {
      // 使用 requestAnimationFrame 确保 DOM 更新后再滚动
      requestAnimationFrame(() => {
        if (interpretationBoxRef.current) {
          interpretationBoxRef.current.scrollTop = interpretationBoxRef.current.scrollHeight
        }
      })
    }
  }, [interpretationDisplay, currentStep, userHasScrolled])

  // 意象生成完成后，等待1秒显示解读框
  // 或者在开始生成解读时立即显示解读框（以便显示加载动画）
  useEffect(() => {
    if (currentStep === 'imagery_generated' && !showInterpretationBox) {
      const timer = setTimeout(() => {
        setShowInterpretationBox(true)
      }, 1000)
      return () => clearTimeout(timer)
    }
    // 如果开始生成解读，立即显示解读框以便显示加载动画
    if (currentStep === 'interpretation_started' && !showInterpretationBox) {
      setShowInterpretationBox(true)
    }
  }, [currentStep, showInterpretationBox])

  // 处理渐进式卡牌显示 - 根据占卜类型动态调整显示时间
  useEffect(() => {
    console.log('🎴 [卡牌显示 useEffect]', {
      'cards.length': cards.length,
      'displayedCards.length': displayedCards.length,
      'currentStep': currentStep,
      'spreadType': spreadType
    })

    if (cards.length === 0) {
      console.log('🎴 [卡牌显示] cards 为空，清空 displayedCards')
      setDisplayedCards([])
      return
    }

    const sortedCards = [...cards].sort((a, b) => a.position_order - b.position_order)
    console.log('🎴 [卡牌显示] sortedCards:', sortedCards.map(c => `${c.card_name_cn || c.card_name_en}(${c.position_order})`))

    // 如果已经显示所有卡牌，不做任何操作（完成逻辑在定时器中处理）
    if (displayedCards.length >= sortedCards.length) {
      return
    }
    
    // 根据占卜类型计算总显示时间
    // 三牌占卜：5秒，十字占卜：10秒
    const totalDisplayTime = spreadType === 'three_card' ? 5000 : 10000
    const intervalPerCard = totalDisplayTime / sortedCards.length
    
    console.log(`🎴 [卡牌显示] 占卜类型: ${spreadType}, 总时间: ${totalDisplayTime}ms, 每张卡间隔: ${intervalPerCard}ms`)
    console.log(`🎴 [卡牌显示] 设置定时器，${intervalPerCard}ms 后显示第 ${displayedCards.length + 1} 张卡`)
    
    // 设置定时器逐张显示卡牌
    const timer = setTimeout(() => {
      const nextIndex = displayedCards.length
      if (nextIndex < sortedCards.length) {
        console.log(`🎴 [卡牌显示] 显示第 ${nextIndex + 1} 张卡`)
        const newDisplayedCards = sortedCards.slice(0, nextIndex + 1)
        setDisplayedCards(newDisplayedCards)
        
        // 如果这是最后一张卡，立即触发完成逻辑
        if (newDisplayedCards.length === sortedCards.length && !allCardsDisplayed) {
          setAllCardsDisplayed(true)
          // 等待1秒后显示意象框
          setTimeout(() => {
            setShowImageryBox(true)
          }, 1000)
        }
      }
    }, intervalPerCard)
    
    return () => clearTimeout(timer)
  }, [cards, displayedCards.length, spreadType, allCardsDisplayed])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion) return

    // 重置状态
    setCurrentStep('question_analysis')
    setError(null)
    setCards([])
    setDisplayedCards([])
    if (typingIntervalRef.current) {
      clearInterval(typingIntervalRef.current)
      typingIntervalRef.current = null
    }
    interpretationBufferRef.current = ''
    setImageryDescription('')
    setInterpretationDisplay('')
    setIsImageryExpanded(false)
    setIsImageryModalOpen(false)
    setIsInterpretationExpanded(false)
    setIsInterpretationModalOpen(false)
    setHasUserInteracted(false)
    setSelectedCardIndex(null)
    setUserHasScrolled(false)
    setShowImageryBox(false)
    setShowInterpretationBox(false)
    setAllCardsDisplayed(false)

    let pendingId: string | null = null
    let pendingCreatedAt: string | null = null

    try {
      pendingId = `pending-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      pendingCreatedAt = new Date().toISOString()
      const pendingIdForRequest = pendingId
      const pendingCreatedAtForRequest = pendingCreatedAt

      if (typeof window !== 'undefined') {
        window.dispatchEvent(
          new CustomEvent('readingPending', {
            detail: {
              pendingId: pendingIdForRequest,
              question: trimmedQuestion,
              createdAt: pendingCreatedAtForRequest,
              sourcePage: 'home',
            },
          })
        )
      }

      // 根据URL参数或默认值确定占卜方式
      const finalSpread = selectedSpread || 'auto'
      
      await tarotAPI.createReadingStream(
        {
          question: trimmedQuestion,
          user_selected_spread: finalSpread === 'auto' ? undefined : finalSpread,
          source_page: 'home',
          user_profile: profile ? {
            age: profile.age,
            gender: profile.gender,
            zodiac_sign: profile.zodiac_sign,
            personality_type: profile.personality_type,
            preferred_source: profile.preferred_source,
            preferred_spread: profile.preferred_spread,
            language: profile.language,
            significator_priority: profile.significator_priority,
          } : undefined,
        },
        (step, data) => {
          // 处理进度更新
          console.log('📊 [进度更新]', new Date().toISOString(), step, data)
          
          // 处理流式意象描述（不更新currentStep）
          if (step === 'imagery_chunk' && data.text) {
            // 直接追加到显示文本（React会自动批量处理更新）
            setImageryDescription(prev => {
              // 如果是第一个chunk，确保意象框已显示
              if (prev.length === 0) {
                setTimeout(() => setShowImageryBox(true), 0)
              }
              return prev + data.text
            })
            return
          }
          
          setCurrentStep(step as ReadingStep)
          
          if (step === 'cards_selected' && (data.selected_cards || data.cards)) {
            // 更新卡牌数据
            const cardList = data.selected_cards || data.cards || []
            console.log('🎴 [cards_selected] 收到卡牌数据:', cardList.length, '张')
            const cardData: CardData[] = cardList.map((card: any) => ({
              card_id: card.card_id || card.id,
              card_name_en: card.card_name_en || card.name,
              card_name_cn: card.card_name_cn,
              position: card.position,
              position_order: card.position_order || 0,
              is_reversed: card.is_reversed || false,
              image_url: card.image_url,
            }))
            console.log('🎴 [cards_selected] 处理后的卡牌数据:', cardData.map(c => `${c.card_name_cn || c.card_name_en}(${c.position_order})`))
            setCards(cardData)
            
            // 确定占卜方式
            if (cardData.length === 3) {
              console.log('🎴 [cards_selected] 占卜方式: 三牌占卜')
              setSpreadType('three_card')
            } else if (cardData.length === 10) {
              console.log('🎴 [cards_selected] 占卜方式: 十字占卜')
              setSpreadType('celtic_cross')
            }
            
            // 立即显示第一张牌
            if (cardData.length > 0) {
              console.log('🎴 [cards_selected] 立即显示第一张牌')
              setDisplayedCards([cardData[0]])
            }
          } else if (step === 'rag_retrieved') {
            // RAG检索完成，准备开始生成意象描述
            console.log('📊 [rag_retrieved] RAG检索完成，准备生成意象描述')
          } else if (step === 'imagery_generated') {
            // 意象描述生成完成（流式输出完毕）
            console.log('📊 [imagery_generated] 意象描述生成完成')
            // 如果data中有完整的imagery_description，可以作为备用
            if (data.imagery_description && !imageryDescription) {
              console.log('🔄 [意象生成完成] 使用备用完整内容')
              setImageryDescription(data.imagery_description)
            }
          } else if (step === 'interpretation_started') {
            // 开始生成解读（不立即显示解读框，让1秒延迟逻辑处理）
            console.log('📊 [interpretation_started] 开始生成解读')
            setCurrentStep('interpretation_started') // 更新currentStep以便问题框显示正确进度
            // 确保解读框显示，以便显示加载动画
            if (!showInterpretationBox) {
              setTimeout(() => setShowInterpretationBox(true), 0)
            }
          }
        },
        (text) => {
          setCurrentStep('interpretation_streaming')

          if (interpretationDisplay.length === 0) {
            setTimeout(() => setShowInterpretationBox(true), 0)
          }

          interpretationBufferRef.current += text
          startInterpretationTyping()
          
          if (!hasUserInteracted && !isImageryExpanded) {
            setIsInterpretationExpanded(true)
          }
        },
        (result) => {
          // 处理完成 - 不进行任何状态更新，避免重渲染
          console.log('✅ [占卜完成]', result)
          setCurrentStep('complete')
          
          // 获取reading_id并保存（用于后续查看详情，但不触发重渲染）
          // complete事件返回的data结构：{ reading_id, question, spread_type, total_time_ms, message }
          const id = result?.reading_id || result?.id
          if (id) {
            setReadingId(id)
          }
          
          // 通知 Sidebar 刷新占卜记录（占卜结果已自动保存到数据库）
          // 使用 setTimeout 避免影响当前渲染
          setTimeout(() => {
            window.dispatchEvent(
              new CustomEvent('readingCreated', {
                detail: {
                  pendingId: pendingIdForRequest,
                  readingId: id,
                  question: trimmedQuestion,
                },
              })
            )
          }, 0)
        },
        (errorMsg) => {
          // 处理错误
          if (typingIntervalRef.current) {
            clearInterval(typingIntervalRef.current)
            typingIntervalRef.current = null
          }
          interpretationBufferRef.current = ''
          setInterpretationDisplay('')
          setError(errorMsg)
          setCurrentStep('idle')

          if (typeof window !== 'undefined') {
            window.dispatchEvent(
              new CustomEvent('readingFailed', {
                detail: {
                  pendingId: pendingIdForRequest,
                  question: trimmedQuestion,
                },
              })
            )
          }
        }
      )
    } catch (err: any) {
      setError(err.message || t('readingFailed'))
      setCurrentStep('idle')

      if (typeof window !== 'undefined' && trimmedQuestion) {
        window.dispatchEvent(
          new CustomEvent('readingFailed', {
            detail: {
              pendingId: pendingId || undefined,
              question: trimmedQuestion,
              createdAt: pendingCreatedAt || undefined,
            },
          })
        )
      }
    }
  }

  const getStepMessage = () => {
    switch (currentStep) {
      case 'question_analysis':
        return t('analyzingQuestion') || '正在分析问题...'
      case 'cards_selected':
      case 'pattern_analyzed':
        return t('selectingCards') || '正在抽取卡牌...'
      case 'rag_retrieved':
        return '正在分析牌型...'
      case 'imagery_generated':
        // 意象生成完成后，如果已经开始生成解读，显示解读状态；否则显示意象状态
        // 检查是否已经开始生成解读（通过检查解读框是否显示或是否有解读内容）
        if (showInterpretationBox || interpretationDisplay.length > 0) {
          return t('generatingInterpretation') || '正在生成最终解读...'
        }
        return t('generatingImageryStatus') || '正在生成意象...'
      case 'interpretation_started':
      case 'interpretation_streaming':
        return t('generatingInterpretation') || '正在生成最终解读...'
      default:
        return ''
    }
  }

  // 获取意象描述框的状态信息
  const getImageryStatus = () => {
    // 如果有显示内容，不显示状态提示
    if (imageryDescription.length > 0) {
      return null
    }
    
    // 根据当前步骤显示不同的状态
    if (currentStep === 'pattern_analyzed' || currentStep === 'rag_retrieved') {
      return '正在分析卡牌...'
    }
    
    // 默认状态
    if (currentStep === 'imagery_generated') {
      return null // 已完成，不显示提示
    }
    
    return '正在生成占卜意象...'
  }

  // 获取解读框的状态信息
  const getInterpretationStatus = () => {
    if (interpretationDisplay.length > 0) {
      return null
    }

    if (currentStep === 'interpretation_started' || currentStep === 'interpretation_streaming') {
      return '正在生成最终解读...'
    }

    return '正在生成最终解读...'
  }

  const threeCardPositions = [t('past'), t('present'), t('future')]

  const handleCardClick = (index: number) => {
    // 保存当前滚动位置
    setScrollPosition(window.scrollY || document.documentElement.scrollTop)
    setSelectedCardIndex(index)
    setHasUserInteracted(true)
  }

  const handleCardModalClose = () => {
    setSelectedCardIndex(null)
    // 恢复滚动位置
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

  return (
    <ProtectedRoute>
      <Sidebar>
        <div className="min-h-screen bg-[var(--bg-primary)] py-8">
          <Container size="md" className="w-full">
            <div className="flex flex-col space-y-6">
              {/* 问题输入框 - 只在idle状态显示完整版本 */}
              {currentStep === 'idle' ? (
                <Card variant="mystical" glowColor="gold" className="w-full sticky top-4 z-10">
                  <CardHeader className="text-center">
                    <CardTitle className="text-3xl font-bold bg-gradient-to-r from-amber-300 via-purple-300 to-amber-300 bg-clip-text text-transparent">
                      {t('whatToAskToday')}
                    </CardTitle>
                    <CardDescription className="text-center">
                      {t('questionPlaceholder')}
                      <Button 
                        variant="link" 
                        className="ml-2 text-sm text-amber-300/70 hover:text-amber-300"
                        onClick={() => setShowTarotExplanation(!showTarotExplanation)}
                      >
                        {showTarotExplanation ? '收起说明' : '查看说明'}
                      </Button>
                    </CardDescription>
                    {showTarotExplanation && (
                      <Alert variant="info" className="text-left mt-4 animate-fadeIn">
                        <p className="font-bold">塔罗占卜可以做什么？</p>
                        <p className="text-sm">
                          塔罗占卜可以帮助你探索生活中的各种问题，比如爱情、事业、学业、人际关系等。它通过牌面的象征意义，为你提供一个全新的视角来审视现状，并揭示未来发展的可能性。塔罗并非预测绝对的未来，而是为你提供指引和启发，帮助你更好地了解自己，从而做出更明智的决定。
                        </p>
                      </Alert>
                    )}
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleSubmit} className="space-y-6">
                      <Textarea
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder={t('questionPlaceholder')}
                        rows={4}
                        disabled={currentStep !== 'idle'}
                        className="text-lg border-amber-500/30 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)]"
                      />
                      <Button
                        type="submit"
                        variant="mystical"
                        size="lg"
                        className="w-full"
                        disabled={currentStep !== 'idle' || !question.trim()}
                      >
                        {t('startReading')}
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              ) : (
                /* 占卜进行中或完成后 - 显示简洁的问题显示 */
                <Card variant="mystical" glowColor="gold" className="w-full sticky top-4 z-10">
                <CardContent className="p-4">
                  <div className="flex flex-col gap-3">
                    <div>
                      <p className="text-sm text-[var(--text-muted)] mb-1">{t('currentQuestion') || '当前问题'}</p>
                      <p className="text-base text-[var(--text-primary)] font-medium line-clamp-2">
                        {question}
                      </p>
                    </div>
                    {currentStep !== 'complete' && (
                      <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3 gap-2">
                        <TarotLoader size="sm" />
                        <span className="text-xs text-[var(--text-muted)] tracking-wide">
                          {getStepMessage()}
                        </span>
                      </div>
                    )}
                  </div>
                  </CardContent>
                </Card>
              )}

              {/* 错误显示 */}
              {error && (
                <Alert variant="error" className="w-full">
                  {error}
                </Alert>
              )}

              {/* 状态显示 - 只在没有卡牌时显示 */}
              {(currentStep === 'question_analysis' || 
                (currentStep === 'cards_selected' && displayedCards.length === 0) ||
                (currentStep === 'pattern_analyzed' && displayedCards.length === 0)) && (
                <Card variant="glow" glowColor="purple" className="w-full">
                  <CardContent className="p-6 text-center">
                    <div className="flex flex-col items-center justify-center gap-4">
                      <TarotLoader size="lg" />
                      <p className="text-lg text-[var(--text-primary)]">{getStepMessage()}</p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* 卡牌展示 */}
              {(displayedCards.length > 0 || currentStep === 'cards_selected' || currentStep === 'pattern_analyzed' || currentStep === 'rag_retrieved') && (
                <Card variant="glow" glowColor="purple" className="w-full relative overflow-hidden" style={{
                  backgroundImage: 'url(/database/images/background/backgroud.png)',
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  backgroundRepeat: 'no-repeat',
                }}>
                  <div className="absolute inset-0 bg-[var(--bg-secondary)]/60 backdrop-blur-[1px]"></div>
                  <div className="relative z-10">
                    <CardHeader className="text-center">
                      <CardTitle className="text-2xl flex items-center justify-center gap-2">
                        {t('selectedCards') || '抽取的卡牌'}
                      {/* 在抽取/分析卡牌时显示加载动画 - 即使有部分卡牌显示，如果还在处理中也要显示 */}
                      {((currentStep === 'cards_selected' || currentStep === 'pattern_analyzed' || currentStep === 'rag_retrieved') && 
                        (displayedCards.length === 0 || (cards.length > 0 && displayedCards.length < cards.length))) && (
                        <TarotLoader size="sm" />
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex justify-center relative">
                    {displayedCards.length > 0 ? (
                      <div className="w-full">
                        {spreadType === 'three_card' ? (
                          <ThreeCardSpread 
                            cards={displayedCards} 
                            positions={threeCardPositions}
                            onCardClick={handleCardClick}
                          />
                        ) : (
                          <CelticCrossSpread 
                            cards={displayedCards}
                            onCardClick={handleCardClick}
                          />
                        )}
                        {/* 如果还有卡牌未显示，在下方显示加载提示 */}
                        {cards.length > 0 && displayedCards.length < cards.length && (
                          <div className="mt-4 flex items-center justify-center gap-2 text-sm text-[var(--text-muted)]">
                            <TarotLoader size="sm" />
                            <span>正在显示卡牌...</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      /* 卡牌正在抽取/分析时显示加载动画 */
                      <div className="flex flex-col items-center justify-center gap-4 py-12">
                        <TarotLoader size="lg" />
                        <p className="text-lg text-[var(--text-primary)]">
                          {currentStep === 'cards_selected' || currentStep === 'pattern_analyzed' 
                            ? t('selectingCards') || '正在抽取卡牌...'
                            : currentStep === 'rag_retrieved'
                            ? '正在分析牌型...'
                            : '正在处理...'}
                        </p>
                      </div>
                    )}
                  </CardContent>
                  </div>
                </Card>
              )}

              {/* 意象描述 */}
              {showImageryBox && (
                <Card 
                  variant="glow" 
                  glowColor="purple" 
                  className="w-full cursor-pointer transition-all hover:border-purple-500/50 animate-fadeIn relative overflow-hidden !bg-transparent !border-purple-500/20"
                  style={{ 
                    animationDelay: '0.2s',
                    backgroundImage: `url('/database/images/background/backgroud.png')`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat',
                  }}
                  onClick={() => {
                    if (imageryDescription) {
                      // 保存滚动位置
                      setScrollPosition(window.scrollY || document.documentElement.scrollTop)
                      setIsImageryModalOpen(true)
                      setHasUserInteracted(true)
                    }
                  }}
                >
                  <div className="absolute inset-0 bg-[var(--bg-secondary)]/60 backdrop-blur-[1px]"></div>
                  <div className="relative z-10">
                    <CardHeader>
                      <CardTitle className="text-xl flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          {t('imageryDescription') || '牌阵意象'}
                          {/* 正在生成意象时显示加载动画 - 只要还在生成中就显示 */}
                          {(currentStep === 'rag_retrieved' || (currentStep === 'imagery_generated' && imageryDescription.length === 0)) && (
                            <TarotLoader size="sm" />
                          )}
                        </span>
                        {imageryDescription && imageryDescription.length > 0 && (
                          <span className="text-sm text-[var(--text-muted)]">
                            {t('clickToViewDetails') || '点击查看详情'}
                          </span>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="min-h-[180px] flex items-center">
                      <div className="w-full">
                      {imageryDescription ? (
                        <p className="text-[var(--text-primary)] whitespace-pre-wrap break-words leading-relaxed line-clamp-2">
                          {imageryDescription}
                        </p>
                      ) : (
                        <div className="flex flex-col items-center justify-center gap-3 py-6 min-h-[150px]">
                          <TarotLoader size="md" />
                          <p className="text-[var(--text-secondary)] italic">
                            {getImageryStatus()}
                          </p>
                        </div>
                      )}
                      </div>
                    </CardContent>
                  </div>
                </Card>
              )}

              {/* 流式解读输出 */}
              {showInterpretationBox && (
                <Card 
                  variant="glow" 
                  glowColor="gold" 
                  className={`w-full animate-fadeIn relative overflow-hidden !bg-transparent !border-amber-500/20 ${!hasUserInteracted && !isImageryExpanded ? 'border-2 border-amber-500/50' : ''}`}
                  style={{ 
                    animationDelay: '0.2s',
                    backgroundImage: `url('/database/images/background/backgroud.png')`,
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat',
                  }}
                >
                  <div className="absolute inset-0 bg-[var(--bg-secondary)]/60 backdrop-blur-[1px]"></div>
                  <div className="relative z-10">
                    <CardHeader 
                      className="cursor-pointer transition-all hover:bg-[var(--bg-secondary)]"
                      onClick={() => {
                        if (interpretationDisplay) {
                          // 保存滚动位置
                          setScrollPosition(window.scrollY || document.documentElement.scrollTop)
                          setIsInterpretationModalOpen(true)
                          setHasUserInteracted(true)
                        }
                      }}
                    >
                      <CardTitle className="text-2xl flex items-center justify-between">
                        <span className="flex items-center gap-2">
                          {t('interpretation') || '占卜解读'}
                          {/* 正在生成解读时显示加载动画 - 只要还在生成中就显示 */}
                          {(currentStep === 'interpretation_started' || currentStep === 'interpretation_streaming') && (
                            <TarotLoader size="sm" />
                          )}
                        </span>
                        {interpretationDisplay && interpretationDisplay.length > 0 && (
                          <span className="text-sm text-[var(--text-muted)]">
                            {t('clickToViewDetails') || '点击查看详情'}
                          </span>
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                    {interpretationDisplay && interpretationDisplay.length > 0 ? (
                      <div 
                        ref={interpretationBoxRef}
                        onScroll={handleInterpretationScroll}
                        className="bg-[var(--bg-primary)] rounded-lg p-4 border border-amber-500/20 min-h-[220px] max-h-[340px] overflow-y-auto scrollbar-gold"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <div className="prose prose-invert max-w-none">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              // 自定义样式组件
                              h1: ({node, ...props}) => <h1 className="text-3xl font-bold mb-4 text-[var(--text-primary)]" {...props} />,
                              h2: ({node, ...props}) => <h2 className="text-2xl font-bold mb-3 text-[var(--text-primary)]" {...props} />,
                              h3: ({node, ...props}) => <h3 className="text-xl font-bold mb-2 text-[var(--text-primary)]" {...props} />,
                              p: ({node, ...props}) => <p className="mb-4 text-[var(--text-primary)] leading-relaxed" {...props} />,
                              ul: ({node, ...props}) => <ul className="list-disc list-inside mb-4 text-[var(--text-primary)]" {...props} />,
                              ol: ({node, ...props}) => <ol className="list-decimal list-inside mb-4 text-[var(--text-primary)]" {...props} />,
                              li: ({node, ...props}) => <li className="mb-1 text-[var(--text-primary)]" {...props} />,
                              hr: ({node, ...props}) => <hr className="my-4 border-[var(--border-color)]" {...props} />,
                              blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-amber-500/50 pl-4 italic text-[var(--text-secondary)]" {...props} />,
                              code: ({node, inline, ...props}: any) => 
                                inline ? (
                                  <code className="bg-[var(--bg-tertiary)] px-1 py-0.5 rounded text-sm text-[var(--text-primary)]" {...props} />
                                ) : (
                                  <code className="block bg-[var(--bg-tertiary)] p-2 rounded text-sm text-[var(--text-primary)] overflow-x-auto" {...props} />
                                ),
                            }}
                          >
                            {interpretationDisplay}
                          </ReactMarkdown>
                          {currentStep === 'interpretation_streaming' && (
                            <span className="inline-block w-2 h-5 bg-amber-500 ml-1 animate-pulse" />
                          )}
                          <div ref={interpretationEndRef} />
                        </div>
                        </div>
                      ) : (
                        <div className="bg-[var(--bg-primary)] rounded-lg p-4 border border-amber-500/20 min-h-[200px] flex flex-col items-center justify-center gap-3">
                          <TarotLoader size="md" />
                          <p className="text-[var(--text-secondary)] italic">
                            {getInterpretationStatus()}
                          </p>
                        </div>
                      )}
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

              {/* 意象描述放大模态框 */}
              {isImageryModalOpen && imageryDescription && (
                <TextModal
                  title={t('imageryDescription') || '牌阵意象'}
                  text={imageryDescription}
                  isStreaming={currentStep === 'imagery_generated'}
                  onClose={() => {
                    setIsImageryModalOpen(false)
                    // 恢复滚动位置
                    setTimeout(() => {
                      window.scrollTo({
                        top: scrollPosition,
                        behavior: 'instant'
                      })
                    }, 0)
                  }}
                />
              )}

              {/* 解读放大模态框 */}
              {isInterpretationModalOpen && interpretationDisplay && (
                <TextModal
                  title={t('interpretation') || '占卜解读'}
                  text={interpretationDisplay}
                  isStreaming={currentStep === 'interpretation_streaming'}
                  onClose={() => {
                    setIsInterpretationModalOpen(false)
                    // 恢复滚动位置
                    setTimeout(() => {
                      window.scrollTo({
                        top: scrollPosition,
                        behavior: 'instant'
                      })
                    }, 0)
                  }}
                />
              )}
            </div>
          </Container>
        </div>
      </Sidebar>
    </ProtectedRoute>
  )
}