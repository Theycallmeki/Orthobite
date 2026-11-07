import { apiClient } from './api'
import type { AxiosResponse } from 'axios'

// ===========================================================================
// Colocated TypeScript Types & Contracts
// ===========================================================================

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

// ===========================================================================
// Authentication & User Management API Endpoints
// ===========================================================================

export const authApi = {
  /**
   * Patient self-registration.
   * Endpoint: POST /auth/register
   */
  register(payload: RegisterRequest): Promise<AxiosResponse<UserResponse>> {
    return apiClient.post('/auth/register', payload)
  },

  /**
   * Authenticate user with identifier (email or username) and password.
   * Endpoint: POST /auth/login
   */
  login(payload: LoginRequest): Promise<AxiosResponse<TokenResponse>> {
    return apiClient.post('/auth/login', payload)
  },

  /**
   * Exchange a valid refresh token for a fresh access token pair.
   * Endpoint: POST /auth/refresh
   */
  refresh(refreshToken: string): Promise<AxiosResponse<TokenResponse>> {
    return apiClient.post('/auth/refresh', { refresh_token: refreshToken })
  },

  /**
   * Fetch authenticated user profile using the current session Bearer token.
   * Endpoint: GET /auth/me
   */
  getMe(): Promise<AxiosResponse<UserResponse>> {
    return apiClient.get('/auth/me')
  },

  /**
   * Admin-only: Register staff accounts (Doctor, Orthodontist, Secretary, Admin).
   * Endpoint: POST /users/staff
   */
  createStaff(payload: StaffCreateRequest): Promise<AxiosResponse<UserResponse>> {
    return apiClient.post('/users/staff', payload)
  },

  /**
   * Change current user's password.
   * Endpoint: POST /users/me/change-password
   */
  changePassword(payload: PasswordChangeRequest): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.post('/users/me/change-password', payload)
  },

  /**
   * Staff-only: List users with optional role and pagination filters.
   * Endpoint: GET /users/
   */
  listUsers(params?: UserQueryParams): Promise<AxiosResponse<UserResponse[]>> {
    return apiClient.get('/users/', { params })
  },

  /**
   * Staff-only: Retrieve user profile by ID.
   * Endpoint: GET /users/{id}
   */
  getUserById(id: number): Promise<AxiosResponse<UserResponse>> {
    return apiClient.get(`/users/${id}`)
  },
}

export default authApi

