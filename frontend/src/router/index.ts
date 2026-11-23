import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthLayout from '@/layouts/AuthLayout.vue'
import LandingPageView from '@/views/LandingPageView.vue'
import LoginView from '@/views/auth/LoginView.vue'

const AppLayout = () => import('@/layouts/AppLayout.vue')
const ChatView = () => import('@/views/chat/ChatView.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: LandingPageView,
  },
  {
    path: '/auth',
    component: AuthLayout,
    children: [
      {
        path: '/login',
        name: 'login',
        component: LoginView,
        meta: { guestOnly: true },
      },
      {
        path: '/register',
        name: 'register',
        component: () => import('@/views/auth/RegisterView.vue'),
        meta: { guestOnly: true },
      },
    ],
  },
  {
    path: '/portal',
    component: AppLayout,
    meta: { requiresAuth: true, roles: ['patient', 'doctor', 'orthodontist', 'secretary', 'admin'] },
    children: [
      {
        path: '',
        name: 'portal-dashboard',
        component: () => import('@/views/patient/DoctorCarouselView.vue'),
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'book',
        name: 'portal-book',
        component: () => import('@/views/patient/BookAppointmentView.vue'),
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'appointments',
        name: 'portal-appointments',
        component: () => import('@/views/patient/MyAppointmentsView.vue'),
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'records',
        name: 'portal-records',
        component: () => import('@/views/patient/TreatmentBookletView.vue'),
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'chat',
        name: 'portal-chat',
        component: ChatView,
        meta: { roles: ['patient', 'secretary'] },
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
        component: () => import('@/views/clinic/AppointmentsScheduleView.vue'),
      },
      {
        path: 'records',
        name: 'clinic-records',
        component: () => import('@/views/clinic/PatientRecordEditorView.vue'),
      },
      {
        path: 'records/history',
        name: 'clinic-treatment-history',
        component: () => import('@/views/clinic/TreatmentHistoryView.vue'),
      },
      {
        path: 'records/files',
        name: 'clinic-patient-files',
        component: () => import('@/views/clinic/PatientFilesView.vue'),
        meta: { roles: ['doctor', 'orthodontist', 'admin'] },
      },
      {
        path: 'booking-settings',
        name: 'clinic-booking-settings',
        component: () => import('@/views/clinic/BookingSettingsView.vue'),
        meta: { roles: ['doctor', 'orthodontist'] },
      },
      {
        path: 'consultation-fee',
        redirect: { name: 'clinic-booking-settings' },
      },
      {
        path: 'availability',
        redirect: { name: 'clinic-booking-settings' },
      },
      {
        path: 'chat',
        name: 'clinic-chat',
        component: ChatView,
        meta: { roles: ['secretary'] },
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
        component: () => import('@/views/admin/AnalyticsDashboardView.vue'),
      },
      {
        path: 'audit',
        name: 'admin-audit',
        component: () => import('@/views/admin/AuditTrailView.vue'),
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

  const role = authStore.role
  const isRoleRestricted = to.matched.some((record) => {
    const allowedRoles = record.meta.roles as string[] | undefined
    return allowedRoles !== undefined && (!role || !allowedRoles.includes(role))
  })

  if (isRoleRestricted) {
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

