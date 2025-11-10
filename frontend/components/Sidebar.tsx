'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { useLanguage } from '@/contexts/LanguageContext'
import { Button } from '@/components/ui/Button'
import { TarotLoader } from '@/components/ui/TarotLoader'
import { cn } from '@/lib/utils'
import { tarotAPI, ReadingListItem } from '@/lib/api'

interface SidebarProps {
  children: React.ReactNode
}

interface PendingReadingItem {
  id: string
  question: string
  source_page?: string
  created_at: string
  status?: string
}

interface ReadingPendingEventDetail {
  pendingId: string
  question: string
  createdAt: string
  sourcePage?: string
}

interface ReadingCreatedEventDetail {
  pendingId?: string
  readingId?: string
  question?: string
}

interface ReadingFailedEventDetail {
  pendingId?: string
  question?: string
  createdAt?: string
}

export function Sidebar({ children }: SidebarProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [readings, setReadings] = useState<ReadingListItem[]>([])
  const [pendingReadings, setPendingReadings] = useState<PendingReadingItem[]>([])
  const [loadingReadings, setLoadingReadings] = useState(false)
  const router = useRouter()
  const pathname = usePathname()
  const { user, signout } = useAuth()
  const { t } = useLanguage()

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        setIsOpen(true)
      } else {
        setIsOpen(false)
      }
    }

    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const loadReadings = useCallback(async () => {
    if (!user) return
    setLoadingReadings(true)
    try {
      const response = await tarotAPI.listReadings(10, 0)
      setReadings(response.readings || [])
      if (Array.isArray(response.readings)) {
        setPendingReadings((prev) =>
          prev.filter(
            (pending) => !response.readings.some((reading: ReadingListItem) => reading.question === pending.question)
          )
        )
      }
    } catch (error) {
      console.error('Failed to load readings:', error)
    } finally {
      setLoadingReadings(false)
    }
  }, [user])

  // 加载占卜记录
  useEffect(() => {
    if (user) {
      loadReadings()
    } else {
      setReadings([])
      setPendingReadings([])
    }
  }, [user, loadReadings])

  // 监听占卜事件，管理占卜进度
  useEffect(() => {
    const handleReadingPending = (event: Event) => {
      const detail = (event as CustomEvent<ReadingPendingEventDetail>).detail
      if (!detail) return
      setPendingReadings((prev) => {
        if (prev.some((item) => item.id === detail.pendingId)) {
          return prev
        }
        const newItem: PendingReadingItem = {
          id: detail.pendingId,
          question: detail.question,
          source_page: detail.sourcePage,
          created_at: detail.createdAt,
          status: 'pending',
        }
        return [newItem, ...prev].slice(0, 10)
      })
    }

    const handleReadingCreated = (event: Event) => {
      const detail = (event as CustomEvent<ReadingCreatedEventDetail>).detail
      if (detail?.pendingId) {
        setPendingReadings((prev) => prev.filter((item) => item.id !== detail.pendingId))
      } else if (detail?.question) {
        setPendingReadings((prev) => prev.filter((item) => item.question !== detail.question))
      } else {
        setPendingReadings([])
      }

      if (user) {
        loadReadings()
      }
    }

    const handleReadingFailed = (event: Event) => {
      const detail = (event as CustomEvent<ReadingFailedEventDetail>).detail
      if (detail?.pendingId) {
        setPendingReadings((prev) => prev.filter((item) => item.id !== detail.pendingId))
      } else if (detail?.question) {
        setPendingReadings((prev) => prev.filter((item) => item.question !== detail.question))
      } else {
        setPendingReadings([])
      }
    }

    window.addEventListener('readingPending', handleReadingPending as EventListener)
    window.addEventListener('readingCreated', handleReadingCreated as EventListener)
    window.addEventListener('readingFailed', handleReadingFailed as EventListener)

    return () => {
      window.removeEventListener('readingPending', handleReadingPending as EventListener)
      window.removeEventListener('readingCreated', handleReadingCreated as EventListener)
      window.removeEventListener('readingFailed', handleReadingFailed as EventListener)
    }
  }, [loadReadings, user])

  const getSourcePageLabel = (sourcePage?: string) => {
    if (!sourcePage) return ''
    switch (sourcePage) {
      case 'home':
        return t('fromHome')
      case 'spread-selection':
        return t('fromSpreadSelection')
      default:
        return sourcePage
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return t('justNow') || '刚刚'
    if (diffMins < 60) return `${diffMins}${t('minutesAgo') || '分钟前'}`
    if (diffHours < 24) return `${diffHours}${t('hoursAgo') || '小时前'}`
    if (diffDays < 7) return `${diffDays}${t('daysAgo') || '天前'}`
    return date.toLocaleDateString()
  }

  const handleSignout = async () => {
    await signout()
    router.push('/login')
  }

  const menuItems = [
    { id: 'home', labelKey: 'home' as const, path: '/', icon: 'home' as const },
    { id: 'spread-selection', labelKey: 'spreadSelection' as const, path: '/spread-selection', icon: 'spread' as const },
    { id: 'chinese-divination', label: '传统占卜', path: '/chinese-divination', icon: 'chinese' as const },
    { id: 'profile', labelKey: 'profile' as const, path: '/profile', icon: 'profile' as const },
  ]

  const renderNavIcon = (icon: 'home' | 'spread' | 'profile' | 'chinese', isActive: boolean) => {
    const className = cn(
      'h-5 w-5 flex-shrink-0 transition-colors duration-200',
      isActive ? 'text-[var(--accent-blue-light)]' : 'text-[var(--text-muted)] group-hover:text-[var(--text-primary)]'
    )

    switch (icon) {
      case 'spread':
        return (
          <svg
            className={className}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path d="M4 4h7v7H4z" />
            <path d="M13 4h7v7h-7z" />
            <path d="M13 13h7v7h-7z" />
            <path d="M4 13h7v7H4z" />
          </svg>
        )
      case 'chinese':
        return (
          <svg
            className={className}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        )
      case 'profile':
        return (
          <svg
            className={className}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path d="M18 20a6 6 0 00-12 0" />
            <path d="M12 12a4 4 0 100-8 4 4 0 000 8z" />
            <circle cx="12" cy="12" r="10" />
          </svg>
        )
      default:
        return (
          <svg
            className={className}
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
        )
    }
  }

  return (
    <div className="flex h-screen bg-[var(--bg-primary)]">
      {/* Mobile hamburger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed top-6 left-6 z-50 p-3 rounded-lg bg-[var(--bg-secondary)] shadow-lg border border-[var(--border-color)] md:hidden hover:bg-[var(--bg-tertiary)] transition-all duration-200"
        aria-label="Toggle sidebar"
      >
        <svg
          className="h-5 w-5 text-[var(--text-primary)]"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          {isOpen ? (
            <path d="M6 18L18 6M6 6l12 12" />
          ) : (
            <path d="M4 6h16M4 12h16M4 18h16" />
          )}
        </svg>
      </button>

      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 md:hidden transition-opacity duration-300"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 left-0 h-full bg-[var(--bg-secondary)] border-r border-[var(--border-color)] z-40 transition-all duration-300 ease-in-out flex flex-col',
          isOpen ? 'translate-x-0' : '-translate-x-full',
          'md:translate-x-0 md:static md:z-auto',
          isCollapsed ? 'w-20' : 'w-64'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-[var(--border-color)] bg-[var(--bg-primary)]/60">
          {!isCollapsed && (
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="flex flex-col min-w-0">
                <span className="font-semibold text-[var(--text-primary)] text-base truncate">
                  {t('appName')}
                </span>
                <span className="text-xs text-[var(--text-muted)] truncate">{t('appSubtitle')}</span>
              </div>
            </div>
          )}


          {/* Desktop collapse button */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden md:flex p-1.5 rounded-md hover:bg-[var(--bg-tertiary)] transition-all duration-200 flex-shrink-0"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg
              className="h-4 w-4 text-[var(--text-muted)]"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {isCollapsed ? (
                <path d="M9 5l7 7-7 7" />
              ) : (
                <path d="M15 19l-7-7 7-7" />
              )}
            </svg>
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto">
          <div className="space-y-1">
            {menuItems.map((item) => {
              const isActive = pathname === item.path
              const label = 'label' in item ? item.label : t(item.labelKey)

              return (
                <button
                  key={item.id}
                  onClick={() => {
                    if (item.path === '/' && pathname === '/') {
                      router.refresh()
                    } else {
                      router.push(item.path)
                    }
                    if (window.innerWidth < 768) {
                      setIsOpen(false)
                    }
                  }}
                  className={cn(
                    'w-full flex items-center rounded-lg text-left transition-all duration-200 group relative',
                    isActive
                      ? 'bg-[var(--accent-blue)]/20 text-[var(--accent-blue-light)]'
                      : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]',
                    isCollapsed ? 'justify-center px-2 py-3' : 'space-x-3 px-3 py-2.5'
                  )}
                  title={isCollapsed ? label : undefined}
                >
                  <div className="flex items-center justify-center min-w-[20px] flex-shrink-0">
                    {renderNavIcon(item.icon, isActive)}
                  </div>

                  {!isCollapsed && (
                    <span className={cn('text-sm min-w-0 truncate', isActive ? 'font-medium' : 'font-normal')}>
                      {label}
                    </span>
                  )}

                  {/* Tooltip for collapsed state */}
                  {isCollapsed && (
                    <div className="absolute left-full ml-2 px-2 py-1 bg-[var(--bg-primary)] text-[var(--text-primary)] text-xs rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 whitespace-nowrap z-50 border border-[var(--border-color)]">
                      {label}
                      <div className="absolute left-0 top-1/2 transform -translate-y-1/2 -translate-x-1 w-1.5 h-1.5 bg-[var(--bg-primary)] rotate-45 border-l border-b border-[var(--border-color)]" />
                    </div>
                  )}
                </button>
              )
            })}
          </div>

          {/* Reading History Section */}
          {!isCollapsed && user && (
            <div className="mt-6 pt-6 border-t border-[var(--border-color)]">
              <div className="px-3 mb-3">
                <h3 className="text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
                  {t('readingHistory')}
                </h3>
              </div>
              <div className="space-y-2 max-h-[300px] overflow-y-auto scrollbar-custom">
                {loadingReadings ? (
                  <div className="px-3 py-2 flex flex-col items-center justify-center gap-2">
                    <TarotLoader size="sm" />
                    <span className="text-sm text-[var(--text-muted)]">{t('loading')}</span>
                  </div>
                ) : pendingReadings.length === 0 && readings.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-[var(--text-muted)]">
                    {t('noReadings')}
                  </div>
                ) : (
                  <>
                    {pendingReadings.map((reading) => (
                      <div
                        key={reading.id}
                        className="w-full text-left px-3 py-2 rounded-lg bg-[var(--accent-blue)]/10 border border-[var(--accent-blue)]/30 transition-all duration-200"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-[var(--text-primary)] truncate break-words line-clamp-2">
                              {reading.question}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              {reading.source_page && (
                                <span className="text-[10px] text-[var(--text-muted)] bg-[var(--bg-primary)] px-1.5 py-0.5 rounded">
                                  {getSourcePageLabel(reading.source_page)}
                                </span>
                              )}
                              <span className="text-[10px] text-[var(--accent-blue-light)] bg-[var(--accent-blue)]/20 px-1.5 py-0.5 rounded">
                                {t('readingInProgress')}
                              </span>
                              <span className="text-[10px] text-[var(--text-muted)]">{t('justNow')}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                    {readings.map((reading) => (
                      <button
                        key={reading.id}
                        onClick={() => {
                          router.push(`/reading/${reading.id}`)
                          if (window.innerWidth < 768) {
                            setIsOpen(false)
                          }
                        }}
                        className="w-full text-left px-3 py-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-all duration-200 group"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-[var(--text-primary)] truncate break-words line-clamp-2">
                              {reading.question}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                              {reading.source_page && (
                                <span className="text-[10px] text-[var(--text-muted)] bg-[var(--bg-primary)] px-1.5 py-0.5 rounded">
                                  {getSourcePageLabel(reading.source_page)}
                                </span>
                              )}
                              <span className="text-[10px] text-[var(--text-muted)]">
                                {formatDate(reading.created_at)}
                              </span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </>
                )}
              </div>
            </div>
          )}
        </nav>

        {/* User section */}
        <div className="mt-auto border-t border-[var(--border-color)]">
          <div className={cn('border-b border-[var(--border-color)] bg-[var(--bg-primary)]/30', isCollapsed ? 'py-3 px-2' : 'p-3')}>
            {!isCollapsed ? (
              <div className="space-y-2">
                <div className="flex items-center space-x-2 min-w-0">
                  <div className="w-8 h-8 bg-[var(--accent-blue)] rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xs font-medium">
                      {user?.email?.[0]?.toUpperCase() || 'U'}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                      {user?.email || t('loading')}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start min-w-0"
                  onClick={handleSignout}
                >
                  <span className="truncate">{t('logout')}</span>
                </Button>
              </div>
            ) : (
              <div className="flex justify-center">
                <div className="w-9 h-9 bg-[var(--accent-blue)] rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-medium">
                    {user?.email?.[0]?.toUpperCase() || 'U'}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
