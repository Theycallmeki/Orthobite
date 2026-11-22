import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { patientsApi, type PatientResponse } from '@/api/patient'

export function useClinicPatientSelection(doctorId?: number) {
  const route = useRoute()
  const router = useRouter()
  const routeName = route.name
  const patients = ref<PatientResponse[]>([])
  const loadingPatients = ref(true)
  const patientLoadError = ref(false)
  const selectedPatient = computed(() => {
    const id = route.query.patient
    if (typeof id !== 'string') return patients.value[0] ?? null
    return patients.value.find((patient) => String(patient.id) === id) ?? null
  })

  function selectPatient(id: number) {
    void router.replace({ query: { ...route.query, patient: String(id) } })
  }

  watch([selectedPatient, () => route.query.patient], ([patient, queryPatient]) => {
    if (route.name === routeName && patient && typeof queryPatient !== 'string') selectPatient(patient.id)
  })

  async function loadPatients() {
    loadingPatients.value = true
    patientLoadError.value = false
    try {
      const pageSize = 100
      const list: PatientResponse[] = []
      for (let skip = 0; ; skip += pageSize) {
        const { data } = await patientsApi.listPatients({ skip, limit: pageSize, doctor_id: doctorId })
        list.push(...data)
        if (data.length < pageSize) break
      }
      patients.value = list
    } catch {
      patientLoadError.value = true
    } finally {
      loadingPatients.value = false
    }
  }

  onMounted(loadPatients)
  return { patients, selectedPatient, selectPatient, loadingPatients, patientLoadError, loadPatients }
}
