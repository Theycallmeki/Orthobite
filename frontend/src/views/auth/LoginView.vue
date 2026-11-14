<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const identifier = ref('')
const password = ref('')

async function handleSubmit() {
  if (!identifier.value || !password.value) {
    return
  }
  try {
    await authStore.login({
      identifier: identifier.value,
      password: password.value,
    })
    const redirect = (route.query.redirect as string) || (
      authStore.isAdmin
        ? '/admin/analytics'
        : (authStore.isDoctor || authStore.isSecretary ? '/clinic/appointments' : '/portal')
    )
    router.push(redirect)
  } catch {
  }
}
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-slate-900 text-center mb-6">
      Sign in to your account
    </h2>

    <div
      v-if="authStore.error"
      class="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm"
    >
      {{ authStore.error }}
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
          Email or Username
        </label>
        <input
          v-model="identifier"
          type="text"
          required
          placeholder="e.g. maria@example.com"
          class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 text-sm"
        />
      </div>

      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
          Password
        </label>
        <input
          v-model="password"
          type="password"
          required
          placeholder="••••••••"
          class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 text-sm"
        />
      </div>

      <button
        type="submit"
        :disabled="authStore.isLoading"
        class="w-full py-2.5 px-4 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium text-sm rounded-lg shadow-sm transition-colors cursor-pointer"
      >
        {{ authStore.isLoading ? 'Signing in...' : 'Sign in' }}
      </button>
    </form>

    <div class="mt-6 text-center text-xs text-slate-600">
      Don't have an account?
      <router-link to="/register" class="text-teal-600 hover:text-teal-700 font-semibold ml-1">
        Create an account
      </router-link>
    </div>
  </div>
</template>

