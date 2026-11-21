<script setup lang="ts">
import { Stethoscope } from 'lucide-vue-next'
</script>

<template>
  <RouterLink
    :to="{ name: 'home' }"
    class="inline-flex w-fit shrink-0 items-center gap-2.5 rounded-xl text-xl font-bold tracking-tight text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-teal-700"
  >
    <span class="grid size-10 place-items-center rounded-xl bg-teal-700 text-white shadow-sm shadow-teal-700/20">
      <Stethoscope class="size-5" aria-hidden="true" />
    </span>
    <span>Ortho<span class="text-teal-700">Bite</span></span>
  </RouterLink>
</template>
