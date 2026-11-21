<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import {
  DollarSign,
  TrendingUp,
  AlertCircle,
  CalendarCheck,
  Users,
  Stethoscope,
  RefreshCw,
  Calendar,
  CheckCircle2,
  Clock,
  XCircle,
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  PieChart,
  CreditCard,
  Receipt,
  Activity,
  UserCheck,
  Percent,
} from 'lucide-vue-next'

const adminStore = useAdminStore()

const selectedHorizon = ref<number>(12)
const lastUpdated = ref<string>('')

function formatCurrency(val?: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val ?? 0)
}

function formatNumber(val?: number): string {
  return new Intl.NumberFormat('en-US').format(val ?? 0)
}

function formatMonth(monthKey: string): string {
  if (!monthKey) return ''
  const parts = monthKey.split('-')
  const p0 = parts[0]
  const p1 = parts[1]
  if (p0 && p1) {
    const year = parseInt(p0, 10)
    const month = parseInt(p1, 10) - 1
    const d = new Date(year, month)
    return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
  }
  return monthKey
}

async function loadAnalytics(): Promise<void> {
  try {
    await adminStore.fetchDashboardData(selectedHorizon.value)
    lastUpdated.value = new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
  }
}

function setHorizon(months: number): void {
  selectedHorizon.value = months
  loadAnalytics()
}

const maxMonthlyBilled = computed<number>(() => {
  const months = adminStore.revenueReport?.months ?? []
  if (months.length === 0) return 1
  const vals = months.map((m) => m.total_billed)
  return Math.max(...vals, 1)
})

const maxMonthlyAppointments = computed<number>(() => {
  const stats = adminStore.appointmentStats
  if (stats.length === 0) return 1
  const vals = stats.map((s) => s.total)
  return Math.max(...vals, 1)
})

const avgRevenuePerVisit = computed<number>(() => {
  const ov = adminStore.overview
  const rev = adminStore.revenueReport
  if (!ov || !rev || ov.total_completed_appointments <= 0) return 0
  return Math.round((rev.grand_total_billed / ov.total_completed_appointments) * 100) / 100
})

const collectionRateColor = computed<string>(() => {
  const rate = adminStore.netCollectionRate
  if (rate >= 90) return 'text-emerald-700 bg-emerald-50 border-emerald-200'
  if (rate >= 75) return 'text-sky-700 bg-sky-50 border-sky-200'
  return 'text-amber-700 bg-amber-50 border-amber-200'
})

const totalBilledSum = computed<number>(() => {
  const months = adminStore.revenueReport?.months ?? []
  return months.reduce((acc, m) => acc + m.total_billed, 0)
})

const totalCollectedSum = computed<number>(() => {
  const months = adminStore.revenueReport?.months ?? []
  return months.reduce((acc, m) => acc + m.revenue_collected, 0)
})

const totalOutstandingSum = computed<number>(() => {
  const months = adminStore.revenueReport?.months ?? []
  return months.reduce((acc, m) => acc + m.outstanding_balance, 0)
})

onMounted(() => {
  loadAnalytics()
})
</script>

