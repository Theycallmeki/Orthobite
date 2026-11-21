<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Clock } from 'lucide-vue-next'
import Button from 'primevue/button'
import { doctorsApi, type DayAvailability, type DoctorPublicResponse } from '@/api/doctor'
import DoctorAvailabilityCalendar from './DoctorAvailabilityCalendar.vue'

const props = defineProps<{ doctor: DoctorPublicResponse; month: string }>()

const days = ref<DayAvailability[]>([])
const selectedDate = ref('')
const loading = ref(true)
const failed = ref(false)
const selectedDay = computed(() => days.value.find((day) => day.date === selectedDate.value))
const openTimes = computed(() => [...new Set(selectedDay.value?.slots
  .filter((slot) => slot.is_available)
  .sort((a, b) => a.start_time.localeCompare(b.start_time))
  .map((slot) => slot.formatted_time))])
const initials = computed(() =>
  props.doctor.full_name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase(),
)

const dateFormat = new Intl.DateTimeFormat('en-PH', {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC',
})

function formatDate(date: string) {
  return dateFormat.format(new Date(`${date}T00:00:00Z`))
}

async function loadAvailability() {
  loading.value = true
  failed.value = false
  try {
    const { data } = await doctorsApi.getDoctorAvailability(props.doctor.id, props.month)
    days.value = data.days
    selectedDate.value = days.value.find((day) => day.slots.some((slot) => slot.is_available))?.date
      ?? days.value[0]?.date ?? ''
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadAvailability)
</script>

<template>
  <article class="grid items-start gap-4 md:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
    <div class="app-panel p-5 sm:p-6">
      <div class="flex items-center gap-3 border-b border-slate-100 pb-4">
        <span aria-hidden="true" class="grid size-12 shrink-0 place-items-center rounded-xl bg-teal-50 font-bold text-teal-800">
          {{ initials }}
        </span>
        <div>
          <h3 class="text-lg font-semibold leading-snug text-slate-900">{{ doctor.full_name }}</h3>
          <p class="text-sm text-slate-600">{{ doctor.specialty }}</p>
        </div>
      </div>

      <div class="mt-4">
        <p v-if="loading" role="status" class="text-sm text-slate-600">Loading available times…</p>
        <div v-else-if="failed">
          <p role="status" class="text-sm text-slate-600">Couldn’t load this schedule.</p>
          <Button type="button" label="Try again" size="small" outlined class="mt-2" @click="loadAvailability" />
        </div>
        <p v-else-if="!days.length" class="text-sm text-slate-600">No schedule for this month.</p>
        <DoctorAvailabilityCalendar v-else v-model="selectedDate" :days="days" :label="`${doctor.full_name} availability`" />
      </div>
    </div>

    <section v-if="selectedDay && !loading && !failed" class="app-panel p-5 sm:p-6">
      <h4 class="flex items-center gap-2 text-lg font-semibold text-slate-900">
        <Clock class="size-5 text-teal-700" aria-hidden="true" />
        Available times
      </h4>
      <div class="mt-2" aria-live="polite">
        <p class="text-sm font-medium text-slate-600">{{ formatDate(selectedDate) }}</p>
        <ul v-if="openTimes.length" aria-label="Open times" class="mt-4 flex flex-wrap gap-2">
          <li v-for="time in openTimes" :key="time" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium whitespace-nowrap text-emerald-950">
            {{ time }}
          </li>
        </ul>
        <p v-else class="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          {{ selectedDay.is_day_off || !selectedDay.slots.length ? 'Day off.' : 'No open times on this date.' }}
        </p>
      </div>
    </section>
  </article>
</template>
