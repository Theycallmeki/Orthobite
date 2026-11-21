<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
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
    <h1 class="mb-6 text-center text-xl font-bold text-slate-900">
      Sign in to your account
    </h1>

    <div
      v-if="authStore.error"
      role="alert"
      class="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm"
    >
      {{ authStore.error }}
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-4">
      <div>
        <label for="login-identifier" class="app-form-label">
          Email or Username
        </label>
        <InputText
          id="login-identifier"
          v-model="identifier"
          autocomplete="username"
          required
          fluid
        />
      </div>

      <div>
        <label for="login-password" class="app-form-label">
          Password
        </label>
        <InputText
          id="login-password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          fluid
        />
      </div>

      <Button
        type="submit"
        :loading="authStore.isLoading"
        :label="authStore.isLoading ? 'Signing in…' : 'Sign in'"
        class="min-h-11 w-full"
      />
    </form>

    <div class="mt-6 text-center text-xs text-slate-600">
      Don't have an account?
      <router-link to="/register" class="text-teal-600 hover:text-teal-700 font-semibold ml-1">
        Create an account
      </router-link>
    </div>
  </div>
</template>