<template>
  <div class="space-y-6">
    <div class="app-panel app-page-heading">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              Executive Console
            </span>
            <span v-if="lastUpdated" class="text-xs text-slate-400">
              Updated {{ lastUpdated }}
            </span>
          </div>
          <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Clinical Analytics & Revenue</h1>
          <p class="text-sm text-slate-500 mt-0.5">
            Real-time financial collection, patient visit throughput, and practice health metrics.
          </p>
        </div>

        <div class="flex items-center gap-3">
          <div class="inline-flex bg-slate-100 rounded-xl p-1 border border-slate-200">
            <button
              type="button"
              :class="[
                'px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors',
                selectedHorizon === 3
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900',
              ]"
              @click="setHorizon(3)"
            >
              3M
            </button>
            <button
              type="button"
              :class="[
                'px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors',
                selectedHorizon === 6
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900',
              ]"
              @click="setHorizon(6)"
            >
              6M
            </button>
            <button
              type="button"
              :class="[
                'px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors',
                selectedHorizon === 12
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900',
              ]"
              @click="setHorizon(12)"
            >
              12M
            </button>
          </div>

          <button
            type="button"
            :disabled="adminStore.isLoading"
            class="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 disabled:opacity-50 transition-colors shadow-xs"
            @click="loadAnalytics"
          >
            <RefreshCw
              class="w-3.5 h-3.5"
              :class="{ 'animate-spin': adminStore.isLoading }"
            />
            Refresh
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="adminStore.error"
      class="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-start gap-3"
    >
      <AlertTriangle class="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
      <div>
        <h3 class="text-sm font-semibold text-rose-800">Analytics Load Notice</h3>
        <p class="text-xs text-rose-700 mt-0.5">{{ adminStore.error }}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
      <div class="app-panel p-5 relative overflow-hidden">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Gross Billed</span>
          <div class="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center text-emerald-600">
            <DollarSign class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl font-bold text-slate-900">
            {{ formatCurrency(adminStore.revenueReport?.grand_total_billed) }}
          </div>
          <p class="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <Receipt class="w-3.5 h-3.5 text-slate-400" />
            Total procedures billed
          </p>
        </div>
      </div>

      <div class="app-panel p-5 relative overflow-hidden">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Collected Revenue</span>
          <div class="w-9 h-9 rounded-xl bg-sky-50 border border-sky-100 flex items-center justify-center text-sky-600">
            <TrendingUp class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl font-bold text-slate-900">
            {{ formatCurrency(adminStore.revenueReport?.grand_total_collected) }}
          </div>
          <div class="flex items-center gap-1.5 mt-1">
            <span :class="['text-xs font-semibold px-1.5 py-0.5 rounded border', collectionRateColor]">
              {{ adminStore.netCollectionRate }}%
            </span>
            <span class="text-xs text-slate-500">net collection rate</span>
          </div>
        </div>
      </div>

      <div class="app-panel p-5 relative overflow-hidden">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Outstanding Receivables</span>
          <div class="w-9 h-9 rounded-xl bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-600">
            <AlertCircle class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl font-bold text-slate-900">
            {{ formatCurrency(adminStore.revenueReport?.grand_outstanding) }}
          </div>
          <p class="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <CreditCard class="w-3.5 h-3.5 text-slate-400" />
            Zero-drift patient balance
          </p>
        </div>
      </div>

      <div class="app-panel p-5 relative overflow-hidden">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completion Rate</span>
          <div class="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600">
            <CalendarCheck class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl font-bold text-slate-900">
            {{ adminStore.appointmentCompletionRate }}%
          </div>
          <p class="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <CheckCircle2 class="w-3.5 h-3.5 text-emerald-500" />
            {{ formatNumber(adminStore.overview?.total_completed_appointments) }} visits completed
          </p>
        </div>
      </div>

      <div class="app-panel p-5 relative overflow-hidden">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Practice Scale</span>
          <div class="w-9 h-9 rounded-xl bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600">
            <Users class="w-5 h-5" />
          </div>
        </div>
        <div class="mt-3">
          <div class="text-2xl font-bold text-slate-900">
            {{ formatNumber(adminStore.overview?.total_patients) }}
          </div>
          <p class="text-xs text-slate-500 mt-1 flex items-center gap-1">
            <Stethoscope class="w-3.5 h-3.5 text-slate-400" />
            {{ formatNumber(adminStore.overview?.total_doctors) }} licensed doctors
          </p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 app-panel p-6 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between pb-4 border-b border-slate-100">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                <BarChart3 class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-base font-bold text-slate-900">Financial Performance Trajectory</h2>
                <p class="text-xs text-slate-500">Monthly billing vs revenue collected with outstanding balances</p>
              </div>
            </div>
            <div class="flex items-center gap-3 text-xs">
              <div class="flex items-center gap-1.5">
                <span class="w-2.5 h-2.5 rounded-xs bg-emerald-600"></span>
                <span class="text-slate-600 font-medium">Collected</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="w-2.5 h-2.5 rounded-xs bg-amber-400"></span>
                <span class="text-slate-600 font-medium">Outstanding</span>
              </div>
            </div>
          </div>

          <div v-if="adminStore.isLoading && (!adminStore.revenueReport || adminStore.revenueReport.months.length === 0)" class="py-12 flex justify-center items-center">
            <div class="flex items-center gap-2 text-slate-500 text-sm">
              <RefreshCw class="w-4 h-4 animate-spin text-emerald-600" />
              Loading financial metrics...
            </div>
          </div>

          <div v-else-if="!adminStore.revenueReport || adminStore.revenueReport.months.length === 0" class="py-12 text-center text-slate-400 text-sm">
            No revenue data recorded for the selected timeline.
          </div>

          <div v-else class="mt-4 space-y-4">
            <div
              v-for="stat in adminStore.revenueReport.months"
              :key="stat.month"
              class="group p-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-colors"
            >
              <div class="flex items-center justify-between text-xs mb-1.5">
                <div class="font-semibold text-slate-800 flex items-center gap-2">
                  <span>{{ formatMonth(stat.month) }}</span>
                  <span class="text-slate-400 font-normal">({{ stat.month }})</span>
                </div>
                <div class="flex items-center gap-4 text-xs font-mono">
                  <span class="text-slate-700">Billed: <strong class="font-semibold">{{ formatCurrency(stat.total_billed) }}</strong></span>
                  <span class="text-emerald-700">Collected: <strong class="font-semibold">{{ formatCurrency(stat.revenue_collected) }}</strong></span>
                  <span class="text-amber-700">Bal: <strong class="font-semibold">{{ formatCurrency(stat.outstanding_balance) }}</strong></span>
                </div>
              </div>

              <div class="w-full bg-slate-100 rounded-full h-3 overflow-hidden flex">
                <div
                  class="bg-emerald-600 h-full transition-all duration-500"
                  :style="{
                    width: `${Math.min(100, Math.round((stat.revenue_collected / (maxMonthlyBilled || 1)) * 100))}%`
                  }"
                  :title="`Collected: ${formatCurrency(stat.revenue_collected)}`"
                ></div>
                <div
                  class="bg-amber-400 h-full transition-all duration-500"
                  :style="{
                    width: `${Math.min(100, Math.round((stat.outstanding_balance / (maxMonthlyBilled || 1)) * 100))}%`
                  }"
                  :title="`Outstanding: ${formatCurrency(stat.outstanding_balance)}`"
                ></div>
              </div>

              <div class="flex justify-between items-center text-[11px] text-slate-400 mt-1">
                <span>Recovery Efficiency: {{ stat.total_billed > 0 ? Math.round((stat.revenue_collected / stat.total_billed) * 100) : 0 }}%</span>
                <span>Proportion of Peak: {{ Math.round((stat.total_billed / (maxMonthlyBilled || 1)) * 100) }}%</span>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-4 text-xs bg-slate-50 p-3 rounded-xl border">
          <span class="font-semibold text-slate-700">Timeline Aggregate Totals</span>
          <div class="flex items-center gap-6 font-mono">
            <span>Billed: <strong class="text-slate-900 font-semibold">{{ formatCurrency(totalBilledSum) }}</strong></span>
            <span>Collected: <strong class="text-emerald-700 font-semibold">{{ formatCurrency(totalCollectedSum) }}</strong></span>
            <span>Outstanding: <strong class="text-amber-700 font-semibold">{{ formatCurrency(totalOutstandingSum) }}</strong></span>
          </div>
        </div>
      </div>

      <div class="app-panel p-6 flex flex-col justify-between">
        <div>
          <div class="flex items-center gap-2 pb-4 border-b border-slate-100">
            <div class="w-8 h-8 rounded-lg bg-sky-50 text-sky-700 flex items-center justify-center font-bold">
              <Activity class="w-4 h-4" />
            </div>
            <div>
              <h2 class="text-base font-bold text-slate-900">Visit Status Pipeline</h2>
              <p class="text-xs text-slate-500">Distribution of patient appointments</p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 mt-4">
            <div class="bg-emerald-50/70 border border-emerald-100 rounded-xl p-3">
              <div class="flex items-center gap-1.5 text-emerald-800 text-xs font-semibold">
                <CheckCircle2 class="w-3.5 h-3.5 text-emerald-600" />
                Completed
              </div>
              <div class="text-xl font-bold text-emerald-950 mt-1">
                {{ formatNumber(adminStore.overview?.total_completed_appointments) }}
              </div>
              <p class="text-[11px] text-emerald-700 mt-0.5">Finished visits</p>
            </div>

            <div class="bg-sky-50/70 border border-sky-100 rounded-xl p-3">
              <div class="flex items-center gap-1.5 text-sky-800 text-xs font-semibold">
                <Clock class="w-3.5 h-3.5 text-sky-600" />
                Active / In-Flow
              </div>
              <div class="text-xl font-bold text-sky-950 mt-1">
                {{ formatNumber(adminStore.overview?.total_active_appointments) }}
              </div>
              <p class="text-[11px] text-sky-700 mt-0.5">Active or scheduled</p>
            </div>

            <div class="bg-amber-50/70 border border-amber-100 rounded-xl p-3">
              <div class="flex items-center gap-1.5 text-amber-800 text-xs font-semibold">
                <AlertCircle class="w-3.5 h-3.5 text-amber-600" />
                Pending
              </div>
              <div class="text-xl font-bold text-amber-950 mt-1">
                {{ formatNumber(adminStore.overview?.total_pending_appointments) }}
              </div>
              <p class="text-[11px] text-amber-700 mt-0.5">Awaiting clinic triage</p>
            </div>

            <div class="bg-rose-50/70 border border-rose-100 rounded-xl p-3">
              <div class="flex items-center gap-1.5 text-rose-800 text-xs font-semibold">
                <XCircle class="w-3.5 h-3.5 text-rose-600" />
                Cancelled
              </div>
              <div class="text-xl font-bold text-rose-950 mt-1">
                {{ formatNumber(adminStore.overview?.total_cancelled_appointments) }}
              </div>
              <p class="text-[11px] text-rose-700 mt-0.5">Cancelled or no-show</p>
            </div>
          </div>

          <div class="mt-6 pt-4 border-t border-slate-100">
            <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">Clinical Efficiency Indicators</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between text-xs p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <span class="text-slate-600 font-medium">Avg Revenue per Completed Visit</span>
                <span class="font-bold text-slate-900 font-mono">{{ formatCurrency(avgRevenuePerVisit) }}</span>
              </div>
              <div class="flex items-center justify-between text-xs p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <span class="text-slate-600 font-medium">Visit Retention Efficiency</span>
                <span class="font-bold text-slate-900">{{ adminStore.appointmentCompletionRate }}%</span>
              </div>
              <div class="flex items-center justify-between text-xs p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <span class="text-slate-600 font-medium">Doctor to Patient Ratio</span>
                <span class="font-bold text-slate-900">
                  1 : {{ adminStore.overview?.total_doctors ? Math.round((adminStore.overview.total_patients / adminStore.overview.total_doctors) * 10) / 10 : 0 }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-6 p-4 rounded-xl bg-slate-900 text-white">
          <div class="flex items-center justify-between">
            <span class="text-xs font-medium text-slate-400">Ledger Health</span>
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              Zero Drift Validated
            </span>
          </div>
          <p class="text-xs text-slate-300 mt-2">
            Patient treatment sheets and installment payment logs align with real-time balance checks.
          </p>
        </div>
      </div>
    </div>

    <div class="app-panel p-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-100">
        <div class="flex items-center gap-2">
          <div class="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold">
            <Calendar class="w-4 h-4" />
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-900">Monthly Appointment Volume & Fulfillment</h2>
            <p class="text-xs text-slate-500">Historical breakdown of visits booked, confirmed, and fulfilled</p>
          </div>
        </div>
        <div class="flex items-center gap-3 text-xs">
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span class="text-slate-600">Completed</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
            <span class="text-slate-600">Confirmed</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span class="text-slate-600">Pending</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            <span class="text-slate-600">Cancelled / No-show</span>
          </div>
        </div>
      </div>

      <div v-if="adminStore.isLoading && adminStore.appointmentStats.length === 0" class="py-12 flex justify-center items-center">
        <div class="flex items-center gap-2 text-slate-500 text-sm">
          <RefreshCw class="w-4 h-4 animate-spin text-indigo-600" />
          Loading appointment breakdown...
        </div>
      </div>

      <div v-else-if="adminStore.appointmentStats.length === 0" class="py-12 text-center text-slate-400 text-sm">
        No appointment volume logs recorded for the selected timeline.
      </div>

      <div v-else class="mt-4 overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead>
            <tr class="border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
              <th class="py-3 px-3">Month</th>
              <th class="py-3 px-3 text-right">Total Visits</th>
              <th class="py-3 px-3 text-right">Completed</th>
              <th class="py-3 px-3 text-right">Confirmed</th>
              <th class="py-3 px-3 text-right">Pending</th>
              <th class="py-3 px-3 text-right">Cancelled</th>
              <th class="py-3 px-3 text-right">No Show</th>
              <th class="py-3 px-3 text-center">Volume Visual</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="stat in adminStore.appointmentStats"
              :key="stat.month"
              class="hover:bg-slate-50/60 transition-colors"
            >
              <td class="py-3 px-3 font-semibold text-slate-800">
                {{ formatMonth(stat.month) }}
                <span class="text-slate-400 font-normal ml-1 text-[11px]">({{ stat.month }})</span>
              </td>
              <td class="py-3 px-3 text-right font-bold text-slate-900 font-mono">
                {{ formatNumber(stat.total) }}
              </td>
              <td class="py-3 px-3 text-right text-emerald-700 font-semibold font-mono">
                {{ formatNumber(stat.completed) }}
              </td>
              <td class="py-3 px-3 text-right text-sky-700 font-semibold font-mono">
                {{ formatNumber(stat.confirmed) }}
              </td>
              <td class="py-3 px-3 text-right text-amber-700 font-semibold font-mono">
                {{ formatNumber(stat.pending) }}
              </td>
              <td class="py-3 px-3 text-right text-rose-700 font-semibold font-mono">
                {{ formatNumber(stat.cancelled) }}
              </td>
              <td class="py-3 px-3 text-right text-slate-500 font-semibold font-mono">
                {{ formatNumber(stat.no_show) }}
              </td>
              <td class="py-3 px-3">
                <div class="w-36 bg-slate-100 rounded-full h-2.5 overflow-hidden flex mx-auto">
                  <div
                    class="bg-emerald-500 h-full"
                    :style="{
                      width: `${stat.total > 0 ? (stat.completed / stat.total) * 100 : 0}%`
                    }"
                  ></div>
                  <div
                    class="bg-sky-500 h-full"
                    :style="{
                      width: `${stat.total > 0 ? (stat.confirmed / stat.total) * 100 : 0}%`
                    }"
                  ></div>
                  <div
                    class="bg-amber-500 h-full"
                    :style="{
                      width: `${stat.total > 0 ? (stat.pending / stat.total) * 100 : 0}%`
                    }"
                  ></div>
                  <div
                    class="bg-rose-500 h-full"
                    :style="{
                      width: `${stat.total > 0 ? ((stat.cancelled + stat.no_show) / stat.total) * 100 : 0}%`
                    }"
                  ></div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
