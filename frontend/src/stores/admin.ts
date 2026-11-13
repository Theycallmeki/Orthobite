import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  adminApi,
  type ClinicOverviewResponse,
  type MonthlyAppointmentStat,
  type RevenueReportResponse,
  type AuditLogResponse,
  type AuditLogListResponse,
  type AuditPurgeResponse,
  type AuditQueryParams,
  type NotificationLogResponse,
  type NotificationListResponse,
  type NotificationQueryParams,
} from '@/api/admin'

function extractError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || fallback
}

export const useAdminStore = defineStore('admin', () => {
  const overview = ref<ClinicOverviewResponse | null>(null)
  const appointmentStats = ref<MonthlyAppointmentStat[]>([])
  const revenueReport = ref<RevenueReportResponse | null>(null)
  const auditLogs = ref<AuditLogResponse[]>([])
  const auditTotal = ref<number>(0)
  const auditPage = ref<number>(1)
  const auditLimit = ref<number>(20)
  const selectedAuditLog = ref<AuditLogResponse | null>(null)
  const notificationLogs = ref<NotificationLogResponse[]>([])
  const notificationTotal = ref<number>(0)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  const netCollectionRate = computed<number>(() => {
    const report = revenueReport.value
    if (!report || report.grand_total_billed <= 0) {
      return 0
    }
    return Math.round((report.grand_total_collected / report.grand_total_billed) * 10000) / 100
  })

  const appointmentCompletionRate = computed<number>(() => {
    const ov = overview.value
    if (!ov) {
      return 0
    }
    const denominator =
      ov.total_completed_appointments +
      ov.total_active_appointments +
      ov.total_cancelled_appointments
    if (denominator <= 0) {
      return 0
    }
    return Math.round((ov.total_completed_appointments / denominator) * 10000) / 100
  })

  const topFailureAuditLogs = computed<AuditLogResponse[]>(() =>
    auditLogs.value.filter((log) => log.action === 'LOGIN_FAILED'),
  )

  const failedNotificationCount = computed<number>(
    () => notificationLogs.value.filter((n) => n.status === 'failed').length,
  )

  async function fetchOverview(): Promise<ClinicOverviewResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await adminApi.getOverview()
      overview.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch clinic overview')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAppointmentBreakdown(months: number = 12): Promise<MonthlyAppointmentStat[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await adminApi.getAppointmentsBreakdown(months)
      appointmentStats.value = response.data.months
      return response.data.months
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch appointment breakdown')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchRevenueReport(months: number = 12): Promise<RevenueReportResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await adminApi.getRevenueReport(months)
      revenueReport.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch revenue report')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchDashboardData(months: number = 12): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      const [overviewRes, apptRes, revenueRes] = await Promise.all([
        adminApi.getOverview(),
        adminApi.getAppointmentsBreakdown(months),
        adminApi.getRevenueReport(months),
      ])
      overview.value = overviewRes.data
      appointmentStats.value = apptRes.data.months
      revenueReport.value = revenueRes.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch admin dashboard data')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAuditLogs(params?: AuditQueryParams): Promise<AuditLogListResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await adminApi.listAuditLogs(params)
      auditLogs.value = response.data.items
      auditTotal.value = response.data.total
      auditPage.value = response.data.page
      auditLimit.value = response.data.limit
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load audit logs')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAuditLogById(id: number): Promise<AuditLogResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await adminApi.getAuditLogById(id)
      selectedAuditLog.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load audit log details')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function purgeAuditLogs(olderThanDays: number = 365): Promise<AuditPurgeResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await adminApi.purgeAuditLogs(olderThanDays)
      await fetchAuditLogs({ page: auditPage.value, limit: auditLimit.value })
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to purge audit logs')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchNotificationLogs(
    params?: NotificationQueryParams,
  ): Promise<NotificationListResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await adminApi.listNotificationLogs(params)
      notificationLogs.value = response.data.logs
      notificationTotal.value = response.data.total
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load notification logs')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    overview,
    appointmentStats,
    revenueReport,
    auditLogs,
    auditTotal,
    auditPage,
    auditLimit,
    selectedAuditLog,
    notificationLogs,
    notificationTotal,
    isLoading,
    error,
    netCollectionRate,
    appointmentCompletionRate,
    topFailureAuditLogs,
    failedNotificationCount,
    fetchOverview,
    fetchAppointmentBreakdown,
    fetchRevenueReport,
    fetchDashboardData,
    fetchAuditLogs,
    fetchAuditLogById,
    purgeAuditLogs,
    fetchNotificationLogs,
  }
})

