<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAppointmentStore } from '@/stores/appointment'
import type { AppointmentResponse, AppointmentStatus } from '@/api/appointment'
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
  CalendarX2,
} from 'lucide-vue-next'

const router = useRouter()
const appointmentStore = useAppointmentStore()

const activeTab = ref<'upcoming' | 'past' | 'cancelled' | 'all'>('upcoming')
const searchQuery = ref<string>('')
const cancellingAppointment = ref<AppointmentResponse | null>(null)
const cancellationReason = ref<string>('')
const isCancelling = ref<boolean>(false)
const cancelError = ref<string | null>(null)

const presetCancelReasons = [
  'Schedule Conflict',
  'Feeling Unwell / Medical Issue',
  'Need to Reschedule Later',
  'Emergency',
  'Other',
]

onMounted(async () => {
  await fetchAppointments()
})

async function fetchAppointments() {
  try {
    await appointmentStore.fetchAppointments()
  } catch {
  }
}

const filteredAppointments = computed<AppointmentResponse[]>(() => {
  let list: AppointmentResponse[] = []
  if (activeTab.value === 'upcoming') {
    list = appointmentStore.upcomingAppointments
  } else if (activeTab.value === 'past') {
    list = appointmentStore.pastAppointments.filter((a) => a.status !== 'cancelled')
  } else if (activeTab.value === 'cancelled') {
    list = appointmentStore.appointments.filter((a) => a.status === 'cancelled')
  } else {
    list = appointmentStore.appointments
  }

  if (!searchQuery.value.trim()) {
    return list
  }

  const q = searchQuery.value.toLowerCase().trim()
  return list.filter((a) => {
    const docName = a.doctor?.full_name?.toLowerCase() || ''
    const docSpecialty = a.doctor?.specialty?.toLowerCase() || ''
    const reason = a.reason_for_visit?.toLowerCase() || ''
    const status = a.status.toLowerCase()
    return docName.includes(q) || docSpecialty.includes(q) || reason.includes(q) || status.includes(q)
  })
})

const upcomingCount = computed(() => appointmentStore.upcomingAppointments.length)
const pastCount = computed(() => appointmentStore.pastAppointments.filter((a) => a.status !== 'cancelled').length)
const cancelledCount = computed(() => appointmentStore.appointments.filter((a) => a.status === 'cancelled').length)
const totalCount = computed(() => appointmentStore.appointments.length)

