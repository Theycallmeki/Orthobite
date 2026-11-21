<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import DoctorAvailabilityCalendar from '@/components/DoctorAvailabilityCalendar.vue'
import { useDoctorStore } from '@/stores/doctor'
import { useAppointmentStore } from '@/stores/appointment'
import type { DayAvailability, TimeSlot } from '@/api/doctor'
import type { AppointmentResponse } from '@/api/appointment'
import {
  Calendar,
  Clock,
  User,
  Stethoscope,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ArrowRight,
  FileText,
  DollarSign,
  Loader2,
  CalendarCheck,
  RefreshCw,
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const doctorStore = useDoctorStore()
const appointmentStore = useAppointmentStore()

const currentYear = ref<number>(new Date().getFullYear())
const currentMonth = ref<number>(new Date().getMonth() + 1)
const selectedDate = ref<string>('')
const selectedSlot = ref<TimeSlot | null>(null)
const selectedReason = ref('Orthodontic Consultation')
const otherReason = ref('')
const otherReasonInput = ref<HTMLInputElement | null>(null)
const reasonForVisit = computed(() => selectedReason.value === 'Other' ? otherReason.value.trim() : selectedReason.value)
const notes = ref<string>('')
const isSubmitting = ref<boolean>(false)
const bookingSuccessData = ref<AppointmentResponse | null>(null)
const consultationFeeFormat = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' })

const commonReasons = [
  'Orthodontic Consultation',
  'Braces Adjustment',
  'Clear Aligners Check',
  'Retainer Fitting',
  'Bite Alignment Check',
  'Tooth Pain / Emergency',
  'Other',
]

const monthFormatted = computed<string>(() => {
  const m = currentMonth.value < 10 ? `0${currentMonth.value}` : `${currentMonth.value}`
  return `${currentYear.value}-${m}`
})

const monthDisplayName = computed<string>(() => {
  const date = new Date(currentYear.value, currentMonth.value - 1, 1)
  return date.toLocaleString('default', { month: 'long', year: 'numeric' })
})

const isCurrentOrPastMonth = computed<boolean>(() => {
  const now = new Date()
  return (
    currentYear.value < now.getFullYear() ||
    (currentYear.value === now.getFullYear() && currentMonth.value <= now.getMonth() + 1)
  )
})

const availableDays = computed<DayAvailability[]>(() => {
  const availability = doctorStore.availability
  return availability && availability.doctor_id === doctorStore.selectedDoctor?.id && availability.month === monthFormatted.value
    ? availability.days
    : []
})

const selectedDayData = computed<DayAvailability | undefined>(() => {
  return availableDays.value.find((d) => d.date === selectedDate.value)
})

const availableSlotsForSelectedDay = computed<TimeSlot[]>(() => {
  if (!selectedDayData.value) return []
  return selectedDayData.value.slots.filter((s) => s.is_available)
})

const formattedSelectedDateDisplay = computed<string>(() => {
  if (!selectedDate.value) return ''
  const parts = selectedDate.value.split('-')
  if (parts.length !== 3) return selectedDate.value
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]))
  return d.toLocaleDateString('default', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })
})

onMounted(async () => {
  const previousDoctor = doctorStore.selectedDoctor
  if (doctorStore.doctors.length === 0) {
    await doctorStore.fetchPublicDoctors().catch(() => {})
  }

  const queryDocId = route.query.doctor_id
  if (queryDocId) {
    const idNum = Number(queryDocId)
    const match = doctorStore.doctors.find((d) => d.id === idNum)
    if (match) {
      doctorStore.selectDoctor(match)
    } else {
      await doctorStore.fetchDoctorById(idNum).catch(() => {})
    }
  } else if (!doctorStore.selectedDoctor && doctorStore.activeDoctors.length > 0) {
    const firstActive = doctorStore.activeDoctors[0]
    if (firstActive) {
      doctorStore.selectDoctor(firstActive)
    }
  }

  if (doctorStore.selectedDoctor && doctorStore.selectedDoctor === previousDoctor) {
    await loadAvailability()
  }
})

