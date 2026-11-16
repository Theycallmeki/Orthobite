<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRecordStore } from '@/stores/record'
import type { ToothMetadata } from '@/api/record'
import {
  Info,
  Check,
  RotateCcw,
  Sparkles,
  Layers,
  ChevronDown,
  X,
} from 'lucide-vue-next'

export interface ToothCondition {
  condition: 'healthy' | 'caries' | 'restored' | 'crown' | 'banded' | 'missing'
  surfaces?: ('M' | 'D' | 'O' | 'B' | 'L')[]
}

const props = withDefaults(
  defineProps<{
    modelValue?: number[]
    conditions?: Record<number, ToothCondition>
    readOnly?: boolean
    showSurfaces?: boolean
  }>(),
  {
    modelValue: () => [],
    conditions: () => ({}),
    readOnly: false,
    showSurfaces: true,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number[]): void
  (e: 'select-tooth', toothId: number): void
  (e: 'select-surface', payload: { toothId: number; surface: 'M' | 'D' | 'O' | 'B' | 'L' }): void
}>()

const recordStore = useRecordStore()

const hoveredTooth = ref<ToothMetadata | null>(null)
const focusedToothId = ref<number | null>(null)
const activeSurfaceMap = ref<Record<number, Set<'M' | 'D' | 'O' | 'B' | 'L'>>>({})

const fallbackTeeth: ToothMetadata[] = [
  { id: 1, fdi_number: 18, name: 'Maxillary Right Third Molar (Wisdom)', arch: 'upper', quadrant: 'upper_right', type: 'molar', row: 0, col: 0, x: 20, y: 20, width: 56, height: 80 },
  { id: 2, fdi_number: 17, name: 'Maxillary Right Second Molar', arch: 'upper', quadrant: 'upper_right', type: 'molar', row: 0, col: 1, x: 82, y: 20, width: 56, height: 80 },
  { id: 3, fdi_number: 16, name: 'Maxillary Right First Molar', arch: 'upper', quadrant: 'upper_right', type: 'molar', row: 0, col: 2, x: 144, y: 20, width: 56, height: 80 },
  { id: 4, fdi_number: 15, name: 'Maxillary Right Second Premolar', arch: 'upper', quadrant: 'upper_right', type: 'premolar', row: 0, col: 3, x: 206, y: 20, width: 56, height: 80 },
  { id: 5, fdi_number: 14, name: 'Maxillary Right First Premolar', arch: 'upper', quadrant: 'upper_right', type: 'premolar', row: 0, col: 4, x: 268, y: 20, width: 56, height: 80 },
  { id: 6, fdi_number: 13, name: 'Maxillary Right Canine', arch: 'upper', quadrant: 'upper_right', type: 'canine', row: 0, col: 5, x: 330, y: 20, width: 56, height: 80 },
  { id: 7, fdi_number: 12, name: 'Maxillary Right Lateral Incisor', arch: 'upper', quadrant: 'upper_right', type: 'incisor', row: 0, col: 6, x: 392, y: 20, width: 56, height: 80 },
  { id: 8, fdi_number: 11, name: 'Maxillary Right Central Incisor', arch: 'upper', quadrant: 'upper_right', type: 'incisor', row: 0, col: 7, x: 454, y: 20, width: 56, height: 80 },
  { id: 9, fdi_number: 21, name: 'Maxillary Left Central Incisor', arch: 'upper', quadrant: 'upper_left', type: 'incisor', row: 0, col: 8, x: 516, y: 20, width: 56, height: 80 },
  { id: 10, fdi_number: 22, name: 'Maxillary Left Lateral Incisor', arch: 'upper', quadrant: 'upper_left', type: 'incisor', row: 0, col: 9, x: 578, y: 20, width: 56, height: 80 },
  { id: 11, fdi_number: 23, name: 'Maxillary Left Canine', arch: 'upper', quadrant: 'upper_left', type: 'canine', row: 0, col: 10, x: 640, y: 20, width: 56, height: 80 },
  { id: 12, fdi_number: 24, name: 'Maxillary Left First Premolar', arch: 'upper', quadrant: 'upper_left', type: 'premolar', row: 0, col: 11, x: 702, y: 20, width: 56, height: 80 },
  { id: 13, fdi_number: 25, name: 'Maxillary Left Second Premolar', arch: 'upper', quadrant: 'upper_left', type: 'premolar', row: 0, col: 12, x: 764, y: 20, width: 56, height: 80 },
  { id: 14, fdi_number: 26, name: 'Maxillary Left First Molar', arch: 'upper', quadrant: 'upper_left', type: 'molar', row: 0, col: 13, x: 826, y: 20, width: 56, height: 80 },
  { id: 15, fdi_number: 27, name: 'Maxillary Left Second Molar', arch: 'upper', quadrant: 'upper_left', type: 'molar', row: 0, col: 14, x: 888, y: 20, width: 56, height: 80 },
  { id: 16, fdi_number: 28, name: 'Maxillary Left Third Molar (Wisdom)', arch: 'upper', quadrant: 'upper_left', type: 'molar', row: 0, col: 15, x: 950, y: 20, width: 56, height: 80 },
  { id: 32, fdi_number: 48, name: 'Mandibular Right Third Molar (Wisdom)', arch: 'lower', quadrant: 'lower_right', type: 'molar', row: 1, col: 0, x: 20, y: 136, width: 56, height: 80 },
  { id: 31, fdi_number: 47, name: 'Mandibular Right Second Molar', arch: 'lower', quadrant: 'lower_right', type: 'molar', row: 1, col: 1, x: 82, y: 136, width: 56, height: 80 },
  { id: 30, fdi_number: 46, name: 'Mandibular Right First Molar', arch: 'lower', quadrant: 'lower_right', type: 'molar', row: 1, col: 2, x: 144, y: 136, width: 56, height: 80 },
  { id: 29, fdi_number: 45, name: 'Mandibular Right Second Premolar', arch: 'lower', quadrant: 'lower_right', type: 'premolar', row: 1, col: 3, x: 206, y: 136, width: 56, height: 80 },
  { id: 28, fdi_number: 44, name: 'Mandibular Right First Premolar', arch: 'lower', quadrant: 'lower_right', type: 'premolar', row: 1, col: 4, x: 268, y: 136, width: 56, height: 80 },
  { id: 27, fdi_number: 43, name: 'Mandibular Right Canine', arch: 'lower', quadrant: 'lower_right', type: 'canine', row: 1, col: 5, x: 330, y: 136, width: 56, height: 80 },
  { id: 26, fdi_number: 42, name: 'Mandibular Right Lateral Incisor', arch: 'lower', quadrant: 'lower_right', type: 'incisor', row: 1, col: 6, x: 392, y: 136, width: 56, height: 80 },
  { id: 25, fdi_number: 41, name: 'Mandibular Right Central Incisor', arch: 'lower', quadrant: 'lower_right', type: 'incisor', row: 1, col: 7, x: 454, y: 136, width: 56, height: 80 },
  { id: 24, fdi_number: 31, name: 'Mandibular Left Central Incisor', arch: 'lower', quadrant: 'lower_left', type: 'incisor', row: 1, col: 8, x: 516, y: 136, width: 56, height: 80 },
  { id: 23, fdi_number: 32, name: 'Mandibular Left Lateral Incisor', arch: 'lower', quadrant: 'lower_left', type: 'incisor', row: 1, col: 9, x: 578, y: 136, width: 56, height: 80 },
  { id: 22, fdi_number: 33, name: 'Mandibular Left Canine', arch: 'lower', quadrant: 'lower_left', type: 'canine', row: 1, col: 10, x: 640, y: 136, width: 56, height: 80 },
  { id: 21, fdi_number: 34, name: 'Mandibular Left First Premolar', arch: 'lower', quadrant: 'lower_left', type: 'premolar', row: 1, col: 11, x: 702, y: 136, width: 56, height: 80 },
  { id: 20, fdi_number: 35, name: 'Mandibular Left Second Premolar', arch: 'lower', quadrant: 'lower_left', type: 'premolar', row: 1, col: 12, x: 764, y: 136, width: 56, height: 80 },
  { id: 19, fdi_number: 36, name: 'Mandibular Left First Molar', arch: 'lower', quadrant: 'lower_left', type: 'molar', row: 1, col: 13, x: 826, y: 136, width: 56, height: 80 },
  { id: 18, fdi_number: 37, name: 'Mandibular Left Second Molar', arch: 'lower', quadrant: 'lower_left', type: 'molar', row: 1, col: 14, x: 888, y: 136, width: 56, height: 80 },
  { id: 17, fdi_number: 38, name: 'Mandibular Left Third Molar (Wisdom)', arch: 'lower', quadrant: 'lower_left', type: 'molar', row: 1, col: 15, x: 950, y: 136, width: 56, height: 80 },
]

