<script setup lang="ts">
import AppBrand from '@/components/AppBrand.vue'
</script>

<template>
  <div class="app-backdrop flex min-h-screen flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="text-center sm:mx-auto sm:w-full sm:max-w-md">
      <AppBrand class="mb-2" />
      <p class="text-center text-xs font-medium uppercase tracking-wider text-slate-500">
        Orthodontics & Bite Alignment Platform
      </p>
    </div>

    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
      <div class="app-panel px-6 py-8 sm:px-10">
        <router-view />
      </div>
    </div>
  </div>
</template>

