<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import { useDoctorStore } from '@/stores/doctor'

const doctorStore = useDoctorStore()
const maxFee = 99_999_999.99
const currentFee = ref<number | null>(null)
const fee = ref('')
const saved = ref(false)
const enteredFee = computed(() => Number(fee.value))
const canSave = computed(() =>
  currentFee.value !== null
  && fee.value.trim() !== ''
  && enteredFee.value >= 0
  && enteredFee.value <= maxFee
  && enteredFee.value !== currentFee.value,
)

async function loadFee() {
  try {
    const profile = await doctorStore.fetchMyProfile()
    currentFee.value = Number(profile.consultation_fee)
    fee.value = currentFee.value.toFixed(2)
  } catch {
    // The store exposes the error for the retry state.
  }
}

async function saveFee() {
  if (!canSave.value || doctorStore.isLoading) return
  saved.value = false
  try {
    const profile = await doctorStore.updateMyProfile({ consultation_fee: enteredFee.value })
    currentFee.value = Number(profile.consultation_fee)
    fee.value = currentFee.value.toFixed(2)
    saved.value = true
  } catch {
    // The store exposes the error and the form keeps the attempted amount.
  }
}

onMounted(loadFee)
</script>

<template>
  <div class="space-y-6">
    <section class="app-panel app-page-heading">
      <h1 class="text-2xl font-bold tracking-tight text-slate-900">Consultation Fee</h1>
      <p class="mt-1 text-sm text-slate-600">Set the fee patients see when booking a consultation with you.</p>
    </section>

    <section class="app-panel max-w-md space-y-4 p-5 sm:p-6">
      <p v-if="currentFee === null && doctorStore.isLoading" role="status" class="text-sm text-slate-600">
        Loading your consultation fee…
      </p>
      <p v-if="doctorStore.error" role="alert" class="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
        {{ doctorStore.error }}
      </p>
      <Button
        v-if="currentFee === null && doctorStore.error"
        type="button"
        label="Try again"
        outlined
        @click="loadFee"
      />

      <form v-if="currentFee !== null" class="space-y-4" @submit.prevent="saveFee">
        <div>
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
            :disabled="doctorStore.isLoading"
            @input="saved = false"
          />
        </div>
        <Button type="submit" label="Save fee" :disabled="!canSave" :loading="doctorStore.isLoading" />
        <p v-if="saved" role="status" class="text-sm font-medium text-emerald-800">
          Consultation fee saved.
        </p>
      </form>
    </section>
  </div>
</template>
