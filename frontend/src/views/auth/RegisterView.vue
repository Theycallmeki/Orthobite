<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
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
    <h1 class="mb-6 text-center text-xl font-bold text-slate-900">
      Create a Patient Account
    </h1>

    <div
      v-if="authStore.error"
      role="alert"
      class="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm"
    >
      {{ authStore.error }}
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-3.5">
      <div>
        <label for="register-name" class="app-form-label">
          Full Name
        </label>
        <InputText
          id="register-name"
          v-model="fullName"
          autocomplete="name"
          required
          fluid
        />
      </div>

      <div>
        <label for="register-username" class="app-form-label">
          Username
        </label>
        <InputText
          id="register-username"
          v-model="username"
          autocomplete="username"
          required
          fluid
        />
      </div>

      <div>
        <label for="register-email" class="app-form-label">
          Email Address
        </label>
        <InputText
          id="register-email"
          v-model="email"
          type="email"
          autocomplete="email"
          required
          fluid
        />
      </div>

      <div>
        <label for="register-phone" class="app-form-label">
          Phone (Optional)
        </label>
        <InputText
          id="register-phone"
          v-model="phone"
          type="tel"
          autocomplete="tel"
          fluid
        />
      </div>

      <div>
        <label for="register-password" class="app-form-label">
          Password
        </label>
        <InputText
          id="register-password"
          v-model="password"
          type="password"
          autocomplete="new-password"
          required
          fluid
        />
      </div>

      <Button
        type="submit"
        :loading="authStore.isLoading"
        :label="authStore.isLoading ? 'Creating account…' : 'Create account'"
        class="mt-2 min-h-11 w-full"
      />
    </form>

    <div class="mt-6 text-center text-xs text-slate-600">
      Already registered?
      <router-link to="/login" class="text-teal-600 hover:text-teal-700 font-semibold ml-1">
        Sign in
      </router-link>
    </div>
  </div>
</template>

