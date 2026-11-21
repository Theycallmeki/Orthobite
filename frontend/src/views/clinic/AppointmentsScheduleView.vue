<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAppointmentStore } from '@/stores/appointment'
import { useDoctorStore } from '@/stores/doctor'
import { useAuthStore } from '@/stores/auth'
import type { AppointmentQueryParams, AppointmentResponse, AppointmentStatus } from '@/api/appointment'
import type { DoctorPublicResponse } from '@/api/doctor'
import {
  Calendar,
  Clock,
  User,
  Stethoscope,
  CheckCircle2,
  AlertCircle,
  XCircle,
  X,
  Plus,
  RefreshCw,
  Search,
  Filter,
  FileText,
  AlertTriangle,
  Loader2,
  CalendarCheck,
  ChevronLeft,
  ChevronRight,
  Phone,
  Mail,
  UserCheck,
  Edit3,
} from 'lucide-vue-next'

const appointmentStore = useAppointmentStore()
const doctorStore = useDoctorStore()
const authStore = useAuthStore()
const canScheduleWalkIn = computed(() => authStore.isSecretary || authStore.isAdmin)

const clinicTimeZone = 'Asia/Manila'
const clinicDateFormat = new Intl.DateTimeFormat('sv-SE', {
  timeZone: clinicTimeZone,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})
const timestampOffset = /(?:Z|[+-]\d{2}:\d{2})$/i
const scheduleViews = [
  { value: 'upcoming', label: 'Upcoming' },
  { value: 'by-date', label: 'By date' },
  { value: 'completed', label: 'Completed' },
] as const
type ScheduleView = typeof scheduleViews[number]['value']
const scheduleView = ref<ScheduleView>(authStore.isSecretary ? 'upcoming' : 'by-date')
const showUpcoming = computed(() => scheduleView.value === 'upcoming')
const showCompleted = computed(() => scheduleView.value === 'completed')
const selectedDate = ref(clinicDateFormat.format())
const selectedDoctorId = ref<number | 'all'>('all')
const statusFilter = ref<'all' | 'pending' | 'confirmed' | 'completed' | 'cancelled'>('all')
const searchQuery = ref<string>('')

const showAdminBookingModal = ref<boolean>(false)
const adminPatientId = ref<number | ''>('')
const adminDoctorId = ref<number | ''>('')
const adminStartTime = ref<string>('')
const adminEndTime = ref<string>('')
const adminReason = ref<string>('Orthodontic Checkup')
const adminNotes = ref<string>('')
const isBookingAdmin = ref<boolean>(false)
const adminBookingError = ref<string | null>(null)

const cancellingAppointment = ref<AppointmentResponse | null>(null)
const cancellationReason = ref<string>('')
const isCancelling = ref<boolean>(false)

const editingNotesAppointment = ref<AppointmentResponse | null>(null)
const visitNotesText = ref<string>('')
const isSavingNotes = ref<boolean>(false)

const presetCancelReasons = [
  'Patient Rescheduled / Called In',
  'Doctor Emergency / Leave',
  'Patient No-Show / Unreachable',
  'Clinic System Duplicate',
]

onMounted(async () => {
  if (doctorStore.doctors.length === 0) {
    await doctorStore.fetchPublicDoctors().catch(() => {})
  }
  await fetchSchedule()
})

watch([scheduleView, selectedDate, selectedDoctorId], async () => {
  await fetchSchedule()
})

async function fetchSchedule() {
  const params: AppointmentQueryParams = {}
  if (showUpcoming.value) {
    params.upcoming_only = true
  } else {
    params.date = selectedDate.value || clinicDateFormat.format()
    if (showCompleted.value) params.status = 'completed'
  }
  if (selectedDoctorId.value !== 'all') {
    params.doctor_id = Number(selectedDoctorId.value)
  }
  try {
    await appointmentStore.fetchAppointments(params)
  } catch {
  }
}

const scheduleAppointments = computed(() => {
  let list = appointmentStore.appointments

  if (showUpcoming.value) {
    list = list.filter((a) => a.status === 'pending' || a.status === 'confirmed')
  } else {
    const date = selectedDate.value || clinicDateFormat.format()
    list = list.filter((a) => getAppointmentDate(a.start_time) === date)
    if (showCompleted.value) list = list.filter((a) => a.status === 'completed')
  }

  if (selectedDoctorId.value !== 'all') {
    list = list.filter((a) => a.doctor_id === Number(selectedDoctorId.value))
  }
  return list
})

