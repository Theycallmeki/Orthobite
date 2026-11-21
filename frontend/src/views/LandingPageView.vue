<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CalendarDays, ChevronDown } from 'lucide-vue-next'
import Button from 'primevue/button'
import { doctorsApi, type DoctorPublicResponse } from '@/api/doctor'
import AppBrand from '@/components/AppBrand.vue'
import DoctorAvailabilityCard from '@/components/DoctorAvailabilityCard.vue'

const clinicDate = new Intl.DateTimeFormat('en-GB', {
  year: 'numeric',
  month: 'numeric',
  timeZone: 'Asia/Manila',
}).formatToParts()
const year = Number(clinicDate.find((part) => part.type === 'year')?.value)
const month = Number(clinicDate.find((part) => part.type === 'month')?.value)
const monthOffset = ref(0)
const selectedMonth = computed(() => new Date(Date.UTC(year, month - 1 + monthOffset.value, 1)))
const monthKey = computed(() => selectedMonth.value.toISOString().slice(0, 7))
const monthLabel = computed(() =>
  selectedMonth.value.toLocaleDateString('en-PH', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }),
)

const doctors = ref<DoctorPublicResponse[]>([])
const selectedDoctorId = ref<number | null>(null)
const selectedDoctor = computed(() => doctors.value.find((doctor) => doctor.id === selectedDoctorId.value))
const loading = ref(true)
const failed = ref(false)

async function loadDoctors() {
  loading.value = true
  failed.value = false
  try {
    const { data } = await doctorsApi.listPublicDoctors()
    doctors.value = data
    selectedDoctorId.value = selectedDoctor.value?.id ?? data[0]?.id ?? null
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(loadDoctors)
</script>

<template>
  <div class="app-backdrop min-h-screen">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
        <AppBrand />
        <a href="#doctor-availability" class="rounded-md text-sm font-semibold text-teal-800 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700">
          Doctor availability
        </a>
      </div>
    </header>

    <main>
      <section class="mx-auto max-w-6xl px-5 pt-8 sm:px-8 sm:pt-12">
        <div class="app-panel px-5 py-12 text-center sm:px-10 sm:py-16">
          <h1 class="mx-auto max-w-2xl text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-6xl">
            Find a time for your orthodontic visit
          </h1>
          <p class="mx-auto mt-4 max-w-xl leading-relaxed text-slate-600 sm:text-lg">
            See when each doctor is available, then sign in to book your appointment.
          </p>
          <RouterLink v-slot="{ href, navigate }" :to="{ name: 'login' }" custom>
            <Button as="a" :href="href" label="Get Started" class="mt-7 min-h-12 px-7" @click="navigate" />
          </RouterLink>
        </div>
      </section>

      <section id="doctor-availability" aria-labelledby="availability-heading" class="mx-auto max-w-6xl scroll-mt-6 px-5 py-12 sm:px-8 sm:py-16">
        <div class="mb-7 flex flex-col gap-5 border-b border-teal-950/10 pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 id="availability-heading" class="text-3xl font-semibold tracking-tight sm:text-4xl">Doctor availability</h2>
            <p class="mt-2 text-slate-600">Choose a doctor and date to see open appointment times in clinic local time.</p>
          </div>
          <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span class="flex items-center gap-2 font-semibold text-teal-950" aria-live="polite">
              <CalendarDays class="size-5 text-teal-700" aria-hidden="true" />
              {{ monthLabel }}
            </span>
            <div v-if="doctors.length" class="flex gap-2" aria-label="Change availability month" role="group">
              <Button
                type="button"
                label="Previous"
                size="small"
                severity="secondary"
                outlined
                :disabled="monthOffset === 0"
                @click="monthOffset--"
              />
              <Button
                type="button"
                label="Next"
                size="small"
                severity="secondary"
                outlined
                @click="monthOffset++"
              />
            </div>
          </div>
        </div>

        <p v-if="loading" role="status" class="app-panel p-6 text-slate-600">Loading doctors…</p>
        <div v-else-if="failed" class="app-panel p-6">
          <p role="status" class="text-slate-700">Doctor schedules are temporarily unavailable.</p>
          <Button type="button" label="Try again" size="small" outlined class="mt-3" @click="loadDoctors" />
        </div>
        <p v-else-if="!doctors.length" role="status" class="app-panel p-6 text-slate-600">There are no doctors accepting appointments right now.</p>
        <div v-else class="space-y-5">
          <div class="max-w-sm">
            <label for="availability-doctor" class="app-form-label">Doctor</label>
            <div class="relative">
              <select
                id="availability-doctor"
                v-model="selectedDoctorId"
                class="w-full appearance-none rounded-lg border border-slate-300 bg-white py-2.5 pr-10 pl-3 text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
              >
                <option v-for="doctor in doctors" :key="doctor.id" :value="doctor.id">
                  {{ doctor.full_name }}
                </option>
              </select>
              <ChevronDown class="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
            </div>
          </div>
          <DoctorAvailabilityCard
            v-if="selectedDoctor"
            :key="`${selectedDoctor.id}-${monthKey}`"
            :doctor="selectedDoctor"
            :month="monthKey"
          />
        </div>
      </section>
    </main>
  </div>
</template>

