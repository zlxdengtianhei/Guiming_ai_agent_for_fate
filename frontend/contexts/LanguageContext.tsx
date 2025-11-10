'use client'

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { Language, translations } from '@/lib/i18n'
import { useAuth } from '@/contexts/AuthContext'

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: keyof typeof translations.zh) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { profile } = useAuth()
  const [language, setLanguageState] = useState<Language>('zh')

  // Initialize language from user profile or localStorage
  useEffect(() => {
    const savedLanguage = typeof window !== 'undefined' 
      ? localStorage.getItem('language') as Language 
      : null
    
    if (profile?.language) {
      setLanguageState(profile.language as Language)
      if (typeof window !== 'undefined') {
        localStorage.setItem('language', profile.language)
      }
    } else if (savedLanguage && (savedLanguage === 'zh' || savedLanguage === 'en')) {
      setLanguageState(savedLanguage)
    }
  }, [profile])

  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
    if (typeof window !== 'undefined') {
      localStorage.setItem('language', lang)
    }
  }

  const t = (key: keyof typeof translations.zh): string => {
    return translations[language][key] || translations.zh[key] || key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}




