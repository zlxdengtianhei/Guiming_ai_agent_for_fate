import React from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'mystical' | 'gold'
  size?: 'sm' | 'md' | 'lg'
}

export function Button({
  children,
  className,
  variant = 'primary',
  size = 'md',
  ...props
}: ButtonProps) {
  const baseStyles = 'inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[var(--bg-primary)] disabled:opacity-50 disabled:cursor-not-allowed'
  
  const variants = {
    primary: 'bg-[var(--accent-blue)] text-white hover:bg-[var(--accent-blue-dark)] focus:ring-[var(--accent-blue)] hover:shadow-lg hover:shadow-blue-500/20',
    secondary: 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]',
    outline: 'border border-[var(--border-color)] bg-transparent text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]',
    ghost: 'bg-transparent text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]',
    mystical: 'bg-gradient-to-r from-purple-600 via-amber-500 to-purple-600 bg-size-200 bg-pos-0 hover:bg-pos-100 text-white border border-purple-500/30 shadow-[0_0_20px_rgba(124,58,237,0.3)] hover:shadow-[0_0_25px_rgba(124,58,237,0.5)] transition-all duration-500',
    gold: 'bg-gradient-to-r from-amber-500 to-amber-600 text-white border border-amber-500/30 shadow-[0_0_15px_rgba(245,158,11,0.3)] hover:shadow-[0_0_20px_rgba(245,158,11,0.5)] hover:from-amber-400 hover:to-amber-500',
  }
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  }
  
  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </button>
  )
}

