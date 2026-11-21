<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import {
  RotateCcw,
  Eraser,
  PenLine,
  Check,
  Download,
  AlertCircle,
} from 'lucide-vue-next'

interface Point {
  x: number
  y: number
}

interface Stroke {
  points: Point[]
  color: string
  width: number
}

const props = withDefaults(
  defineProps<{
    width?: number
    height?: number
    strokeColor?: string
    lineWidth?: number
    backgroundColor?: string
    placeholder?: string
    readOnly?: boolean
    showConfirm?: boolean
  }>(),
  {
    width: 600,
    height: 220,
    strokeColor: '#0f172a',
    lineWidth: 2.5,
    backgroundColor: '#ffffff',
    placeholder: 'Sign using mouse, stylus, or touch...',
    readOnly: false,
    showConfirm: true,
  },
)

const emit = defineEmits<{
  (e: 'change', hasSignature: boolean): void
  (e: 'save', signatureBase64: string): void
  (e: 'clear'): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const isDrawing = ref<boolean>(false)
const strokes = ref<Stroke[]>([])
const currentStroke = ref<Stroke | null>(null)
const activeColor = ref<string>(props.strokeColor)
const activeWidth = ref<number>(props.lineWidth)
const hasSignature = ref<boolean>(false)

const availableColors = ['#0f172a', '#1d4ed8', '#047857']
const strokeWidths = [
  { label: 'Fine', value: 1.5 },
  { label: 'Medium', value: 2.5 },
  { label: 'Thick', value: 4.0 },
]

onMounted(() => {
  nextTick(() => {
    initCanvas()
    window.addEventListener('resize', handleResize)
  })
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})

watch(
  () => [props.width, props.height],
  () => {
    nextTick(() => {
      initCanvas()
      redraw()
    })
  },
)

function getCanvasCoordinates(e: MouseEvent | TouchEvent): Point | null {
  const canvas = canvasRef.value
  if (!canvas) return null

  const rect = canvas.getBoundingClientRect()
  let clientX = 0
  let clientY = 0

  if ('touches' in e) {
    const touch = e.touches[0]
    if (!touch) return null
    clientX = touch.clientX
    clientY = touch.clientY
  } else {
    clientX = e.clientX
    clientY = e.clientY
  }

  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height

  return {
    x: (clientX - rect.left) * scaleX,
    y: (clientY - rect.top) * scaleY,
  }
}

function initCanvas() {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return

  const dpr = window.devicePixelRatio || 1
  const displayWidth = container.clientWidth || props.width
  const displayHeight = props.height

  canvas.width = displayWidth * dpr
  canvas.height = displayHeight * dpr
  canvas.style.width = `${displayWidth}px`
  canvas.style.height = `${displayHeight}px`

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.scale(dpr, dpr)
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  redraw()
}

function handleResize() {
  initCanvas()
}

function startDrawing(e: MouseEvent | TouchEvent) {
  if (props.readOnly) return
  if ('button' in e && e.button !== 0) return

  const pt = getCanvasCoordinates(e)
  if (!pt) return

  isDrawing.value = true
  const stroke: Stroke = {
    points: [pt],
    color: activeColor.value,
    width: activeWidth.value,
  }
  currentStroke.value = stroke
  strokes.value.push(stroke)

  drawPoint(pt)
}

function draw(e: MouseEvent | TouchEvent) {
  if (!isDrawing.value || !currentStroke.value || props.readOnly) return

  const pt = getCanvasCoordinates(e)
  if (!pt) return

  const points = currentStroke.value.points
  points.push(pt)

  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.strokeStyle = currentStroke.value.color
  ctx.lineWidth = currentStroke.value.width

  if (points.length >= 3) {
    const len = points.length
    const p0 = points[len - 3]
    const p1 = points[len - 2]
    const p2 = points[len - 1]
    if (p0 && p1 && p2) {
      const midPoint = {
        x: (p1.x + p2.x) / 2,
        y: (p1.y + p2.y) / 2,
      }

      ctx.beginPath()
      const prevMid = {
        x: (p0.x + p1.x) / 2,
        y: (p0.y + p1.y) / 2,
      }
      ctx.moveTo(prevMid.x, prevMid.y)
      ctx.quadraticCurveTo(p1.x, p1.y, midPoint.x, midPoint.y)
      ctx.stroke()
    }
  } else if (points.length === 2) {
    const p0 = points[0]
    const p1 = points[1]
    if (p0 && p1) {
      ctx.beginPath()
      ctx.moveTo(p0.x, p0.y)
      ctx.lineTo(p1.x, p1.y)
      ctx.stroke()
    }
  }

  if (!hasSignature.value) {
    hasSignature.value = true
    emit('change', true)
  }
}

function stopDrawing() {
  if (!isDrawing.value) return
  isDrawing.value = false
  currentStroke.value = null
  redraw()
}

function drawPoint(pt: Point) {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.fillStyle = activeColor.value
  ctx.beginPath()
  ctx.arc(pt.x, pt.y, activeWidth.value / 2, 0, Math.PI * 2)
  ctx.fill()
}

function redraw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  for (const stroke of strokes.value) {
    const pts = stroke.points
    if (pts.length === 0) continue

    ctx.strokeStyle = stroke.color
    ctx.lineWidth = stroke.width
    ctx.fillStyle = stroke.color

    if (pts.length === 1) {
      const pt0 = pts[0]
      if (pt0) {
        ctx.beginPath()
        ctx.arc(pt0.x, pt0.y, stroke.width / 2, 0, Math.PI * 2)
        ctx.fill()
      }
      continue
    }

    const firstPt = pts[0]
    if (!firstPt) continue

    ctx.beginPath()
    ctx.moveTo(firstPt.x, firstPt.y)

    for (let i = 1; i < pts.length - 1; i++) {
      const curr = pts[i]
      const next = pts[i + 1]
      if (curr && next) {
        const midX = (curr.x + next.x) / 2
        const midY = (curr.y + next.y) / 2
        ctx.quadraticCurveTo(curr.x, curr.y, midX, midY)
      }
    }

    const last = pts[pts.length - 1]
    if (last) {
      ctx.lineTo(last.x, last.y)
      ctx.stroke()
    }
  }

  const hasStrokes = strokes.value.length > 0
  if (hasSignature.value !== hasStrokes) {
    hasSignature.value = hasStrokes
    emit('change', hasStrokes)
  }
}

