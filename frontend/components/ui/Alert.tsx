import React from 'react'
import { cn } from '@/lib/utils'

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'success' | 'error' | 'warning' | 'info' | 'mystical'
  icon?: React.ReactNode
}

const variantClasses = {
  default: 'bg-[var(--bg-secondary)] border-[var(--border-color)] text-[var(--text-primary)]',
  success: 'bg-green-500/20 border-green-500/50 text-green-400',
  error: 'bg-red-500/20 border-red-500/50 text-red-400',
  warning: 'bg-amber-500/20 border-amber-500/50 text-amber-400',
  info: 'bg-blue-500/20 border-blue-500/50 text-blue-400',
  mystical: 'bg-gradient-to-r from-purple-500/20 via-amber-500/20 to-purple-500/20 border-purple-500/30 text-purple-200 shadow-[0_0_15px_rgba(124,58,237,0.2)]',
}

export function Alert({
  children,
  className,
  variant = 'default',
  icon,
  ...props
}: AlertProps) {
  return (
    <div
      className={cn(
        'rounded-lg border px-4 py-3 break-words flex items-start gap-3',
        variantClasses[variant],
        className
      )}
      {...props}
    >
      {icon && <div className="flex-shrink-0 mt-0.5">{icon}</div>}
      <div className="flex-1">{children}</div>
    </div>
  )
}




