import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthLayout from '@/layouts/AuthLayout.vue'
import AppLayout from '@/layouts/AppLayout.vue'

const AuthPlaceholder = {
  template: `
    <div class="text-center py-4">
      <h2 class="text-lg font-bold text-slate-900 mb-1">Authentication</h2>
      <p class="text-xs text-slate-500">Form will mount here.</p>
    </div>
  `,
}

const PortalPlaceholder = {
  template: `
    <div class="p-8 text-center bg-white rounded-2xl border border-slate-200 shadow-xs">
      <h2 class="text-xl font-bold text-slate-800 mb-2">Workspace Module</h2>
      <p class="text-sm text-slate-500">Module content will mount here.</p>
    </div>
  `,
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: () => {
      const authStore = useAuthStore()
      if (!authStore.isAuthenticated) {
        return '/login'
      }
      if (authStore.isAdmin) {
        return '/admin/analytics'
      }
      if (authStore.isDoctor || authStore.isSecretary) {
        return '/clinic/appointments'
      }
      return '/portal'
    },
  },
  {
    path: '/auth',
    component: AuthLayout,
    children: [
      {
        path: '/login',
        name: 'login',
        component: AuthPlaceholder,
        meta: { guestOnly: true },
      },
      {
        path: '/register',
        name: 'register',
        component: AuthPlaceholder,
        meta: { guestOnly: true },
      },
    ],
  },
  {
    path: '/portal',
    component: AppLayout,
    meta: { requiresAuth: true, roles: ['patient', 'admin'] },
    children: [
      {
        path: '',
        name: 'portal-dashboard',
        component: PortalPlaceholder,
      },
      {
        path: 'book',
        name: 'portal-book',
        component: PortalPlaceholder,
      },
      {
        path: 'appointments',
        name: 'portal-appointments',
        component: PortalPlaceholder,
      },
      {
        path: 'records',
        name: 'portal-records',
        component: PortalPlaceholder,
      },
      {
        path: 'chat',
        name: 'portal-chat',
        component: PortalPlaceholder,
        meta: { requiresAuth: true },
      },
    ],
  },
  {
    path: '/clinic',
    component: AppLayout,
    meta: { requiresAuth: true, roles: ['doctor', 'orthodontist', 'secretary', 'admin'] },
    children: [
      {
        path: 'appointments',
        name: 'clinic-appointments',
        component: PortalPlaceholder,
      },
      {
        path: 'records',
        name: 'clinic-records',
        component: PortalPlaceholder,
      },
    ],
  },
  {
    path: '/admin',
    component: AppLayout,
    meta: { requiresAuth: true, roles: ['admin'] },
    children: [
      {
        path: 'analytics',
        name: 'admin-analytics',
        component: PortalPlaceholder,
      },
      {
        path: 'audit',
        name: 'admin-audit',
        component: PortalPlaceholder,
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: {
      template: `
        <div class="min-h-screen flex items-center justify-center bg-slate-50 p-6 text-center">
          <div>
            <h1 class="text-4xl font-bold text-slate-900 mb-2">404</h1>
            <p class="text-sm text-slate-600 mb-4">Page not found</p>
            <router-link to="/" class="inline-block px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium">Return Home</router-link>
          </div>
        </div>
      `,
    },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  if (authStore.token && !authStore.user) {
    await authStore.init()
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const guestOnly = to.matched.some((record) => record.meta.guestOnly)

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  if (guestOnly && authStore.isAuthenticated) {
    if (authStore.isAdmin) {
      next('/admin/analytics')
    } else if (authStore.isDoctor || authStore.isSecretary) {
      next('/clinic/appointments')
    } else {
      next('/portal')
    }
    return
  }

  const allowedRoles = to.matched
    .flatMap((record) => (record.meta.roles as string[]) || [])
    .filter(Boolean)

  if (allowedRoles.length > 0 && authStore.role && !allowedRoles.includes(authStore.role)) {
    if (authStore.isAdmin) {
      next('/admin/analytics')
    } else if (authStore.isDoctor || authStore.isSecretary) {
      next('/clinic/appointments')
    } else {
      next('/portal')
    }
    return
  }

  next()
})

export default router

