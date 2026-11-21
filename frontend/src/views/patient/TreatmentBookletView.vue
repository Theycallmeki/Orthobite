<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRecordStore } from '@/stores/record'
import { useAuthStore } from '@/stores/auth'
import type { TreatmentRecordResponse, PaymentResponse } from '@/api/record'
import {
  BookOpen,
  DollarSign,
  Calendar,
  CheckCircle2,
  FileCheck,
  CreditCard,
  User,
  Stethoscope,
  Clock,
  Printer,
  RefreshCw,
  AlertCircle,
  FileText,
  BadgeDollarSign,
  ShieldCheck,
  Receipt,
  Eye,
  X,
  Loader2,
} from 'lucide-vue-next'

const recordStore = useRecordStore()
const authStore = useAuthStore()

const activeSection = ref<'treatments' | 'payments'>('treatments')
const previewSignatureUrl = ref<string | null>(null)
const selectedRecordModal = ref<TreatmentRecordResponse | null>(null)

onMounted(async () => {
  await loadPatientLedger()
})

async function loadPatientLedger() {
  const patientId = authStore.user?.id
  if (!patientId) return
  try {
    await recordStore.fetchPatientLedger(patientId)
  } catch {
  }
}

const ledger = computed(() => recordStore.currentPatientLedger)
const treatments = computed<TreatmentRecordResponse[]>(() => ledger.value?.treatments || [])
const allPayments = computed<PaymentResponse[]>(() => ledger.value?.all_payments || [])

function formatCurrency(val: number | string): string {
  const num = Number(val) || 0
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num)
}

