/**
 * API client for backend communication
 */

import axios from 'axios'

// API URL from environment variable, fallback to localhost for development
const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_URL = rawApiUrl.replace(/\/+$/, '') // Remove trailing slashes

// Debug logging (outputs to browser console)
if (typeof window !== 'undefined') {
  console.log('='.repeat(60))
  console.log('[API Client] API Configuration:')
  console.log('[API Client] NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL || '(undefined)')
  console.log('[API Client] API_URL:', API_URL)
  console.log('[API Client] NODE_ENV:', process.env.NODE_ENV)
  console.log('='.repeat(60))
  
  if (process.env.NODE_ENV === 'production' && !process.env.NEXT_PUBLIC_API_URL) {
    console.error('[API Client] WARNING: NEXT_PUBLIC_API_URL not set! Using fallback:', API_URL)
  }
  
  if (process.env.NODE_ENV === 'production' && API_URL.includes('localhost')) {
    console.error('[API Client] ERROR: API_URL points to localhost in production!')
  }
  
  if (API_URL.includes('guimingaiagentforfate-production')) {
    console.error('[API Client] ERROR: API_URL contains old domain!')
  }
}

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
apiClient.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else {
    // 如果没有access_token，清除Authorization header
    // 这样如果只有refresh_token，拦截器可以处理刷新
    delete config.headers.Authorization
  }
  return config
})

