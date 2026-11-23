<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { isAxiosError } from 'axios'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { useDoctorStore } from '@/stores/doctor'

defineProps<{ heading?: 'h1' | 'h2' }>()

const doctorStore = useDoctorStore()
const maxFee = 99_999_999.99
const feeFormat = new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' })
const currentFee = ref<number | null>(null)
const fee = ref('')
const busy = ref(false)
const error = ref('')
const saved = ref(false)
const enteredFee = computed(() => Number(fee.value))
const canSave = computed(() =>
  currentFee.value !== null
  && fee.value.trim() !== ''
  && enteredFee.value >= 0
  && enteredFee.value <= maxFee
  && enteredFee.value !== currentFee.value,
)

function feeError(cause: unknown, fallback: string) {
  const detail: unknown = isAxiosError(cause) ? cause.response?.data?.detail : undefined
  return typeof detail === 'string' && detail ? detail : fallback
}

async function loadFee() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    const profile = await doctorStore.fetchMyProfile()
    currentFee.value = Number(profile.consultation_fee)
    fee.value = currentFee.value.toFixed(2)
  } catch (cause) {
    error.value = feeError(cause, 'Could not load your consultation fee.')
  } finally {
    busy.value = false
  }
}

async function saveFee() {
  if (!canSave.value || busy.value) return
  busy.value = true
  error.value = ''
  saved.value = false
  try {
    const profile = await doctorStore.updateMyProfile({ consultation_fee: enteredFee.value })
    currentFee.value = Number(profile.consultation_fee)
    fee.value = currentFee.value.toFixed(2)
    saved.value = true
  } catch (cause) {
    error.value = feeError(cause, 'Could not save your consultation fee.')
  } finally {
    busy.value = false
  }
}

onMounted(loadFee)
</script>

<template>
  <section aria-labelledby="consultation-fee-heading" class="app-panel grid gap-5 p-5 sm:p-6 md:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
    <div>
      <component :is="heading ?? 'h2'" id="consultation-fee-heading" class="font-bold tracking-tight text-slate-900" :class="heading === 'h1' ? 'text-2xl' : 'text-lg'">
        Consultation Fee
      </component>
      <p class="mt-1 text-sm text-slate-600">Patients see this fee when booking a consultation with you.</p>
      <p v-if="currentFee !== null" class="mt-3">
        <span class="block text-sm font-medium text-slate-600">Current fee</span>
        <span class="text-xl font-bold text-slate-900 tabular-nums">{{ feeFormat.format(currentFee) }}</span>
      </p>
    </div>

    <div class="min-w-0 space-y-3">
      <p v-if="currentFee === null && busy" role="status" class="text-sm text-slate-600">
        Loading your consultation fee…
      </p>
      <p v-if="error" role="alert" class="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
        {{ error }}
      </p>
      <Button
        v-if="currentFee === null && error"
        type="button"
        label="Try again"
        outlined
        @click="loadFee"
      />

      <form v-if="currentFee !== null" class="space-y-3" @submit.prevent="saveFee">
        <div class="flex items-end gap-3">
          <div class="min-w-0 flex-1">
            <label for="consultation-fee" class="app-form-label">Amount (₱)</label>
            <InputText
              id="consultation-fee"
              v-model="fee"
              type="number"
              inputmode="decimal"
              min="0"
              :max="maxFee"
              step="0.01"
              required
              fluid
              :disabled="busy"
              @input="saved = false"
            />
          </div>
          <Button type="submit" label="Save fee" class="shrink-0" :disabled="!canSave" :loading="busy" />
        </div>
        <p v-if="saved" role="status" class="text-sm font-medium text-emerald-800">
          Consultation fee saved.
        </p>
      </form>
    </div>
  </section>
</template>