function clear() {
  strokes.value = []
  currentStroke.value = null
  hasSignature.value = false
  redraw()
  emit('clear')
  emit('change', false)
}

function undo() {
  if (strokes.value.length === 0) return
  strokes.value.pop()
  redraw()
}

function isEmpty(): boolean {
  return strokes.value.length === 0
}

function toDataURL(type = 'image/png'): string {
  const canvas = canvasRef.value
  if (!canvas || isEmpty()) return ''
  return canvas.toDataURL(type)
}

function toBlob(): Promise<Blob | null> {
  const canvas = canvasRef.value
  return new Promise((resolve) => {
    if (!canvas || isEmpty()) {
      resolve(null)
      return
    }
    canvas.toBlob((blob) => {
      resolve(blob)
    }, 'image/png')
  })
}

function handleSave() {
  const data = toDataURL('image/png')
  if (data) {
    emit('save', data)
  }
}

defineExpose({
  clear,
  undo,
  isEmpty,
  toDataURL,
  toBlob,
})
</script>

<template>
  <div class="space-y-3 select-none">
    <div v-if="!readOnly" class="flex flex-wrap items-center justify-between gap-3 px-1">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-1.5 p-1 rounded-xl bg-slate-100 border border-slate-200">
          <button
            v-for="color in availableColors"
            :key="color"
            type="button"
            @click="activeColor = color"
            :class="[
              'w-6 h-6 rounded-lg transition border flex items-center justify-center cursor-pointer',
              activeColor === color ? 'ring-2 ring-teal-500 scale-105 border-white' : 'border-transparent hover:scale-105'
            ]"
            :style="{ backgroundColor: color }"
            :aria-label="`Color ${color}`"
          >
            <Check v-if="activeColor === color" class="w-3.5 h-3.5 text-white" />
          </button>
        </div>

        <div class="flex items-center gap-1 p-1 rounded-xl bg-slate-100 border border-slate-200">
          <button
            v-for="w in strokeWidths"
            :key="w.value"
            type="button"
            @click="activeWidth = w.value"
            :class="[
              'px-2.5 py-1 rounded-lg text-xs font-semibold transition cursor-pointer',
              activeWidth === w.value ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-900'
            ]"
          >
            {{ w.label }}
          </button>
        </div>
      </div>

      <div class="flex items-center gap-1.5">
        <button
          type="button"
          @click="undo"
          :disabled="strokes.length === 0"
          class="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-xs"
        >
          <RotateCcw class="w-3.5 h-3.5" />
          Undo
        </button>

        <button
          type="button"
          @click="clear"
          :disabled="strokes.length === 0"
          class="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-rose-600 text-xs font-semibold transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-xs"
        >
          <Eraser class="w-3.5 h-3.5" />
          Clear
        </button>
      </div>
    </div>

    <div
      ref="containerRef"
      class="relative rounded-3xl border border-slate-300/80 bg-white overflow-hidden shadow-xs touch-none"
    >
      <canvas
        ref="canvasRef"
        @mousedown="startDrawing"
        @mousemove="draw"
        @mouseup="stopDrawing"
        @mouseleave="stopDrawing"
        @touchstart.passive="startDrawing"
        @touchmove.passive="draw"
        @touchend.passive="stopDrawing"
        class="block w-full cursor-crosshair"
      ></canvas>

      <div
        v-if="!hasSignature"
        class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-slate-300 space-y-1.5 px-4 text-center"
      >
        <PenLine class="w-7 h-7 text-slate-300" />
        <p class="text-xs font-medium text-slate-400">{{ placeholder }}</p>
      </div>

      <div class="absolute bottom-6 left-8 right-8 pointer-events-none border-b border-dashed border-slate-300 flex justify-between text-[10px] text-slate-400 pb-1">
        <span>Patient Consent Signature</span>
        <span>X</span>
      </div>
    </div>

    <div v-if="!readOnly" class="flex items-center justify-between px-1 text-xs">
      <span class="text-slate-400 text-[11px] flex items-center gap-1">
        <PenLine class="w-3.5 h-3.5 text-teal-600" />
        Draw signature within the bordered canvas area.
      </span>

      <button
        v-if="hasSignature && showConfirm"
        type="button"
        @click="handleSave"
        class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-teal-600 hover:bg-teal-700 text-white font-semibold text-xs transition cursor-pointer shadow-sm shadow-teal-600/20"
      >
        <Check class="w-3.5 h-3.5" />
        Confirm Signature
      </button>
    </div>
  </div>
</template>
