import { apiClient } from './api'
import type { AxiosResponse } from 'axios'


export type AuditAction = 'CREATE' | 'READ' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'LOGIN_FAILED'

export type NotificationType = 'booking_confirmation' | 'reminder_24h' | 'reminder_2h' | 'cancellation_notice'

export type NotificationStatus = 'pending' | 'sent' | 'failed'


export interface AuditLogResponse {
  id: number
  actor_id: number | null
  action: AuditAction
  resource: string
  resource_id: number | null
  ip_address: string | null
  extra: Record<string, unknown> | null
  timestamp: string
}

export interface AuditLogListResponse {
  total: number
  page: number
  limit: number
  items: AuditLogResponse[]
}

export interface AuditPurgeResponse {
  deleted_count: number
  cutoff_date: string
  message: string
}

export interface AuditQueryParams {
  actor_id?: number
  action?: AuditAction
  resource?: string
  date_from?: string
  date_to?: string
  page?: number
  limit?: number
}


export interface ClinicOverviewResponse {
  total_patients: number
  total_doctors: number
  total_active_appointments: number
  total_completed_appointments: number
  total_pending_appointments: number
  total_cancelled_appointments: number
}

export interface MonthlyAppointmentStat {
  month: string
  total: number
  confirmed: number
  completed: number
  cancelled: number
  no_show: number
  pending: number
}

export interface AppointmentBreakdownResponse {
  months: MonthlyAppointmentStat[]
}

export interface MonthlyRevenueStat {
  month: string
  revenue_collected: number
  outstanding_balance: number
  total_billed: number
}

export interface RevenueReportResponse {
  months: MonthlyRevenueStat[]
  grand_total_billed: number
  grand_total_collected: number
  grand_outstanding: number
}


export interface NotificationLogResponse {
  id: number
  appointment_id: number
  recipient: string
  type: NotificationType
  status: NotificationStatus
  subject: string | null
  brevo_message_id?: string | null
  error_message: string | null
  scheduled_for: string | null
  sent_at: string | null
  created_at: string
}

export interface NotificationListResponse {
  total: number
  logs: NotificationLogResponse[]
}

export interface NotificationQueryParams {
  appointment_id?: number
  type?: NotificationType
  status?: NotificationStatus
  skip?: number
  limit?: number
}


export const adminApi = {


  getOverview(): Promise<AxiosResponse<ClinicOverviewResponse>> {
    return apiClient.get('/admin/analytics/overview')
  },


  getAppointmentsBreakdown(months: number = 12): Promise<AxiosResponse<AppointmentBreakdownResponse>> {
    return apiClient.get('/admin/analytics/appointments', { params: { months } })
  },


  getRevenueReport(months: number = 12): Promise<AxiosResponse<RevenueReportResponse>> {
    return apiClient.get('/admin/analytics/revenue', { params: { months } })
  },


  listAuditLogs(params?: AuditQueryParams): Promise<AxiosResponse<AuditLogListResponse>> {
    return apiClient.get('/admin/audit/logs', { params })
  },


  getAuditLogById(id: number): Promise<AxiosResponse<AuditLogResponse>> {
    return apiClient.get(`/admin/audit/logs/${id}`)
  },


  purgeAuditLogs(olderThanDays: number = 365): Promise<AxiosResponse<AuditPurgeResponse>> {
    return apiClient.delete('/admin/audit/purge', {
      params: { older_than_days: olderThanDays },
    })
  },


  listNotificationLogs(
    params?: NotificationQueryParams,
  ): Promise<AxiosResponse<NotificationListResponse>> {
    return apiClient.get('/notifications/logs', { params })
  },
}

export default adminApi
