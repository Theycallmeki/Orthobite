import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserResponse, type LoginRequest, type RegisterRequest, type PasswordChangeRequest, type TokenResponse } from '@/api/auth'
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from '@/api/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserResponse | null>(null)
  const token = ref<string | null>(getAccessToken())
  const refreshToken = ref<string | null>(getRefreshToken())
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed<boolean>(() => !!token.value && !!user.value)
  const role = computed(() => user.value?.role || null)
  const isAdmin = computed<boolean>(() => user.value?.role === 'admin')
  const isDoctor = computed<boolean>(() => user.value?.role === 'doctor' || user.value?.role === 'orthodontist')
  const isSecretary = computed<boolean>(() => user.value?.role === 'secretary')
  const isStaff = computed<boolean>(() => ['admin', 'doctor', 'orthodontist', 'secretary'].includes(user.value?.role || ''))
  const isPatient = computed<boolean>(() => user.value?.role === 'patient')

  async function login(credentials: LoginRequest): Promise<TokenResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.login(credentials)
      const data = response.data
      token.value = data.access_token
      refreshToken.value = data.refresh_token
      setTokens(data.access_token, data.refresh_token)
      await fetchCurrentUser()
      return data
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed'
      error.value = message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function register(payload: RegisterRequest): Promise<UserResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.register(payload)
      return response.data
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Registration failed'
      error.value = message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchCurrentUser(): Promise<UserResponse | null> {
    if (!token.value) {
      user.value = null
      return null
    }
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.getMe()
      user.value = response.data
      return response.data
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 401) {
        logout()
      }
      return null
    } finally {
      isLoading.value = false
    }
  }

  function logout(): void {
    user.value = null
    token.value = null
    refreshToken.value = null
    clearTokens()
  }

  async function changePassword(payload: PasswordChangeRequest): Promise<{ message: string }> {
    isLoading.value = true
    error.value = null
    try {
      const response = await authApi.changePassword(payload)
      return response.data
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Password change failed'
      error.value = message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function init(): Promise<void> {
    if (token.value && !user.value) {
      await fetchCurrentUser()
    }
  }

  return {
    user,
    token,
    refreshToken,
    isLoading,
    error,
    isAuthenticated,
    role,
    isAdmin,
    isDoctor,
    isSecretary,
    isStaff,
    isPatient,
    login,
    register,
    fetchCurrentUser,
    logout,
    changePassword,
    init,
  }
})

