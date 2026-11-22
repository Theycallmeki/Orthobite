<script setup lang="ts">
import { computed, onBeforeUnmount, ref, shallowRef, useId, watch } from 'vue'
import { isAxiosError } from 'axios'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { Download, Eye, FileImage, FileText, Upload } from 'lucide-vue-next'
import type { PatientResponse } from '@/api/patient'
import { patientFilesApi, type PatientFile, type PatientFileUpdate } from '@/api/patientFile'
import { useClinicPatientSelection } from '@/composables/useClinicPatientSelection'
import { useAuthStore } from '@/stores/auth'

const PDF_MEDIA_TYPE = 'application/pdf'
const FILE_TYPES: Record<string, string> = {
  [PDF_MEDIA_TYPE]: 'PDF', 'image/jpeg': 'JPEG', 'image/png': 'PNG', 'image/webp': 'WebP',
}
const supportsInlinePdf = navigator.pdfViewerEnabled !== false
const FILE_ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp'
const FILE_LIMIT = 10 * 1024 * 1024
const PAGE_SIZE = 25
const DATE_FORMAT = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' })
const SIZE_FORMAT = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 })

type FileAction = { kind: 'upload' } | { kind: 'edit' | 'replace' | 'delete' | 'preview'; file: PatientFile }
type FilePreview = { url: string; filename: string; isPdf: boolean }

const authStore = useAuthStore()
const { patients, selectedPatient, selectPatient, loadingPatients, patientLoadError, loadPatients } =
  useClinicPatientSelection(authStore.isDoctor ? authStore.user?.id : undefined)
const patientId = computed(() => selectedPatient.value?.id)
const files = ref<PatientFile[]>([])
const loadingFiles = ref(false)
const filesError = ref('')
const page = ref(0)
const hasNextPage = ref(false)
const notice = ref<{ text: string; error?: boolean } | null>(null)

const action = shallowRef<FileAction | null>(null)
const actionError = ref('')
const pendingPatients = ref(new Set<number>())
const saving = computed(() => patientId.value !== undefined && pendingPatients.value.has(patientId.value))
const draftFile = shallowRef<File | null>(null)
const draftName = ref('')
const draftDescription = ref('')
const preview = shallowRef<FilePreview | null>(null)
const pdfTitleId = useId()
const isPdfPreview = computed(() => action.value?.kind === 'preview'
  && (preview.value?.isPdf ?? action.value.file.media_type === PDF_MEDIA_TYPE))
const isExpandedPreview = computed(() => supportsInlinePdf && isPdfPreview.value)
const downloading = ref<number | null>(null)
const currentFile = computed(() => action.value && action.value.kind !== 'upload' ? action.value.file : null)
const changes = computed(() => {
  const file = currentFile.value
  const update: PatientFileUpdate = {}
  if (file) {
    const name = draftName.value.trim()
    if (name !== file.display_name) update.display_name = name
    if (draftDescription.value !== (file.description ?? '')) update.description = draftDescription.value.trim() || null
  }
  return update
})
const canSubmit = computed(() => {
  switch (action.value?.kind) {
    case 'upload':
    case 'replace': return draftFile.value !== null
    case 'edit': return !!draftName.value.trim() && Object.keys(changes.value).length > 0
    case 'delete': return true
    default: return false
  }
})
const actionLabel = computed(() => {
  switch (action.value?.kind) {
    case 'upload': return 'Upload file'
    case 'edit': return 'Edit file details'
    case 'replace': return 'Replace file'
    case 'delete': return 'Delete file'
    case 'preview': return 'File preview'
  }
})

let scope = new AbortController()
let listRequest: AbortController | undefined
let previewRequest: AbortController | undefined

function patientLabel(patient: PatientResponse) {
  return patient.user?.full_name || `Patient #${patient.id}`
}

function formatSize(bytes: number) {
  if (bytes >= 1024 * 1024) return `${SIZE_FORMAT.format(bytes / (1024 * 1024))} MiB`
  if (bytes >= 1024) return `${SIZE_FORMAT.format(bytes / 1024)} KiB`
  return `${bytes} B`
}