onMounted(async () => {
  if (!recordStore.toothTemplate) {
    await recordStore.fetchToothTemplate().catch(() => {})
  }
})

const teethList = computed<ToothMetadata[]>(() => {
  return recordStore.toothTemplate?.teeth || fallbackTeeth
})

const upperTeeth = computed<ToothMetadata[]>(() => {
  return teethList.value.filter((t) => t.arch === 'upper')
})

const lowerTeeth = computed<ToothMetadata[]>(() => {
  return teethList.value.filter((t) => t.arch === 'lower')
})

const selectedSet = computed<Set<number>>(() => {
  return new Set(props.modelValue)
})

const focusedTooth = computed<ToothMetadata | undefined>(() => {
  if (!focusedToothId.value) return undefined
  return teethList.value.find((t) => t.id === focusedToothId.value)
})

function isToothSelected(id: number): boolean {
  return selectedSet.value.has(id)
}

function handleToothClick(tooth: ToothMetadata) {
  if (props.readOnly) return

  const current = [...props.modelValue]
  const idx = current.indexOf(tooth.id)

  if (idx !== -1) {
    current.splice(idx, 1)
  } else {
    current.push(tooth.id)
  }

  current.sort((a, b) => a - b)
  emit('update:modelValue', current)
  emit('select-tooth', tooth.id)

  if (props.showSurfaces) {
    focusedToothId.value = tooth.id
  }
}

function handleSelectArch(arch: 'upper' | 'lower') {
  if (props.readOnly) return
  const archTeeth = (arch === 'upper' ? upperTeeth.value : lowerTeeth.value).map((t) => t.id)
  const current = new Set(props.modelValue)
  const allSelected = archTeeth.every((id) => current.has(id))

  if (allSelected) {
    archTeeth.forEach((id) => current.delete(id))
  } else {
    archTeeth.forEach((id) => current.add(id))
  }

  const updated = Array.from(current).sort((a, b) => a - b)
  emit('update:modelValue', updated)
}

function handleClearAll() {
  if (props.readOnly) return
  emit('update:modelValue', [])
  focusedToothId.value = null
}

function handleToggleSurface(toothId: number, surface: 'M' | 'D' | 'O' | 'B' | 'L') {
  if (props.readOnly) return
  if (!activeSurfaceMap.value[toothId]) {
    activeSurfaceMap.value[toothId] = new Set()
  }

  const set = activeSurfaceMap.value[toothId]
  if (set.has(surface)) {
    set.delete(surface)
  } else {
    set.add(surface)
  }

  emit('select-surface', { toothId, surface })
}

function isSurfaceActive(toothId: number, surface: 'M' | 'D' | 'O' | 'B' | 'L'): boolean {
  return !!activeSurfaceMap.value[toothId]?.has(surface)
}