const filteredAppointments = computed<AppointmentResponse[]>(() => {
  let list = scheduleAppointments.value
  if (statusFilter.value === 'pending') {
    list = list.filter((a) => a.status === 'pending')
  } else if (statusFilter.value === 'confirmed') {
    list = list.filter((a) => a.status === 'confirmed')
  } else if (statusFilter.value === 'completed') {
    list = list.filter((a) => a.status === 'completed')
  } else if (statusFilter.value === 'cancelled') {
    list = list.filter((a) => a.status === 'cancelled' || a.status === 'no_show')
  }

  if (!searchQuery.value.trim()) {
    return list
  }

  const q = searchQuery.value.toLowerCase().trim()
  return list.filter((a) => {
    const patName = a.patient?.full_name?.toLowerCase() || ''
    const patEmail = a.patient?.email?.toLowerCase() || ''
    const docName = a.doctor?.full_name?.toLowerCase() || ''
    const reason = a.reason_for_visit?.toLowerCase() || ''
    const refId = `#${a.id}`
    return (
      patName.includes(q) ||
      patEmail.includes(q) ||
      docName.includes(q) ||
      reason.includes(q) ||
      refId.includes(q)
    )
  })
})

const countAll = computed(() => scheduleAppointments.value.length)
const countPending = computed(() => scheduleAppointments.value.filter((a) => a.status === 'pending').length)
const countConfirmed = computed(() => scheduleAppointments.value.filter((a) => a.status === 'confirmed').length)
const countCompleted = computed(() => scheduleAppointments.value.filter((a) => a.status === 'completed').length)
const countCancelled = computed(() => scheduleAppointments.value.filter((a) => a.status === 'cancelled' || a.status === 'no_show').length)

function setScheduleView(view: ScheduleView) {
  if (scheduleView.value === view) return
  scheduleView.value = view
  statusFilter.value = 'all'
}

function setToday() {
  selectedDate.value = clinicDateFormat.format()
}

function setTomorrow() {
  selectedDate.value = shiftDate(clinicDateFormat.format(), 1)
}

