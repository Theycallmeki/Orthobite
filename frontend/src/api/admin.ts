import { apiClient } from './api'
import type { AxiosResponse } from 'axios'

// ===========================================================================
// Colocated TypeScript Types & Contracts
// ===========================================================================

export type AuditAction = 'CREATE' | 'READ' | 'UPDATE' | 'DELETE' | 'LOGIN' | 'LOGIN_FAILED'

export type NotificationType = 'booking_confirmation' | 'reminder_24h' | 'reminder_2h' | 'cancellation_notice'

export type NotificationStatus = 'pending' | 'sent' | 'failed'

// Audit Logging Types
export interface AuditLogResponse {
  id: number
  actor_id: number | null
  action: AuditAction
  resource: string
  resource_id: number | null
  ip_address: string | null
  extra: Record<string, unknown> | null
  timestamp: string // ISO-8601 string
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
  date_from?: string // ISO string
  date_to?: string // ISO string
  page?: number
  limit?: number
}

// Analytics Dashboard Types
export interface ClinicOverviewResponse {
  total_patients: number
  total_doctors: number
  total_active_appointments: number
  total_completed_appointments: number
  total_pending_appointments: number
  total_cancelled_appointments: number
}

export interface MonthlyAppointmentStat {
  month: string // "YYYY-MM"
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
  month: string // "YYYY-MM"
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

// Notification Logs Types
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

// ===========================================================================
// Admin Analytics, Compliance & Notifications API Endpoints
// ===========================================================================

export const adminApi = {
  // -------------------------------------------------------------------------
  // Dashboard Analytics
  // -------------------------------------------------------------------------

  /**
   * High-level dashboard counters: total active patients, doctors, and appointment status breakdown.
   * Admin only.
   * Endpoint: GET /admin/analytics/overview
   */
  getOverview(): Promise<AxiosResponse<ClinicOverviewResponse>> {
    return apiClient.get('/admin/analytics/overview')
  },

  /**
   * Per-month appointment volume broken down by status (confirmed, completed, etc.).
   * Feeds analytics bar and line charts.
   * Admin only.
   * Endpoint: GET /admin/analytics/appointments
   */
  getAppointmentsBreakdown(months: number = 12): Promise<AxiosResponse<AppointmentBreakdownResponse>> {
    return apiClient.get('/admin/analytics/appointments', { params: { months } })
  },

  /**
   * Monthly revenue collected vs total billed with net outstanding balance.
   * Feeds the financial health chart on the admin dashboard.
   * Admin only.
   * Endpoint: GET /admin/analytics/revenue
   */
  getRevenueReport(months: number = 12): Promise<AxiosResponse<RevenueReportResponse>> {
    return apiClient.get('/admin/analytics/revenue', { params: { months } })
  },

  // -------------------------------------------------------------------------
  // DPA 2012 Compliance Audit Trail
  // -------------------------------------------------------------------------

  /**
   * Paginated immutable audit trail with filters (actor, action, resource, date range).
   * Satisfies Data Privacy Act of 2012 compliance.
   * Admin only.
   * Endpoint: GET /admin/audit/logs
   */
  listAuditLogs(params?: AuditQueryParams): Promise<AxiosResponse<AuditLogListResponse>> {
    return apiClient.get('/admin/audit/logs', { params })
  },

  /**
   * Retrieve a specific audit log entry by ID.
   * Admin only.
   * Endpoint: GET /admin/audit/logs/{id}
   */
  getAuditLogById(id: number): Promise<AxiosResponse<AuditLogResponse>> {
    return apiClient.get(`/admin/audit/logs/${id}`)
  },

  /**
   * Permanently purge audit logs older than N days (minimum 30 days per retention policy).
   * Admin only.
   * Endpoint: DELETE /admin/audit/purge
   */
  purgeAuditLogs(olderThanDays: number = 365): Promise<AxiosResponse<AuditPurgeResponse>> {
    return apiClient.delete('/admin/audit/purge', {
      params: { older_than_days: olderThanDays },
    })
  },

  // -------------------------------------------------------------------------
  // Notification Dispatch Audit
  // -------------------------------------------------------------------------

  /**
   * List transactional email dispatch logs from Brevo (confirmations, 24h reminders, cancellations).
   * Staff/Admin only.
   * Endpoint: GET /notifications/logs
   */
  listNotificationLogs(
    params?: NotificationQueryParams,
  ): Promise<AxiosResponse<NotificationListResponse>> {
    return apiClient.get('/notifications/logs', { params })
  },
}

export default adminApi

