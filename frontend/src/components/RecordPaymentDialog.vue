<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import SignaturePad from '@/components/SignaturePad.vue'
import { type PaymentMethod, type PaymentResponse, type TreatmentRecordResponse } from '@/api/record'
import { useRecordStore } from '@/stores/record'

const props = defineProps<{
  record: TreatmentRecordResponse
  savedSignature?: PaymentResponse
}>()
const emit = defineEmits<{ close: []; saved: [payment: PaymentResponse] }>()
const recordStore = useRecordStore()
const requestId = crypto.randomUUID()
const amount = ref(Number(props.record.balance).toFixed(2))
const method = ref<PaymentMethod>('Cash')
const receipt = ref('')
const signatureMode = ref<'none' | 'draw' | 'reuse'>('none')
const reuseApproved = ref(false)
const hasDrawing = ref(false)
const signaturePad = ref<InstanceType<typeof SignaturePad> | null>(null)
const saving = ref(false)
const error = ref('')

watch(signatureMode, () => {
  reuseApproved.value = false
  hasDrawing.value = false
})

const canSave = computed(() =>
  Number(amount.value) > 0
  && (signatureMode.value !== 'draw' || hasDrawing.value)
  && (signatureMode.value !== 'reuse' || (!!props.savedSignature && reuseApproved.value)),
)

async function submit() {
  if (saving.value || !canSave.value) return
  const signature = signatureMode.value === 'draw' ? signaturePad.value?.toDataURL('image/png') : undefined
  if (signatureMode.value === 'draw' && (!signature || signaturePad.value?.isEmpty())) return

  saving.value = true
  error.value = ''
  try {
    const payment = await recordStore.addPaymentForRecord(props.record.id, {
      patient_id: props.record.patient_id,
      amount: amount.value,
      method: method.value,
      receipt_no: receipt.value.trim() || undefined,
      payment_request_id: requestId,
      consent_signature_base64: signature,
      reuse_consent_payment_id: signatureMode.value === 'reuse' ? props.savedSignature?.id : undefined,
      reuse_consent_confirmed: signatureMode.value === 'reuse' ? reuseApproved.value : undefined,
    })
    emit('saved', payment)
  } catch {
    error.value = typeof recordStore.error === 'string'
      ? recordStore.error
      : 'Could not record the payment.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Dialog
    :visible="true"
    modal
    header="Record Payment"
    class="w-[min(36rem,calc(100vw-2rem))]"
    :closable="!saving"
    :close-on-escape="!saving"
    @update:visible="emit('close')"
  >
    <p class="mb-4 text-sm text-slate-600">{{ record.patient_name }} · {{ record.treatment_name }}</p>
    <form class="space-y-4" @submit.prevent="submit">
      <fieldset :disabled="saving" class="space-y-4">
        <div class="grid gap-3 sm:grid-cols-2">
          <div>
            <label for="payment-amount" class="app-form-label">Amount paid (₱)</label>
            <InputText id="payment-amount" v-model="amount" type="number" min="0.01" max="9999999999.99" step="0.01" inputmode="decimal" required fluid />
          </div>
          <div>
            <label for="payment-method" class="app-form-label">Payment method</label>
            <select id="payment-method" v-model="method" class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900">
              <option>Cash</option>
              <option>GCash</option>
              <option>Card</option>
            </select>
          </div>
        </div>
        <div>
          <label for="payment-receipt" class="app-form-label">Receipt number (optional)</label>
          <InputText id="payment-receipt" v-model="receipt" maxlength="100" fluid />
        </div>
        <fieldset class="space-y-2 rounded-xl border border-slate-200 p-3 text-sm">
          <legend class="px-1 font-semibold text-slate-800">Electronic consent (optional)</legend>
          <label class="flex items-center gap-2"><input v-model="signatureMode" type="radio" value="none" /> No signature</label>
          <label class="flex items-center gap-2"><input v-model="signatureMode" type="radio" value="draw" /> Capture a new signature</label>
          <label v-if="savedSignature" class="flex items-center gap-2">
            <input v-model="signatureMode" type="radio" value="reuse" /> Reuse this patient’s saved signature
          </label>
          <label v-if="signatureMode === 'reuse'" class="flex items-start gap-2 rounded-lg bg-teal-50 p-3">
            <input v-model="reuseApproved" type="checkbox" class="mt-1" />
            The patient agrees to reuse their saved signature for this payment.
          </label>
          <SignaturePad
            v-if="signatureMode === 'draw'"
            ref="signaturePad"
            :height="145"
            :read-only="saving"
            :show-confirm="false"
            @change="hasDrawing = $event"
          />
        </fieldset>
      </fieldset>
      <p v-if="error" role="alert" class="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{{ error }}</p>
      <div class="flex justify-end gap-2">
        <Button type="button" label="Cancel" severity="secondary" outlined :disabled="saving" @click="emit('close')" />
        <Button type="submit" label="Save payment" :loading="saving" :disabled="!canSave" />
      </div>
    </form>
  </Dialog>
</template>
