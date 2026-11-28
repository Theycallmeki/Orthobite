import { apiClient } from './api'
import type { AxiosResponse } from 'axios'
import type { UserResponse } from './auth'

export interface PatientResponse {
  id: number
  user_id?: number
  date_of_birth?: string | null
  gender?: string | null
  phone?: string | null
  address?: string | null
  treatment_stage?: string
  assigned_doctor_id?: number | null
  bite_type?: string
  notes?: string | null
  user?: UserResponse
}

export const patientsApi = {
  listPatients(params?: {
    skip?: number
    limit?: number
    doctor_id?: number
  }): Promise<AxiosResponse<PatientResponse[]>> {
    return apiClient.get('/patients/', { params })
  },

  getPatientById(id: number): Promise<AxiosResponse<PatientResponse>> {
    return apiClient.get(`/patients/${id}`)
  },
}

export default patientsApi
