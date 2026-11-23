<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import Button from 'primevue/button'
import AppBrand from '@/components/AppBrand.vue'
import ClinicRecordsMenu from '@/components/ClinicRecordsMenu.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import {
  Calendar,
  Clock,
  BookOpen,
  MessageSquare,
  BarChart3,
  ShieldCheck,
  ClipboardList,
  LogOut,
  User,
} from 'lucide-vue-next'

const authStore = useAuthStore()
const chatStore = useChatStore()
const router = useRouter()
const route = useRoute()

onMounted(() => {
  if (authStore.isPatient || authStore.isSecretary) {
    chatStore.connectWebSocket()
    chatStore.fetchConversations().catch(() => {})
  }
})
onBeforeUnmount(chatStore.resetChat)

const navLinks = computed(() => {
  const links: Array<{ name: string; path: string; icon: typeof Calendar; badge?: number }> = []

  if (authStore.isPatient) {
    links.push(
      { name: 'Doctors', path: '/portal', icon: User },
      { name: 'Book Visit', path: '/portal/book', icon: Calendar },
      { name: 'My Visits', path: '/portal/appointments', icon: Clock },
      { name: 'Treatment & Ledger', path: '/portal/records', icon: BookOpen },
      {
        name: 'Live Chat',
        path: '/portal/chat',
        icon: MessageSquare,
        badge: chatStore.totalUnreadCount,
      },
    )
  } else if (authStore.isDoctor || authStore.isSecretary) {
    links.push(
      { name: 'Appointments', path: '/clinic/appointments', icon: Calendar },
      { name: 'Patient Records', path: '/clinic/records', icon: ClipboardList },
    )
    if (authStore.isSecretary) {
      links.push({
        name: 'Live Chat',
        path: '/clinic/chat',
        icon: MessageSquare,
        badge: chatStore.totalUnreadCount,
      })
    }
  } else if (authStore.isAdmin) {
    links.push(
      { name: 'Analytics', path: '/admin/analytics', icon: BarChart3 },
      { name: 'Audit Logs', path: '/admin/audit', icon: ShieldCheck },
      { name: 'Appointments', path: '/clinic/appointments', icon: Calendar },
      { name: 'Patient Records', path: '/clinic/records', icon: ClipboardList },
    )
  }

  return links
})

function isNavActive(path: string) {
  return route.path === path || (path === '/clinic/appointments' && route.name === 'clinic-booking-settings')
}

function handleLogout() {
  chatStore.resetChat()
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-backdrop flex min-h-screen flex-col">
    <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-8">
            <AppBrand />

            <nav class="hidden items-center gap-1 lg:flex" aria-label="Workspace">
              <template v-for="link in navLinks" :key="link.path">
                <ClinicRecordsMenu v-if="link.path === '/clinic/records'" />
                <router-link
                  v-else
                  :to="link.path"
                  class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                  :class="isNavActive(link.path)
                    ? 'bg-teal-50 text-teal-700 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'"
                >
                  <component :is="link.icon" class="w-4 h-4" />
                  <span>{{ link.name }}</span>
                  <span
                    v-if="link.badge && link.badge > 0"
                    class="ml-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-rose-500 rounded-full"
                  >
                    {{ link.badge > 99 ? '99+' : link.badge }}
                  </span>
                </router-link>
              </template>
            </nav>
          </div>

          <div class="flex items-center gap-4">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-600 font-semibold text-xs">
                {{ authStore.user?.full_name?.charAt(0) || 'U' }}
              </div>
              <div class="hidden sm:block text-left">
                <div class="text-sm font-medium text-slate-900 leading-none">
                  {{ authStore.user?.full_name }}
                </div>
                <div class="text-xs uppercase font-bold text-teal-600 mt-1">
                  {{ authStore.role }}
                </div>
              </div>
            </div>

            <Button
              type="button"
              severity="secondary"
              text
              aria-label="Sign out"
              title="Sign out"
              @click="handleLogout"
            >
              <LogOut class="w-5 h-5" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>

      <nav class="flex items-center justify-around overflow-x-auto border-t border-slate-100 px-4 py-2 lg:hidden" aria-label="Workspace">
        <template v-for="link in navLinks" :key="link.path">
          <ClinicRecordsMenu v-if="link.path === '/clinic/records'" mobile />
          <router-link
            v-else
            :to="link.path"
            class="flex flex-col items-center gap-1 py-1 px-2 rounded-md text-xs font-medium"
            :class="isNavActive(link.path) ? 'text-teal-700 font-semibold' : 'text-slate-600'"
          >
            <div class="relative">
              <component :is="link.icon" class="w-5 h-5" />
              <span
                v-if="link.badge && link.badge > 0"
                class="absolute -top-1 -right-2 w-4 h-4 bg-rose-500 text-white rounded-full text-[10px] flex items-center justify-center"
              >
                {{ link.badge }}
              </span>
            </div>
            <span class="text-[11px]">{{ link.name }}</span>
          </router-link>
        </template>
      </nav>
    </header>

    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <router-view />
    </main>

    <footer class="bg-white border-t border-slate-200 py-4 text-center text-xs text-slate-500">
      &copy; {{ new Date().getFullYear() }} OrthoBite Orthodontics. All rights reserved.
    </footer>
  </div>
</template>

