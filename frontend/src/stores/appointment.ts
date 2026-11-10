import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  appointmentsApi,
  type AppointmentResponse,
  type AppointmentStatus,
  type AppointmentCreateRequest,
  type AppointmentAdminCreateRequest,
  type AppointmentUpdate,
  type AppointmentQueryParams,
} from '@/api/appointment'

function extractError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || fallback
}

export const useAppointmentStore = defineStore('appointment', () => {
  const appointments = ref<AppointmentResponse[]>([])
  const currentAppointment = ref<AppointmentResponse | null>(null)
  const filterStatus = ref<AppointmentStatus | null>(null)
  const filterDate = ref<string | null>(null)
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)
  const bookingError = ref<string | null>(null)

  const upcomingAppointments = computed<AppointmentResponse[]>(() => {
    const now = Date.now()
    return appointments.value
      .filter((a) => {
        const isUpcomingStatus = a.status === 'pending' || a.status === 'confirmed'
        const time = new Date(a.start_time).getTime()
        return isUpcomingStatus && time >= now
      })
      .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())
  })

  const pastAppointments = computed<AppointmentResponse[]>(() => {
    const now = Date.now()
    return appointments.value
      .filter((a) => {
        const isPastStatus = a.status === 'completed' || a.status === 'cancelled' || a.status === 'no_show'
        const time = new Date(a.start_time).getTime()
        return isPastStatus || time < now
      })
      .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime())
  })

  const pendingAppointments = computed<AppointmentResponse[]>(() =>
    appointments.value.filter((a) => a.status === 'pending'),
  )

  const confirmedAppointments = computed<AppointmentResponse[]>(() =>
    appointments.value.filter((a) => a.status === 'confirmed'),
  )

  const filteredAppointments = computed<AppointmentResponse[]>(() => {
    return appointments.value.filter((a) => {
      if (filterStatus.value && a.status !== filterStatus.value) {
        return false
      }
      if (filterDate.value && !a.start_time.startsWith(filterDate.value)) {
        return false
      }
      return true
    })
  })

  function _syncAppointment(updated: AppointmentResponse): void {
    const idx = appointments.value.findIndex((a) => a.id === updated.id)
    if (idx !== -1) {
      appointments.value[idx] = updated
    } else {
      appointments.value.unshift(updated)
    }
    if (currentAppointment.value?.id === updated.id) {
      currentAppointment.value = updated
    }
  }

  function setFilterStatus(status: AppointmentStatus | null): void {
    filterStatus.value = status
  }

  function setFilterDate(date: string | null): void {
    filterDate.value = date
  }

  function clearFilters(): void {
    filterStatus.value = null
    filterDate.value = null
  }

  async function fetchAppointments(params?: AppointmentQueryParams): Promise<AppointmentResponse[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await appointmentsApi.listAppointments(params)
      appointments.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch appointments')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function getAppointmentById(id: number): Promise<AppointmentResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await appointmentsApi.getAppointmentById(id)
      currentAppointment.value = response.data
      _syncAppointment(response.data)
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load appointment details')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function bookAppointment(
    payload: AppointmentCreateRequest | AppointmentAdminCreateRequest,
  ): Promise<AppointmentResponse> {
    isLoading.value = true
    bookingError.value = null
    error.value = null
    try {
      const response = await appointmentsApi.createAppointment(payload)
      appointments.value.unshift(response.data)
      currentAppointment.value = response.data
      return response.data
    } catch (err: unknown) {
      const msg = extractError(err, 'Failed to book appointment')
      bookingError.value = msg
      error.value = msg
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updateAppointment(
    id: number,
    payload: AppointmentUpdate,
  ): Promise<AppointmentResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await appointmentsApi.updateAppointment(id, payload)
      _syncAppointment(response.data)
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to update appointment')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updateAppointmentStatus(
    id: number,
    status: AppointmentStatus,
    cancellationReason?: string,
  ): Promise<AppointmentResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await appointmentsApi.updateAppointmentStatus(id, status, cancellationReason)
      _syncAppointment(response.data)
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to update appointment status')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function cancelAppointment(id: number, reason?: string): Promise<AppointmentResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await appointmentsApi.cancelAppointment(id, reason)
      _syncAppointment(response.data)
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to cancel appointment')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    appointments,
    currentAppointment,
    filterStatus,
    filterDate,
    isLoading,
    error,
    bookingError,
    upcomingAppointments,
    pastAppointments,
    pendingAppointments,
    confirmedAppointments,
    filteredAppointments,
    setFilterStatus,
    setFilterDate,
    clearFilters,
    fetchAppointments,
    getAppointmentById,
    bookAppointment,
    updateAppointment,
    updateAppointmentStatus,
    cancelAppointment,
  }
})

