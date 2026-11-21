<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { ArrowLeft, Plus, X } from 'lucide-vue-next'
import { doctorsApi, type AvailabilityRule, type TimeOff } from '@/api/doctor'

type WorkingHours = Omit<AvailabilityRule, 'slot_duration_minutes'> & {
  key: number
  slot_duration_minutes: number | ''
}

const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const rules = ref<WorkingHours[]>([])
const timeOff = ref<TimeOff[]>([])
const block = ref({ start: '', end: '', reason: '' })
const loading = ref(false)
const loaded = ref(false)
const savingRules = ref(false)
const changingTimeOff = ref(false)
const loadError = ref('')
const hoursError = ref('')
const timeOffError = ref('')
const hoursNotice = ref('')
const timeOffNotice = ref('')
let nextKey = 0

function setRules(items: AvailabilityRule[]) {
  rules.value = items.filter((item) => item.is_active !== false).map((item) => ({
    ...item,
    key: ++nextKey,
    slot_duration_minutes: item.slot_duration_minutes ?? 30,
  }))
}

function getError(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}

async function loadSchedule() {
  loading.value = true
  loadError.value = ''
  try {
    const [weekly, blocks] = await Promise.all([doctorsApi.getMyAvailabilityRules(), doctorsApi.listMyTimeOff()])
    setRules(weekly.data)
    timeOff.value = blocks.data
    loaded.value = true
  } catch (error) {
    loadError.value = getError(error, 'Could not load your availability.')
  } finally {
    loading.value = false
  }
}

function addHours(day: number) {
  hoursNotice.value = ''
  rules.value.push({
    key: ++nextKey,
    day_of_week: day,
    start_time: '09:00',
    end_time: '17:00',
    slot_duration_minutes: 30,
  })
}

function removeHours(key: number) {
  hoursNotice.value = ''
  rules.value = rules.value.filter((rule) => rule.key !== key)
}

function timeInSeconds(value: string) {
  const [hours = 0, minutes = 0, seconds = 0] = value.split(':').map(Number)
  return hours * 3600 + minutes * 60 + seconds
}

async function saveHours() {
  if (savingRules.value) return
  hoursError.value = ''
  hoursNotice.value = ''
  const sorted = [...rules.value].sort((a, b) =>
    a.day_of_week - b.day_of_week || timeInSeconds(a.start_time) - timeInSeconds(b.start_time),
  )
  for (const [index, rule] of sorted.entries()) {
    const start = timeInSeconds(rule.start_time)
    const end = timeInSeconds(rule.end_time)
    const duration = Number(rule.slot_duration_minutes)
    const day = weekdays[rule.day_of_week]
    if (!rule.start_time || !rule.end_time || duration < 10 || duration > 240 || end - start < duration * 60) {
      hoursError.value = `Choose hours that fit at least one appointment slot on ${day}.`
      return
    }
    const previous = sorted[index - 1]
    if (previous?.day_of_week === rule.day_of_week && start < timeInSeconds(previous.end_time)) {
      hoursError.value = `Hours overlap on ${day}.`
      return
    }
  }

  savingRules.value = true
  try {
    const { data } = await doctorsApi.setMyAvailabilityRules(sorted.map((rule) => ({
      day_of_week: rule.day_of_week,
      start_time: rule.start_time,
      end_time: rule.end_time,
      slot_duration_minutes: Number(rule.slot_duration_minutes),
      is_active: true,
    })))
    setRules(data)
    hoursNotice.value = 'Weekly availability saved.'
  } catch (error) {
    hoursError.value = getError(error, 'Could not save your weekly availability.')
  } finally {
    savingRules.value = false
  }
}

async function addTimeOff() {
  if (changingTimeOff.value) return
  timeOffError.value = ''
  timeOffNotice.value = ''
  if (block.value.start >= block.value.end) {
    timeOffError.value = 'Choose an end date and time after the start.'
    return
  }
  changingTimeOff.value = true
  try {
    const { data } = await doctorsApi.createTimeOff({
      start_datetime: block.value.start,
      end_datetime: block.value.end,
      reason: block.value.reason.trim() || undefined,
    })
    timeOff.value = [...timeOff.value, data].sort((a, b) => a.start_datetime.localeCompare(b.start_datetime))
    block.value = { start: '', end: '', reason: '' }
    timeOffNotice.value = 'Time off added.'
  } catch (error) {
    timeOffError.value = getError(error, 'Could not add this time-off block.')
  } finally {
    changingTimeOff.value = false
  }
}

async function removeTimeOff(id: number) {
  if (changingTimeOff.value) return
  timeOffError.value = ''
  timeOffNotice.value = ''
  changingTimeOff.value = true
  try {
    await doctorsApi.removeTimeOff(id)
    timeOff.value = timeOff.value.filter((item) => item.id !== id)
    timeOffNotice.value = 'Time off removed.'
  } catch (error) {
    timeOffError.value = getError(error, 'Could not remove this time-off block.')
  } finally {
    changingTimeOff.value = false
  }
}

const displayTime = new Intl.DateTimeFormat('en-PH', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'UTC',
})