function formatDate(isoStr: string): string {
  try {
    const d = new Date(isoStr)
    return d.toLocaleDateString('default', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return isoStr
  }
}

function formatTime(startIso: string, endIso: string): string {
  try {
    const s = new Date(startIso)
    const e = new Date(endIso)
    const sTime = s.toLocaleTimeString('default', { hour: 'numeric', minute: '2-digit' })
    const eTime = e.toLocaleTimeString('default', { hour: 'numeric', minute: '2-digit' })
    return `${sTime} - ${eTime}`
  } catch {
    return ''
  }
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

function getStatusLabel(status: AppointmentStatus) {
  switch (status) {
    case 'confirmed':
      return 'Confirmed'
    case 'pending':
      return 'Pending Review'
    case 'completed':
      return 'Completed'
    case 'cancelled':
      return 'Cancelled'
    case 'no_show':
      return 'No Show'
    default:
      return status
  }
}

function canCancel(appt: AppointmentResponse): boolean {
  if (appt.status !== 'pending' && appt.status !== 'confirmed') return false
  const time = new Date(appt.start_time).getTime()
  return time > Date.now()
}

function openCancelModal(appt: AppointmentResponse) {
  cancellingAppointment.value = appt
  cancellationReason.value = 'Schedule Conflict'
  cancelError.value = null
}

function closeCancelModal() {
  cancellingAppointment.value = null
  cancellationReason.value = ''
  cancelError.value = null
}

async function handleConfirmCancel() {
  if (!cancellingAppointment.value) return
  isCancelling.value = true
  cancelError.value = null
  try {
    await appointmentStore.cancelAppointment(
      cancellingAppointment.value.id,
      cancellationReason.value.trim() || undefined,
    )
    closeCancelModal()
  } catch (err: unknown) {
    cancelError.value = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to cancel appointment'
  } finally {
    isCancelling.value = false
  }
}
</script>

<template>
  <div class="space-y-6 pb-12">
    <div class="app-panel app-page-heading flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          My Appointments
        </h1>
        <p class="text-sm text-slate-500 mt-1">
          Review consultation schedules, past clinical visits, and manage appointment bookings.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="fetchAppointments"
          :disabled="appointmentStore.isLoading"
          class="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 font-medium text-xs transition cursor-pointer shadow-xs disabled:opacity-50"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': appointmentStore.isLoading }" />
          Refresh
        </button>

        <router-link
          to="/portal/book"
          class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl app-primary-action font-semibold text-xs transition shadow-md shadow-teal-600/20"
        >
          <Plus class="w-4 h-4" />
          Book Appointment
        </router-link>
      </div>
    </div>

    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-3">
      <div class="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
        <button
          type="button"
          @click="activeTab = 'upcoming'"
          :class="[
            'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer whitespace-nowrap',
            activeTab === 'upcoming'
              ? 'bg-teal-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          Upcoming
          <span
            :class="[
              'px-2 py-0.5 rounded-full text-[11px] font-bold',
              activeTab === 'upcoming' ? 'bg-teal-700 text-teal-100' : 'bg-slate-200 text-slate-700'
            ]"
          >
            {{ upcomingCount }}
          </span>
        </button>

        <button
          type="button"
          @click="activeTab = 'past'"
          :class="[
            'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer whitespace-nowrap',
            activeTab === 'past'
              ? 'bg-teal-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          Past Visits
          <span
            :class="[
              'px-2 py-0.5 rounded-full text-[11px] font-bold',
              activeTab === 'past' ? 'bg-teal-700 text-teal-100' : 'bg-slate-200 text-slate-700'
            ]"
          >
            {{ pastCount }}
          </span>
        </button>

        <button
          type="button"
          @click="activeTab = 'cancelled'"
          :class="[
            'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer whitespace-nowrap',
            activeTab === 'cancelled'
              ? 'bg-teal-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          Cancelled
          <span
            :class="[
              'px-2 py-0.5 rounded-full text-[11px] font-bold',
              activeTab === 'cancelled' ? 'bg-teal-700 text-teal-100' : 'bg-slate-200 text-slate-700'
            ]"
          >
            {{ cancelledCount }}
          </span>
        </button>

        <button
          type="button"
          @click="activeTab = 'all'"
          :class="[
            'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer whitespace-nowrap',
            activeTab === 'all'
              ? 'bg-teal-600 text-white shadow-xs'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          All
          <span
            :class="[
              'px-2 py-0.5 rounded-full text-[11px] font-bold',
              activeTab === 'all' ? 'bg-teal-700 text-teal-100' : 'bg-slate-200 text-slate-700'
            ]"
          >
            {{ totalCount }}
          </span>
        </button>
      </div>

      <div class="relative min-w-64">
        <Search class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search doctor, procedure, or status..."
          class="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
        />
      </div>
    </div>

    <div v-if="appointmentStore.isLoading && appointmentStore.appointments.length === 0" class="py-16 text-center space-y-3">
      <Loader2 class="w-8 h-8 animate-spin mx-auto text-teal-600" />
      <p class="text-sm font-medium text-slate-500">Loading your appointment records...</p>
    </div>

    <div v-else-if="filteredAppointments.length === 0" class="app-panel p-12 text-center max-w-lg mx-auto space-y-4">
      <div class="w-16 h-16 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
        <CalendarX2 class="w-8 h-8" />
      </div>
      <div>
        <h3 class="text-base font-bold text-slate-900">No Appointments Found</h3>
        <p class="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
          {{
            searchQuery
              ? 'No appointments matched your search query.'
              : activeTab === 'upcoming'
                ? 'You do not have any upcoming consultations scheduled.'
                : 'No appointment history records found in this category.'
          }}
        </p>
      </div>
      <div class="pt-2">
        <router-link
          to="/portal/book"
          class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl app-primary-action font-semibold text-xs transition shadow-md shadow-teal-600/20"
        >
          <Plus class="w-4 h-4" />
          Schedule a Consultation
        </router-link>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div
        v-for="appt in filteredAppointments"
        :key="appt.id"
        class="app-panel p-5 hover:shadow-md transition-shadow flex flex-col justify-between space-y-4"
      >
        <div class="space-y-3.5">
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-3">
              <img
                v-if="appt.doctor?.photo_url"
                :src="appt.doctor.photo_url"
                :alt="appt.doctor.full_name"
                class="w-11 h-11 rounded-xl object-cover border border-slate-200"
              />
              <div v-else class="w-11 h-11 rounded-xl bg-teal-700 text-white flex items-center justify-center font-bold text-sm shadow-xs">
                {{ appt.doctor?.full_name ? appt.doctor.full_name.charAt(0) : 'D' }}
              </div>

              <div>
                <h3 class="text-sm font-bold text-slate-900 leading-tight">
                  {{ appt.doctor?.full_name || 'Assigned Doctor' }}
                </h3>
                <p class="text-xs text-teal-700 font-medium">
                  {{ appt.doctor?.specialty || 'Orthodontics' }}
                </p>
              </div>
            </div>

            <span
              :class="[
                'px-2.5 py-1 rounded-full text-[11px] font-bold border capitalize shrink-0',
                getStatusBadgeClass(appt.status)
              ]"
            >
              {{ getStatusLabel(appt.status) }}
            </span>
          </div>

          <div class="p-3 bg-slate-50/80 rounded-xl border border-slate-100 space-y-1.5 text-xs">
            <div class="flex items-center gap-2 text-slate-700 font-semibold">
              <Calendar class="w-4 h-4 text-teal-600 shrink-0" />
              <span>{{ appt.formatted_date || formatDate(appt.start_time) }}</span>
            </div>
            <div class="flex items-center gap-2 text-slate-600">
              <Clock class="w-4 h-4 text-slate-400 shrink-0" />
              <span>{{ appt.formatted_time || formatTime(appt.start_time, appt.end_time) }}</span>
            </div>
          </div>

          <div class="space-y-1 text-xs">
            <span class="font-bold text-slate-700 block">Reason for Consultation:</span>
            <p class="text-slate-900 font-medium bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              {{ appt.reason_for_visit || 'General Dental Consultation' }}
            </p>
          </div>

          <div v-if="appt.notes" class="text-xs text-slate-500 bg-amber-50/60 p-2.5 rounded-lg border border-amber-200/50">
            <span class="font-semibold text-amber-900 block">Notes:</span>
            <p class="text-amber-950 mt-0.5">{{ appt.notes }}</p>
          </div>

          <div v-if="appt.status === 'cancelled' && appt.cancellation_reason" class="text-xs bg-rose-50 p-2.5 rounded-lg border border-rose-200 text-rose-800">
            <span class="font-bold block">Cancellation Note:</span>
            <p class="mt-0.5">{{ appt.cancellation_reason }}</p>
          </div>
        </div>

        <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
          <span class="text-[11px] text-slate-400">
            Ref #{{ appt.id }}
          </span>

          <button
            v-if="canCancel(appt)"
            type="button"
            @click="openCancelModal(appt)"
            class="text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-3 py-1.5 rounded-lg transition cursor-pointer"
          >
            Cancel Appointment
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="cancellingAppointment"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs"
    >
      <div class="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-5 animate-in fade-in duration-200">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2 text-rose-600">
            <AlertTriangle class="w-5 h-5" />
            <h3 class="text-base font-bold text-slate-900">Cancel Appointment</h3>
          </div>
          <button
            type="button"
            @click="closeCancelModal"
            class="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <p class="text-xs text-slate-600 leading-relaxed">
          Are you sure you want to cancel your consultation with <strong class="text-slate-900">{{ cancellingAppointment.doctor?.full_name }}</strong> scheduled for <strong class="text-slate-900">{{ cancellingAppointment.formatted_date || formatDate(cancellingAppointment.start_time) }}</strong>?
        </p>

        <div class="space-y-2">
          <label class="block text-xs font-bold text-slate-700">Reason for Cancellation</label>
          <div class="flex flex-wrap gap-1.5 mb-2">
            <button
              v-for="r in presetCancelReasons"
              :key="r"
              type="button"
              @click="cancellationReason = r"
              :class="[
                'px-2.5 py-1 rounded-lg text-[11px] font-medium transition cursor-pointer',
                cancellationReason === r
                  ? 'bg-rose-600 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              ]"
            >
              {{ r }}
            </button>
          </div>
          <input
            v-model="cancellationReason"
            type="text"
            required
            class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-transparent transition"
            placeholder="Please specify a reason"
          />
        </div>

        <div v-if="cancelError" class="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ cancelError }}</span>
        </div>

        <div class="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            @click="closeCancelModal"
            :disabled="isCancelling"
            class="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-700 text-xs font-semibold hover:bg-slate-50 transition cursor-pointer"
          >
            Keep Appointment
          </button>

          <button
            type="button"
            @click="handleConfirmCancel"
            :disabled="isCancelling || !cancellationReason.trim()"
            class="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold transition cursor-pointer shadow-md shadow-rose-600/20 disabled:opacity-50 flex items-center gap-1.5"
          >
            <Loader2 v-if="isCancelling" class="w-3.5 h-3.5 animate-spin" />
            <span>{{ isCancelling ? 'Cancelling...' : 'Confirm Cancellation' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

