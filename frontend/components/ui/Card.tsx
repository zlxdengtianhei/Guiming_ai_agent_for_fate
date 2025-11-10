import React from 'react'
import { cn } from '@/lib/utils'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'mystical' | 'glow'
  glowColor?: 'gold' | 'purple' | 'cyan' | 'blue'
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', glowColor = 'gold', ...props }, ref) => {
    const glowClasses = {
      gold: 'hover:shadow-[0_0_20px_rgba(245,158,11,0.3)] border-amber-500/20',
      purple: 'hover:shadow-[0_0_20px_rgba(124,58,237,0.3)] border-purple-500/20',
      cyan: 'hover:shadow-[0_0_20px_rgba(6,182,212,0.3)] border-cyan-500/20',
      blue: 'hover:shadow-[0_0_20px_rgba(59,130,246,0.3)] border-blue-500/20',
    }

    const variantClasses = {
      default: 'bg-[var(--bg-secondary)] border-[var(--border-color)]',
      mystical: 'bg-gradient-to-br from-[var(--bg-secondary)] via-[var(--bg-tertiary)] to-[var(--bg-secondary)] border-amber-500/30',
      glow: `bg-[var(--bg-secondary)] border ${glowClasses[glowColor]} transition-all duration-300`,
    }

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-xl border p-6 shadow-lg transition-all duration-300',
          variantClasses[variant],
          className
        )}
        {...props}
      />
    )
  }
)
Card.displayName = 'Card'

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex flex-col space-y-1.5 pb-4', className)}
    {...props}
  />
))
CardHeader.displayName = 'CardHeader'

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      'text-2xl font-semibold leading-none tracking-tight text-[var(--text-primary)]',
      className
    )}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn('text-sm text-[var(--text-secondary)]', className)}
    {...props}
  />
))
CardDescription.displayName = 'CardDescription'

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('pt-0', className)} {...props} />
))
CardContent.displayName = 'CardContent'

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('flex items-center pt-4', className)}
    {...props}
  />
))
CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }




