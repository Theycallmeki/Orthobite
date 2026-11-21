<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Menu from 'primevue/menu'
import { ChevronDown, ClipboardList } from 'lucide-vue-next'

const props = defineProps<{ mobile?: boolean }>()
const menu = ref<InstanceType<typeof Menu> | null>(null)
const open = ref(false)
const route = useRoute()
const router = useRouter()
const menuId = computed(() => props.mobile ? 'clinic-records-menu-mobile' : 'clinic-records-menu')
const inRecords = computed(() => route.name === 'clinic-records' || route.name === 'clinic-treatment-history')
const items = [
  { label: 'Record Editor', command: () => goTo('clinic-records') },
  { label: 'Treatment History', command: () => goTo('clinic-treatment-history') },
]

function goTo(name: string) {
  const patient = route.query.patient
  void router.push({ name, query: inRecords.value && typeof patient === 'string' ? { patient } : {} })
}
</script>

<template>
  <button
    type="button"
    class="flex shrink-0 items-center rounded-lg font-medium transition-colors hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-teal-700"
    :class="[
      mobile ? 'flex-col gap-1 px-2 py-1 text-[11px]' : 'gap-2 px-3 py-2 text-sm',
      inRecords ? 'bg-teal-50 text-teal-700' : 'text-slate-600',
    ]"
    aria-haspopup="menu"
    :aria-controls="menuId"
    :aria-expanded="open"
    @click="menu?.toggle($event)"
  >
    <ClipboardList :class="mobile ? 'size-5' : 'size-4'" aria-hidden="true" />
    <span class="flex items-center gap-1 whitespace-nowrap">Patient Records <ChevronDown class="size-3" aria-hidden="true" /></span>
  </button>
  <Menu :id="menuId" ref="menu" :model="items" popup @show="open = true" @hide="open = false" />
</template>
