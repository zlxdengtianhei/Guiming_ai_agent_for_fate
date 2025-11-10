import React from 'react'
import { cn } from '@/lib/utils'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'gold' | 'purple' | 'cyan' | 'blue' | 'mystical' | 'error'
  size?: 'sm' | 'md' | 'lg'
}

const variantClasses = {
  default: 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-[var(--border-color)]',
  gold: 'bg-amber-500/20 text-amber-300 border-amber-500/30 shadow-[0_0_8px_rgba(245,158,11,0.2)]',
  purple: 'bg-purple-500/20 text-purple-300 border-purple-500/30 shadow-[0_0_8px_rgba(124,58,237,0.2)]',
  cyan: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30 shadow-[0_0_8px_rgba(6,182,212,0.2)]',
  blue: 'bg-blue-500/20 text-blue-300 border-blue-500/30 shadow-[0_0_8px_rgba(59,130,246,0.2)]',
  mystical: 'bg-gradient-to-r from-purple-500/30 via-amber-500/30 to-purple-500/30 text-white border-purple-500/40 shadow-[0_0_10px_rgba(124,58,237,0.3)]',
  error: 'bg-red-500/20 text-red-300 border-red-500/30 shadow-[0_0_8px_rgba(239,68,68,0.2)]',
}

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
  lg: 'text-base px-3 py-1.5',
}

export function Badge({
  children,
  className,
  variant = 'default',
  size = 'md',
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border font-medium transition-all duration-200',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
}

