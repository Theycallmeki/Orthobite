import { apiClient } from './api'
import type { AxiosResponse } from 'axios'


export type AppointmentStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled' | 'no_show'

export interface AppointmentDoctorSummary {
  id: number
  full_name: string
  specialty: string
  photo_url: string | null
}

export interface AppointmentPatientSummary {
  id: number
  full_name: string
  email: string
  phone: string | null
}

export interface AppointmentResponse {
  id: number
  patient_id: number
  patient?: AppointmentPatientSummary
  doctor_id: number
  doctor?: AppointmentDoctorSummary
  start_time: string
  end_time: string
  status: AppointmentStatus
  reason_for_visit: string | null
  notes: string | null
  cancellation_reason: string | null
  created_at: string
  updated_at?: string | null
}

export interface AppointmentCreateRequest {
  doctor_id: number
  start_time: string
  end_time: string
  reason_for_visit?: string
  notes?: string
}

export interface AppointmentAdminCreateRequest extends AppointmentCreateRequest {
  patient_id: number
}

export interface AppointmentUpdate {
  doctor_id?: number
  start_time?: string
  end_time?: string
  reason_for_visit?: string
  notes?: string
}

export interface AppointmentStatusUpdate {
  status: AppointmentStatus
  cancellation_reason?: string
}

export interface AppointmentQueryParams {
  doctor_id?: number
  patient_id?: number
  status?: AppointmentStatus
  start_date?: string
  end_date?: string
  skip?: number
  limit?: number
}


export const appointmentsApi = {

  listAppointments(params?: AppointmentQueryParams): Promise<AxiosResponse<AppointmentResponse[]>> {
    return apiClient.get('/appointments/', { params })
  },


  createAppointment(
    payload: AppointmentCreateRequest | AppointmentAdminCreateRequest,
  ): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.post('/appointments/', payload)
  },


  getAppointmentById(id: number): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.get(`/appointments/${id}`)
  },


  updateAppointment(id: number, payload: AppointmentUpdate): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.patch(`/appointments/${id}`, payload)
  },


  updateAppointmentStatus(
    id: number,
    status: AppointmentStatus,
    cancellation_reason?: string,
  ): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.patch(`/appointments/${id}/status`, {
      status,
      cancellation_reason,
    })
  },


  cancelAppointment(id: number, reason?: string): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.post(`/appointments/${id}/cancel`, null, {
      params: { reason },
    })
  },
}

export default appointmentsApi
