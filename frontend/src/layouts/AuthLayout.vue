<script setup lang="ts">
import { Stethoscope } from 'lucide-vue-next'
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-teal-50 via-slate-50 to-cyan-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="flex justify-center items-center gap-2 mb-2">
        <div class="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white shadow-md shadow-teal-600/30">
          <Stethoscope class="w-6 h-6" />
        </div>
        <span class="text-2xl font-bold tracking-tight text-slate-900">
          Ortho<span class="text-teal-600">Bite</span>
        </span>
      </div>
      <p class="text-center text-xs font-medium uppercase tracking-wider text-slate-500">
        Orthodontics & Bite Alignment Platform
      </p>
    </div>

    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
      <div class="bg-white py-8 px-6 shadow-xl shadow-slate-200/50 rounded-2xl border border-slate-100 sm:px-10">
        <router-view />
      </div>
    </div>
  </div>
</template>