function canPreviewFile(mediaType: string) {
  return Object.hasOwn(FILE_TYPES, mediaType)
}

function fileError(error: unknown, fallback: string) {
  if (!isAxiosError(error)) return fallback
  const detail: unknown = error.response?.data?.detail
  const status = error.response?.status
  if (status === 403) return 'You no longer have access to this patient’s files.'
  if (status === 413) return 'Choose a file up to 10 MiB.'
  if (status === 422) return 'Check the file name and description.'
  return typeof detail === 'string' ? detail : fallback
}

async function loadFiles(pageIndex = page.value) {
  const id = patientId.value
  if (id === undefined) return
  listRequest?.abort()
  const request = new AbortController()
  listRequest = request
  loadingFiles.value = true
  filesError.value = ''
  try {
    const { data } = await patientFilesApi.list(id, pageIndex * PAGE_SIZE, PAGE_SIZE + 1, request.signal)
    if (request.signal.aborted) return
    if (!data.length && pageIndex > 0) {
      void loadFiles(0)
      return
    }
    files.value = data.slice(0, PAGE_SIZE)
    page.value = pageIndex
    hasNextPage.value = data.length > PAGE_SIZE
  } catch (error) {
    if (!request.signal.aborted) filesError.value = fileError(error, 'Could not load files. Try again.')
  } finally {
    if (!request.signal.aborted) loadingFiles.value = false
  }
}

function closeAction() {
  previewRequest?.abort()
  if (preview.value) URL.revokeObjectURL(preview.value.url)
  preview.value = null
  action.value = null
  actionError.value = ''
  draftFile.value = null
  draftName.value = ''
  draftDescription.value = ''
}

function openAction(nextAction: FileAction) {
  closeAction()
  action.value = nextAction
  if (nextAction.kind === 'edit') {
    draftName.value = nextAction.file.display_name
    draftDescription.value = nextAction.file.description ?? ''
  }
}

async function previewFile(file: PatientFile) {
  openAction({ kind: 'preview', file })
  const request = new AbortController()
  previewRequest = request
  try {
    const { data, headers } = await patientFilesApi.getContent(file.patient_id, file.id, true, request.signal)
    if (request.signal.aborted) return
    if (!canPreviewFile(data.type)) {
      actionError.value = 'Preview is unavailable for this file. Try downloading it.'
      return
    }
    preview.value = {
      url: URL.createObjectURL(data),
      filename: downloadName(headers['content-disposition'], file.display_name),
      isPdf: data.type === PDF_MEDIA_TYPE,
    }
  } catch (error) {
    if (!request.signal.aborted) actionError.value = fileError(error, 'Could not load the file preview.')
  }
}

function downloadName(header: unknown, fallback: string) {
  if (typeof header !== 'string') return fallback
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header)?.[1]
  if (!encoded) return fallback
  try {
    return decodeURIComponent(encoded)
  } catch {
    return fallback
  }
}

async function downloadFile(file: PatientFile) {
  const { signal } = scope
  downloading.value = file.id
  notice.value = null
  try {
    const { data, headers } = await patientFilesApi.getContent(file.patient_id, file.id, false, signal)
    if (signal.aborted) return
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = downloadName(headers['content-disposition'], file.display_name)
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) {
    if (!signal.aborted) notice.value = { text: fileError(error, 'Could not download the file.'), error: true }
  } finally {
    if (!signal.aborted) downloading.value = null
  }
}

function chooseFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  actionError.value = ''
  draftFile.value = null
  if (!file) return
  if (file.size > FILE_LIMIT || file.size === 0) {
    actionError.value = file.size === 0 ? 'Choose a file with content.' : 'Choose a file up to 10 MiB.'
    input.value = ''
    return
  }
  draftFile.value = file
}

