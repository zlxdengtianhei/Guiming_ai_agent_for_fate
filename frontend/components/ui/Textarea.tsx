import React from 'react'
import { cn } from '@/lib/utils'

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

export function Textarea({ className, ...props }: TextareaProps) {
  return (
    <textarea
      className={cn(
        'w-full px-4 py-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg',
        'text-[var(--text-primary)] placeholder-[var(--text-muted)]',
        'focus:outline-none focus:ring-2 focus:ring-[var(--accent-blue)] focus:border-transparent',
        'transition-all duration-200 resize-none',
        className
      )}
      {...props}
    />
  )
}




