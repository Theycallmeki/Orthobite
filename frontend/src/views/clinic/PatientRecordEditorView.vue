<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRecordStore } from '@/stores/record'
import { useDoctorStore } from '@/stores/doctor'
import { useAuthStore } from '@/stores/auth'
import { useClinicPatientSelection } from '@/composables/useClinicPatientSelection'
import ToothMatrix from '@/components/ToothMatrix.vue'
import {
  FileText,
  User,
  Stethoscope,
  Calendar,
  DollarSign,
  CheckCircle2,
  AlertCircle,
  Plus,
  RefreshCw,
  Search,
  Layers,
  RotateCcw,
  Loader2,
  BookOpen,
} from 'lucide-vue-next'

const recordStore = useRecordStore()
const doctorStore = useDoctorStore()
const authStore = useAuthStore()

const { patients, selectedPatient, selectPatient, loadingPatients, patientLoadError, loadPatients } = useClinicPatientSelection()
const patientSearchQuery = ref('')

const selectedTeethIds = ref<number[]>([])
const treatmentName = ref<string>('Archwire Replacement (NiTi)')
const toothNumberCustom = ref<string>('')
const valueOfWork = ref<number | ''>(150)
const downPayment = ref<number | ''>('')
const treatmentDate = ref<string>(new Date().toISOString().split('T')[0] || '')
const attendingDoctorId = ref<number | ''>('')
const clinicalNotes = ref<string>('')

const isSubmitting = ref<boolean>(false)
const submitSuccessMessage = ref<string | null>(null)
const submitErrorMessage = ref<string | null>(null)

const procedurePresets = [
  'Braces Placement',
  'Braces Adjustment',
  'Archwire Replacement (NiTi)',
  'Bracket Rebonding / Replacement',
  'Molar Band Cementation',
  'Elastics / Power Chain Placement',
  'Interproximal Reduction (IPR)',
  'Clear Aligner Delivery & Attachments',
  'Retainer Impression & Delivery',
  'Dental Prophylaxis & Scaling',
]

onMounted(async () => {
  if (doctorStore.doctors.length === 0) {
    await doctorStore.fetchPublicDoctors().catch(() => {})
  }

  attendingDoctorId.value = authStore.isDoctor
    ? (authStore.user?.id ?? '')
    : (doctorStore.activeDoctors[0]?.user_id ?? '')

})

watch(selectedTeethIds, (newIds) => {
  if (newIds.length > 0) {
    toothNumberCustom.value = newIds.join(', ')
  }
})

watch(selectedPatient, (patient) => {
  if (patient?.user_id) {
    recordStore.fetchPatientLedger(patient.user_id).catch(() => {})
  }
})

const filteredPatients = computed(() => {
  const query = patientSearchQuery.value.trim().toLowerCase()
  return patients.value.filter((patient) =>
    (patient.user?.full_name ?? '').toLowerCase().includes(query)
    || (patient.user?.email ?? '').toLowerCase().includes(query)
    || String(patient.id).includes(query),
  )
})

const selectedLedger = computed(() => {
  const ledger = recordStore.currentPatientLedger
  return ledger && ledger.patient_id === selectedPatient.value?.user_id ? ledger : null
})

function formatCurrency(val: number | string): string {
  const num = Number(val) || 0
  return new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(num)
}

function handlePresetClick(preset: string) {
  treatmentName.value = preset
}

function resetForm() {
  treatmentName.value = 'Archwire Replacement (NiTi)'
  selectedTeethIds.value = []
  toothNumberCustom.value = ''
  valueOfWork.value = 150
  downPayment.value = ''
  treatmentDate.value = new Date().toISOString().split('T')[0] || ''
  clinicalNotes.value = ''
}

