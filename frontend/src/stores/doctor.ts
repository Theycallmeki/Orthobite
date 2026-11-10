import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  doctorsApi,
  type DoctorPublicResponse,
  type DoctorAvailabilityResponse,
  type AvailabilityRule,
  type TimeOff,
  type TimeOffCreate,
  type DoctorProfileUpdate,
} from '@/api/doctor'

function extractError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || fallback
}

export const useDoctorStore = defineStore('doctor', () => {
  const doctors = ref<DoctorPublicResponse[]>([])
  const selectedDoctor = ref<DoctorPublicResponse | null>(null)
  const availability = ref<DoctorAvailabilityResponse | null>(null)
  const myProfile = ref<DoctorPublicResponse | null>(null)
  const myAvailabilityRules = ref<AvailabilityRule[]>([])
  const myTimeOff = ref<TimeOff[]>([])
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  const availabilitySlots = computed<Record<string, string[]>>(
    () => availability.value?.available_slots || {},
  )

  const activeDoctors = computed<DoctorPublicResponse[]>(() =>
    doctors.value.filter((d) => d.is_accepting_patients),
  )

  const hasAvailableSlots = computed<boolean>(() =>
    Object.values(availabilitySlots.value).some((slots) => slots.length > 0),
  )

  function selectDoctor(doctor: DoctorPublicResponse | null): void {
    selectedDoctor.value = doctor
    if (!doctor) {
      availability.value = null
    }
  }

  function clearAvailability(): void {
    availability.value = null
  }

  async function fetchPublicDoctors(): Promise<DoctorPublicResponse[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.listPublicDoctors()
      doctors.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch doctors')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchDoctorById(doctorId: number): Promise<DoctorPublicResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.getDoctorById(doctorId)
      selectedDoctor.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch doctor profile')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchDoctorAvailability(
    doctorId: number,
    month?: string,
  ): Promise<DoctorAvailabilityResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.getDoctorAvailability(doctorId, month)
      availability.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load doctor availability')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMyProfile(): Promise<DoctorPublicResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.getMyDoctorProfile()
      myProfile.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load your doctor profile')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updateMyProfile(payload: DoctorProfileUpdate): Promise<DoctorPublicResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.updateMyDoctorProfile(payload)
      myProfile.value = response.data
      const idx = doctors.value.findIndex((d) => d.id === response.data.id)
      if (idx !== -1) {
        doctors.value[idx] = response.data
      }
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to update doctor profile')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMyRules(): Promise<AvailabilityRule[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.getMyAvailabilityRules()
      myAvailabilityRules.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch availability rules')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function saveMyRules(rules: AvailabilityRule[]): Promise<AvailabilityRule[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.setMyAvailabilityRules(rules)
      myAvailabilityRules.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to save availability rules')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMyTimeOff(): Promise<TimeOff[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.listMyTimeOff()
      myTimeOff.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to fetch scheduled time off')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function addTimeOff(payload: TimeOffCreate): Promise<TimeOff> {
    isLoading.value = true
    error.value = null
    try {
      const response = await doctorsApi.createTimeOff(payload)
      myTimeOff.value.push(response.data)
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to schedule time off')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    doctors,
    selectedDoctor,
    availability,
    availabilitySlots,
    myProfile,
    myAvailabilityRules,
    myTimeOff,
    isLoading,
    error,
    activeDoctors,
    hasAvailableSlots,
    selectDoctor,
    clearAvailability,
    fetchPublicDoctors,
    fetchDoctorById,
    fetchDoctorAvailability,
    fetchMyProfile,
    updateMyProfile,
    fetchMyRules,
    saveMyRules,
    fetchMyTimeOff,
    addTimeOff,
  }
})

