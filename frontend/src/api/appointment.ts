import { apiClient } from './api'
import type { AxiosResponse } from 'axios'

// ===========================================================================
// Colocated TypeScript Types & Contracts
// ===========================================================================

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
  start_time: string // ISO-8601 string
  end_time: string // ISO-8601 string
  status: AppointmentStatus
  reason_for_visit: string | null
  notes: string | null
  cancellation_reason: string | null
  created_at: string
  updated_at?: string | null
}

export interface AppointmentCreateRequest {
  doctor_id: number
  start_time: string // ISO-8601 string
  end_time: string // ISO-8601 string
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
  start_date?: string // YYYY-MM-DD
  end_date?: string // YYYY-MM-DD
  skip?: number
  limit?: number
}

// ===========================================================================
// Appointment Booking & Scheduling API Endpoints
// ===========================================================================

export const appointmentsApi = {
  /**
   * Query appointments with role-aware filtering.
   * Patients view their own, doctors view their schedule, staff can filter by any parameter.
   * Endpoint: GET /appointments/
   */
  listAppointments(params?: AppointmentQueryParams): Promise<AxiosResponse<AppointmentResponse[]>> {
    return apiClient.get('/appointments/', { params })
  },

  /**
   * Book an appointment. Validates slot conflicts and doctor availability rules.
   * Patients book for themselves; staff/admin can supply a patient_id.
   * Endpoint: POST /appointments/
   */
  createAppointment(
    payload: AppointmentCreateRequest | AppointmentAdminCreateRequest,
  ): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.post('/appointments/', payload)
  },

  /**
   * Retrieve appointment details by ID.
   * Accessible by the patient, the doctor, or staff.
   * Endpoint: GET /appointments/{id}
   */
  getAppointmentById(id: number): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.get(`/appointments/${id}`)
  },

  /**
   * Update clinical notes, reason, or reschedule appointment time.
   * Staff only.
   * Endpoint: PATCH /appointments/{id}
   */
  updateAppointment(id: number, payload: AppointmentUpdate): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.patch(`/appointments/${id}`, payload)
  },

  /**
   * Transition appointment workflow status (confirmed, completed, cancelled, no_show).
   * Staff or assigned doctor only.
   * Endpoint: PATCH /appointments/{id}/status
   */
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

  /**
   * Cancel an appointment with a cancellation reason.
   * Can be initiated by patient (own appointment) or staff.
   * Endpoint: POST /appointments/{id}/cancel
   */
  cancelAppointment(id: number, reason?: string): Promise<AxiosResponse<AppointmentResponse>> {
    return apiClient.post(`/appointments/${id}/cancel`, null, {
      params: { reason },
    })
  },
}

export default appointmentsApi

