import { apiClient } from './api'
import type { AxiosResponse } from 'axios'


export type UserRole = 'admin' | 'doctor' | 'orthodontist' | 'secretary' | 'patient'

export interface UserResponse {
  id: number
  username: string
  full_name: string
  email: string
  phone: string | null
  role: UserRole
  avatar_url: string | null
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user_id: number
  username: string
  full_name: string
  role: UserRole
}

export interface RegisterRequest {
  full_name: string
  username: string
  email: string
  phone?: string
  password: string
}

export interface LoginRequest {
  identifier: string
  password: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface StaffCreateRequest {
  full_name: string
  username: string
  email: string
  phone?: string
  password: string
  role: 'doctor' | 'orthodontist' | 'secretary' | 'admin'
}

export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

export interface UserQueryParams {
  skip?: number
  limit?: number
  role?: UserRole
}


export const authApi = {

  register(payload: RegisterRequest): Promise<AxiosResponse<UserResponse>> {
    return apiClient.post('/auth/register', payload)
  },


  login(payload: LoginRequest): Promise<AxiosResponse<TokenResponse>> {
    return apiClient.post('/auth/login', payload)
  },


  refresh(refreshToken: string): Promise<AxiosResponse<TokenResponse>> {
    return apiClient.post('/auth/refresh', { refresh_token: refreshToken })
  },


  getMe(): Promise<AxiosResponse<UserResponse>> {
    return apiClient.get('/auth/me')
  },


  createStaff(payload: StaffCreateRequest): Promise<AxiosResponse<UserResponse>> {
    return apiClient.post('/users/staff', payload)
  },


  changePassword(payload: PasswordChangeRequest): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.post('/users/me/change-password', payload)
  },


  listUsers(params?: UserQueryParams): Promise<AxiosResponse<UserResponse[]>> {
    return apiClient.get('/users/', { params })
  },


  getUserById(id: number): Promise<AxiosResponse<UserResponse>> {
    return apiClient.get(`/users/${id}`)
  },
}

export default authApi
