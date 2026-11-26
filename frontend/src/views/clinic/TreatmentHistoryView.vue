<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { BookOpen, CreditCard } from 'lucide-vue-next'
import { API_BASE_URL } from '@/api/api'
import { recordsApi, type PatientLedgerSummary, type PaymentResponse, type TreatmentRecordResponse } from '@/api/record'
import RecordPaymentDialog from '@/components/RecordPaymentDialog.vue'
import TreatmentRecordDetails from '@/components/TreatmentRecordDetails.vue'
import { useClinicPatientSelection } from '@/composables/useClinicPatientSelection'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const { patients, selectedPatient, selectPatient, loadingPatients, patientLoadError, loadPatients, patientLinkQuery } = useClinicPatientSelection()
const ledger = ref<PatientLedgerSummary | null>(null)
const activeTab = ref('history')
const recordViews = ['Cards', 'Table'] as const
const recordView = computed(() => route.query.view === 'table' ? 'Table' : 'Cards')
const expandedTreatmentId = ref<number | null>(null)
const loadingHistory = ref(false)
const historyError = ref('')
const paymentTarget = ref<TreatmentRecordResponse | null>(null)
const paymentStatus = ref('')
const paymentError = ref('')
const isLoadingConsent = ref(false)
const previewSignatureModalUrl = ref<string | null>(null)
const termsTarget = ref<TreatmentRecordResponse | null>(null)
const downPaymentDraft = ref('')
const termsSaving = ref(false)
const termsError = ref('')
let historyRequest = 0
let signatureRequest = 0
const currency = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' })
const patientTreatments = computed(() => ledger.value?.treatments ?? [])
const savedPaymentSignature = computed(() => ledger.value?.all_payments.find((payment) => payment.has_consent))
const balanceRecords = computed(() => patientTreatments.value
  .filter((record) => Number(record.balance) > 0 || Number(record.down_payment_amount ?? 0) > 0)
  .sort((first, second) => downPaymentDue(second) - downPaymentDue(first)),
)
const showBalanceActions = computed(() => authStore.isDoctor || authStore.isSecretary)

function setRecordView(view: typeof recordViews[number]) {
  if (recordView.value === view) return
  expandedTreatmentId.value = null
  void router.replace({ query: { ...route.query, view: view === 'Table' ? 'table' : undefined } })
}

function hasRecordDetails(record: TreatmentRecordResponse) {
  return Boolean(record.notes || record.payments.length || record.signature_url)
}

function canRecordPayment(record: TreatmentRecordResponse) {
  return authStore.isSecretary && Number(record.balance) > 0
}

function formatCurrency(value: number | string) {
  return currency.format(Number(value))
}

function formatDate(value: string) {
  const date = new Date(value.length === 10 ? value + 'T00:00:00' : value)
  return date.toLocaleDateString('en-PH', { month: 'short', day: 'numeric', year: 'numeric' })
}

function downPaymentDue(record: TreatmentRecordResponse) {
  return Math.max(0, Math.round(Number(record.down_payment_amount ?? 0) * 100) - Math.round(Number(record.total_paid) * 100)) / 100
}

async function loadHistory() {
  const id = selectedPatient.value?.user_id
  if (!id) return
  const request = ++historyRequest
  loadingHistory.value = true
  historyError.value = ''
  try {
    const { data } = await recordsApi.getPatientLedger(id)
    if (request === historyRequest && data.patient_id === id) ledger.value = data
  } catch {
    if (request === historyRequest) historyError.value = 'Could not load the treatment history.'
  } finally {
    if (request === historyRequest) loadingHistory.value = false
  }
}

function openPayment(record: TreatmentRecordResponse) {
  paymentTarget.value = record
  paymentStatus.value = ''
  paymentError.value = ''
}

function finishPayment(payment: PaymentResponse) {
  paymentTarget.value = null
  paymentStatus.value = payment.has_consent ? 'Payment and signature saved.' : 'Payment saved.'
  void loadHistory()
}

