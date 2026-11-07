import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

// ---------------------------------------------------------------------------
// Axios Instance Configuration
// ---------------------------------------------------------------------------
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

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
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error),
)

// ---------------------------------------------------------------------------
// Response Interceptor: Handle 401 Unauthorized & Token Refresh
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
      if (originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
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

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        isRefreshing = false
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        return Promise.reject(error)
      }

      try {
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newAccessToken = response.data.access_token
        const newRefreshToken = response.data.refresh_token

        localStorage.setItem('access_token', newAccessToken)
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken)
        }

        apiClient.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`
        processQueue(null, newAccessToken)

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        }
        return apiClient(originalRequest)
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

// ---------------------------------------------------------------------------
// Domain API Modules
// ---------------------------------------------------------------------------

// Authentication & Profile
export const authApi = {
  register: (payload: { full_name: string; username: string; email: string; phone?: string; password: string }) =>
    apiClient.post('/auth/register', payload),

  login: (payload: { identifier: string; password: string }) =>
    apiClient.post('/auth/login', payload),

  refresh: (refreshToken: string) =>
    apiClient.post('/auth/refresh', { refresh_token: refreshToken }),

  getMe: () =>
    apiClient.get('/auth/me'),

  createStaff: (payload: { full_name: string; username: string; email: string; phone?: string; password: string; role: string }) =>
    apiClient.post('/users/staff', payload),

  changePassword: (payload: { old_password: string; new_password: string }) =>
    apiClient.post('/users/me/change-password', payload),
}

// Doctors & Availability
export const doctorsApi = {
  listPublicDoctors: () =>
    apiClient.get('/doctors/'),

  getDoctorById: (doctorId: number) =>
    apiClient.get(`/doctors/${doctorId}`),

  getDoctorAvailability: (doctorId: number, month?: string) =>
    apiClient.get(`/doctors/${doctorId}/availability`, { params: { month } }),

  getMyDoctorProfile: () =>
    apiClient.get('/doctors/me/profile'),

  updateMyDoctorProfile: (payload: Record<string, unknown>) =>
    apiClient.patch('/doctors/me/profile', payload),

  getMyAvailabilityRules: () =>
    apiClient.get('/doctors/me/availability'),

  setMyAvailabilityRules: (rules: Array<Record<string, unknown>>) =>
    apiClient.put('/doctors/me/availability', { rules }),

  createTimeOff: (payload: { start_datetime: string; end_datetime: string; reason?: string }) =>
    apiClient.post('/doctors/me/time-off', payload),

  listMyTimeOff: () =>
    apiClient.get('/doctors/me/time-off'),
}

// Appointments
export const appointmentsApi = {
  listAppointments: (params?: { doctor_id?: number; patient_id?: number; status?: string; start_date?: string; end_date?: string }) =>
    apiClient.get('/appointments/', { params }),

  createAppointment: (payload: { doctor_id: number; start_time: string; end_time: string; reason_for_visit?: string; notes?: string }) =>
    apiClient.post('/appointments/', payload),

  getAppointmentById: (id: number) =>
    apiClient.get(`/appointments/${id}`),

  updateAppointmentStatus: (id: number, status: string, reason?: string) =>
    apiClient.patch(`/appointments/${id}/status`, { status, cancellation_reason: reason }),

  cancelAppointment: (id: number, reason?: string) =>
    apiClient.post(`/appointments/${id}/cancel`, null, { params: { reason } }),
}

// Digital Patient Records & Financial Ledger
export const recordsApi = {
  getToothChartTemplate: () =>
    apiClient.get('/records/tooth-chart/template'),

  uploadSignatureFile: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/records/signatures/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  saveSignatureBase64: (signatureData: string) =>
    apiClient.post('/records/signatures/base64', { signature_data: signatureData }),

  createTreatmentRecord: (payload: {
    patient_id: number
    doctor_id?: number
    treatment_name: string
    tooth_number?: string
    value_of_work: number | string
    date?: string
    notes?: string
    signature_url?: string
    signature_base64?: string
  }) => apiClient.post('/records/', payload),

  getTreatmentRecord: (recordId: number) =>
    apiClient.get(`/records/${recordId}`),

  updateTreatmentRecord: (recordId: number, payload: Record<string, unknown>) =>
    apiClient.patch(`/records/${recordId}`, payload),

  deleteTreatmentRecord: (recordId: number) =>
    apiClient.delete(`/records/${recordId}`),

  createPaymentForRecord: (recordId: number, payload: { patient_id?: number; amount: number | string; method: string; receipt_no?: string; notes?: string }) =>
    apiClient.post(`/records/${recordId}/payments`, payload),

  createGeneralPayment: (payload: { patient_id: number; amount: number | string; method: string; receipt_no?: string; notes?: string }) =>
    apiClient.post('/records/payments', payload),

  getPatientLedger: (patientId: number) =>
    apiClient.get(`/records/patient/${patientId}/ledger`),
}

// Live Chat & Conversations
export const chatApi = {
  listConversations: () =>
    apiClient.get('/chat/conversations'),

  createConversation: (patientId?: number) =>
    apiClient.post('/chat/conversations', { patient_id: patientId }),

  getConversationHistory: (conversationId: number, params?: { limit?: number; before_id?: number }) =>
    apiClient.get(`/chat/conversations/${conversationId}/history`, { params }),

  markAsRead: (conversationId: number) =>
    apiClient.post(`/chat/conversations/${conversationId}/read`),
}

// Admin Audit Logging (DPA Compliance)
export const auditApi = {
  listLogs: (params?: { actor_id?: number; action?: string; resource?: string; date_from?: string; date_to?: string; page?: number; limit?: number }) =>
    apiClient.get('/admin/audit/logs', { params }),

  getLogById: (logId: number) =>
    apiClient.get(`/admin/audit/logs/${logId}`),

  purgeOldLogs: (olderThanDays: number = 365) =>
    apiClient.delete('/admin/audit/purge', { params: { older_than_days: olderThanDays } }),
}

// Admin Dashboard Analytics
export const analyticsApi = {
  getOverview: () =>
    apiClient.get('/admin/analytics/overview'),

  getAppointmentsBreakdown: (months: number = 12) =>
    apiClient.get('/admin/analytics/appointments', { params: { months } }),

  getRevenueReport: (months: number = 12) =>
    apiClient.get('/admin/analytics/revenue', { params: { months } }),
}

// Notifications
export const notificationsApi = {
  listLogs: (params?: { appointment_id?: number; type?: string; status?: string; skip?: number; limit?: number }) =>
    apiClient.get('/notifications/logs', { params }),
}

// Export default Axios instance for custom queries
export default apiClient

