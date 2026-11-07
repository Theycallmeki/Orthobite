import { apiClient } from './api'
import type { AxiosResponse } from 'axios'


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
  available_slots: Record<string, string[]>
}

export interface AvailabilityRule {
  id?: number
  day_of_week: number
  start_time: string
  end_time: string
  slot_duration_minutes?: number
  is_active?: boolean
}

export interface SetAvailabilityRulesRequest {
  rules: AvailabilityRule[]
}

export interface TimeOff {
  id?: number
  doctor_id?: number
  start_datetime: string
  end_datetime: string
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


export const doctorsApi = {

  listPublicDoctors(): Promise<AxiosResponse<DoctorPublicResponse[]>> {
    return apiClient.get('/doctors/')
  },


  getDoctorById(doctorId: number): Promise<AxiosResponse<DoctorPublicResponse>> {
    return apiClient.get(`/doctors/${doctorId}`)
  },


  getDoctorAvailability(doctorId: number, month?: string): Promise<AxiosResponse<DoctorAvailabilityResponse>> {
    return apiClient.get(`/doctors/${doctorId}/availability`, { params: { month } })
  },


  getMyDoctorProfile(): Promise<AxiosResponse<DoctorPublicResponse>> {
    return apiClient.get('/doctors/me/profile')
  },


  updateMyDoctorProfile(payload: DoctorProfileUpdate): Promise<AxiosResponse<DoctorPublicResponse>> {
    return apiClient.patch('/doctors/me/profile', payload)
  },


  getMyAvailabilityRules(): Promise<AxiosResponse<AvailabilityRule[]>> {
    return apiClient.get('/doctors/me/availability')
  },


  setMyAvailabilityRules(rules: AvailabilityRule[]): Promise<AxiosResponse<AvailabilityRule[]>> {
    return apiClient.put('/doctors/me/availability', { rules })
  },


  createTimeOff(payload: TimeOffCreate): Promise<AxiosResponse<TimeOff>> {
    return apiClient.post('/doctors/me/time-off', payload)
  },


  listMyTimeOff(): Promise<AxiosResponse<TimeOff[]>> {
    return apiClient.get('/doctors/me/time-off')
  },
}

export default doctorsApi