async function submitAction() {
  const id = patientId.value
  const target = action.value
  const upload = draftFile.value
  if (id === undefined || !target || target.kind === 'preview' || saving.value || !canSubmit.value) return
  const { signal } = scope
  pendingPatients.value.add(id)
  actionError.value = ''
  notice.value = null
  try {
    let text: string
    switch (target.kind) {
      case 'upload':
        if (!upload) return
        await patientFilesApi.upload(id, upload, draftDescription.value.trim())
        text = 'File uploaded.'
        break
      case 'edit':
        await patientFilesApi.update(id, target.file.id, changes.value)
        text = 'File details saved.'
        break
      case 'replace':
        if (!upload) return
        await patientFilesApi.replace(id, target.file.id, upload)
        text = 'New file version saved.'
        break
      case 'delete':
        await patientFilesApi.remove(id, target.file.id)
        text = 'File deleted.'
        break
    }
    if (!signal.aborted) {
      if (action.value === target) closeAction()
      notice.value = { text }
    }
    if (!scope.signal.aborted && patientId.value === id) {
      void loadFiles(target.kind === 'upload' && !signal.aborted ? 0 : page.value)
    }
  } catch (error) {
    if (!signal.aborted) {
      const text = fileError(error, 'Could not save the change. Try again.')
      if (action.value === target) actionError.value = text
      else notice.value = { text, error: true }
    }
  } finally {
    pendingPatients.value.delete(id)
  }
}

function clearScope() {
  scope.abort()
  listRequest?.abort()
  closeAction()
}

watch(patientId, () => {
  clearScope()
  scope = new AbortController()
  files.value = []
  filesError.value = ''
  loadingFiles.value = false
  notice.value = null
  downloading.value = null
  page.value = 0
  hasNextPage.value = false
  void loadFiles()
})
onBeforeUnmount(clearScope)
</script>