function editTerms(record: TreatmentRecordResponse) {
  termsTarget.value = record
  downPaymentDraft.value = record.down_payment_amount == null ? '' : Number(record.down_payment_amount).toFixed(2)
  termsError.value = ''
  paymentStatus.value = ''
}

async function saveTerms() {
  const target = termsTarget.value
  if (!target || termsSaving.value) return
  termsSaving.value = true
  termsError.value = ''
  try {
    await recordsApi.updateTreatmentRecord(target.id, { down_payment_amount: downPaymentDraft.value.trim() || null })
    if (termsTarget.value !== target) return
    termsTarget.value = null
    paymentStatus.value = 'Down payment updated.'
    void loadHistory()
  } catch (error) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
    termsError.value = typeof detail === 'string' ? detail : 'Could not update the down payment.'
  } finally {
    termsSaving.value = false
  }
}

function closeSignaturePreview() {
  signatureRequest++
  const url = previewSignatureModalUrl.value
  if (url?.startsWith('blob:')) URL.revokeObjectURL(url)
  previewSignatureModalUrl.value = null
  isLoadingConsent.value = false
}

async function viewPaymentConsent(paymentId: number) {
  closeSignaturePreview()
  const request = signatureRequest
  isLoadingConsent.value = true
  paymentError.value = ''
  try {
    const { data } = await recordsApi.getPaymentConsent(paymentId)
    if (request === signatureRequest) previewSignatureModalUrl.value = URL.createObjectURL(data)
  } catch {
    if (request === signatureRequest) paymentError.value = 'Could not load the payment signature.'
  } finally {
    if (request === signatureRequest) isLoadingConsent.value = false
  }
}

function viewTreatmentSignature(url: string) {
  closeSignaturePreview()
  previewSignatureModalUrl.value = url.startsWith('/') ? API_BASE_URL.replace(/\/$/, '') + url : url
}

watch(selectedPatient, () => {
  historyRequest++
  ledger.value = null
  loadingHistory.value = false
  historyError.value = ''
  expandedTreatmentId.value = null
  paymentTarget.value = null
  paymentStatus.value = ''
  paymentError.value = ''
  termsTarget.value = null
  closeSignaturePreview()
  void loadHistory()
})
onBeforeUnmount(() => {
  historyRequest++
  closeSignaturePreview()
})
</script>

