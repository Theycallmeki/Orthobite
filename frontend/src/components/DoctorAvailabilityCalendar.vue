<script setup lang="ts">
import { computed } from 'vue'
import type { DayAvailability } from '@/api/doctor'

const props = defineProps<{ days: DayAvailability[]; label: string }>()
const selectedDate = defineModel<string>({ required: true })

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const firstWeekday = computed(() => props.days[0]?.day_of_week ?? 0)
const dateFormat = new Intl.DateTimeFormat('en-PH', { dateStyle: 'full', timeZone: 'UTC' })
const statuses = {
  available: { label: 'Available', color: 'border-emerald-200 bg-emerald-50 text-emerald-900' },
  unavailable: { label: 'Unavailable or fully booked', color: 'border-rose-200 bg-rose-50 text-rose-900' },
  off: { label: 'Day off', color: 'border-slate-200 bg-white text-slate-700' },
}

const calendarDays = computed(() => props.days.map((day) => {
  const status = day.slots.some((slot) => slot.is_available)
    ? statuses.available
    : day.is_day_off || !day.slots.length ? statuses.off : statuses.unavailable
  return {
    ...day,
    status,
    label: `${dateFormat.format(new Date(`${day.date}T00:00:00Z`))}, ${status.label}`,
  }
}))
</script>

<template>
  <div role="group" :aria-label="label">
    <div class="grid grid-cols-7 gap-1 text-center">
      <span v-for="weekday in weekdays" :key="weekday" aria-hidden="true" class="py-1 text-xs font-semibold text-slate-600">
        {{ weekday }}
      </span>
      <span v-for="empty in firstWeekday" :key="`blank-${empty}`" aria-hidden="true"></span>
      <button
        v-for="day in calendarDays"
        :key="day.date"
        type="button"
        :aria-pressed="selectedDate === day.date"
        :aria-label="day.label"
        class="min-h-9 rounded-md border text-sm font-semibold transition hover:shadow-sm focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-teal-700"
        :class="[day.status.color, { 'ring-2 ring-inset ring-teal-700': selectedDate === day.date }]"
        @click="selectedDate = day.date"
      >
        {{ Number(day.date.slice(-2)) }}
      </button>
    </div>
    <ul class="mt-3 flex flex-wrap gap-x-3 gap-y-1.5 text-xs text-slate-700">
      <li v-for="status in statuses" :key="status.label" class="flex items-center gap-1.5">
        <span aria-hidden="true" class="size-3 rounded-sm border" :class="status.color"></span>
        {{ status.label }}
      </li>
    </ul>
  </div>
</template>
