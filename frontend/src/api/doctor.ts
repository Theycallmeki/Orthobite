import { apiClient } from './api'
import type { AxiosResponse } from 'axios'

// ===========================================================================
// Colocated TypeScript Types & Contracts
// ===========================================================================

export interface DoctorPublicResponse {
  id: number
  user_id: number
  full_name: string
  specialty: string
  bio: string | null
  photo_url: string | null
  years_of_experience: number
  education: string | null
  consultation_fee: number | string
  is_accepting_patients: boolean
}

export interface DoctorAvailabilityResponse {
  doctor_id: number
  doctor_name: string
  month: string
  slot_duration_minutes: number
  available_slots: Record<string, string[]> // Mapping of "YYYY-MM-DD" -> ["09:00:00", "09:30:00", ...]
}

export interface AvailabilityRule {
  id?: number
  day_of_week: number // 0 = Monday, ..., 6 = Sunday
  start_time: string // "09:00:00"
  end_time: string // "17:00:00"
  slot_duration_minutes?: number
  is_active?: boolean
}

export interface SetAvailabilityRulesRequest {
  rules: AvailabilityRule[]
}

export interface TimeOff {
  id?: number
  doctor_id?: number
  start_datetime: string // ISO-8601 string
  end_datetime: string // ISO-8601 string
  reason?: string | null
  created_at?: string
}

export interface TimeOffCreate {
  start_datetime: string
  end_datetime: string
  reason?: string
}

export interface DoctorProfileUpdate {
  specialty?: string
  bio?: string
  photo_url?: string
  years_of_experience?: number
  education?: string
  consultation_fee?: number | string
  is_accepting_patients?: boolean
}

// ===========================================================================
// Doctor & Availability API Endpoints
// ===========================================================================

export const doctorsApi = {
  /**
   * Public: List all active doctors accepting patients for the homepage carousel.
   * Endpoint: GET /doctors/
   */
  listPublicDoctors(): Promise<AxiosResponse<DoctorPublicResponse[]>> {
    return apiClient.get('/doctors/')
  },

  /**
   * Public: Get doctor public profile by ID.
   * Endpoint: GET /doctors/{doctorId}
   */
  getDoctorById(doctorId: number): Promise<AxiosResponse<DoctorPublicResponse>> {
    return apiClient.get(`/doctors/${doctorId}`)
  },

  /**
   * Public: Retrieve real-time available 30-min time slots for calendar booking.
   * Endpoint: GET /doctors/{doctorId}/availability?month=YYYY-MM
   */
  getDoctorAvailability(doctorId: number, month?: string): Promise<AxiosResponse<DoctorAvailabilityResponse>> {
    return apiClient.get(`/doctors/${doctorId}/availability`, { params: { month } })
  },

  /**
   * Doctor-only: Retrieve logged-in doctor's own profile details.
   * Endpoint: GET /doctors/me/profile
   */
  getMyDoctorProfile(): Promise<AxiosResponse<DoctorPublicResponse>> {
    return apiClient.get('/doctors/me/profile')
  },

  /**
   * Doctor-only: Update profile bio, photo, fee, or patient acceptance status.
   * Endpoint: PATCH /doctors/me/profile
   */
  updateMyDoctorProfile(payload: DoctorProfileUpdate): Promise<AxiosResponse<DoctorPublicResponse>> {
    return apiClient.patch('/doctors/me/profile', payload)
  },

  /**
   * Doctor-only: Query weekly recurring schedule rules (Monday to Sunday).
   * Endpoint: GET /doctors/me/availability
   */
  getMyAvailabilityRules(): Promise<AxiosResponse<AvailabilityRule[]>> {
    return apiClient.get('/doctors/me/availability')
  },

  /**
   * Doctor-only: Set or replace weekly recurring availability rules.
   * Endpoint: PUT /doctors/me/availability
   */
  setMyAvailabilityRules(rules: AvailabilityRule[]): Promise<AxiosResponse<AvailabilityRule[]>> {
    return apiClient.put('/doctors/me/availability', { rules })
  },

  /**
   * Doctor-only: Schedule a leave or blocked time-off range.
   * Endpoint: POST /doctors/me/time-off
   */
  createTimeOff(payload: TimeOffCreate): Promise<AxiosResponse<TimeOff>> {
    return apiClient.post('/doctors/me/time-off', payload)
  },

  /**
   * Doctor-only: List scheduled leaves and blocked ranges.
   * Endpoint: GET /doctors/me/time-off
   */
  listMyTimeOff(): Promise<AxiosResponse<TimeOff[]>> {
    return apiClient.get('/doctors/me/time-off')
  },
}

export default doctorsApi