<template>
  <div class="space-y-5 pb-12">
    <section class="app-panel app-page-heading">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <h1 class="text-2xl font-bold tracking-tight text-slate-900">
          Treatment History<span v-if="selectedPatient?.user?.full_name"> for {{ selectedPatient.user.full_name }}</span>
        </h1>
        <RouterLink
          :to="{ name: 'clinic-records', query: patientLinkQuery }"
          class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-teal-700 hover:bg-teal-50"
        >
          Record Editor
        </RouterLink>
      </div>
      <div class="mt-4 max-w-md">
        <label for="history-patient" class="app-form-label">Patient</label>
        <select
          id="history-patient"
          :value="selectedPatient?.id ?? ''"
          :disabled="loadingPatients || !patients.length"
          class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 focus-visible:outline-2 focus-visible:outline-teal-700"
          @change="selectPatient(Number(($event.target as HTMLSelectElement).value))"
        >
          <option value="" disabled>{{ loadingPatients ? 'Loading patients...' : 'Choose a patient' }}</option>
          <option v-for="patient in patients" :key="patient.id" :value="patient.id">
            {{ patient.user?.full_name || 'Patient #' + patient.id }} &middot; #{{ patient.id }}
          </option>
        </select>
      </div>
    </section>

    <div v-if="patientLoadError || historyError" class="app-panel flex items-center gap-3 p-4">
      <p role="alert" class="text-sm text-rose-700">{{ patientLoadError ? 'Could not load patients.' : historyError }}</p>
      <Button type="button" label="Retry" size="small" text @click="patientLoadError ? loadPatients() : loadHistory()" />
    </div>
    <p v-else-if="loadingHistory" role="status" class="app-panel p-4 text-sm text-slate-600">Loading treatment history...</p>
    <p v-else-if="selectedPatient && !selectedPatient.user_id" class="app-panel p-4 text-sm text-slate-600">This profile is not linked to a patient account.</p>
    <p v-else-if="!selectedPatient && !loadingPatients" class="app-panel p-4 text-sm text-slate-600">
      {{ patients.length ? 'Choose a patient to view their treatment history.' : 'No patients found.' }}
    </p>

    <template v-if="ledger">
      <p v-if="paymentStatus" role="status" class="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{{ paymentStatus }}</p>
      <p v-if="paymentError" role="alert" class="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{{ paymentError }}</p>
      <Tabs v-model:value="activeTab" lazy scrollable>
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
          <TabList class="min-w-0 sm:flex-1">
            <Tab value="history">Treatment History</Tab>
            <Tab value="balance">Down Payments &amp; Balances</Tab>
          </TabList>
          <div role="group" aria-label="Record view" class="inline-flex self-end rounded-lg border border-slate-200 bg-white p-0.5 sm:self-auto">
            <button
              v-for="view in recordViews"
              :key="view"
              type="button"
              :aria-pressed="recordView === view"
              class="rounded-md px-3 py-1.5 text-xs font-semibold focus-visible:outline-2 focus-visible:outline-teal-700"
              :class="recordView === view ? 'bg-teal-50 text-teal-800' : 'text-slate-600 hover:bg-slate-50'"
              @click="setRecordView(view)"
            >
              {{ view }}
            </button>
          </div>
        </div>
        <TabPanels class="bg-transparent px-0 pb-0">
          <TabPanel value="history">
            <div v-if="ledger" class="app-panel p-6 space-y-4">
              <div class="flex items-center justify-between pb-3 border-b border-slate-100">
                <div class="flex items-center gap-2">
                  <BookOpen class="w-5 h-5 text-teal-600" />
                  <div>
                    <h2 class="text-sm font-extrabold text-slate-900">Procedures and installments</h2>
                  </div>
                </div>

                <span class="text-xs font-bold text-slate-500">
                  {{ patientTreatments.length }} Record(s)
                </span>
              </div>

              <div v-if="patientTreatments.length === 0" class="py-12 text-center text-xs text-slate-400 space-y-2">
                <BookOpen class="w-6 h-6 mx-auto text-slate-300" />
                <p>No prior treatment records logged for this patient.</p>
              </div>

              <div v-else-if="recordView === 'Table'" tabindex="0" role="region" aria-label="Treatment records table"
                class="max-h-96 overflow-auto rounded-lg border border-slate-200 focus-visible:outline-2 focus-visible:outline-teal-700">
                <table aria-label="Treatment records" class="w-full min-w-[48rem] text-left text-sm">
                  <thead class="sticky top-0 z-10 bg-slate-50 text-xs text-slate-700 shadow-xs">
                    <tr>
                      <th scope="col" class="px-3 py-2">Procedure</th>
                      <th scope="col" class="px-3 py-2">Date</th>
                      <th scope="col" class="px-3 py-2">Doctor</th>
                      <th scope="col" class="px-3 py-2 text-right">Fee</th>
                      <th scope="col" class="px-3 py-2 text-right">Paid</th>
                      <th scope="col" class="px-3 py-2 text-right">Remaining</th>
                      <th scope="col" class="px-3 py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-200">
                    <template v-for="rec in patientTreatments" :key="rec.id">
                      <tr>
                        <th scope="row" class="px-3 py-2 text-slate-900">
                          {{ rec.treatment_name }}
                          <span v-if="rec.tooth_number" class="block text-xs font-normal text-slate-600">Tooth #{{ rec.tooth_number }}</span>
                        </th>
                        <td class="px-3 py-2 whitespace-nowrap text-slate-600">{{ formatDate(rec.date) }}</td>
                        <td class="px-3 py-2 text-slate-600">{{ rec.doctor_name || '—' }}</td>
                        <td class="px-3 py-2 text-right whitespace-nowrap tabular-nums">{{ formatCurrency(rec.value_of_work) }}</td>
                        <td class="px-3 py-2 text-right whitespace-nowrap tabular-nums text-emerald-700">{{ formatCurrency(rec.total_paid) }}</td>
                        <td class="px-3 py-2 text-right whitespace-nowrap tabular-nums">{{ formatCurrency(rec.balance) }}</td>
                        <td class="px-3 py-2">
                          <div v-if="hasRecordDetails(rec) || canRecordPayment(rec)" class="flex flex-wrap items-center gap-1">
                            <Button v-if="hasRecordDetails(rec)" type="button" label="Details" size="small" text
                              :aria-label="`Details for ${rec.treatment_name}`" :aria-expanded="expandedTreatmentId === rec.id"
                              @click="expandedTreatmentId = expandedTreatmentId === rec.id ? null : rec.id" />
                            <Button v-if="canRecordPayment(rec)" type="button" label="Record Payment" size="small" @click="openPayment(rec)" />
                          </div>
                          <span v-else class="text-slate-600">—</span>
                        </td>
                      </tr>
                      <tr v-if="expandedTreatmentId === rec.id && hasRecordDetails(rec)">
                        <td colspan="7" class="bg-slate-50 px-3 py-3">
                          <TreatmentRecordDetails
                            :record="rec"
                            :loading-consent="isLoadingConsent"
                            :format-date="formatDate"
                            :format-currency="formatCurrency"
                            @view-payment-consent="viewPaymentConsent"
                            @view-treatment-signature="viewTreatmentSignature"
                          />
                        </td>
                      </tr>
                    </template>
                  </tbody>
                </table>
              </div>

              <div v-else class="space-y-3">
                <div
                  v-for="rec in patientTreatments"
                  :key="rec.id"
                  class="p-4 rounded-2xl border border-slate-100 bg-slate-50/70 hover:bg-slate-50 transition space-y-2.5 text-xs"
                >
                  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div class="flex items-center gap-2.5">
                      <span class="font-bold text-slate-900 text-sm">{{ rec.treatment_name }}</span>
                      <span v-if="rec.tooth_number" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-200 text-slate-700">
                        Tooth #{{ rec.tooth_number }}
                      </span>
                      <span
                        :class="[
                          'px-2 py-0.5 rounded-full text-[10px] font-bold',
                          Number(rec.balance) <= 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                        ]"
                      >
                        {{ Number(rec.balance) <= 0 ? 'Settled' : `Bal: ${formatCurrency(rec.balance)}` }}
                      </span>
                    </div>

                    <div class="text-[11px] text-slate-500 flex items-center gap-2">
                      <span>{{ formatDate(rec.date) }}</span>
                      <span v-if="rec.doctor_name">&bull; Dr. {{ rec.doctor_name }}</span>
                    </div>
                  </div>

                  <div class="grid grid-cols-3 gap-2 bg-white p-2.5 rounded-xl border border-slate-200/80">
                    <div>
                      <span class="text-slate-400 text-[10px] block">Fee</span>
                      <span class="font-bold text-slate-900">{{ formatCurrency(rec.value_of_work) }}</span>
                    </div>
                    <div>
                      <span class="text-slate-400 text-[10px] block">Paid</span>
                      <span class="font-bold text-emerald-700">{{ formatCurrency(rec.total_paid) }}</span>
                    </div>
                    <div>
                      <span class="text-slate-400 text-[10px] block">Remaining</span>
                      <span class="font-bold text-slate-800">{{ formatCurrency(rec.balance) }}</span>
                    </div>
                  </div>

                  <div v-if="canRecordPayment(rec)" class="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      class="app-primary-action inline-flex items-center gap-2 rounded-lg px-3 py-2 font-semibold"
                      @click="openPayment(rec)"
                    >
                      <CreditCard class="size-4" aria-hidden="true" />
                      Record Payment
                    </button>
                  </div>

                  <TreatmentRecordDetails
                    v-if="hasRecordDetails(rec)"
                    :record="rec"
                    :loading-consent="isLoadingConsent"
                    :format-date="formatDate"
                    :format-currency="formatCurrency"
                    @view-payment-consent="viewPaymentConsent"
                    @view-treatment-signature="viewTreatmentSignature"
                  />
                </div>
              </div>
            </div>
          </TabPanel>
          <TabPanel value="balance" class="space-y-4">
            <section class="app-panel flex flex-wrap items-center justify-between gap-3 p-5">
              <div>
                <h2 class="text-sm font-semibold text-teal-800">Remaining patient balance</h2>
                <p class="mt-1 text-2xl font-bold text-slate-900">{{ formatCurrency(ledger.balance_due) }}</p>
              </div>
              <span class="text-sm text-slate-600">Total paid: {{ formatCurrency(ledger.total_amount_paid) }}</span>
            </section>
            <p v-if="!balanceRecords.length" class="app-panel p-4 text-sm text-slate-600">No outstanding treatment charges or down payment plans.</p>
            <div v-else-if="recordView === 'Table'" tabindex="0" role="region" aria-label="Down payment and balance table"
              class="app-panel max-h-96 overflow-auto focus-visible:outline-2 focus-visible:outline-teal-700">
              <table aria-label="Down payments and balances" class="w-full min-w-[53rem] text-left text-sm">
                <thead class="sticky top-0 z-10 bg-slate-50 text-xs text-slate-700 shadow-xs">
                  <tr>
                    <th scope="col" class="px-3 py-2">Procedure</th>
                    <th scope="col" class="px-3 py-2">Date</th>
                    <th scope="col" class="px-3 py-2 text-right">Treatment charge</th>
                    <th scope="col" class="px-3 py-2 text-right">Paid to date</th>
                    <th scope="col" class="px-3 py-2 text-right">Required down payment</th>
                    <th scope="col" class="px-3 py-2 text-right">Down payment still due</th>
                    <th scope="col" class="px-3 py-2 text-right">Remaining balance</th>
                    <th v-if="showBalanceActions" scope="col" class="px-3 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-200">
                  <tr v-for="record in balanceRecords" :key="record.id">
                    <th scope="row" class="px-3 py-2 text-slate-900">{{ record.treatment_name }}</th>
                    <td class="px-3 py-2 whitespace-nowrap text-slate-600">{{ formatDate(record.date) }}</td>
                    <td class="px-3 py-2 text-right whitespace-nowrap tabular-nums">{{ formatCurrency(record.value_of_work) }}</td>
                    <td class="px-3 py-2 text-right whitespace-nowrap tabular-nums">{{ formatCurrency(record.total_paid) }}</td>
                    <td class="px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      {{ Number(record.down_payment_amount) > 0 ? formatCurrency(record.down_payment_amount ?? 0) : '—' }}
                    </td>
                    <td class="px-3 py-2 text-right whitespace-nowrap tabular-nums">
                      <span v-if="Number(record.down_payment_amount) > 0" :class="downPaymentDue(record) ? 'text-amber-800' : 'text-emerald-800'">
                        {{ downPaymentDue(record) ? formatCurrency(downPaymentDue(record)) : 'Covered' }}
                      </span>
                      <span v-else>—</span>
                    </td>
                    <td class="px-3 py-2 text-right font-semibold whitespace-nowrap tabular-nums text-teal-900">{{ formatCurrency(record.balance) }}</td>
                    <td v-if="showBalanceActions" class="px-3 py-2">
                      <Button v-if="authStore.isDoctor" type="button" size="small" outlined
                        :label="Number(record.down_payment_amount) > 0 ? 'Edit down payment' : 'Set down payment'" @click="editTerms(record)" />
                      <Button v-else-if="canRecordPayment(record)" type="button" label="Record Payment" size="small" @click="openPayment(record)" />
                      <span v-else class="text-slate-600">—</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <template v-else>
              <article v-for="record in balanceRecords" :key="record.id" class="app-panel space-y-4 p-5">
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 class="font-bold text-slate-900">{{ record.treatment_name }}</h3>
                    <p class="text-xs text-slate-600">{{ formatDate(record.date) }}</p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <Button
                      v-if="authStore.isDoctor"
                      type="button"
                      :label="Number(record.down_payment_amount) > 0 ? 'Edit down payment' : 'Set down payment'"
                      size="small"
                      outlined
                      @click="editTerms(record)"
                    />
                    <Button v-if="canRecordPayment(record)" type="button" label="Record Payment" size="small" @click="openPayment(record)" />
                  </div>
                </div>
                <dl class="grid grid-cols-2 gap-3 rounded-xl bg-slate-50 p-3 text-sm sm:grid-cols-3">
                  <div>
                    <dt class="text-slate-600">Treatment charge</dt>
                    <dd class="font-semibold text-slate-900">{{ formatCurrency(record.value_of_work) }}</dd>
                  </div>
                  <div>
                    <dt class="text-slate-600">Paid to date</dt>
                    <dd class="font-semibold text-slate-900">{{ formatCurrency(record.total_paid) }}</dd>
                  </div>
                  <div>
                    <dt class="text-slate-600">Remaining balance</dt>
                    <dd class="font-semibold text-teal-900">{{ formatCurrency(record.balance) }}</dd>
                  </div>
                  <div v-if="Number(record.down_payment_amount) > 0">
                    <dt class="text-slate-600">Required down payment</dt>
                    <dd class="font-semibold text-slate-900">{{ formatCurrency(record.down_payment_amount ?? 0) }}</dd>
                  </div>
                  <div v-if="Number(record.down_payment_amount) > 0">
                    <dt class="text-slate-600">Down payment still due</dt>
                    <dd class="font-semibold" :class="downPaymentDue(record) ? 'text-amber-800' : 'text-emerald-800'">
                      {{ downPaymentDue(record) ? formatCurrency(downPaymentDue(record)) : 'Covered' }}
                    </dd>
                  </div>
                </dl>
              </article>
            </template>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>

    <RecordPaymentDialog
      v-if="paymentTarget"
      :record="paymentTarget"
      :saved-signature="savedPaymentSignature"
      @close="paymentTarget = null"
      @saved="finishPayment"
    />
    <Dialog :visible="!!previewSignatureModalUrl" modal header="Patient Signature" class="w-[min(28rem,calc(100vw-2rem))]" @update:visible="closeSignaturePreview">
      <img v-if="previewSignatureModalUrl" :src="previewSignatureModalUrl" alt="Patient signature" class="mx-auto max-h-56 max-w-full object-contain" />
    </Dialog>
    <Dialog
      :visible="!!termsTarget"
      modal
      header="Required Down Payment"
      class="w-[min(28rem,calc(100vw-2rem))]"
      :closable="!termsSaving"
      :close-on-escape="!termsSaving"
      @update:visible="termsTarget = null"
    >
      <form v-if="termsTarget" class="space-y-3" @submit.prevent="saveTerms">
        <p class="text-sm font-semibold text-slate-800">{{ termsTarget.treatment_name }}</p>
        <div>
          <label for="history-down-payment" class="app-form-label">Required amount (₱)</label>
          <InputText id="history-down-payment" v-model="downPaymentDraft" type="number" min="0" :max="Number(termsTarget.value_of_work)" step="0.01" inputmode="decimal" :disabled="termsSaving" fluid />
          <p class="mt-1 text-xs text-slate-600">Leave blank to remove the down payment requirement.</p>
        </div>
        <p v-if="termsError" role="alert" class="text-sm text-rose-700">{{ termsError }}</p>
        <div class="flex justify-end gap-2">
          <Button type="button" label="Cancel" severity="secondary" outlined :disabled="termsSaving" @click="termsTarget = null" />
          <Button type="submit" label="Save down payment" :loading="termsSaving" />
        </div>
      </form>
    </Dialog>
  </div>
</template>