watch(
  () => doctorStore.selectedDoctor,
  async (newDoctor) => {
    if (newDoctor) {
      selectedSlot.value = null
      await loadAvailability()
    }
  },
)

async function loadAvailability() {
  if (!doctorStore.selectedDoctor) return
  selectedDate.value = ''
  try {
    await doctorStore.fetchDoctorAvailability(doctorStore.selectedDoctor.id, monthFormatted.value)
    if (availableDays.value.length > 0) {
      const todayStr = new Date().toISOString().split('T')[0] || ''
      const firstWithSlots = availableDays.value.find(
        (d) => d.date >= todayStr && d.slots.some((s) => s.is_available),
      )
      if (firstWithSlots) {
        selectedDate.value = firstWithSlots.date
      } else {
        const firstDay = availableDays.value[0]
        if (firstDay) {
          selectedDate.value = firstDay.date
        }
      }
    }
  } catch {
  }
}

async function handlePrevMonth() {
  if (isCurrentOrPastMonth.value) return
  if (currentMonth.value === 1) {
    currentMonth.value = 12
    currentYear.value -= 1
  } else {
    currentMonth.value -= 1
  }
  selectedSlot.value = null
  await loadAvailability()
}

async function handleNextMonth() {
  if (currentMonth.value === 12) {
    currentMonth.value = 1
    currentYear.value += 1
  } else {
    currentMonth.value += 1
  }
  selectedSlot.value = null
  await loadAvailability()
}

function handleSelectDoctor(event: Event) {
  const id = Number((event.target as HTMLSelectElement).value)
  const doctor = doctorStore.activeDoctors.find((option) => option.id === id)
  if (doctor) doctorStore.selectDoctor(doctor)
}

function handleSelectDay(dateStr: string) {
  selectedDate.value = dateStr
  selectedSlot.value = null
}

function handleSelectSlot(slot: TimeSlot) {
  if (!slot.is_available) return
  selectedSlot.value = slot
}

async function handleConfirmBooking() {
  if (!doctorStore.selectedDoctor || !selectedSlot.value || !reasonForVisit.value || isSubmitting.value) return
  isSubmitting.value = true
  try {
    const res = await appointmentStore.bookAppointment({
      doctor_id: doctorStore.selectedDoctor.id,
      start_time: selectedSlot.value.start_time,
      end_time: selectedSlot.value.end_time,
      reason_for_visit: reasonForVisit.value.trim(),
      notes: notes.value.trim() || undefined,
    })
    bookingSuccessData.value = res
  } catch {
  } finally {
    isSubmitting.value = false
  }
}

async function selectReason(reason: string) {
  selectedReason.value = reason
  if (reason === 'Other') {
    await nextTick()
    otherReasonInput.value?.focus()
  }
}

function handleBookAnother() {
  bookingSuccessData.value = null
  selectedSlot.value = null
  notes.value = ''
  selectedReason.value = 'Orthodontic Consultation'
  otherReason.value = ''
  loadAvailability()
}
</script>

