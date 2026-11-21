<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import type { AuditAction, AuditLogResponse } from '@/api/admin'
import {
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  Trash2,
  Eye,
  X,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Clock,
  User,
  Activity,
  Calendar,
  Lock,
  Database,
  Globe,
  FileCode,
  CheckCircle2,
} from 'lucide-vue-next'

const adminStore = useAdminStore()

const filterAction = ref<AuditAction | ''>('')
const filterResource = ref<string>('')
const filterActorId = ref<number | ''>('')
const filterDateFrom = ref<string>('')
const filterDateTo = ref<string>('')
const currentPage = ref<number>(1)
const pageSize = ref<number>(25)

const selectedLog = ref<AuditLogResponse | null>(null)
const showInspector = ref<boolean>(false)

const showPurgeModal = ref<boolean>(false)
const purgeDays = ref<number>(365)
const purgeConfirmation = ref<string>('')
const isPurging = ref<boolean>(false)
const purgeSuccessMessage = ref<string | null>(null)

function formatDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function getActionBadgeClass(action: AuditAction): string {
  switch (action) {
    case 'CREATE':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'READ':
      return 'bg-sky-50 text-sky-700 border-sky-200'
    case 'UPDATE':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'DELETE':
      return 'bg-rose-50 text-rose-700 border-rose-200'
    case 'LOGIN':
      return 'bg-indigo-50 text-indigo-700 border-indigo-200'
    case 'LOGIN_FAILED':
      return 'bg-red-100 text-red-800 border-red-300 font-bold'
    default:
      return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

async function loadAuditLogs(page: number = currentPage.value): Promise<void> {
  currentPage.value = page
  try {
    await adminStore.fetchAuditLogs({
      page,
      limit: pageSize.value,
      action: filterAction.value || undefined,
      resource: filterResource.value.trim() || undefined,
      actor_id: typeof filterActorId.value === 'number' ? filterActorId.value : undefined,
      date_from: filterDateFrom.value ? new Date(filterDateFrom.value).toISOString() : undefined,
      date_to: filterDateTo.value ? new Date(filterDateTo.value).toISOString() : undefined,
    })
  } catch {
  }
}

function resetFilters(): void {
  filterAction.value = ''
  filterResource.value = ''
  filterActorId.value = ''
  filterDateFrom.value = ''
  filterDateTo.value = ''
  currentPage.value = 1
  loadAuditLogs(1)
}

function openInspector(log: AuditLogResponse): void {
  selectedLog.value = log
  showInspector.value = true
}

function closeInspector(): void {
  selectedLog.value = null
  showInspector.value = false
}

function openPurgeDialog(): void {
  purgeDays.value = 365
  purgeConfirmation.value = ''
  purgeSuccessMessage.value = null
  showPurgeModal.value = true
}

function closePurgeDialog(): void {
  showPurgeModal.value = false
  purgeConfirmation.value = ''
}

async function handleExecutePurge(): Promise<void> {
  if (purgeConfirmation.value.toUpperCase() !== 'PURGE') return
  isPurging.value = true
  try {
    const res = await adminStore.purgeAuditLogs(purgeDays.value)
    purgeSuccessMessage.value = `Successfully purged ${res.deleted_count} logs older than ${res.cutoff_date}.`
    setTimeout(() => {
      closePurgeDialog()
    }, 2000)
  } catch {
  } finally {
    isPurging.value = false
  }
}

const totalPages = computed<number>(() => {
  if (adminStore.auditTotal <= 0) return 1
  return Math.ceil(adminStore.auditTotal / pageSize.value)
})

const startRecordIndex = computed<number>(() => {
  if (adminStore.auditTotal === 0) return 0
  return (currentPage.value - 1) * pageSize.value + 1
})

const endRecordIndex = computed<number>(() => {
  return Math.min(currentPage.value * pageSize.value, adminStore.auditTotal)
})

onMounted(() => {
  loadAuditLogs(1)
})
</script>

<template>
  <div class="space-y-6">
    <div class="app-panel app-page-heading">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              <Lock class="w-3 h-3 mr-1" />
              Compliance & Security
            </span>
            <span class="text-xs text-slate-400">DPA 2012 / HIPAA Standard</span>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Security Audit Trail</h1>
          <p class="text-sm text-slate-500 mt-0.5">
            Immutable system activity logging, forensic request inspection, and data protection tracking.
          </p>
        </div>

        <div class="flex items-center gap-3">
          <button
            type="button"
            class="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-rose-700 bg-rose-50 border border-rose-200 rounded-xl hover:bg-rose-100 transition-colors shadow-xs"
            @click="openPurgeDialog"
          >
            <Trash2 class="w-3.5 h-3.5" />
            Purge Old Logs
          </button>

          <button
            type="button"
            :disabled="adminStore.isLoading"
            class="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-xs"
            @click="loadAuditLogs(currentPage)"
          >
            <RefreshCw
              class="w-3.5 h-3.5"
              :class="{ 'animate-spin': adminStore.isLoading }"
            />
            Refresh
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 pt-6 border-t border-slate-100">
        <div class="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/60">
          <div class="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
            <Database class="w-5 h-5" />
          </div>
          <div>
            <div class="text-xs text-slate-500 font-medium">Total Audit Events</div>
            <div class="text-lg font-bold text-slate-900 font-mono">
              {{ adminStore.auditTotal.toLocaleString() }}
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/60">
          <div class="w-9 h-9 rounded-lg bg-red-100 text-red-700 flex items-center justify-center">
            <ShieldAlert class="w-5 h-5" />
          </div>
          <div>
            <div class="text-xs text-slate-500 font-medium">Security Alerts</div>
            <div class="text-lg font-bold text-red-700 font-mono">
              {{ adminStore.topFailureAuditLogs.length }}
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/60">
          <div class="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
            <Activity class="w-5 h-5" />
          </div>
          <div>
            <div class="text-xs text-slate-500 font-medium">Retention Policy</div>
            <div class="text-lg font-bold text-slate-900">
              Active Immutable
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="adminStore.error"
      class="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-start gap-3"
    >
      <AlertTriangle class="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
      <div>
        <h3 class="text-sm font-semibold text-rose-800">Audit Trail Notice</h3>
        <p class="text-xs text-rose-700 mt-0.5">{{ adminStore.error }}</p>
      </div>
    </div>

    <div class="app-panel p-5 space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div class="flex items-center gap-2 text-sm font-bold text-slate-800">
          <Filter class="w-4 h-4 text-indigo-600" />
          Filter Audit Log Stream
        </div>
        <button
          type="button"
          class="text-xs text-indigo-600 hover:text-indigo-800 font-semibold"
          @click="resetFilters"
        >
          Reset Filters
        </button>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Action Type</label>
          <select
            v-model="filterAction"
            class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 py-2 px-2.5 transition-colors"
            @change="loadAuditLogs(1)"
          >
            <option value="">All Actions</option>
            <option value="CREATE">CREATE</option>
            <option value="READ">READ</option>
            <option value="UPDATE">UPDATE</option>
            <option value="DELETE">DELETE</option>
            <option value="LOGIN">LOGIN</option>
            <option value="LOGIN_FAILED">LOGIN_FAILED</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Resource</label>
          <input
            v-model="filterResource"
            type="text"
            placeholder="e.g. appointment, record"
            class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 py-2 px-2.5 transition-colors"
            @keyup.enter="loadAuditLogs(1)"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Actor User ID</label>
          <input
            v-model.number="filterActorId"
            type="number"
            placeholder="e.g. 1"
            class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 py-2 px-2.5 transition-colors"
            @keyup.enter="loadAuditLogs(1)"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Date From</label>
          <input
            v-model="filterDateFrom"
            type="date"
            class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 py-2 px-2.5 transition-colors"
            @change="loadAuditLogs(1)"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Date To</label>
          <input
            v-model="filterDateTo"
            type="date"
            class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 py-2 px-2.5 transition-colors"
            @change="loadAuditLogs(1)"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Page Size</label>
          <select
            v-model.number="pageSize"
            class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-indigo-500 py-2 px-2.5 transition-colors"
            @change="loadAuditLogs(1)"
          >
            <option :value="10">10 / page</option>
            <option :value="25">25 / page</option>
            <option :value="50">50 / page</option>
            <option :value="100">100 / page</option>
          </select>
        </div>
      </div>
    </div>

    <div class="app-panel overflow-hidden">
      <div v-if="adminStore.isLoading && adminStore.auditLogs.length === 0" class="py-16 text-center">
        <RefreshCw class="w-6 h-6 animate-spin text-indigo-600 mx-auto mb-2" />
        <p class="text-xs text-slate-500">Querying compliance audit logs...</p>
      </div>

      <div v-else-if="adminStore.auditLogs.length === 0" class="py-16 text-center">
        <Lock class="w-8 h-8 text-slate-300 mx-auto mb-2" />
        <h3 class="text-sm font-semibold text-slate-700">No matching audit logs</h3>
        <p class="text-xs text-slate-400 mt-1">Try adjusting the filter criteria or date range.</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="bg-slate-50/75 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <th class="py-3 px-4">Event ID</th>
              <th class="py-3 px-4">Timestamp</th>
              <th class="py-3 px-4">Action</th>
              <th class="py-3 px-4">Actor</th>
              <th class="py-3 px-4">Target Resource</th>
              <th class="py-3 px-4">Client IP</th>
              <th class="py-3 px-4 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="log in adminStore.auditLogs"
              :key="log.id"
              class="hover:bg-slate-50/80 transition-colors"
            >
              <td class="py-3.5 px-4 font-mono text-slate-500 font-medium">
                #{{ log.id }}
              </td>
              <td class="py-3.5 px-4 font-mono text-slate-700 whitespace-nowrap">
                {{ formatDate(log.timestamp) }}
              </td>
              <td class="py-3.5 px-4">
                <span
                  :class="[
                    'inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold border',
                    getActionBadgeClass(log.action),
                  ]"
                >
                  {{ log.action }}
                </span>
              </td>
              <td class="py-3.5 px-4">
                <div class="flex items-center gap-1.5 font-medium text-slate-800">
                  <User class="w-3.5 h-3.5 text-slate-400" />
                  <span v-if="log.actor_id !== null">User #{{ log.actor_id }}</span>
                  <span v-else class="text-slate-400 italic">System / Anon</span>
                </div>
              </td>
              <td class="py-3.5 px-4">
                <div class="flex items-center gap-1.5">
                  <span class="inline-flex px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-100 text-slate-700">
                    {{ log.resource }}
                  </span>
                  <span v-if="log.resource_id !== null" class="font-mono text-slate-500 text-[11px]">
                    #{{ log.resource_id }}
                  </span>
                </div>
              </td>
              <td class="py-3.5 px-4 font-mono text-slate-500 text-[11px]">
                {{ log.ip_address || '—' }}
              </td>
              <td class="py-3.5 px-4 text-right">
                <button
                  type="button"
                  class="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors"
                  @click="openInspector(log)"
                >
                  <Eye class="w-3 h-3" />
                  Details
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 border-t border-slate-100 text-xs">
        <div class="text-slate-500">
          Showing <span class="font-semibold text-slate-800">{{ startRecordIndex }}</span> to
          <span class="font-semibold text-slate-800">{{ endRecordIndex }}</span> of
          <span class="font-semibold text-slate-800">{{ adminStore.auditTotal }}</span> log entries
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            :disabled="currentPage <= 1 || adminStore.isLoading"
            class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-semibold disabled:opacity-40 hover:bg-slate-50 transition-colors"
            @click="loadAuditLogs(currentPage - 1)"
          >
            <ChevronLeft class="w-3.5 h-3.5" />
            Previous
          </button>

          <span class="px-2 font-mono text-slate-600 font-medium">
            Page {{ currentPage }} / {{ totalPages }}
          </span>

          <button
            type="button"
            :disabled="currentPage >= totalPages || adminStore.isLoading"
            class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-semibold disabled:opacity-40 hover:bg-slate-50 transition-colors"
            @click="loadAuditLogs(currentPage + 1)"
          >
            Next
            <ChevronRight class="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showInspector && selectedLog"
      class="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4"
      @click.self="closeInspector"
    >
      <div class="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        <div class="flex items-center justify-between p-5 border-b border-slate-100 bg-slate-50">
          <div class="flex items-center gap-2">
            <FileCode class="w-5 h-5 text-indigo-600" />
            <div>
              <h2 class="text-base font-bold text-slate-900">Audit Event Inspector</h2>
              <p class="text-xs text-slate-500 font-mono">Event Log #{{ selectedLog.id }}</p>
            </div>
          </div>
          <button
            type="button"
            class="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg transition-colors"
            @click="closeInspector"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="p-6 space-y-4 overflow-y-auto flex-1">
          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <span class="text-slate-400 font-medium block">Timestamp</span>
              <span class="font-mono font-semibold text-slate-900 mt-0.5 block">
                {{ formatDate(selectedLog.timestamp) }}
              </span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <span class="text-slate-400 font-medium block">Action Executed</span>
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border mt-1',
                  getActionBadgeClass(selectedLog.action),
                ]"
              >
                {{ selectedLog.action }}
              </span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <span class="text-slate-400 font-medium block">Actor User</span>
              <span class="font-medium text-slate-900 mt-0.5 block">
                {{ selectedLog.actor_id !== null ? `User #${selectedLog.actor_id}` : 'System Anonymous' }}
              </span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/60">
              <span class="text-slate-400 font-medium block">Client IP Address</span>
              <span class="font-mono text-slate-900 mt-0.5 block">
                {{ selectedLog.ip_address || 'Not Recorded' }}
              </span>
            </div>
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200/60 col-span-2">
              <span class="text-slate-400 font-medium block">Target Entity</span>
              <span class="font-mono font-semibold text-slate-900 mt-0.5 block">
                Resource: {{ selectedLog.resource }}
                <span v-if="selectedLog.resource_id !== null">(ID #{{ selectedLog.resource_id }})</span>
              </span>
            </div>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-bold text-slate-700 uppercase tracking-wider">Payload & Extra Context</span>
              <span class="text-[11px] text-slate-400 font-mono">application/json</span>
            </div>
            <pre class="bg-slate-900 text-slate-100 p-4 rounded-xl text-xs font-mono overflow-x-auto max-h-60">{{ JSON.stringify(selectedLog.extra, null, 2) || '{}' }}</pre>
          </div>
        </div>

        <div class="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
          <button
            type="button"
            class="px-4 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors shadow-xs"
            @click="closeInspector"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showPurgeModal"
      class="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4"
      @click.self="closePurgeDialog"
    >
      <div class="bg-white rounded-2xl border border-rose-200 shadow-2xl max-w-md w-full overflow-hidden">
        <div class="p-5 border-b border-rose-100 bg-rose-50/50 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Trash2 class="w-5 h-5 text-rose-600" />
            <h2 class="text-base font-bold text-rose-950">Purge Historic Audit Logs</h2>
          </div>
          <button
            type="button"
            class="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg transition-colors"
            @click="closePurgeDialog"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="p-6 space-y-4 text-xs">
          <div class="bg-amber-50 border border-amber-200 rounded-xl p-3 text-amber-800 flex items-start gap-2">
            <AlertTriangle class="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <span>
              This operation permanently deletes audit log records older than the selected retention horizon. This action cannot be reversed.
            </span>
          </div>

          <div v-if="purgeSuccessMessage" class="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-emerald-800 flex items-center gap-2">
            <CheckCircle2 class="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{{ purgeSuccessMessage }}</span>
          </div>

          <div>
            <label class="block font-semibold text-slate-700 mb-1">Retention Horizon (Days)</label>
            <input
              v-model.number="purgeDays"
              type="number"
              min="30"
              class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-rose-500 py-2 px-3"
            />
            <p class="text-[11px] text-slate-400 mt-1">Logs older than {{ purgeDays }} days will be permanently purged.</p>
          </div>

          <div>
            <label class="block font-semibold text-slate-700 mb-1">
              Type <strong class="text-rose-700 font-mono">PURGE</strong> to confirm:
            </label>
            <input
              v-model="purgeConfirmation"
              type="text"
              placeholder="PURGE"
              class="w-full text-xs rounded-xl border-slate-200 bg-slate-50 focus:bg-white focus:ring-2 focus:ring-rose-500 py-2 px-3 uppercase"
            />
          </div>
        </div>

        <div class="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-end gap-3">
          <button
            type="button"
            class="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
            @click="closePurgeDialog"
          >
            Cancel
          </button>
          <button
            type="button"
            :disabled="purgeConfirmation.toUpperCase() !== 'PURGE' || isPurging"
            class="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-rose-600 rounded-xl hover:bg-rose-700 disabled:opacity-40 transition-colors shadow-xs"
            @click="handleExecutePurge"
          >
            <Trash2 class="w-3.5 h-3.5" :class="{ 'animate-spin': isPurging }" />
            {{ isPurging ? 'Purging...' : 'Permanently Purge' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
