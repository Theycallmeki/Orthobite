<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import Menu from 'primevue/menu'
import { Ellipsis } from 'lucide-vue-next'
import type { PatientResponse } from '@/api/patient'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ patient: PatientResponse; patientName: string }>()
const authStore = useAuthStore()
const triggerId = useId()
const menuId = `${triggerId}-actions`
const menu = ref<InstanceType<typeof Menu> | null>(null)
const open = ref(false)

const items = computed(() => {
  const query = { patient: String(props.patient.id) }
  const actions = [{ label: 'Treatment History', to: { name: 'clinic-treatment-history', query } }]
  if (authStore.isAdmin || (authStore.isDoctor && authStore.user?.id === props.patient.assigned_doctor_id)) {
    actions.push({ label: 'Documents', to: { name: 'clinic-patient-files', query } })
  }
  return actions
})
</script>

<template>
  <button
    :id="triggerId"
    type="button"
    class="inline-flex size-8 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 hover:text-teal-800 focus-visible:outline-2 focus-visible:outline-teal-700"
    :aria-label="`Actions for ${patientName}`"
    aria-haspopup="menu"
    :aria-controls="menuId"
    :aria-expanded="open"
    @click="menu?.toggle($event)"
  >
    <Ellipsis class="size-5" aria-hidden="true" />
  </button>
  <Menu
    :id="menuId"
    ref="menu"
    :model="items"
    :aria-labelledby="triggerId"
    popup
    append-to="body"
    @show="open = true"
    @hide="open = false"
  >
    <template #item="{ item, label, props: itemProps }">
      <RouterLink :to="item.to" v-bind="itemProps.action">{{ label }}</RouterLink>
    </template>
  </Menu>
</template>