<template>
  <div class="max-w-6xl mx-auto space-y-8 pb-12">
    <div class="app-panel app-page-heading">
      <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
        Book an Orthodontic Appointment
      </h1>
      <p class="text-sm text-slate-500 mt-1">
        Choose your doctor, pick an available calendar slot, and submit your consultation request.
      </p>
    </div>

    <div v-if="bookingSuccessData" class="bg-white rounded-3xl border border-teal-200 p-8 sm:p-10 shadow-xl shadow-teal-900/5 text-center max-w-2xl mx-auto space-y-6">
      <div class="w-16 h-16 rounded-full bg-teal-100 text-teal-600 flex items-center justify-center mx-auto shadow-inner">
        <CalendarCheck class="w-8 h-8" />
      </div>

      <div class="space-y-2">
        <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
          Booking Confirmed
        </span>
        <h2 class="text-2xl font-bold text-slate-900">Appointment Request Submitted</h2>
        <p class="text-slate-600 text-sm max-w-md mx-auto">
          Your appointment request with <strong class="text-slate-900">{{ bookingSuccessData.doctor?.full_name || doctorStore.selectedDoctor?.full_name }}</strong> has been registered. An email notification has been dispatched.
        </p>
      </div>

      <div class="bg-slate-50 rounded-2xl p-5 border border-slate-200/80 text-left space-y-3 text-sm">
        <div class="flex justify-between items-center pb-2 border-b border-slate-200">
          <span class="text-slate-500 font-medium">Appointment Reference</span>
          <span class="font-bold text-slate-900">#{{ bookingSuccessData.id }}</span>
        </div>
        <div class="flex justify-between items-center pb-2 border-b border-slate-200">
          <span class="text-slate-500 font-medium">Doctor</span>
          <span class="font-semibold text-teal-800">{{ bookingSuccessData.doctor?.full_name || doctorStore.selectedDoctor?.full_name }}</span>
        </div>
        <div class="flex justify-between items-center pb-2 border-b border-slate-200">
          <span class="text-slate-500 font-medium">Scheduled Time</span>
          <span class="font-semibold text-slate-900">{{ bookingSuccessData.formatted_date || formattedSelectedDateDisplay }} &bull; {{ bookingSuccessData.formatted_time || selectedSlot?.formatted_time }}</span>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-slate-500 font-medium">Reason for Visit</span>
          <span class="font-medium text-slate-800">{{ bookingSuccessData.reason_for_visit }}</span>
        </div>
      </div>

      <div class="flex flex-col sm:flex-row gap-3 justify-center pt-2">
        <router-link
          to="/portal/appointments"
          class="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-teal-600 text-white font-semibold text-sm hover:bg-teal-700 transition shadow-md shadow-teal-600/20"
        >
          View My Appointments
          <ArrowRight class="w-4 h-4" />
        </router-link>
        <button
          type="button"
          @click="handleBookAnother"
          class="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-semibold text-sm hover:bg-slate-200 transition cursor-pointer"
        >
          <RefreshCw class="w-4 h-4" />
          Book Another
        </button>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <div class="lg:col-span-8 space-y-6">
        <div class="app-panel p-6">
          <div class="flex items-center justify-between pb-4 border-b border-slate-100 mb-5">
            <h2 class="text-base font-bold text-slate-900 flex items-center gap-2">
              <Stethoscope class="w-5 h-5 text-teal-600" />
              Assigned Specialist
            </h2>
          </div>

          <div class="mb-5 max-w-sm">
            <label for="booking-doctor" class="app-form-label">Doctor</label>
            <div class="relative">
              <select
                id="booking-doctor"
                :value="doctorStore.selectedDoctor?.id ?? ''"
                :disabled="doctorStore.isLoading || !doctorStore.activeDoctors.length"
                class="w-full appearance-none rounded-lg border border-slate-300 bg-white py-2.5 pr-10 pl-3 text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700 disabled:bg-slate-50 disabled:text-slate-500"
                @change="handleSelectDoctor"
              >
                <option value="" disabled>Choose a doctor</option>
                <option v-for="doctor in doctorStore.activeDoctors" :key="doctor.id" :value="doctor.id">
                  {{ doctor.full_name }} &middot; {{ doctor.specialty }} &middot; {{ consultationFeeFormat.format(Number(doctor.consultation_fee)) }}
                </option>
              </select>
              <ChevronDown class="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
            </div>
          </div>

          <div v-if="doctorStore.selectedDoctor" class="flex flex-col sm:flex-row items-start sm:items-center gap-4 bg-slate-50/80 p-4 rounded-2xl border border-slate-100">
            <img
              v-if="doctorStore.selectedDoctor.photo_url"
              :src="doctorStore.selectedDoctor.photo_url"
              :alt="doctorStore.selectedDoctor.full_name"
              class="w-16 h-16 rounded-2xl object-cover shadow-xs border border-slate-200"
            />
            <div v-else class="w-16 h-16 rounded-2xl bg-teal-700 text-white flex items-center justify-center font-bold text-xl shadow-xs">
              {{ doctorStore.selectedDoctor.full_name.charAt(0) }}
            </div>

            <div class="flex-1 space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-lg font-bold text-slate-900">{{ doctorStore.selectedDoctor.full_name }}</h3>
                <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-800">
                  {{ doctorStore.selectedDoctor.specialty }}
                </span>
              </div>
              <p class="text-xs text-slate-500 line-clamp-1">
                {{ doctorStore.selectedDoctor.education || 'Board-Certified Orthodontics' }} &bull; {{ doctorStore.selectedDoctor.years_of_experience }} years practice
              </p>
            </div>

            <div class="text-right sm:border-l sm:border-slate-200 sm:pl-4">
              <span class="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">Fee</span>
              <span class="text-lg font-extrabold text-teal-700">{{ consultationFeeFormat.format(Number(doctorStore.selectedDoctor.consultation_fee)) }}</span>
            </div>
          </div>

          <div v-else class="text-center py-6 text-slate-500 text-sm">
            <User class="w-8 h-8 text-slate-300 mx-auto mb-2" />
            Choose a doctor to view their schedule.
          </div>
        </div>

        <div class="app-panel p-6 space-y-6">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Calendar class="w-5 h-5 text-teal-600" />
              <h2 class="text-base font-bold text-slate-900">Select Date & Time</h2>
            </div>

            <div class="flex items-center gap-2">
              <button
                type="button"
                @click="handlePrevMonth"
                :disabled="isCurrentOrPastMonth || doctorStore.isLoading"
                :class="[
                  'p-1.5 rounded-lg border border-slate-200 transition',
                  isCurrentOrPastMonth || doctorStore.isLoading
                    ? 'opacity-40 cursor-not-allowed bg-slate-100 text-slate-400'
                    : 'hover:bg-slate-50 text-slate-700 cursor-pointer'
                ]"
                aria-label="Previous Month"
              >
                <ChevronLeft class="w-4 h-4" />
              </button>

              <span class="text-xs font-bold text-slate-800 min-w-32 text-center">
                {{ monthDisplayName }}
              </span>

              <button
                type="button"
                @click="handleNextMonth"
                :disabled="doctorStore.isLoading"
                :class="[
                  'p-1.5 rounded-lg border border-slate-200 transition',
                  doctorStore.isLoading
                    ? 'opacity-40 cursor-not-allowed bg-slate-100 text-slate-400'
                    : 'hover:bg-slate-50 text-slate-700 cursor-pointer'
                ]"
                aria-label="Next Month"
              >
                <ChevronRight class="w-4 h-4" />
              </button>
            </div>
          </div>

          <div v-if="doctorStore.isLoading" class="py-12 text-center text-slate-400 space-y-2">
            <Loader2 class="w-6 h-6 animate-spin mx-auto text-teal-600" />
            <p class="text-xs font-medium">Checking calendar availability...</p>
          </div>

          <div v-else class="space-y-5">
            <DoctorAvailabilityCalendar
              :model-value="selectedDate"
              :days="availableDays"
              label="Available appointment dates"
              @update:model-value="handleSelectDay"
            />

            <div class="pt-2 border-t border-slate-100">
              <div class="flex items-center justify-between mb-3">
                <span class="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                  <Clock class="w-4 h-4 text-slate-500" />
                  Open time slots &bull; {{ formattedSelectedDateDisplay }}
                </span>
              </div>

              <div v-if="availableSlotsForSelectedDay.length > 0" class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-2.5">
                <button
                  v-for="slot in availableSlotsForSelectedDay"
                  :key="slot.start_time"
                  type="button"
                  @click="handleSelectSlot(slot)"
                  :class="[
                    'py-2.5 px-3 rounded-xl border text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-1.5',
                    selectedSlot?.start_time === slot.start_time
                      ? 'border-teal-600 bg-teal-600 text-white shadow-sm'
                      : 'border-slate-200 bg-white hover:border-teal-400 text-slate-800 hover:bg-teal-50/30'
                  ]"
                >
                  <Clock class="w-3.5 h-3.5" :class="selectedSlot?.start_time === slot.start_time ? 'text-teal-200' : 'text-slate-400'" />
                  {{ slot.formatted_time }}
                </button>
              </div>

              <div v-else class="text-center py-8 bg-slate-50 rounded-2xl border border-slate-100">
                <AlertCircle class="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
                <p class="text-xs font-medium text-slate-600">
                  {{ selectedDayData && (selectedDayData.is_day_off || !selectedDayData.slots.length)
                    ? 'Day off.' : 'No open time slots on this date.' }}
                </p>
                <p class="text-[11px] text-slate-400 mt-0.5">Please choose an alternate day above with available slots.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="lg:col-span-4 space-y-6">
        <div class="app-panel p-6 space-y-5 sticky top-24">
          <div class="flex items-center gap-2 pb-3 border-b border-slate-100">
            <FileText class="w-5 h-5 text-teal-600" />
            <h2 class="text-base font-bold text-slate-900">Consultation Details</h2>
          </div>

          <div class="space-y-2">
            <label class="block text-xs font-bold text-slate-700">Reason for Consultation</label>
            <div class="flex flex-wrap gap-1.5 mb-2">
              <button
                v-for="r in commonReasons"
                :key="r"
                type="button"
                :aria-pressed="selectedReason === r"
                @click="selectReason(r)"
                :class="[
                  'px-2.5 py-1 rounded-lg text-[11px] font-medium transition cursor-pointer',
                  selectedReason === r
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                ]"
              >
                {{ r }}
              </button>
            </div>
            <div v-if="selectedReason === 'Other'">
              <label for="consultation-other" class="app-form-label">Other reason</label>
              <input
                id="consultation-other"
                ref="otherReasonInput"
                v-model="otherReason"
                type="text"
                maxlength="255"
                required
                class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
                placeholder="Describe your reason for visiting"
              />
            </div>
          </div>

          <div class="space-y-1.5">
            <label class="block text-xs font-bold text-slate-700">Clinical Notes (Optional)</label>
            <textarea
              v-model="notes"
              rows="3"
              class="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
              placeholder="Any symptoms, concerns, or previous orthodontic history..."
            ></textarea>
          </div>

          <div class="bg-slate-50 rounded-2xl p-4 border border-slate-200/80 space-y-2 text-xs">
            <div class="flex justify-between text-slate-600">
              <span>Doctor</span>
              <span class="font-bold text-slate-900 truncate max-w-44">{{ doctorStore.selectedDoctor?.full_name || 'None' }}</span>
            </div>
            <div class="flex justify-between text-slate-600">
              <span>Date</span>
              <span class="font-bold text-slate-900">{{ selectedDate || 'Select a date' }}</span>
            </div>
            <div class="flex justify-between text-slate-600">
              <span>Time</span>
              <span class="font-bold text-teal-700">{{ selectedSlot?.formatted_time || 'Select a slot' }}</span>
            </div>
            <div class="flex justify-between text-slate-600 pt-2 border-t border-slate-200 font-semibold">
              <span>Consultation Fee</span>
              <span class="font-extrabold text-slate-900 text-sm">
                {{ consultationFeeFormat.format(Number(doctorStore.selectedDoctor?.consultation_fee ?? 0)) }}
              </span>
            </div>
          </div>

          <div v-if="appointmentStore.bookingError" class="p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2 text-red-700 text-xs">
            <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
            <p>{{ appointmentStore.bookingError }}</p>
          </div>

          <button
            type="button"
            @click="handleConfirmBooking"
            :disabled="!doctorStore.selectedDoctor || !selectedSlot || !reasonForVisit.trim() || isSubmitting"
            :class="[
              'w-full py-3.5 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition shadow-md',
              !doctorStore.selectedDoctor || !selectedSlot || !reasonForVisit.trim() || isSubmitting
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                : 'app-primary-action shadow-teal-600/25 cursor-pointer active:scale-98'
            ]"
          >
            <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
            <CalendarCheck v-else class="w-4 h-4" />
            <span>{{ isSubmitting ? 'Confirming Appointment...' : 'Book Appointment' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