function formatTimeOff(value: string) {
  return displayTime.format(new Date(`${value.slice(0, 16)}Z`))
}

onMounted(loadSchedule)
</script>

<template>
  <div class="space-y-5 pb-12">
    <header class="app-panel app-page-heading flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-slate-900">My Availability</h1>
        <p class="mt-1 text-sm text-slate-600">Set the times patients can request with you. Times are in Philippine time.</p>
      </div>
      <RouterLink :to="{ name: 'clinic-appointments' }" class="inline-flex items-center gap-2 text-sm font-semibold text-teal-800 hover:underline">
        <ArrowLeft class="size-4" /> Appointments
      </RouterLink>
    </header>

    <div v-if="loadError" class="app-panel space-y-3 p-5">
      <p role="alert" class="text-sm text-rose-700">{{ loadError }}</p>
      <Button type="button" label="Try again" outlined @click="loadSchedule" />
    </div>
    <p v-if="loading" class="app-panel p-5 text-sm text-slate-600" role="status">Loading your availability…</p>

    <template v-if="loaded">
      <form class="app-panel space-y-4 p-5 sm:p-6" @submit.prevent="saveHours" @input="hoursNotice = ''">
        <h2 class="text-lg font-bold text-slate-900">Weekly Hours</h2>
        <fieldset v-for="(day, index) in weekdays" :key="day" :disabled="savingRules" class="space-y-2 rounded-xl border border-slate-200 px-3 pb-3">
          <legend class="px-1 text-sm font-semibold text-slate-800">{{ day }}</legend>
          <div v-for="rule in rules.filter((item) => item.day_of_week === index)" :key="rule.key" class="grid grid-cols-2 items-end gap-2 sm:grid-cols-[1fr_1fr_1fr_auto]">
            <label class="text-xs font-medium text-slate-700">
              Start
              <input v-model="rule.start_time" type="time" step="1" required class="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2" />
            </label>
            <label class="text-xs font-medium text-slate-700">
              End
              <input v-model="rule.end_time" type="time" step="1" required class="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2" />
            </label>
            <label class="text-xs font-medium text-slate-700">
              Slot length (minutes)
              <input v-model.number="rule.slot_duration_minutes" type="number" min="10" max="240" required class="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2" />
            </label>
            <Button type="button" severity="secondary" text :aria-label="`Remove ${day} hours`" @click="removeHours(rule.key)">
              <X class="size-4" aria-hidden="true" />
            </Button>
          </div>
          <div class="flex flex-wrap items-center gap-3">
            <span v-if="!rules.some((rule) => rule.day_of_week === index)" class="text-sm text-slate-500">Day off</span>
            <Button type="button" :aria-label="`Add ${day} hours`" size="small" text @click="addHours(index)">
              <Plus class="size-4" aria-hidden="true" /> Add hours
            </Button>
          </div>
        </fieldset>
        <p v-if="hoursError" role="alert" class="text-sm text-rose-700">{{ hoursError }}</p>
        <p v-if="hoursNotice" role="status" class="text-sm text-teal-800">{{ hoursNotice }}</p>
        <Button type="submit" label="Save Weekly Hours" :loading="savingRules" />
      </form>

      <section class="app-panel space-y-4 p-5 sm:p-6">
        <h2 class="text-lg font-bold text-slate-900">Time Off</h2>
        <form class="grid items-end gap-3 sm:grid-cols-2" @submit.prevent="addTimeOff">
          <label class="text-sm font-medium text-slate-700">
            From
            <input v-model="block.start" type="datetime-local" required :disabled="changingTimeOff" class="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2" />
          </label>
          <label class="text-sm font-medium text-slate-700">
            Until
            <input v-model="block.end" type="datetime-local" required :disabled="changingTimeOff" class="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2" />
          </label>
          <label class="text-sm font-medium text-slate-700">
            Reason (optional)
            <input v-model="block.reason" type="text" maxlength="255" :disabled="changingTimeOff" class="mt-1 block w-full rounded-lg border border-slate-200 px-3 py-2" />
          </label>
          <div><Button type="submit" label="Block Time" :disabled="changingTimeOff" /></div>
        </form>
        <p v-if="timeOffError" role="alert" class="text-sm text-rose-700">{{ timeOffError }}</p>
        <p v-if="timeOffNotice" role="status" class="text-sm text-teal-800">{{ timeOffNotice }}</p>
        <p v-if="!timeOff.length" class="text-sm text-slate-500">No time off scheduled.</p>
        <ul v-else class="divide-y divide-slate-100">
          <li v-for="item in timeOff" :key="item.id" class="flex flex-wrap items-center justify-between gap-2 py-3">
            <div class="text-sm text-slate-700">
              <p class="font-medium">{{ formatTimeOff(item.start_datetime) }} to {{ formatTimeOff(item.end_datetime) }}</p>
              <p v-if="item.reason" class="text-slate-500">{{ item.reason }}</p>
            </div>
            <Button v-if="item.id" type="button" label="Remove block" size="small" severity="danger" text :disabled="changingTimeOff" @click="removeTimeOff(item.id)" />
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>
