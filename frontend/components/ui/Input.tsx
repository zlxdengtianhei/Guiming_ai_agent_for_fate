import React from 'react'
import { cn } from '@/lib/utils'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'mystical'
}

export function Input({ className, variant = 'default', ...props }: InputProps) {
  const variantClasses = variant === 'mystical' 
    ? 'border-amber-500/30 focus:ring-amber-500/50 focus:border-amber-500/50 focus:shadow-[0_0_15px_rgba(245,158,11,0.2)]'
    : 'border-[var(--border-color)] focus:ring-[var(--accent-blue)] focus:border-transparent'

  return (
    <input
      className={cn(
        'w-full px-4 py-2 bg-[var(--bg-secondary)] border rounded-lg',
        'text-[var(--text-primary)] placeholder-[var(--text-muted)]',
        'focus:outline-none focus:ring-2 transition-all duration-200',
        variantClasses,
        className
      )}
      {...props}
    />
  )
}

