<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const fullName = ref('')
const username = ref('')
const email = ref('')
const phone = ref('')
const password = ref('')

async function handleSubmit() {
  if (!fullName.value || !username.value || !email.value || !password.value) {
    return
  }
  try {
    await authStore.register({
      full_name: fullName.value,
      username: username.value,
      email: email.value,
      phone: phone.value || undefined,
      password: password.value,
    })
    await authStore.login({
      identifier: username.value,
      password: password.value,
    })
    router.push('/portal')
  } catch {
  }
}
</script>

<template>
  <div>
    <h2 class="text-xl font-bold text-slate-900 text-center mb-6">
      Create a Patient Account
    </h2>

    <div
      v-if="authStore.error"
      class="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm"
    >
      {{ authStore.error }}
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-3.5">
      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
          Full Name
        </label>
        <input
          v-model="fullName"
          type="text"
          required
          placeholder="Juan Dela Cruz"
          class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 text-sm"
        />
      </div>

      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
          Username
        </label>
        <input
          v-model="username"
          type="text"
          required
          placeholder="juandc"
          class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 text-sm"
        />
      </div>

      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
          Email Address
        </label>
        <input
          v-model="email"
          type="email"
          required
          placeholder="juan@example.com"
          class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-600 text-sm"
        />
      </div>

      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
          Phone (Optional)
        </label>
        <input
          v-model="phone"
          type="tel"
          placeholder="+639171234567"
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
        class="w-full py-2.5 px-4 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium text-sm rounded-lg shadow-sm transition-colors cursor-pointer mt-2"
      >
        {{ authStore.isLoading ? 'Creating account...' : 'Create account' }}
      </button>
    </form>

    <div class="mt-6 text-center text-xs text-slate-600">
      Already registered?
      <router-link to="/login" class="text-teal-600 hover:text-teal-700 font-semibold ml-1">
        Sign in
      </router-link>
    </div>
  </div>
</template>