// Response interceptor to handle token refresh
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value?: any) => void
  reject: (error?: any) => void
}> = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => {
    // 更新最后活动时间（排除刷新token的请求，避免重复更新）
    if (typeof window !== 'undefined' && !response.config.url?.includes('/refresh')) {
      localStorage.setItem('last_activity', Date.now().toString())
    }
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // 如果是401错误且不是刷新token的请求，尝试刷新token
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/refresh') && !originalRequest.url?.includes('/signin')) {
      if (isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then(token => {
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`
              return apiClient(originalRequest)
            } else {
              return Promise.reject(new Error('Token refresh failed'))
            }
          })
          .catch(err => {
            return Promise.reject(err)
          })
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null
      
      if (!refreshToken) {
        // 没有refresh_token，清除所有token
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user_id')
          localStorage.removeItem('user_email')
          localStorage.removeItem('last_activity')
        }
        processQueue(error, null)
        isRefreshing = false
        return Promise.reject(error)
      }

      try {
        console.log('[API Interceptor] Attempting to refresh token...')
        
        // 检查是否30天未使用
        const lastActivity = typeof window !== 'undefined' ? localStorage.getItem('last_activity') : null
        if (lastActivity) {
          const daysSinceLastActivity = (Date.now() - parseInt(lastActivity)) / (1000 * 60 * 60 * 24)
          console.log('[API Interceptor] Days since last activity:', daysSinceLastActivity)
          if (daysSinceLastActivity > 30) {
            console.log('[API Interceptor] Session expired: 30 days of inactivity')
            // 30天未使用，清除token
            if (typeof window !== 'undefined') {
              localStorage.removeItem('access_token')
              localStorage.removeItem('refresh_token')
              localStorage.removeItem('user_id')
              localStorage.removeItem('user_email')
              localStorage.removeItem('last_activity')
            }
            processQueue(new Error('Session expired. Please login again.'), null)
            isRefreshing = false
            return Promise.reject(error)
          }
        }

        // 尝试刷新token（使用axios直接调用，避免触发拦截器）
        console.log('[API Interceptor] Calling refresh endpoint...')
        const refreshUrl = `${API_URL}/api/auth/refresh`
        console.log('[API Interceptor] Refresh URL:', refreshUrl)
        const refreshResponse = await axios.post(refreshUrl, { refresh_token: refreshToken }, {
          headers: {
            'Content-Type': 'application/json',
          }
        })
        
        const access_token = refreshResponse.data.access_token
        const newRefreshToken = refreshResponse.data.refresh_token
        
        if (!access_token || !newRefreshToken) {
          throw new Error('Invalid refresh response: missing tokens')
        }
        
        console.log('[API Interceptor] Token refreshed successfully')
        
        // 保存新的tokens
        if (typeof window !== 'undefined') {
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', newRefreshToken)
          localStorage.setItem('user_id', refreshResponse.data.user_id)
          localStorage.setItem('user_email', refreshResponse.data.email)
          localStorage.setItem('last_activity', Date.now().toString())
        }

        processQueue(null, access_token)
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        isRefreshing = false
        
        console.log('[API Interceptor] Retrying original request with new token')
        return apiClient(originalRequest)
      } catch (refreshError: any) {
        console.error('[API Interceptor] Token refresh failed:', {
          message: refreshError?.message,
          response: refreshError?.response?.data,
          status: refreshError?.response?.status
        })
        // 刷新失败，清除token
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user_id')
          localStorage.removeItem('user_email')
          localStorage.removeItem('last_activity')
        }
        processQueue(refreshError, null)
        isRefreshing = false
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// Auth API types
export interface SignUpRequest {
  email: string
  password: string
}

export interface SignInRequest {
  email: string
  password: string
}

export interface SignInResponse {
  access_token: string
  refresh_token: string
  user_id: string
  email: string
}

export interface SignUpResponse {
  id: string
  email: string
  created_at: string
  requires_email_confirmation: boolean
}

export interface UserResponse {
  id: string
  email: string
}

export interface UserProfile {
  id?: string
  user_id?: string
  age?: number
  gender?: string
  zodiac_sign?: string
  appearance_type?: string  // 保留字段，不再使用
  personality_type?: string
  preferred_source?: string
  preferred_spread?: string
  language?: string
  significator_priority?: string  // 'question_first' | 'personality_first'
  interpretation_model?: string  // 'deepseek' | 'gpt4omini' | 'gemini_2.5_pro'
}

export interface UserProfileCreate {
  age?: number
  gender?: string
  zodiac_sign?: string
  appearance_type?: string  // 保留字段，不再使用
  personality_type?: string
  preferred_source?: string
  preferred_spread?: string
  language?: string
  significator_priority?: string  // 'question_first' | 'personality_first'
  interpretation_model?: string  // 'deepseek' | 'gpt4omini' | 'gemini_2.5_pro'
}

// Tarot API types
export interface TarotReadingRequest {
  question: string
  user_selected_spread?: string
  use_rag_for_pattern?: boolean
  preferred_source?: string
  user_profile?: UserProfileCreate
  source_page?: string  // 占卜来源页面：home, manual-input, spread-selection
}

export interface TarotReadingResponse {
  reading_id?: string
  id?: string
  question: string
  question_analysis?: Record<string, any>
  spread_type: string
  significator?: Record<string, any>
  cards: Array<{
    card_id: string
    card_name_en?: string
    card_name_cn?: string
    name?: string
    suit?: string
    number?: number
    is_reversed: boolean
    position?: string
    position_order?: number
    image_url?: string
  }>
  interpretation?: string | Record<string, any>
  imagery_description?: string
  metadata?: Record<string, any>
  created_at?: string
}

// Auth API
export const authAPI = {
  signup: async (data: SignUpRequest): Promise<SignUpResponse> => {
    const response = await apiClient.post('/api/auth/signup', data)
    return response.data
  },

  signin: async (data: SignInRequest): Promise<SignInResponse> => {
    const response = await apiClient.post('/api/auth/signin', data)
    // Store tokens
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', response.data.access_token)
      localStorage.setItem('refresh_token', response.data.refresh_token)
      localStorage.setItem('user_id', response.data.user_id)
      localStorage.setItem('user_email', response.data.email)
      // 记录最后一次使用时间
      localStorage.setItem('last_activity', Date.now().toString())
    }
    return response.data
  },

  signout: async (): Promise<void> => {
    try {
      await apiClient.post('/api/auth/signout')
    } finally {
      // Clear tokens regardless of API call success
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user_id')
        localStorage.removeItem('user_email')
        localStorage.removeItem('last_activity')
      }
    }
  },

  getMe: async (): Promise<UserResponse> => {
    const response = await apiClient.get('/api/auth/me')
    // 更新最后活动时间
    if (typeof window !== 'undefined') {
      localStorage.setItem('last_activity', Date.now().toString())
    }
    return response.data
  },

  refreshToken: async (refreshToken: string): Promise<SignInResponse> => {
    // 直接使用axios调用，避免触发拦截器
    const refreshUrl = `${API_URL}/api/auth/refresh`
    const response = await axios.post(refreshUrl, { refresh_token: refreshToken }, {
      headers: {
        'Content-Type': 'application/json',
      }
    })
    // Store new tokens
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', response.data.access_token)
      localStorage.setItem('refresh_token', response.data.refresh_token)
      localStorage.setItem('user_id', response.data.user_id)
      localStorage.setItem('user_email', response.data.email)
      // 更新最后活动时间
      localStorage.setItem('last_activity', Date.now().toString())
    }
    return response.data
  },

  resendConfirmation: async (data: SignUpRequest): Promise<{ message: string; email?: string }> => {
    const response = await apiClient.post('/api/auth/resend-confirmation', data)
    return response.data
  },
}

// User Profile API
export const userAPI = {
  getProfile: async (): Promise<UserProfile> => {
    const response = await apiClient.get('/api/user/profile')
    return response.data
  },

  createProfile: async (data: UserProfileCreate): Promise<UserProfile> => {
    const response = await apiClient.post('/api/user/profile', data)
    return response.data
  },

  updateProfile: async (data: Partial<UserProfileCreate>): Promise<UserProfile> => {
    const response = await apiClient.put('/api/user/profile', data)
    return response.data
  },
}

// Tarot API
export const tarotAPI = {
  createReading: async (data: TarotReadingRequest): Promise<TarotReadingResponse> => {
    const response = await apiClient.post('/api/tarot/reading', data)
    return response.data
  },

  createReadingStream: async (
    data: TarotReadingRequest,
    onProgress: (step: string, progressData: any) => void,
    onInterpretation: (text: string) => void,
    onComplete: (result: any) => void,
    onError: (error: string) => void
  ): Promise<void> => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    // Ensure proper URL concatenation (avoid double slashes)
    const baseUrl = API_URL.replace(/\/+$/, '')
    const path = '/api/tarot/reading/stream'
    const streamUrl = `${baseUrl}${path}`
    
    // Debug logging (outputs to browser console)
    if (typeof window !== 'undefined') {
      console.log('[Tarot API] createReadingStream URL:', streamUrl)
    }

    const response = await fetch(streamUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unable to read error response')
      console.error('[Tarot API] createReadingStream failed:', {
        status: response.status,
        statusText: response.statusText,
        url: streamUrl,
        error: errorText,
        apiUrl: API_URL
      })
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('No reader available')
    }

    let buffer = ''
    let currentEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        
        if (line.startsWith('event: ')) {
          currentEvent = line.substring(7).trim()
        } else if (line.startsWith('data: ')) {
          const dataStr = line.substring(6).trim()
          if (!dataStr) continue
          
          try {
            const data = JSON.parse(dataStr)
            
            // 根据事件类型处理
            if (currentEvent === 'progress') {
              // progress事件的数据格式: { step: '...', ...other data }
              const step = data.step || 'unknown'
              onProgress(step, data)
            } else if (currentEvent === 'imagery_chunk') {
              // ⭐ 意象描述流式块
              onProgress('imagery_chunk', data)
            } else if (currentEvent === 'interpretation') {
              onInterpretation(data.text || '')
            } else if (currentEvent === 'error') {
              onError(data.error || 'Unknown error')
            } else if (currentEvent === 'complete') {
              onComplete(data)
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, dataStr)
          }
          
          currentEvent = '' // 重置事件类型
        }
      }
    }
  },

  getReading: async (readingId: string): Promise<TarotReadingResponse> => {
    const response = await apiClient.get(`/api/tarot/readings/${readingId}`)
    return response.data
  },

  listReadings: async (limit: number = 10, offset: number = 0) => {
    const response = await apiClient.get('/api/tarot/readings', {
      params: { limit, offset },
    })
    return response.data
  },
}

export interface ReadingListItem {
  id: string
  question: string
  spread_type: string
  source_page?: string
  created_at: string
  status: string
}