function shiftDate(date: string, days: number) {
  const d = new Date(`${date}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

function moveSelectedDate(days: number) {
  selectedDate.value = shiftDate(selectedDate.value || clinicDateFormat.format(), days)
}

function getAppointmentDate(timestamp: string) {
  return timestampOffset.test(timestamp) ? clinicDateFormat.format(new Date(timestamp)) : timestamp.slice(0, 10)
}

function formatDisplayDate(dateStr: string): string {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  if (parts.length !== 3) return dateStr
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
  return d.toLocaleDateString('default', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatTime(timestamp: string): string {
  const withOffset = timestampOffset.test(timestamp)
  return new Date(withOffset ? timestamp : `${timestamp}Z`).toLocaleTimeString('en-PH', {
    timeZone: withOffset ? clinicTimeZone : 'UTC',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getStatusBadgeClass(status: AppointmentStatus) {
  switch (status) {
    case 'confirmed':
      return 'bg-emerald-100 text-emerald-800 border-emerald-200'
    case 'pending':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'completed':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'cancelled':
      return 'bg-rose-100 text-rose-800 border-rose-200'
    case 'no_show':
      return 'bg-slate-100 text-slate-700 border-slate-200'
    default:
      return 'bg-slate-100 text-slate-800 border-slate-200'
  }
}

async function handleConfirmAppointment(appt: AppointmentResponse) {
  try {
    await appointmentStore.updateAppointmentStatus(appt.id, 'confirmed')
  } catch {
  }
}

async function handleCompleteAppointment(appt: AppointmentResponse) {
  try {
    await appointmentStore.updateAppointmentStatus(appt.id, 'completed')
  } catch {
  }
}

async function handleMarkNoShow(appt: AppointmentResponse) {
  try {
    await appointmentStore.updateAppointmentStatus(appt.id, 'no_show')
  } catch {
  }
}

function openCancelModal(appt: AppointmentResponse) {
  cancellingAppointment.value = appt
  cancellationReason.value = 'Patient Rescheduled / Called In'
}

function closeCancelModal() {
  cancellingAppointment.value = null
  cancellationReason.value = ''
}

async function submitCancel() {
  if (!cancellingAppointment.value) return
  isCancelling.value = true
  try {
    await appointmentStore.updateAppointmentStatus(
      cancellingAppointment.value.id,
      'cancelled',
      cancellationReason.value.trim() || undefined,
    )
    closeCancelModal()
  } catch {
  } finally {
    isCancelling.value = false
  }
}

function openEditNotesModal(appt: AppointmentResponse) {
  editingNotesAppointment.value = appt
  visitNotesText.value = appt.notes || ''
}

function closeEditNotesModal() {
  editingNotesAppointment.value = null
  visitNotesText.value = ''
}

async function submitSaveNotes() {
  if (!editingNotesAppointment.value) return
  isSavingNotes.value = true
  try {
    await appointmentStore.updateAppointment(editingNotesAppointment.value.id, {
      notes: visitNotesText.value.trim() || undefined,
    })
    closeEditNotesModal()
  } catch {
  } finally {
    isSavingNotes.value = false
  }
}

function openAdminBooking() {
  adminPatientId.value = ''
  adminDoctorId.value = doctorStore.activeDoctors[0]?.id || ''
  adminStartTime.value = `${selectedDate.value}T09:00`
  adminEndTime.value = `${selectedDate.value}T09:30`
  adminReason.value = 'Orthodontic Consultation'
  adminNotes.value = ''
  adminBookingError.value = null
  showAdminBookingModal.value = true
}

function closeAdminBooking() {
  showAdminBookingModal.value = false
  adminBookingError.value = null
}

async function submitAdminBooking() {
  if (!adminDoctorId.value || !adminPatientId.value || !adminStartTime.value) return
  isBookingAdmin.value = true
  adminBookingError.value = null
  try {
    const startDt = new Date(adminStartTime.value)
    const endDt = adminEndTime.value ? new Date(adminEndTime.value) : new Date(startDt.getTime() + 30 * 60000)
    const endTimeStr = adminEndTime.value || endDt.toISOString().slice(0, 16)

    await appointmentStore.bookAppointment({
      doctor_id: Number(adminDoctorId.value),
      patient_id: Number(adminPatientId.value),
      start_time: adminStartTime.value,
      end_time: endTimeStr,
      reason_for_visit: adminReason.value.trim() || undefined,
      notes: adminNotes.value.trim() || undefined,
    })
    closeAdminBooking()
    await fetchSchedule()
  } catch (err: unknown) {
    adminBookingError.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
      'Failed to create appointment on behalf of patient'
  } finally {
    isBookingAdmin.value = false
  }
}
</script>

<template>
  <div class="space-y-6 pb-16">
    <div class="app-panel app-page-heading flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Clinic Schedule Manager
        </h1>
        <p class="text-sm text-slate-500 mt-1">
          {{ authStore.isSecretary
            ? 'Review appointment requests, approve visits, and manage the clinic schedule.'
            : 'Review daily schedules and update visit statuses.' }}
        </p>
      </div>

      <div class="flex items-center gap-2.5">
        <button
          type="button"
          @click="fetchSchedule"
          :disabled="appointmentStore.isLoading"
          class="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 font-medium text-xs transition cursor-pointer shadow-xs disabled:opacity-50"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': appointmentStore.isLoading }" />
          Refresh
        </button>

        <button
          v-if="canScheduleWalkIn"
          type="button"
          @click="openAdminBooking"
          class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl app-primary-action font-semibold text-xs transition shadow-md shadow-teal-600/20 cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          Schedule Walk-In Visit
        </button>
        <RouterLink
          v-if="authStore.isDoctor"
          :to="{ name: 'clinic-availability' }"
          class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl app-primary-action font-semibold text-xs shadow-md shadow-teal-600/20"
        >
          <Calendar class="size-4" />
          My Availability
        </RouterLink>
      </div>
    </div>

    <div v-if="!showCompleted" class="grid grid-cols-2 gap-3" :class="showUpcoming ? 'sm:grid-cols-3' : 'sm:grid-cols-5'">
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
        <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Total Visits</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-black text-slate-900">{{ countAll }}</span>
          <span class="text-[11px] text-slate-500 font-medium">scheduled</span>
        </div>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-amber-200/80 shadow-xs bg-amber-50/20">
        <span class="text-[11px] font-bold uppercase tracking-wider text-amber-800">Pending</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-black text-amber-700">{{ countPending }}</span>
          <span class="text-[11px] text-amber-600 font-medium">awaiting review</span>
        </div>
      </div>

      <div class="bg-white p-4 rounded-2xl border border-emerald-200/80 shadow-xs bg-emerald-50/20">
        <span class="text-[11px] font-bold uppercase tracking-wider text-emerald-800">Confirmed</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-black text-emerald-700">{{ countConfirmed }}</span>
          <span class="text-[11px] text-emerald-600 font-medium">ready for visit</span>
        </div>
      </div>

      <div v-if="!showUpcoming" class="bg-white p-4 rounded-2xl border border-blue-200/80 shadow-xs bg-blue-50/20">
        <span class="text-[11px] font-bold uppercase tracking-wider text-blue-800">Completed</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-black text-blue-700">{{ countCompleted }}</span>
          <span class="text-[11px] text-blue-600 font-medium">discharged</span>
        </div>
      </div>

      <div v-if="!showUpcoming" class="bg-white p-4 rounded-2xl border border-rose-200/80 shadow-xs bg-rose-50/20 col-span-2 sm:col-span-1">
        <span class="text-[11px] font-bold uppercase tracking-wider text-rose-800">Cancelled / No-Show</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-black text-rose-700">{{ countCancelled }}</span>
          <span class="text-[11px] text-rose-600 font-medium">unattended</span>
        </div>
      </div>
    </div>

    <div class="bg-white p-4 rounded-3xl border border-slate-200 shadow-xs space-y-4">
      <div v-if="authStore.isSecretary" class="flex flex-wrap items-center gap-2">
        <button
          v-for="view in scheduleViews"
          :key="view.value"
          type="button"
          :aria-pressed="scheduleView === view.value"
          class="px-3 py-1.5 rounded-xl border text-xs font-bold transition cursor-pointer"
          :class="scheduleView === view.value ? 'bg-teal-50 border-teal-200 text-teal-800' : 'border-slate-200 text-slate-700 hover:bg-slate-50'"
          @click="setScheduleView(view.value)"
        >
          {{ view.label }}
        </button>
      </div>
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div v-if="!showUpcoming" class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            @click="setToday"
            class="px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-800 transition cursor-pointer"
          >
            Today
          </button>
          <button
            v-if="!showCompleted"
            type="button"
            @click="setTomorrow"
            class="px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-800 transition cursor-pointer"
          >
            Tomorrow
          </button>

          <div class="flex items-center gap-1 border border-slate-200 rounded-xl px-2 py-1 bg-slate-50/80">
            <button
              type="button"
              @click="moveSelectedDate(-1)"
              class="p-1 text-slate-500 hover:text-slate-800 cursor-pointer"
              aria-label="Previous day"
            >
              <ChevronLeft class="w-4 h-4" />
            </button>
            <input
              v-model="selectedDate"
              type="date"
              aria-label="Appointment date"
              @change="selectedDate || setToday()"
              class="text-xs font-bold text-slate-800 bg-transparent border-none focus:outline-none cursor-pointer"
            />
            <button
              type="button"
              @click="moveSelectedDate(1)"
              class="p-1 text-slate-500 hover:text-slate-800 cursor-pointer"
              aria-label="Next day"
            >
              <ChevronRight class="w-4 h-4" />
            </button>
          </div>

          <span class="text-xs font-bold text-teal-800 hidden sm:inline ml-2">
            {{ formatDisplayDate(selectedDate) }}
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <div class="flex items-center gap-2">
            <Stethoscope class="w-4 h-4 text-slate-400" />
            <select
              v-model="selectedDoctorId"
              aria-label="Filter by doctor"
              class="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500 transition cursor-pointer"
            >
              <option value="all">All Orthodontists & Doctors</option>
              <option
                v-for="doc in doctorStore.doctors"
                :key="doc.id"
                :value="doc.id"
              >
                {{ doc.full_name }} ({{ doc.specialty }})
              </option>
            </select>
          </div>

          <div class="relative min-w-56 flex-1 sm:flex-none">
            <Search class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search patient or doctor..."
              class="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 transition"
            />
          </div>
        </div>
      </div>

      <div v-if="!showCompleted" class="flex items-center gap-1.5 overflow-x-auto pb-1 pt-1 border-t border-slate-100">
        <button
          type="button"
          @click="statusFilter = 'all'"
          :class="[
            'px-3.5 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer whitespace-nowrap',
            statusFilter === 'all'
              ? 'bg-teal-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          All ({{ countAll }})
        </button>

        <button
          type="button"
          @click="statusFilter = 'pending'"
          :class="[
            'px-3.5 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer whitespace-nowrap',
            statusFilter === 'pending'
              ? 'bg-amber-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          Pending ({{ countPending }})
        </button>

        <button
          type="button"
          @click="statusFilter = 'confirmed'"
          :class="[
            'px-3.5 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer whitespace-nowrap',
            statusFilter === 'confirmed'
              ? 'bg-emerald-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          Confirmed ({{ countConfirmed }})
        </button>

        <button
          v-if="!showUpcoming"
          type="button"
          @click="statusFilter = 'completed'"
          :class="[
            'px-3.5 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer whitespace-nowrap',
            statusFilter === 'completed'
              ? 'bg-blue-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          Completed ({{ countCompleted }})
        </button>

        <button
          v-if="!showUpcoming"
          type="button"
          @click="statusFilter = 'cancelled'"
          :class="[
            'px-3.5 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer whitespace-nowrap',
            statusFilter === 'cancelled'
              ? 'bg-rose-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          Cancelled / No-Show ({{ countCancelled }})
        </button>
      </div>
    </div>

    <div v-if="showCompleted" class="flex flex-wrap items-center justify-between gap-2">
      <h2 class="text-lg font-bold text-slate-900">Completed Visits</h2>
      <span v-if="!appointmentStore.isLoading && !appointmentStore.error" class="text-sm text-slate-600" aria-live="polite">
        {{ filteredAppointments.length }} {{ filteredAppointments.length === 1 ? 'visit' : 'visits' }}
      </span>
    </div>

    <p v-if="appointmentStore.error" role="alert" class="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
      {{ appointmentStore.error }}
    </p>
    <div v-if="appointmentStore.isLoading" class="py-16 text-center space-y-3">
      <Loader2 class="w-8 h-8 animate-spin mx-auto text-teal-600" />
      <p class="text-xs font-medium text-slate-500">Loading appointments...</p>
    </div>

    <div v-else-if="filteredAppointments.length === 0" class="app-panel p-12 text-center max-w-md mx-auto space-y-3">
      <div class="w-14 h-14 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
        <CalendarCheck class="w-7 h-7" />
      </div>
      <h3 class="text-base font-bold text-slate-900">{{ showCompleted ? 'No Completed Visits' : 'No Appointments Scheduled' }}</h3>
      <p class="text-xs text-slate-500">
        {{ showCompleted
          ? 'No completed visits match the selected date and filters.'
          : searchQuery || statusFilter !== 'all'
          ? 'No appointments match your filters.'
          : (showUpcoming ? 'There are no upcoming visits or pending requests.' : `No consultations found for ${formatDisplayDate(selectedDate)}.`) }}
      </p>
      <div v-if="!showCompleted && canScheduleWalkIn" class="pt-2">
        <button
          type="button"
          @click="openAdminBooking"
          class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl app-primary-action font-semibold text-xs transition cursor-pointer shadow-sm"
        >
          <Plus class="w-4 h-4" />
          Book Walk-In Patient
        </button>
      </div>
    </div>

    <div v-else class="space-y-3.5">
      <div
        v-for="appt in filteredAppointments"
        :key="appt.id"
        class="app-panel p-5 hover:shadow-md transition flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div class="flex items-start gap-4">
          <div class="flex flex-col items-center justify-center w-20 py-2.5 rounded-xl bg-slate-50 border border-slate-200 shrink-0 text-center">
            <Clock class="w-4 h-4 text-teal-600 mb-0.5" />
            <span class="text-xs font-black text-slate-900 leading-tight">
              {{ formatTime(appt.start_time) }}
            </span>
            <span class="text-[10px] text-slate-400 font-medium">
              {{ formatTime(appt.end_time) }}
            </span>
          </div>

          <div class="space-y-1">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-sm font-bold text-slate-900">
                {{ appt.patient?.full_name || `Patient #${appt.patient_id}` }}
              </h3>
              <span
                :class="[
                  'px-2.5 py-0.5 rounded-full text-[10px] font-bold border capitalize',
                  getStatusBadgeClass(appt.status)
                ]"
              >
                {{ appt.status === 'pending' ? 'Pending approval' : appt.status.replace('_', ' ') }}
              </span>
              <span class="text-[10px] text-slate-400 font-mono">
                Ref #{{ appt.id }}
              </span>
            </div>

            <p class="text-xs font-semibold text-teal-800">
              {{ appt.reason_for_visit || 'General Consultation' }}
            </p>

            <div class="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 pt-0.5">
              <span v-if="showUpcoming" class="flex items-center gap-1">
                <Calendar class="w-3.5 h-3.5 text-slate-400" />
                {{ formatDisplayDate(getAppointmentDate(appt.start_time)) }}
              </span>
              <span class="flex items-center gap-1">
                <Stethoscope class="w-3.5 h-3.5 text-slate-400" />
                {{ appt.doctor?.full_name || `Doctor #${appt.doctor_id}` }}
              </span>
              <span v-if="appt.patient?.phone" class="flex items-center gap-1">
                <Phone class="w-3.5 h-3.5 text-slate-400" />
                {{ appt.patient.phone }}
              </span>
              <span v-if="appt.patient?.email" class="flex items-center gap-1">
                <Mail class="w-3.5 h-3.5 text-slate-400" />
                {{ appt.patient.email }}
              </span>
            </div>

            <div v-if="appt.notes" class="text-xs text-slate-600 bg-slate-50 p-2 rounded-lg border border-slate-100 mt-1 max-w-xl">
              <span class="font-bold text-slate-700">Notes:</span> {{ appt.notes }}
            </div>

            <div v-if="appt.status === 'cancelled' && appt.cancellation_reason" class="text-xs text-rose-700 bg-rose-50 p-2 rounded-lg border border-rose-200 mt-1">
              <span class="font-bold">Cancellation Reason:</span> {{ appt.cancellation_reason }}
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 self-end md:self-center border-t md:border-t-0 pt-3 md:pt-0 w-full md:w-auto justify-end">
          <button
            type="button"
            @click="openEditNotesModal(appt)"
            class="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 text-xs font-semibold transition cursor-pointer flex items-center gap-1"
          >
            <Edit3 class="w-3.5 h-3.5" />
            Notes
          </button>

          <template v-if="appt.status === 'pending'">
            <button
              v-if="authStore.isSecretary"
              type="button"
              @click="handleConfirmAppointment(appt)"
              class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition cursor-pointer shadow-xs"
            >
              Approve Request
            </button>
            <button
              type="button"
              @click="openCancelModal(appt)"
              class="px-2.5 py-1.5 rounded-xl text-rose-600 hover:bg-rose-50 text-xs font-semibold transition cursor-pointer"
            >
              Cancel
            </button>
          </template>

          <template v-else-if="appt.status === 'confirmed'">
            <button
              type="button"
              @click="handleCompleteAppointment(appt)"
              class="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition cursor-pointer shadow-xs flex items-center gap-1"
            >
              <UserCheck class="w-3.5 h-3.5" />
              Complete Visit
            </button>
            <button
              type="button"
              @click="handleMarkNoShow(appt)"
              class="px-2.5 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-700 text-xs font-semibold transition cursor-pointer"
            >
              No-Show
            </button>
            <button
              type="button"
              @click="openCancelModal(appt)"
              class="px-2.5 py-1.5 rounded-xl text-rose-600 hover:bg-rose-50 text-xs font-semibold transition cursor-pointer"
            >
              Cancel
            </button>
          </template>
        </div>
      </div>
    </div>

    <div
      v-if="cancellingAppointment"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs"
    >
      <div class="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2 text-rose-600 font-bold">
            <AlertTriangle class="w-5 h-5" />
            <h3 class="text-base text-slate-900">Cancel Consultation</h3>
          </div>
          <button
            type="button"
            @click="closeCancelModal"
            class="text-slate-400 hover:text-slate-600 p-1"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <p class="text-xs text-slate-600">
          Cancel visit for <strong class="text-slate-900">{{ cancellingAppointment.patient?.full_name || `Patient #${cancellingAppointment.patient_id}` }}</strong> with <strong class="text-slate-900">{{ cancellingAppointment.doctor?.full_name }}</strong>.
        </p>

        <div class="space-y-2">
          <label class="block text-xs font-bold text-slate-700">Reason</label>
          <div class="flex flex-wrap gap-1.5 mb-2">
            <button
              v-for="r in presetCancelReasons"
              :key="r"
              type="button"
              @click="cancellationReason = r"
              :class="[
                'px-2 py-1 rounded-lg text-[10px] font-semibold transition cursor-pointer',
                cancellationReason === r ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              ]"
            >
              {{ r }}
            </button>
          </div>
          <input
            v-model="cancellationReason"
            type="text"
            required
            class="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-rose-500 focus:outline-none"
            placeholder="Specify reason..."
          />
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            @click="closeCancelModal"
            class="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
          >
            Keep Visit
          </button>
          <button
            type="button"
            @click="submitCancel"
            :disabled="isCancelling || !cancellationReason.trim()"
            class="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          >
            <Loader2 v-if="isCancelling" class="w-3.5 h-3.5 animate-spin" />
            <span>Confirm Cancellation</span>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="editingNotesAppointment"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs"
    >
      <div class="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2 text-teal-700 font-bold">
            <FileText class="w-5 h-5" />
            <h3 class="text-base text-slate-900">Clinical Visit Notes</h3>
          </div>
          <button
            type="button"
            @click="closeEditNotesModal"
            class="text-slate-400 hover:text-slate-600 p-1"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="space-y-1.5">
          <label class="block text-xs font-bold text-slate-700">Notes / Symptoms</label>
          <textarea
            v-model="visitNotesText"
            rows="4"
            class="w-full p-3 rounded-xl border border-slate-200 text-xs text-slate-900 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            placeholder="Enter clinical notes for this visit..."
          ></textarea>
        </div>

        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            @click="closeEditNotesModal"
            class="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            @click="submitSaveNotes"
            :disabled="isSavingNotes"
            class="px-4 py-2 rounded-xl app-primary-action text-xs font-bold transition cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          >
            <Loader2 v-if="isSavingNotes" class="w-3.5 h-3.5 animate-spin" />
            <span>Save Notes</span>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showAdminBookingModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs"
    >
      <div class="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-7 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2 text-teal-700 font-bold">
            <Plus class="w-5 h-5" />
            <h3 class="text-base text-slate-900">Schedule Patient Visit (Staff)</h3>
          </div>
          <button
            type="button"
            @click="closeAdminBooking"
            class="text-slate-400 hover:text-slate-600 p-1"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <form @submit.prevent="submitAdminBooking" class="space-y-4">
          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Patient User ID *</label>
            <input
              v-model="adminPatientId"
              type="number"
              required
              class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              placeholder="e.g. 1"
            />
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Attending Specialist *</label>
            <select
              v-model="adminDoctorId"
              required
              class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none cursor-pointer"
            >
              <option
                v-for="doc in doctorStore.activeDoctors"
                :key="doc.id"
                :value="doc.id"
              >
                {{ doc.full_name }} ({{ doc.specialty }})
              </option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label class="block text-xs font-bold text-slate-700">Start Time *</label>
              <input
                v-model="adminStartTime"
                type="datetime-local"
                required
                class="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>

            <div class="space-y-1">
              <label class="block text-xs font-bold text-slate-700">End Time</label>
              <input
                v-model="adminEndTime"
                type="datetime-local"
                class="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              />
            </div>
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Reason for Consultation</label>
            <input
              v-model="adminReason"
              type="text"
              class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              placeholder="e.g. Bracket adjustment, consult"
            />
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Visit Notes (Optional)</label>
            <textarea
              v-model="adminNotes"
              rows="2"
              class="w-full p-3 rounded-xl border border-slate-200 text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
              placeholder="Clinical symptoms or patient concerns..."
            ></textarea>
          </div>

          <div v-if="adminBookingError" class="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
            <AlertCircle class="w-4 h-4 shrink-0" />
            <span>{{ adminBookingError }}</span>
          </div>

          <div class="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              @click="closeAdminBooking"
              class="px-4 py-2.5 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="isBookingAdmin || !adminPatientId || !adminDoctorId || !adminStartTime"
              class="px-5 py-2.5 rounded-xl app-primary-action text-xs font-bold transition cursor-pointer shadow-md shadow-teal-600/20 disabled:opacity-50 flex items-center gap-1.5"
            >
              <Loader2 v-if="isBookingAdmin" class="w-3.5 h-3.5 animate-spin" />
              <span>Submit Appointment Request</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
