'use client'

import { useEffect, useRef, useState } from 'react'
import { useLanguage } from '@/contexts/LanguageContext'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface TextModalProps {
  title: string
  text: string
  isStreaming?: boolean
  onClose: () => void
}

export function TextModal({ title, text, isStreaming = false, onClose }: TextModalProps) {
  const { t } = useLanguage()
  const textBoxRef = useRef<HTMLDivElement>(null)
  const lastScrollTopRef = useRef<number>(0)
  const [userHasScrolled, setUserHasScrolled] = useState(false)

  // 检测用户是否手动滚动了文本框
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
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

  // 自动滚动到文本底部（仅在用户未手动滚动且正在流式输出时）
  useEffect(() => {
    if (isStreaming && !userHasScrolled && textBoxRef.current) {
      textBoxRef.current.scrollTop = textBoxRef.current.scrollHeight
    }
  }, [text, isStreaming, userHasScrolled])

  // 处理键盘ESC关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative max-w-4xl w-full mx-4 bg-[var(--bg-secondary)] rounded-lg border-2 border-purple-500/50 p-6 max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 标题和关闭按钮 */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-purple-500/20">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">{title}</h2>
          <button
            onClick={onClose}
            className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors text-2xl"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* 文本内容区域 - 支持滚动 */}
        <div
          ref={textBoxRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto bg-[var(--bg-primary)] rounded-lg p-4 border border-purple-500/20 scrollbar-custom"
        >
          <div className="prose prose-invert prose-purple max-w-none">
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
                blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-purple-500/50 pl-4 italic text-[var(--text-secondary)]" {...props} />,
                code: ({node, inline, ...props}: any) =>
                  inline ? (
                    <code className="bg-[var(--bg-tertiary)] px-1 py-0.5 rounded text-sm text-[var(--text-primary)]" {...props} />
                  ) : (
                    <code className="block bg-[var(--bg-tertiary)] p-2 rounded text-sm text-[var(--text-primary)] overflow-x-auto" {...props} />
                  ),
              }}
            >
              {text}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-2 h-5 bg-purple-500 ml-1 animate-pulse" />
            )}
          </div>
        </div>

        {/* 提示信息 */}
        {isStreaming && userHasScrolled && (
          <div className="mt-2 text-center">
            <p className="text-xs text-[var(--text-muted)]">
              {t('streamingScrollHint') || '内容正在生成中，滚动到底部可继续自动滚动'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}




