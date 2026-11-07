import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

// ---------------------------------------------------------------------------
// Server Connection & Base URL Configuration
// ---------------------------------------------------------------------------
// In development, Vite proxy forwards requests (/auth, /doctors, etc.) to backend http://localhost:8000.
// In production or custom env, VITE_API_BASE_URL can override the target.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL || ''

// ---------------------------------------------------------------------------
// Token Storage Helpers
// ---------------------------------------------------------------------------
export const TOKEN_KEYS = {
  ACCESS: 'access_token',
  REFRESH: 'refresh_token',
} as const

export const getAccessToken = (): string | null => localStorage.getItem(TOKEN_KEYS.ACCESS)
export const getRefreshToken = (): string | null => localStorage.getItem(TOKEN_KEYS.REFRESH)

export const setTokens = (accessToken: string, refreshToken?: string): void => {
  localStorage.setItem(TOKEN_KEYS.ACCESS, accessToken)
  if (refreshToken) {
    localStorage.setItem(TOKEN_KEYS.REFRESH, refreshToken)
  }
}

export const clearTokens = (): void => {
  localStorage.removeItem(TOKEN_KEYS.ACCESS)
  localStorage.removeItem(TOKEN_KEYS.REFRESH)
}

// ---------------------------------------------------------------------------
// Core Axios Client
// ---------------------------------------------------------------------------
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ---------------------------------------------------------------------------
// Request Interceptor: Attach JWT Bearer Token
// ---------------------------------------------------------------------------
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

// ---------------------------------------------------------------------------
// Response Interceptor: 401 Unauthorized Auto-Refresh Queue
// ---------------------------------------------------------------------------
let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else if (token) {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      // Do not attempt refresh on login or refresh endpoints themselves
      if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            return apiClient(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        isRefreshing = false
        clearTokens()
        return Promise.reject(error)
      }

      try {
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newAccessToken = response.data.access_token
        const newRefreshToken = response.data.refresh_token

        setTokens(newAccessToken, newRefreshToken)
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`
        processQueue(null, newAccessToken)

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        }
        return apiClient(originalRequest)
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        clearTokens()
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

// ---------------------------------------------------------------------------
// WebSocket Connection Helper
// ---------------------------------------------------------------------------
export const getWebSocketUrl = (path: string = '/ws/chat'): string => {
  const token = getAccessToken()
  const tokenParam = token ? `?token=${encodeURIComponent(token)}` : ''

  if (API_BASE_URL.startsWith('http://')) {
    return API_BASE_URL.replace('http://', 'ws://') + path + tokenParam
  }
  if (API_BASE_URL.startsWith('https://')) {
    return API_BASE_URL.replace('https://', 'wss://') + path + tokenParam
  }

  // Relative to current host (Vite dev server proxy handles /ws to backend ws://localhost:8000)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${path}${tokenParam}`
}

export default apiClient
