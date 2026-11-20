import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AuthLayout from '@/layouts/AuthLayout.vue'
import AppLayout from '@/layouts/AppLayout.vue'
import LoginView from '@/views/auth/LoginView.vue'
import RegisterView from '@/views/auth/RegisterView.vue'
import DoctorCarouselView from '@/views/patient/DoctorCarouselView.vue'
import BookAppointmentView from '@/views/patient/BookAppointmentView.vue'
import MyAppointmentsView from '@/views/patient/MyAppointmentsView.vue'
import TreatmentBookletView from '@/views/patient/TreatmentBookletView.vue'
import ChatView from '@/views/chat/ChatView.vue'
import AppointmentsScheduleView from '@/views/clinic/AppointmentsScheduleView.vue'
import PatientRecordEditorView from '@/views/clinic/PatientRecordEditorView.vue'
import AnalyticsDashboardView from '@/views/admin/AnalyticsDashboardView.vue'
import AuditTrailView from '@/views/admin/AuditTrailView.vue'


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
        component: LoginView,
        meta: { guestOnly: true },
      },
      {
        path: '/register',
        name: 'register',
        component: RegisterView,
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
        component: DoctorCarouselView,
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'book',
        name: 'portal-book',
        component: BookAppointmentView,
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'appointments',
        name: 'portal-appointments',
        component: MyAppointmentsView,
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'records',
        name: 'portal-records',
        component: TreatmentBookletView,
        meta: { roles: ['patient', 'admin'] },
      },
      {
        path: 'chat',
        name: 'portal-chat',
        component: ChatView,
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
        component: AppointmentsScheduleView,
      },
      {
        path: 'records',
        name: 'clinic-records',
        component: PatientRecordEditorView,
      },
      {
        path: 'chat',
        name: 'clinic-chat',
        component: ChatView,
        meta: { requiresAuth: true },
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
        component: AnalyticsDashboardView,
      },
      {
        path: 'audit',
        name: 'admin-audit',
        component: AuditTrailView,
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

