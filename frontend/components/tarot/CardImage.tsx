'use client'

import { useState, useEffect, useRef } from 'react'

interface CardImageProps {
  imageUrl: string
  alt: string
  isReversed: boolean
  containerClassName?: string
  imageClassName?: string
  onLoad?: () => void
  key?: string | number  // 添加key支持，用于强制重新渲染
}

/**
 * 卡牌图像组件
 * 显示逻辑：纵向图像，显示中间1/3部分（上面遮住1/3，下面遮住1/3）
 * - 图像宽度填满容器
 * - 图像高度放大3倍
 * - 显示中间1/3部分
 */
export function CardImage({
  imageUrl,
  alt,
  isReversed,
  containerClassName = '',
  imageClassName = '',
  onLoad,
}: CardImageProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [renderKey, setRenderKey] = useState(0)  // 用于强制重新渲染
  const imgRef = useRef<HTMLImageElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // 加载图像
  useEffect(() => {
    // 重置状态
    setIsLoading(true)
    
    const img = new Image()
    img.onload = () => {
      setIsLoading(false)
      if (onLoad) onLoad()
    }
    img.onerror = () => {
      setIsLoading(false)
    }
    img.src = imageUrl
    
    // 当imageUrl或isReversed变化时，强制重新渲染
    setRenderKey(prev => prev + 1)
  }, [imageUrl, isReversed, onLoad])

  // 计算显示样式：纵向图像，显示中间1/3
  const getDisplayStyle = () => {
    return {
      width: '100%',
      height: '300%',  // 高度放大3倍
      objectFit: 'cover' as const,
      position: 'absolute' as const,
      top: '50%',
      left: '50%',
      transform: `translate(-50%, -50%) ${isReversed ? 'rotate(180deg)' : ''}`,
      opacity: 0.9,  // 统一设置图片不透明度
    }
  }

  if (isLoading) {
    return (
      <div
        ref={containerRef}
        className={`w-full h-full flex items-center justify-center ${containerClassName}`}
      >
        <div className="text-xs text-[var(--text-secondary)]">加载中...</div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={`w-full h-full overflow-hidden relative ${containerClassName}`}
    >
      <img
        key={renderKey}  // 使用key强制重新渲染
        ref={imgRef}
        src={imageUrl}
        alt={alt}
        className={imageClassName}
        style={getDisplayStyle()}
        onLoad={() => {
          setIsLoading(false)
        }}
      />
    </div>
  )
}

