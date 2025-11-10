import React from 'react'
import { cn } from '@/lib/utils'

interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
  centered?: boolean
}

const sizeClasses = {
  sm: 'max-w-2xl',
  md: 'max-w-4xl',
  lg: 'max-w-6xl',
  xl: 'max-w-7xl',
  full: 'max-w-full',
}

export function Container({
  children,
  className,
  size = 'md',
  centered = true,
  ...props
}: ContainerProps) {
  return (
    <div
      className={cn(
        'w-full px-4 sm:px-6 lg:px-8',
        centered && 'mx-auto',
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}




