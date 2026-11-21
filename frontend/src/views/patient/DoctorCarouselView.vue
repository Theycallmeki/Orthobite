<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import { useDoctorStore } from '@/stores/doctor'
import { useAuthStore } from '@/stores/auth'
import type { DoctorPublicResponse } from '@/api/doctor'
import {
  Calendar,
  Award,
  GraduationCap,
  BookOpen,
  ChevronRight,
  UserCheck,
} from 'lucide-vue-next'

const doctorStore = useDoctorStore()
const authStore = useAuthStore()
const router = useRouter()

const selectedSpecialty = ref<string>('All')

onMounted(() => {
  doctorStore.fetchPublicDoctors().catch(() => {})
})

const specialties = computed<string[]>(() => {
  const set = new Set<string>()
  doctorStore.activeDoctors.forEach((d) => {
    if (d.specialty) {
      set.add(d.specialty)
    }
  })
  return ['All', ...Array.from(set)]
})

const filteredDoctors = computed<DoctorPublicResponse[]>(() => {
  if (selectedSpecialty.value === 'All') {
    return doctorStore.activeDoctors
  }
  return doctorStore.activeDoctors.filter((d) => d.specialty === selectedSpecialty.value)
})

function handleBookDoctor(doctor: DoctorPublicResponse) {
  doctorStore.selectDoctor(doctor)
  router.push('/portal/book')
}
</script>

<template>
  <div class="space-y-8">
    <div class="app-panel app-page-heading">
      <div class="max-w-2xl space-y-3">
        <h1 class="text-2xl font-bold tracking-tight text-slate-900">
          Welcome, {{ authStore.user?.full_name || 'Patient' }}
        </h1>

        <p class="text-sm leading-relaxed text-slate-600">
          Book orthodontic consultations, discover dental specialists, track procedure history, and communicate in real time with our clinical care team.
        </p>

        <div class="pt-3 flex flex-wrap gap-3">
          <RouterLink v-slot="{ href, navigate }" to="/portal/book" custom>
            <Button as="a" :href="href" size="small" @click="navigate">
              <Calendar class="size-4" aria-hidden="true" />
              Book Consultation
            </Button>
          </RouterLink>
          <RouterLink v-slot="{ href, navigate }" to="/portal/records" custom>
            <Button as="a" :href="href" size="small" severity="secondary" outlined @click="navigate">
              <BookOpen class="size-4" aria-hidden="true" />
              Treatment Ledger
            </Button>
          </RouterLink>
        </div>
      </div>
    </div>

    <div>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h2 class="text-xl font-bold text-slate-900">Dental & Orthodontic Specialists</h2>
          <p class="text-xs text-slate-500 mt-0.5">Select a practitioner to inspect available calendar slots</p>
        </div>

        <div class="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <button
            v-for="spec in specialties"
            :key="spec"
            @click="selectedSpecialty = spec"
            class="px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-colors cursor-pointer"
            :class="selectedSpecialty === spec
              ? 'bg-teal-600 text-white shadow-xs'
              : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'"
          >
            {{ spec }}
          </button>
        </div>
      </div>

      <div v-if="doctorStore.isLoading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="i in 3" :key="i" class="app-panel p-6 animate-pulse space-y-4">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 bg-slate-200 rounded-2xl"></div>
            <div class="space-y-2 flex-1">
              <div class="h-4 bg-slate-200 rounded-md w-3/4"></div>
              <div class="h-3 bg-slate-200 rounded-md w-1/2"></div>
            </div>
          </div>
          <div class="h-10 bg-slate-100 rounded-lg"></div>
        </div>
      </div>

      <div
        v-else-if="filteredDoctors.length === 0"
        class="app-panel p-12 text-center space-y-2"
      >
        <UserCheck class="w-10 h-10 text-slate-300 mx-auto" />
        <h3 class="text-sm font-semibold text-slate-800">No specialists found</h3>
        <p class="text-xs text-slate-500 max-w-sm mx-auto">
          No practitioners currently match the selected specialty filter.
        </p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="doctor in filteredDoctors"
          :key="doctor.id"
          class="app-panel p-6 flex flex-col justify-between hover:shadow-md transition-all duration-200 group"
        >
          <div class="space-y-4">
            <div class="flex items-start gap-4">
              <div class="w-14 h-14 rounded-2xl bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-700 font-bold text-xl shrink-0 group-hover:bg-teal-600 group-hover:text-white transition-colors">
                {{ doctor.full_name.charAt(0) }}
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="font-bold text-slate-900 leading-tight truncate">{{ doctor.full_name }}</h3>
                <span class="inline-block mt-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-teal-50 text-teal-700">
                  {{ doctor.specialty }}
                </span>
                <div class="flex items-center gap-3 text-xs text-slate-500 mt-2">
                  <span class="flex items-center gap-1">
                    <Award class="w-3.5 h-3.5 text-slate-400" />
                    {{ doctor.years_of_experience }} yrs
                  </span>
                  <span v-if="doctor.education" class="flex items-center gap-1 truncate" :title="doctor.education">
                    <GraduationCap class="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    {{ doctor.education }}
                  </span>
                </div>
              </div>
            </div>

            <p v-if="doctor.bio" class="text-xs text-slate-600 line-clamp-2 leading-relaxed">
              {{ doctor.bio }}
            </p>
          </div>

          <div class="pt-5 mt-5 border-t border-slate-100 flex items-center justify-between">
            <div>
              <div class="text-[10px] uppercase font-bold text-slate-400">Consultation</div>
              <div class="text-base font-extrabold text-slate-900">
                ₱{{ Number(doctor.consultation_fee).toLocaleString() }}
              </div>
            </div>

            <button
              @click="handleBookDoctor(doctor)"
              class="inline-flex items-center gap-1.5 px-4 py-2 app-primary-action text-xs font-semibold rounded-xl shadow-xs transition-colors cursor-pointer"
            >
              <span>Book Visit</span>
              <ChevronRight class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

