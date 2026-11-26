<script setup lang="ts">
import Button from 'primevue/button'
import { Eye, ShieldCheck } from 'lucide-vue-next'
import type { TreatmentRecordResponse } from '@/api/record'

defineProps<{
  record: TreatmentRecordResponse
  loadingConsent: boolean
  formatCurrency: (value: number | string) => string
  formatDate: (value: string) => string
}>()

const emit = defineEmits<{
  viewPaymentConsent: [paymentId: number]
  viewTreatmentSignature: [url: string]
}>()
</script>

<template>
  <div class="space-y-2 text-xs">
    <div v-if="record.notes" class="wrap-anywhere rounded-lg border border-slate-200/60 bg-white p-2 text-slate-600">
      <span class="font-semibold text-slate-700">Notes</span>
      <p class="whitespace-pre-wrap">{{ record.notes }}</p>
    </div>

    <div v-if="record.payments.length" class="space-y-2 border-t border-slate-200 pt-3">
      <p class="font-semibold text-slate-800">Installment payments</p>
      <ul class="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
        <li v-for="payment in record.payments" :key="payment.id" class="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
          <p class="text-slate-600">{{ formatDate(payment.payment_date) }} &middot; {{ payment.method }}<span v-if="payment.receipt_no"> &middot; {{ payment.receipt_no }}</span></p>
          <div class="flex items-center gap-2">
            <span class="font-semibold text-slate-800">{{ formatCurrency(payment.amount) }}</span>
            <Button v-if="payment.has_consent" type="button" label="View signature" size="small" text :disabled="loadingConsent" @click="emit('viewPaymentConsent', payment.id)" />
          </div>
        </li>
      </ul>
    </div>

    <div v-if="record.signature_url" class="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px]">
      <span class="flex items-center gap-1 font-medium text-emerald-700">
        <ShieldCheck class="size-3.5" aria-hidden="true" />
        Patient consent signature authenticated
      </span>
      <button
        type="button"
        class="flex items-center gap-1 font-semibold text-teal-700 hover:underline"
        @click="emit('viewTreatmentSignature', record.signature_url)"
      >
        <Eye class="size-3.5" aria-hidden="true" />
        View Signature
      </button>
    </div>
  </div>
</template>