async function handleSaveTreatmentRecord() {
  const targetPatientId = selectedPatient.value?.user_id
  if (isSubmitting.value || !targetPatientId || !treatmentName.value.trim() || valueOfWork.value === '') return

  isSubmitting.value = true
  submitSuccessMessage.value = null
  submitErrorMessage.value = null
  if (downPayment.value !== '' && (downPayment.value < 0 || downPayment.value > valueOfWork.value)) {
    submitErrorMessage.value = 'Enter a down payment between zero and the treatment charge.'
    isSubmitting.value = false
    return
  }

  try {
    const newRecord = await recordStore.createTreatmentRecord({
      patient_id: targetPatientId,
      doctor_id: attendingDoctorId.value ? Number(attendingDoctorId.value) : undefined,
      treatment_name: treatmentName.value.trim(),
      tooth_number: toothNumberCustom.value.trim() || undefined,
      value_of_work: Number(valueOfWork.value),
      down_payment_amount: downPayment.value === '' ? undefined : downPayment.value,
      date: treatmentDate.value || undefined,
      notes: clinicalNotes.value.trim() || undefined,
    })

    resetForm()
    submitSuccessMessage.value = `Treatment procedure #${newRecord.id} recorded successfully.`
  } catch (err: unknown) {
    submitErrorMessage.value =
      (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
      'Failed to record clinical treatment'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="space-y-8 pb-16">
    <div class="app-panel app-page-heading flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Clinical Treatment Record Editor
        </h1>
        <p class="text-sm text-slate-500 mt-1">
          Chart treatment and review the patient's balance.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2.5">
        <RouterLink
          :to="{ name: 'clinic-treatment-history', query: selectedPatient ? { patient: String(selectedPatient.id) } : {} }"
          class="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs font-semibold text-teal-700 hover:bg-teal-50"
        >
          <BookOpen class="size-4" aria-hidden="true" />
          Treatment History
        </RouterLink>
        <button
          type="button"
          @click="resetForm"
          class="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 font-medium text-xs transition cursor-pointer shadow-xs"
        >
          <RotateCcw class="w-3.5 h-3.5" />
          Reset Form
        </button>

        <button
          type="button"
          @click="selectedPatient?.user_id && recordStore.fetchPatientLedger(selectedPatient.user_id)"
          :disabled="recordStore.isLoading || !selectedPatient?.user_id"
          class="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 font-medium text-xs transition cursor-pointer shadow-xs disabled:opacity-50"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': recordStore.isLoading }" />
          Refresh Ledger
        </button>
      </div>
    </div>

    <div class="app-panel p-5 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <User class="w-5 h-5 text-teal-600" />
          <h2 class="text-sm font-extrabold text-slate-900">Patient Selection & Profile</h2>
        </div>

        <div class="relative min-w-64">
          <Search class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            v-model="patientSearchQuery"
            type="text"
            placeholder="Search patient by name or ID..."
            class="w-full pl-9 pr-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 transition"
          />
        </div>
      </div>

      <p v-if="loadingPatients" role="status" class="text-sm text-slate-600">Loading patients...</p>
      <div v-else-if="patientLoadError" class="flex items-center gap-3 text-sm text-rose-700">
        <p role="alert">Could not load patients.</p>
        <button type="button" class="underline" @click="loadPatients">Retry</button>
      </div>
      <div v-else class="grid grid-cols-1 sm:grid-cols-3 md:grid-cols-4 gap-2.5 max-h-40 overflow-y-auto p-1">
        <div
          v-for="pat in filteredPatients"
          :key="pat.id"
          @click="selectPatient(pat.id)"
          :class="[
            'p-3 rounded-2xl border transition cursor-pointer flex items-center gap-3',
            selectedPatient?.id === pat.id
              ? 'border-teal-600 bg-teal-50/80 ring-2 ring-teal-500 shadow-xs'
              : 'border-slate-200 bg-white hover:border-teal-300'
          ]"
        >
          <div class="w-9 h-9 rounded-full bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-xs shrink-0">
            {{ pat.user?.full_name?.charAt(0) || 'P' }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-xs font-bold text-slate-900 truncate">
              {{ pat.user?.full_name || `Patient #${pat.id}` }}
            </p>
            <p class="text-[10px] text-slate-500 truncate">
              ID #{{ pat.user_id || pat.id }} &bull; {{ pat.treatment_stage || 'Consultation' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="selectedLedger" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="app-panel p-5">
        <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Total Billed Procedures</span>
        <span class="text-2xl font-black text-slate-900 mt-1 block">
          {{ formatCurrency(recordStore.totalValueOfWork) }}
        </span>
        <p class="text-[11px] text-slate-400 mt-0.5">Historical work for {{ selectedLedger.patient_name }}</p>
      </div>

      <div class="bg-white rounded-3xl border border-emerald-200 p-5 shadow-xs bg-emerald-50/20">
        <span class="text-[11px] font-bold text-emerald-800 uppercase tracking-wider block">Total Amount Paid</span>
        <span class="text-2xl font-black text-emerald-700 mt-1 block">
          {{ formatCurrency(recordStore.totalPaid) }}
        </span>
        <p class="text-[11px] text-emerald-600 mt-0.5">Verified installments & receipts</p>
      </div>

      <div
        :class="[
          'rounded-3xl border p-5 shadow-xs',
          recordStore.balanceDue > 0
            ? 'bg-amber-50/40 border-amber-200 text-amber-900'
            : 'bg-teal-50/40 border-teal-200 text-teal-900'
        ]"
      >
        <span class="text-[11px] font-bold uppercase tracking-wider block">Outstanding Balance Due</span>
        <span class="text-2xl font-black mt-1 block">
          {{ formatCurrency(recordStore.balanceDue) }}
        </span>
        <p class="text-[11px] opacity-75 mt-0.5">
          {{ recordStore.balanceDue <= 0 ? 'Account settled (Zero Drift)' : 'Current patient balance' }}
        </p>
      </div>
    </div>

    <div class="app-panel p-6 space-y-4">
      <div class="flex items-center gap-2 pb-2 border-b border-slate-100">
        <Layers class="w-5 h-5 text-teal-600" />
        <div>
          <h2 class="text-sm font-extrabold text-slate-900">Interactive Odontogram Chart</h2>
          <p class="text-xs text-slate-500">Click teeth to link affected regions directly to this clinical treatment sheet</p>
        </div>
      </div>

      <ToothMatrix v-model="selectedTeethIds" :show-surfaces="true" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <div class="lg:col-span-7 app-panel p-6 space-y-5">
        <div class="flex items-center gap-2 pb-3 border-b border-slate-100">
          <FileText class="w-5 h-5 text-teal-600" />
          <h2 class="text-sm font-extrabold text-slate-900">Treatment Procedure Details</h2>
        </div>

        <div class="space-y-2">
          <label class="block text-xs font-bold text-slate-700">Quick Procedure Presets</label>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="p in procedurePresets"
              :key="p"
              type="button"
              @click="handlePresetClick(p)"
              :class="[
                'px-2.5 py-1 rounded-lg text-[11px] font-medium transition cursor-pointer',
                treatmentName === p
                  ? 'bg-teal-600 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              ]"
            >
              {{ p }}
            </button>
          </div>
        </div>

        <div class="space-y-1">
          <label class="block text-xs font-bold text-slate-700">Procedure Name *</label>
          <input
            v-model="treatmentName"
            type="text"
            required
            class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            placeholder="e.g. Upper ceramic bracket bonding"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Affected Tooth Numbers</label>
            <input
              v-model="toothNumberCustom"
              type="text"
              class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:ring-2 focus:ring-teal-500 focus:outline-none"
              placeholder="e.g. 11, 21, or selected from matrix above"
            />
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Value of Work (₱) *</label>
            <input
              v-model="valueOfWork"
              type="number"
              step="0.01"
              required
              class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:ring-2 focus:ring-teal-500 focus:outline-none"
              placeholder="0.00"
            />
          </div>
        </div>

        <div class="space-y-1">
          <label for="treatment-down-payment" class="block text-xs font-bold text-slate-700">Required down payment (₱) · Optional</label>
          <input
            id="treatment-down-payment"
            v-model="downPayment"
            type="number"
            min="0"
            :max="valueOfWork === '' ? undefined : valueOfWork"
            step="0.01"
            placeholder="Only for treatments that require a down payment"
            class="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Date of Procedure *</label>
            <input
              v-model="treatmentDate"
              type="date"
              required
              class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            />
          </div>

          <div class="space-y-1">
            <label class="block text-xs font-bold text-slate-700">Attending Specialist</label>
            <select
              v-model="attendingDoctorId"
              class="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs text-slate-900 focus:ring-2 focus:ring-teal-500 focus:outline-none cursor-pointer"
            >
              <option value="">Default / Logged-in Practitioner</option>
              <option
                v-for="doc in doctorStore.activeDoctors"
                :key="doc.id"
                :value="doc.user_id"
              >
                {{ doc.full_name }} ({{ doc.specialty }})
              </option>
            </select>
          </div>
        </div>

        <div class="space-y-1">
          <label class="block text-xs font-bold text-slate-700">Clinical Progress Notes</label>
          <textarea
            v-model="clinicalNotes"
            rows="3"
            class="w-full p-3 rounded-xl border border-slate-200 text-xs text-slate-900 focus:ring-2 focus:ring-teal-500 focus:outline-none"
            placeholder="Document archwire gauges, bracket positions, patient feedback, or hygiene instructions..."
          ></textarea>
        </div>
      </div>

      <div class="lg:col-span-5 space-y-6">
        <div v-if="submitSuccessMessage" class="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2 text-emerald-800 text-xs">
          <CheckCircle2 class="w-4 h-4 shrink-0" />
          <span>{{ submitSuccessMessage }}</span>
        </div>

        <div v-if="submitErrorMessage" class="p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-center gap-2 text-rose-800 text-xs">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ submitErrorMessage }}</span>
        </div>

        <button
          type="button"
          @click="handleSaveTreatmentRecord"
          :disabled="isSubmitting || !selectedPatient?.user_id || !treatmentName.trim() || valueOfWork === ''"
          class="w-full py-4 px-6 rounded-2xl app-primary-action font-extrabold text-sm transition shadow-lg shadow-teal-600/25 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 active:scale-98"
        >
          <Loader2 v-if="isSubmitting" class="w-4 h-4 animate-spin" />
          <CheckCircle2 v-else class="w-4 h-4" />
          <span>{{ isSubmitting ? 'Recording Clinical Sheet...' : 'Save Treatment Record' }}</span>
        </button>
      </div>
    </div>

  </div>
</template>
