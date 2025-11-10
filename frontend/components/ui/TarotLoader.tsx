'use client'

import { CSSProperties, useEffect, useMemo, useRef, useState } from 'react'

interface TarotLoaderProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

interface IconData {
  name: string
  svg: string
}

const FALLBACK_ICONS: IconData[] = [
  {
    name: 'cups',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><path d="M 30 30 H 70 Q 65 50 50 55 Q 35 50 30 30 Z" /><line x1="50" y1="55" x2="50" y2="72" /><path d="M 40 72 H 60" /><path d="M 37 77 H 63" /></g></svg>`,
  },
  {
    name: 'swords',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><path d="M 50 18 L 45 34 L 50 32 L 55 34 Z" /><line x1="50" y1="32" x2="50" y2="72" /><line x1="38" y1="58" x2="62" y2="58" /><line x1="48" y1="58" x2="48" y2="74" /><line x1="52" y1="58" x2="52" y2="74" /><circle cx="50" cy="78" r="4" /></g></svg>`,
  },
  {
    name: 'wands',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><line x1="50" y1="20" x2="50" y2="80" /><path d="M 48 20 Q 50 16 52 20" /><path d="M 50 35 L 44 38" /><path d="M 50 45 L 56 42" /><path d="M 50 60 L 44 63" /></g></svg>`,
  },
  {
    name: 'pentacles',
    svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"><circle cx="50" cy="50" r="22" /><path d="M50 30 L58 66 L32 43 H68 L42 66 Z" /></g></svg>`,
  },
]

const SIZE_CONFIG = {
  sm: { main: 32, trail: 20 },
  md: { main: 48, trail: 28 },
  lg: { main: 72, trail: 40 },
} as const

const ICON_ROTATION_INTERVAL = 1400
const ICONS_ENDPOINT = '/api/arcana-icons'

export function TarotLoader({ size = 'md', className = '' }: TarotLoaderProps) {
  const [icons, setIcons] = useState<IconData[]>(FALLBACK_ICONS)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [animationKey, setAnimationKey] = useState(0)
  const isMountedRef = useRef(false)

  useEffect(() => {
    let isCancelled = false

    const fetchIcons = async () => {
      try {
        const response = await fetch(ICONS_ENDPOINT, { cache: 'no-store' })
        if (!response.ok) {
          return
        }

        const data = await response.json()
        if (data?.icons?.length && !isCancelled) {
          setIcons(data.icons)
        }
      } catch (error) {
        console.warn('[TarotLoader] Failed to fetch arcana icons, using fallback set.', error)
      }
    }

    fetchIcons()

    return () => {
      isCancelled = true
    }
  }, [])

  useEffect(() => {
    if (icons.length === 0) {
      return
    }

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % icons.length)
    }, ICON_ROTATION_INTERVAL)

    return () => clearInterval(interval)
  }, [icons])

  useEffect(() => {
    if (isMountedRef.current) {
      setAnimationKey((key) => key + 1)
    } else {
      isMountedRef.current = true
    }
  }, [currentIndex])

  const sizeConfig = SIZE_CONFIG[size]
  const activeIcon = icons[currentIndex]
  const opacityScale = [0.95, 0.85, 0.65, 0.45]

  const leadingIcon = useMemo<IconData | null>(() => {
    if (icons.length <= 1) {
      return null
    }
    const previousIndex = (currentIndex - 1 + icons.length) % icons.length
    if (previousIndex === currentIndex) {
      return null
    }
    return icons[previousIndex]
  }, [icons, currentIndex])

  const trailingIcons = useMemo(() => {
    if (icons.length <= 1) return []
    const results: IconData[] = []
    const maxTrail = leadingIcon ? 2 : 3
    let offset = 1
    while (results.length < maxTrail && offset < icons.length) {
      const icon = icons[(currentIndex + offset) % icons.length]
      if (!leadingIcon || icon.name !== leadingIcon.name || icons.length === 2) {
        results.push(icon)
      }
      offset += 1
    }
    return results
  }, [icons, currentIndex, leadingIcon])

  const mainOpacityIndex = leadingIcon ? 1 : 0
  const getOpacityValue = (index: number) => opacityScale[Math.min(index, opacityScale.length - 1)]

  return (
    <div className={`arcana-loader flex items-center gap-4 ${className}`}>
      {leadingIcon && (
        <div
          className="arcana-loader__trail-icon arcana-loader__trail-icon--leading"
          style={
            {
              width: `${sizeConfig.trail}px`,
              height: `${sizeConfig.trail}px`,
              animationDelay: '0ms',
              '--arcana-opacity': getOpacityValue(0),
            } as CSSProperties
          }
          dangerouslySetInnerHTML={{ __html: leadingIcon.svg }}
        />
      )}
      <div
        className="arcana-loader__main"
        style={
          {
            width: `${sizeConfig.main}px`,
            height: `${sizeConfig.main}px`,
            '--arcana-opacity': getOpacityValue(mainOpacityIndex),
          } as CSSProperties
        }
      >
        {activeIcon ? (
          <div
            key={`${activeIcon.name}-${animationKey}`}
            className="arcana-loader__icon animate-arcana-loader"
            dangerouslySetInnerHTML={{ __html: activeIcon.svg }}
          />
        ) : (
          <div className="arcana-loader__dot" />
        )}
      </div>
      {trailingIcons.length > 0 && (
        <div className="arcana-loader__trail">
          {trailingIcons.map((icon, index) => (
            <div
              key={`${icon.name}-${index}-${animationKey}`}
              className="arcana-loader__trail-icon"
              style={
                {
                  width: `${sizeConfig.trail}px`,
                  height: `${sizeConfig.trail}px`,
                  animationDelay: `${(index + 1) * 140}ms`,
                  '--arcana-opacity': getOpacityValue(mainOpacityIndex + index + 1),
                } as CSSProperties
              }
              dangerouslySetInnerHTML={{ __html: icon.svg }}
            />
          ))}
        </div>
      )}
    </div>
  )
}