function formatDate(isoStr: string): string {
  try {
    const d = new Date(isoStr)
    return d.toLocaleDateString('default', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  } catch {
    return isoStr
  }
}

function handlePrint() {
  window.print()
}
</script>

<template>
  <div class="space-y-8 pb-16 print:p-0 print:space-y-4">
    <div class="app-panel app-page-heading flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between print:hidden">
      <div>
        <h1 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          Treatment Booklet & Financial Ledger
        </h1>
        <p class="text-sm text-slate-500 mt-1">
          Review clinical orthodontic procedures, signed treatment sheets, and zero-drift payment ledgers.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <button
          type="button"
          @click="loadPatientLedger"
          :disabled="recordStore.isLoading"
          class="inline-flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 font-medium text-xs transition cursor-pointer shadow-xs disabled:opacity-50"
        >
          <RefreshCw class="w-3.5 h-3.5" :class="{ 'animate-spin': recordStore.isLoading }" />
          Refresh
        </button>

        <button
          type="button"
          @click="handlePrint"
          class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs transition shadow-sm cursor-pointer"
        >
          <Printer class="w-4 h-4" />
          Print Booklet
        </button>
      </div>
    </div>

    <div class="hidden print:block border-b border-slate-300 pb-4 mb-4">
      <div class="flex justify-between items-start">
        <div>
          <h2 class="text-2xl font-black text-slate-900 tracking-tight">OrthoBite Orthodontics</h2>
          <p class="text-xs text-slate-600">Official Clinical Patient Booklet & Statement of Account</p>
        </div>
        <div class="text-right text-xs text-slate-600">
          <p><strong>Patient:</strong> {{ authStore.user?.full_name }}</p>
          <p><strong>Date Generated:</strong> {{ new Date().toLocaleDateString() }}</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="app-panel p-6 relative overflow-hidden">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Value of Work</span>
          <div class="w-9 h-9 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center">
            <BadgeDollarSign class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-4">
          <span class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {{ formatCurrency(recordStore.totalValueOfWork) }}
          </span>
          <p class="text-[11px] text-slate-400 mt-1">Total clinical procedures billed</p>
        </div>
      </div>

      <div class="bg-white rounded-3xl border border-emerald-200 p-6 shadow-xs relative overflow-hidden bg-gradient-to-br from-white to-emerald-50/30">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-emerald-800 uppercase tracking-wider">Total Amount Paid</span>
          <div class="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
            <CheckCircle2 class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-4">
          <span class="text-2xl sm:text-3xl font-extrabold text-emerald-700 tracking-tight">
            {{ formatCurrency(recordStore.totalPaid) }}
          </span>
          <p class="text-[11px] text-emerald-600 mt-1">Confirmed payments and installments</p>
        </div>
      </div>

      <div
        :class="[
          'rounded-3xl border p-6 shadow-xs relative overflow-hidden',
          recordStore.balanceDue > 0
            ? 'bg-amber-50/40 border-amber-200'
            : 'bg-teal-50/40 border-teal-200'
        ]"
      >
        <div class="flex items-center justify-between">
          <span
            :class="[
              'text-xs font-bold uppercase tracking-wider',
              recordStore.balanceDue > 0 ? 'text-amber-800' : 'text-teal-800'
            ]"
          >
            Outstanding Balance
          </span>
          <div
            :class="[
              'w-9 h-9 rounded-xl flex items-center justify-center',
              recordStore.balanceDue > 0 ? 'bg-amber-100 text-amber-700' : 'bg-teal-100 text-teal-700'
            ]"
          >
            <ShieldCheck class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-4">
          <span
            :class="[
              'text-2xl sm:text-3xl font-extrabold tracking-tight',
              recordStore.balanceDue > 0 ? 'text-amber-900' : 'text-teal-900'
            ]"
          >
            {{ formatCurrency(recordStore.balanceDue) }}
          </span>
          <p class="text-[11px] text-slate-500 mt-1">
            {{ recordStore.balanceDue <= 0 ? 'Account fully settled (Zero Drift)' : 'Current unpaid balance' }}
          </p>
        </div>
      </div>
    </div>

    <div class="flex items-center gap-2 border-b border-slate-200 pb-3 print:hidden">
      <button
        type="button"
        @click="activeSection = 'treatments'"
        :class="[
          'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer',
          activeSection === 'treatments'
            ? 'bg-teal-600 text-white shadow-xs'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
        ]"
      >
        <BookOpen class="w-4 h-4" />
        Clinical Treatment Procedures ({{ treatments.length }})
      </button>

      <button
        type="button"
        @click="activeSection = 'payments'"
        :class="[
          'px-4 py-2 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer',
          activeSection === 'payments'
            ? 'bg-teal-600 text-white shadow-xs'
            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
        ]"
      >
        <Receipt class="w-4 h-4" />
        Payment Receipts ({{ allPayments.length }})
      </button>
    </div>

    <div v-if="recordStore.isLoading && !ledger" class="py-16 text-center space-y-3">
      <Loader2 class="w-8 h-8 animate-spin mx-auto text-teal-600" />
      <p class="text-sm font-medium text-slate-500">Loading treatment booklet...</p>
    </div>

    <div v-else-if="activeSection === 'treatments' || !activeSection" class="space-y-4">
      <div v-if="treatments.length === 0" class="app-panel p-12 text-center max-w-lg mx-auto space-y-3">
        <div class="w-14 h-14 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
          <BookOpen class="w-7 h-7" />
        </div>
        <h3 class="text-base font-bold text-slate-900">No Treatment Records Yet</h3>
        <p class="text-xs text-slate-500 max-w-xs mx-auto">
          Your attending orthodontist will record procedures, tooth surface updates, and payment installments here after your consultation.
        </p>
      </div>

      <div
        v-for="record in treatments"
        :key="record.id"
        class="app-panel p-6 hover:shadow-md transition-shadow space-y-4"
      >
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-teal-50 text-teal-700 flex items-center justify-center font-bold shrink-0">
              <Stethoscope class="w-5 h-5" />
            </div>
            <div>
              <h3 class="text-sm sm:text-base font-bold text-slate-900">
                {{ record.treatment_name }}
              </h3>
              <p class="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                <span>{{ formatDate(record.date) }}</span>
                <span v-if="record.doctor_name">&bull; Dr. {{ record.doctor_name }}</span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <span
              v-if="record.tooth_number"
              class="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700"
            >
              Tooth #{{ record.tooth_number }}
            </span>
            <span
              :class="[
                'px-2.5 py-1 rounded-full text-xs font-bold',
                Number(record.balance) <= 0
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800'
              ]"
            >
              {{ Number(record.balance) <= 0 ? 'Settled' : `Bal: ${formatCurrency(record.balance)}` }}
            </span>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50/80 p-3.5 rounded-xl border border-slate-100 text-xs">
          <div>
            <span class="text-slate-400 block font-medium">Value of Work</span>
            <span class="font-bold text-slate-800 text-sm">{{ formatCurrency(record.value_of_work) }}</span>
          </div>
          <div>
            <span class="text-slate-400 block font-medium">Amount Paid</span>
            <span class="font-bold text-emerald-700 text-sm">{{ formatCurrency(record.total_paid) }}</span>
          </div>
          <div>
            <span class="text-slate-400 block font-medium">Remaining Balance</span>
            <span class="font-bold text-slate-900 text-sm">{{ formatCurrency(record.balance) }}</span>
          </div>
        </div>

        <div v-if="record.notes" class="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100">
          <span class="font-bold text-slate-700 block mb-0.5">Clinical Progress Notes:</span>
          <p>{{ record.notes }}</p>
        </div>

        <div v-if="record.signature_url" class="flex items-center gap-3 pt-2 text-xs text-slate-600">
          <ShieldCheck class="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Patient signature captured & verified on chart</span>
          <button
            type="button"
            @click="previewSignatureUrl = record.signature_url"
            class="text-teal-600 font-semibold hover:underline cursor-pointer ml-auto flex items-center gap-1"
          >
            <Eye class="w-3.5 h-3.5" />
            Inspect Signature
          </button>
        </div>

        <div v-if="record.payments && record.payments.length > 0" class="pt-2">
          <span class="text-xs font-bold text-slate-700 block mb-2">Installment Payment History:</span>
          <div class="overflow-x-auto">
            <table class="w-full text-xs text-left">
              <thead class="text-slate-400 bg-slate-50 uppercase tracking-wider font-semibold text-[10px]">
                <tr>
                  <th class="py-2 px-3 rounded-l-lg">Date</th>
                  <th class="py-2 px-3">Receipt No</th>
                  <th class="py-2 px-3">Method</th>
                  <th class="py-2 px-3 text-right rounded-r-lg">Amount</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="p in record.payments" :key="p.id" class="text-slate-700">
                  <td class="py-2 px-3">{{ formatDate(p.payment_date) }}</td>
                  <td class="py-2 px-3 font-mono text-[11px] text-slate-500">{{ p.receipt_no || 'N/A' }}</td>
                  <td class="py-2 px-3">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700">
                      {{ p.method }}
                    </span>
                  </td>
                  <td class="py-2 px-3 text-right font-bold text-emerald-700">{{ formatCurrency(p.amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeSection === 'payments'" class="space-y-4">
      <div v-if="allPayments.length === 0" class="app-panel p-12 text-center max-w-lg mx-auto space-y-3">
        <div class="w-14 h-14 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
          <Receipt class="w-7 h-7" />
        </div>
        <h3 class="text-base font-bold text-slate-900">No Payments Recorded</h3>
        <p class="text-xs text-slate-500 max-w-xs mx-auto">
          No installment payments or general receipts have been issued to your account yet.
        </p>
      </div>

      <div v-else class="app-panel overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="text-slate-400 bg-slate-50 uppercase tracking-wider font-semibold text-[10px] border-b border-slate-100">
              <tr>
                <th class="py-3 px-4">Receipt #</th>
                <th class="py-3 px-4">Date</th>
                <th class="py-3 px-4">Method</th>
                <th class="py-3 px-4">Notes</th>
                <th class="py-3 px-4 text-right">Amount</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-slate-700">
              <tr v-for="p in allPayments" :key="p.id" class="hover:bg-slate-50/50 transition">
                <td class="py-3 px-4 font-mono font-bold text-slate-900">
                  {{ p.receipt_no || `#REC-${p.id}` }}
                </td>
                <td class="py-3 px-4">{{ formatDate(p.payment_date) }}</td>
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-teal-50 text-teal-800 border border-teal-200">
                    {{ p.method }}
                  </span>
                </td>
                <td class="py-3 px-4 text-slate-500 max-w-xs truncate">{{ p.notes || 'Installment settlement' }}</td>
                <td class="py-3 px-4 text-right font-extrabold text-emerald-700 text-sm">
                  {{ formatCurrency(p.amount) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div
      v-if="previewSignatureUrl"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs print:hidden"
    >
      <div class="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-100">
          <div class="flex items-center gap-2 text-teal-700">
            <ShieldCheck class="w-5 h-5" />
            <h3 class="text-base font-bold text-slate-900">Patient Electronic Signature</h3>
          </div>
          <button
            type="button"
            @click="previewSignatureUrl = null"
            class="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="bg-slate-50 p-4 rounded-2xl border border-slate-200 flex items-center justify-center">
          <img
            :src="previewSignatureUrl"
            alt="Patient Signature"
            class="max-h-48 object-contain"
          />
        </div>

        <p class="text-[11px] text-slate-400 text-center">
          Digitally authenticated by patient consent on clinical record sheet.
        </p>

        <div class="pt-2 text-center">
          <button
            type="button"
            @click="previewSignatureUrl = null"
            class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