<template>
  <div class="space-y-5 pb-10">
    <section class="app-panel app-page-heading">
      <h1 class="text-2xl font-bold tracking-tight text-slate-900">Documents</h1>
      <div class="mt-4 max-w-md">
        <label for="files-patient" class="app-form-label">Patient</label>
        <select
          id="files-patient"
          :value="selectedPatient?.id ?? ''"
          :disabled="loadingPatients || patientLoadError || !patients.length"
          class="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 focus-visible:outline-2 focus-visible:outline-teal-700"
          @change="selectPatient(Number(($event.target as HTMLSelectElement).value))"
        >
          <option value="" disabled>{{ loadingPatients ? 'Loading patients…' : 'Choose a patient' }}</option>
          <option v-for="patient in patients" :key="patient.id" :value="patient.id">{{ patientLabel(patient) }}</option>
        </select>
      </div>
    </section>

    <div v-if="patientLoadError" class="app-panel flex flex-wrap items-center justify-between gap-3 p-4">
      <p role="alert" class="text-sm text-rose-800">Could not load patients.</p>
      <Button label="Try again" severity="secondary" size="small" outlined @click="loadPatients" />
    </div>
    <p v-else-if="!loadingPatients && !selectedPatient" class="app-panel p-4 text-sm text-slate-600">
      {{ patients.length ? 'Choose a patient to see their files.' : authStore.isDoctor ? 'No patients are assigned to you yet.' : 'No patient profiles are available.' }}
    </p>

    <section v-if="selectedPatient && !patientLoadError" class="app-panel overflow-hidden" aria-label="Patient documents">
      <div class="flex justify-end px-4 py-4 sm:px-5">
        <Button size="small" :disabled="loadingFiles || !!filesError || saving" @click="openAction({ kind: 'upload' })">
          <Upload class="size-4" aria-hidden="true" /> Upload file
        </Button>
      </div>

      <p v-if="notice" :role="notice.error ? 'alert' : 'status'" class="mx-4 mb-3 rounded-lg px-3 py-2 text-sm sm:mx-5"
        :class="notice.error ? 'bg-rose-50 text-rose-800' : 'bg-teal-50 text-teal-800'">{{ notice.text }}</p>
      <p v-if="saving && !action" role="status" class="px-5 pb-3 text-sm text-slate-600">Saving changes…</p>
      <p v-if="loadingFiles" role="status" class="px-5 pb-6 text-sm text-slate-600">Loading files…</p>
      <div v-else-if="filesError" class="flex flex-wrap items-center gap-3 px-5 pb-5">
        <p role="alert" class="text-sm text-rose-800">{{ filesError }}</p>
        <Button label="Try again" severity="secondary" size="small" outlined @click="loadFiles()" />
      </div>
      <p v-else-if="!files.length" class="mx-4 mb-4 rounded-xl border border-dashed border-slate-300 p-5 text-sm text-slate-600 sm:mx-5">
        No documents for this patient yet.
      </p>

      <template v-else>
        <ul class="divide-y divide-slate-200 border-t border-slate-200" aria-label="Documents">
          <li v-for="file in files" :key="file.id" class="flex flex-col gap-3 px-4 py-4 sm:px-5 lg:flex-row lg:items-center lg:justify-between">
            <div class="flex min-w-0 gap-3">
              <div class="grid size-10 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-600">
                <component :is="file.media_type.startsWith('image/') ? FileImage : FileText" class="size-5" aria-hidden="true" />
              </div>
              <div class="min-w-0">
                <h3 class="font-semibold wrap-anywhere text-slate-900">{{ file.display_name }}</h3>
                <p v-if="file.description" class="mt-1 text-sm wrap-anywhere whitespace-pre-wrap text-slate-700">{{ file.description }}</p>
                <p class="mt-1 flex flex-wrap gap-x-2 text-xs text-slate-600">
                  <span>{{ FILE_TYPES[file.media_type] ?? file.media_type }} · {{ formatSize(file.size_bytes) }}</span>
                  <span>· {{ DATE_FORMAT.format(new Date(file.created_at)) }} · {{ file.uploaded_by_name }}</span>
                  <span v-if="file.version > 1">· Version {{ file.version }}</span>
                </p>
              </div>
            </div>
            <div class="flex flex-wrap gap-1" :aria-label="`Actions for ${file.display_name}`" role="group">
              <Button v-if="canPreviewFile(file.media_type)" text size="small" @click="previewFile(file)">
                <Eye class="size-4" aria-hidden="true" /> Preview
              </Button>
              <Button text size="small" :loading="downloading === file.id" :disabled="downloading !== null" @click="downloadFile(file)">
                <Download class="size-4" aria-hidden="true" /> Download
              </Button>
              <Button label="Edit details" text size="small" :disabled="saving" @click="openAction({ kind: 'edit', file })" />
              <Button label="Replace" text size="small" :disabled="saving" @click="openAction({ kind: 'replace', file })" />
              <Button label="Delete" text size="small" severity="danger" :disabled="saving" @click="openAction({ kind: 'delete', file })" />
            </div>
          </li>
        </ul>
        <nav v-if="page || hasNextPage" aria-label="File pages" class="flex items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 sm:px-5">
          <Button label="Previous" size="small" severity="secondary" outlined :disabled="page === 0" @click="loadFiles(page - 1)" />
          <span class="text-sm text-slate-600">Page {{ page + 1 }}</span>
          <Button label="Next" size="small" severity="secondary" outlined :disabled="!hasNextPage" @click="loadFiles(page + 1)" />
        </nav>
      </template>
    </section>

    <Dialog :visible="!!action" :header="actionLabel" modal
      :class="isExpandedPreview
        ? 'h-[calc(100dvh-1rem)] max-h-none w-[calc(100vw-1rem)] max-w-[112rem] sm:h-[calc(100dvh-2rem)] sm:w-[calc(100vw-2rem)]'
        : 'w-[min(34rem,calc(100vw-2rem))]'"
      :pt="isPdfPreview ? { root: { 'aria-labelledby': pdfTitleId }, header: { class: 'gap-3 px-3 py-2 sm:px-5' } } : undefined"
      :content-class="isExpandedPreview ? 'flex min-h-0 flex-1 flex-col' : undefined"
      :draggable="!isExpandedPreview"
      :block-scroll="isExpandedPreview"
      @update:visible="closeAction">
      <template v-if="isPdfPreview" #header>
        <div class="grid min-w-0 flex-1 gap-x-5 gap-y-1 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
          <div class="min-w-0">
            <h2 :id="pdfTitleId" :title="currentFile?.display_name" class="truncate text-sm font-semibold text-slate-900">
              {{ currentFile?.display_name ?? 'PDF preview' }}
            </h2>
            <p v-if="selectedPatient" class="truncate text-xs text-slate-600">{{ patientLabel(selectedPatient) }}</p>
          </div>
          <div v-if="preview?.isPdf" class="flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold text-teal-700 sm:text-sm">
            <a :href="preview.url" target="_blank" rel="noopener noreferrer" class="underline">Open PDF in new tab</a>
            <a :href="preview.url" :download="preview.filename" class="underline">Download PDF</a>
          </div>
        </div>
      </template>
      <div v-if="action && selectedPatient" :class="isExpandedPreview ? 'flex min-h-0 flex-1 flex-col' : 'space-y-4'">
        <div v-if="!isPdfPreview" class="shrink-0 text-sm text-slate-600">
          <p>{{ patientLabel(selectedPatient) }}</p>
          <p v-if="currentFile" class="mt-1 font-semibold wrap-anywhere text-slate-900">{{ currentFile.display_name }}</p>
        </div>
        <template v-if="action.kind === 'preview'">
          <p v-if="actionError" role="alert" class="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{{ actionError }}</p>
          <template v-else-if="preview?.isPdf">
            <iframe v-if="supportsInlinePdf" :src="preview.url" :title="currentFile?.display_name ?? 'PDF preview'"
              class="min-h-0 w-full flex-1 rounded-lg border border-slate-200 bg-slate-100" />
          </template>
          <img v-else-if="preview" :src="preview.url" :alt="currentFile?.display_name"
            class="mx-auto max-h-[65vh] w-full rounded-lg bg-slate-100 object-contain" />
          <p v-else role="status" class="text-sm text-slate-600">Loading preview…</p>
        </template>
        <form v-else class="space-y-4" @submit.prevent="submitAction">
          <fieldset :disabled="saving" class="min-w-0 space-y-3">
            <p v-if="action.kind === 'replace'" class="text-sm text-slate-700">The new upload becomes the current version. Earlier versions are retained.</p>
            <p v-if="action.kind === 'delete'" class="text-sm text-slate-700">Delete this file from the Documents list? The file and its versions will be retained in the medical record.</p>
            <div v-if="action.kind === 'upload' || action.kind === 'replace'">
              <label for="patient-file-input" class="app-form-label">File</label>
              <input id="patient-file-input" type="file" :accept="FILE_ACCEPT" aria-describedby="patient-file-formats" required
                class="block w-full rounded-lg border border-slate-300 p-2 text-sm text-slate-800 file:mr-3 file:rounded-md file:bg-teal-50 file:px-2 file:py-1 file:font-semibold file:text-teal-800"
                @change="chooseFile" />
              <p id="patient-file-formats" class="mt-1 text-xs text-slate-600">PDF, JPEG, PNG, or WebP up to 10 MiB.</p>
            </div>
            <div v-if="action.kind === 'edit'">
              <label for="patient-file-name" class="app-form-label">File name</label>
              <input id="patient-file-name" v-model="draftName" required maxlength="255" class="w-full rounded-lg border border-slate-300 p-2 text-sm" />
            </div>
            <div v-if="action.kind === 'upload' || action.kind === 'edit'">
              <label for="patient-file-description" class="app-form-label">Description (optional)</label>
              <textarea id="patient-file-description" v-model="draftDescription" maxlength="2000" rows="3" class="w-full rounded-lg border border-slate-300 p-2 text-sm" />
            </div>
          </fieldset>
          <p v-if="actionError" role="alert" class="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{{ actionError }}</p>
          <p v-if="saving" role="status" class="text-sm text-slate-600">Saving for {{ patientLabel(selectedPatient) }}…</p>
          <div class="flex flex-wrap justify-end gap-2">
            <Button type="button" :label="saving ? 'Close' : 'Cancel'" severity="secondary" outlined @click="closeAction" />
            <Button type="submit" :label="action.kind === 'edit' ? 'Save changes' : actionLabel"
              :severity="action.kind === 'delete' ? 'danger' : undefined" :loading="saving" :disabled="saving || !canSubmit" />
          </div>
        </form>
      </div>
    </Dialog>
  </div>
</template>
