<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ChevronDown, Clock } from 'lucide-vue-next'
import Button from 'primevue/button'
import { doctorsApi, type DoctorPublicResponse } from '@/api/doctor'

const props = defineProps<{ doctor: DoctorPublicResponse; month: string }>()

const availableDays = ref<{ date: string; times: string[] }[]>([])
const selectedDate = ref('')
const loading = ref(true)
const failed = ref(false)
const selectedDay = computed(() => availableDays.value.find((day) => day.date === selectedDate.value))
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
    availableDays.value = data.days
      .map((day) => ({
        date: day.date,
        times: [...new Set(day.slots
          .filter((slot) => slot.is_available)
          .sort((a, b) => a.start_time.localeCompare(b.start_time))
          .map((slot) => slot.formatted_time))],
      }))
      .filter((day) => day.times.length > 0)
    selectedDate.value = availableDays.value[0]?.date ?? ''
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadAvailability)
</script>

<template>
  <article class="app-panel p-5 sm:p-6">
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
      <p v-else-if="!selectedDay" class="text-sm text-slate-600">No open appointments this month.</p>
      <template v-else>
        <label :for="`availability-date-${doctor.id}`" class="app-form-label">
          Available dates
        </label>
        <div class="relative mt-1.5">
          <select
            :id="`availability-date-${doctor.id}`"
            v-model="selectedDate"
            class="app-field w-full appearance-none py-2.5 pr-9 pl-3"
          >
            <option v-for="day in availableDays" :key="day.date" :value="day.date">{{ formatDate(day.date) }}</option>
          </select>
          <ChevronDown class="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-slate-600" aria-hidden="true" />
        </div>

        <div class="mt-4" aria-live="polite">
          <p class="flex items-center gap-1.5 text-sm font-semibold text-slate-700">
            <Clock class="size-4 text-teal-700" aria-hidden="true" />
            Open times
          </p>
          <ul class="mt-2 flex flex-wrap gap-2">
            <li v-for="time in selectedDay.times" :key="time" class="rounded-md bg-teal-50 px-2.5 py-1.5 text-sm font-medium whitespace-nowrap text-teal-950">
              {{ time }}
            </li>
          </ul>
        </div>
      </template>
    </div>
  </article>
</template>