function getConditionClass(toothId: number): string {
  const cond = props.conditions[toothId]
  if (!cond) return ''

  switch (cond.condition) {
    case 'caries':
      return 'border-rose-500 bg-rose-50/70 text-rose-900 ring-1 ring-rose-400'
    case 'restored':
      return 'border-sky-500 bg-sky-50/70 text-sky-900 ring-1 ring-sky-400'
    case 'crown':
      return 'border-purple-500 bg-purple-50/70 text-purple-900 ring-1 ring-purple-400'
    case 'banded':
      return 'border-teal-500 bg-teal-50/80 text-teal-900 ring-2 ring-teal-500'
    case 'missing':
      return 'border-slate-300 bg-slate-100 text-slate-400 line-through opacity-50'
    default:
      return ''
  }
}
</script>

<template>
  <div class="space-y-4 select-none">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center font-bold">
          <Layers class="w-5 h-5" />
        </div>
        <div>
          <h3 class="text-sm font-extrabold text-slate-900">Adult Permanent Dental Matrix</h3>
          <p class="text-xs text-slate-500">Universal Numbering (1–32) &bull; FDI World Dental Notation</p>
        </div>
      </div>

      <div v-if="!readOnly" class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          @click="handleSelectArch('upper')"
          class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition cursor-pointer"
        >
          Maxillary (Upper)
        </button>
        <button
          type="button"
          @click="handleSelectArch('lower')"
          class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition cursor-pointer"
        >
          Mandibular (Lower)
        </button>
        <button
          type="button"
          @click="handleClearAll"
          class="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-rose-600 text-xs font-semibold transition cursor-pointer"
        >
          Reset
        </button>
      </div>
    </div>

    <div class="bg-white rounded-3xl border border-slate-200 p-5 shadow-xs overflow-x-auto">
      <div class="min-w-[760px] space-y-6">
        <div>
          <div class="flex justify-between items-center px-2 mb-2">
            <span class="text-[11px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded-full">
              Maxillary Arch (Upper Jaw)
            </span>
            <span class="text-[10px] text-slate-400 font-medium">Right Quadrant 1 &bull; Left Quadrant 2</span>
          </div>

          <div class="grid grid-cols-16 gap-1 relative">
            <div class="absolute left-1/2 top-0 bottom-0 w-0.5 bg-teal-300/60 -translate-x-1/2 z-10 pointer-events-none"></div>

            <div
              v-for="tooth in upperTeeth"
              :key="tooth.id"
              @mouseenter="hoveredTooth = tooth"
              @mouseleave="hoveredTooth = null"
              @click="handleToothClick(tooth)"
              :class="[
                'p-1.5 rounded-xl border flex flex-col items-center justify-between text-center transition cursor-pointer relative min-h-24',
                isToothSelected(tooth.id)
                  ? 'border-teal-600 bg-teal-600 text-white shadow-md shadow-teal-600/20 z-20'
                  : getConditionClass(tooth.id) || 'border-slate-200 bg-slate-50/60 hover:border-teal-400 hover:bg-teal-50/20 text-slate-700'
              ]"
            >
              <span
                :class="[
                  'text-[10px] font-bold px-1 rounded-sm leading-tight',
                  isToothSelected(tooth.id) ? 'bg-teal-700 text-teal-100' : 'text-slate-400'
                ]"
              >
                #{{ tooth.id }}
              </span>

              <div class="my-1 text-center">
                <div
                  :class="[
                    'w-6 h-7 rounded-t-lg mx-auto border transition flex items-center justify-center font-mono text-[9px] font-bold',
                    isToothSelected(tooth.id)
                      ? 'bg-white text-teal-900 border-white shadow-xs'
                      : 'bg-white text-slate-600 border-slate-300'
                  ]"
                >
                  {{ tooth.fdi_number }}
                </div>
              </div>

              <span
                :class="[
                  'text-[9px] font-medium truncate max-w-full block capitalize',
                  isToothSelected(tooth.id) ? 'text-teal-100' : 'text-slate-400'
                ]"
              >
                {{ tooth.type.slice(0, 3) }}
              </span>
            </div>
          </div>
        </div>

        <div>
          <div class="flex justify-between items-center px-2 mb-2">
            <span class="text-[11px] font-bold uppercase tracking-wider text-teal-800 bg-teal-50 px-2.5 py-0.5 rounded-full">
              Mandibular Arch (Lower Jaw)
            </span>
            <span class="text-[10px] text-slate-400 font-medium">Right Quadrant 4 &bull; Left Quadrant 3</span>
          </div>

          <div class="grid grid-cols-16 gap-1 relative">
            <div class="absolute left-1/2 top-0 bottom-0 w-0.5 bg-teal-300/60 -translate-x-1/2 z-10 pointer-events-none"></div>

            <div
              v-for="tooth in lowerTeeth"
              :key="tooth.id"
              @mouseenter="hoveredTooth = tooth"
              @mouseleave="hoveredTooth = null"
              @click="handleToothClick(tooth)"
              :class="[
                'p-1.5 rounded-xl border flex flex-col items-center justify-between text-center transition cursor-pointer relative min-h-24',
                isToothSelected(tooth.id)
                  ? 'border-teal-600 bg-teal-600 text-white shadow-md shadow-teal-600/20 z-20'
                  : getConditionClass(tooth.id) || 'border-slate-200 bg-slate-50/60 hover:border-teal-400 hover:bg-teal-50/20 text-slate-700'
              ]"
            >
              <span
                :class="[
                  'text-[10px] font-bold px-1 rounded-sm leading-tight',
                  isToothSelected(tooth.id) ? 'bg-teal-700 text-teal-100' : 'text-slate-400'
                ]"
              >
                #{{ tooth.id }}
              </span>

              <div class="my-1 text-center">
                <div
                  :class="[
                    'w-6 h-7 rounded-b-lg mx-auto border transition flex items-center justify-center font-mono text-[9px] font-bold',
                    isToothSelected(tooth.id)
                      ? 'bg-white text-teal-900 border-white shadow-xs'
                      : 'bg-white text-slate-600 border-slate-300'
                  ]"
                >
                  {{ tooth.fdi_number }}
                </div>
              </div>

              <span
                :class="[
                  'text-[9px] font-medium truncate max-w-full block capitalize',
                  isToothSelected(tooth.id) ? 'text-teal-100' : 'text-slate-400'
                ]"
              >
                {{ tooth.type.slice(0, 3) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="hoveredTooth || focusedTooth" class="p-3 bg-slate-50 rounded-2xl border border-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <Info class="w-4 h-4 text-teal-600 shrink-0" />
        <span class="font-bold text-slate-900">
          Tooth #{{ (hoveredTooth || focusedTooth)?.id }} (FDI {{ (hoveredTooth || focusedTooth)?.fdi_number }}):
        </span>
        <span class="text-slate-600">
          {{ (hoveredTooth || focusedTooth)?.name }}
        </span>
      </div>

      <div class="flex items-center gap-2 text-[11px] text-slate-500 font-medium">
        <span class="capitalize">{{ (hoveredTooth || focusedTooth)?.arch }} Arch</span>
        &bull;
        <span class="capitalize">{{ (hoveredTooth || focusedTooth)?.type }}</span>
      </div>
    </div>

    <div v-if="showSurfaces && focusedTooth" class="bg-white p-5 rounded-2xl border border-teal-200 shadow-xs space-y-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Sparkles class="w-4 h-4 text-teal-600" />
          <h4 class="text-xs font-bold text-slate-900">
            Anatomical Surface Selector &bull; Tooth #{{ focusedTooth.id }} ({{ focusedTooth.fdi_number }})
          </h4>
        </div>
        <button
          type="button"
          @click="focusedToothId = null"
          class="text-slate-400 hover:text-slate-600 p-1 rounded-md"
        >
          <X class="w-4 h-4" />
        </button>
      </div>

      <div class="flex flex-col sm:flex-row items-center gap-6 justify-center py-2">
        <div class="relative w-36 h-36 flex items-center justify-center">
          <button
            type="button"
            @click="handleToggleSurface(focusedTooth.id, 'B')"
            :class="[
              'absolute top-0 w-20 h-9 rounded-t-xl border text-[10px] font-bold transition flex items-center justify-center cursor-pointer',
              isSurfaceActive(focusedTooth.id, 'B')
                ? 'bg-teal-600 text-white border-teal-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-teal-50'
            ]"
          >
            Facial / Buccal (B)
          </button>

          <button
            type="button"
            @click="handleToggleSurface(focusedTooth.id, 'M')"
            :class="[
              'absolute left-0 h-20 w-9 rounded-l-xl border text-[10px] font-bold transition flex items-center justify-center cursor-pointer',
              isSurfaceActive(focusedTooth.id, 'M')
                ? 'bg-teal-600 text-white border-teal-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-teal-50'
            ]"
          >
            Mesial (M)
          </button>

          <button
            type="button"
            @click="handleToggleSurface(focusedTooth.id, 'O')"
            :class="[
              'w-12 h-12 rounded-lg border text-[11px] font-extrabold transition flex items-center justify-center z-10 cursor-pointer shadow-xs',
              isSurfaceActive(focusedTooth.id, 'O')
                ? 'bg-teal-600 text-white border-teal-600'
                : 'bg-white text-slate-800 border-slate-300 hover:bg-teal-50'
            ]"
          >
            O / I
          </button>

          <button
            type="button"
            @click="handleToggleSurface(focusedTooth.id, 'D')"
            :class="[
              'absolute right-0 h-20 w-9 rounded-r-xl border text-[10px] font-bold transition flex items-center justify-center cursor-pointer',
              isSurfaceActive(focusedTooth.id, 'D')
                ? 'bg-teal-600 text-white border-teal-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-teal-50'
            ]"
          >
            Distal (D)
          </button>

          <button
            type="button"
            @click="handleToggleSurface(focusedTooth.id, 'L')"
            :class="[
              'absolute bottom-0 w-20 h-9 rounded-b-xl border text-[10px] font-bold transition flex items-center justify-center cursor-pointer',
              isSurfaceActive(focusedTooth.id, 'L')
                ? 'bg-teal-600 text-white border-teal-600'
                : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-teal-50'
            ]"
          >
            Lingual (L)
          </button>
        </div>

        <div class="text-xs space-y-1.5 text-slate-600 max-w-xs">
          <p class="font-bold text-slate-800">Tagged Surfaces on #{{ focusedTooth.id }}:</p>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="s in ['M', 'D', 'O', 'B', 'L'] as const"
              :key="s"
              :class="[
                'px-2 py-0.5 rounded text-[11px] font-bold border',
                isSurfaceActive(focusedTooth.id, s)
                  ? 'bg-teal-100 text-teal-800 border-teal-300'
                  : 'bg-slate-100 text-slate-400 border-slate-200'
              ]"
            >
              {{ s === 'O' ? 'Occlusal/Incisal (O)' : s === 'B' ? 'Buccal/Facial (B)' : s === 'L' ? 'Lingual (L)' : s === 'M' ? 'Mesial (M)' : 'Distal (D)' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="modelValue.length > 0" class="flex flex-wrap items-center gap-1.5 pt-2">
      <span class="text-xs font-bold text-slate-700 mr-1">Selected Teeth ({{ modelValue.length }}):</span>
      <span
        v-for="id in modelValue"
        :key="id"
        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-teal-50 text-teal-800 border border-teal-200"
      >
        #{{ id }}
        <button
          v-if="!readOnly"
          type="button"
          @click="handleToothClick(teethList.find(t => t.id === id)!)"
          class="hover:text-rose-600 cursor-pointer ml-0.5"
        >
          &times;
        </button>
      </span>
    </div>
  </div>
</template>
