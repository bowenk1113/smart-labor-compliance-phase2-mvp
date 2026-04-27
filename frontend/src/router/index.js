import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import History from '@/views/History.vue'
import AdminLogin from '@/views/admin/Login.vue'
import AdminDashboard from '@/views/admin/Dashboard.vue'
import AdminLogs from '@/views/admin/Logs.vue'
import AdminFeedbacks from '@/views/admin/Feedbacks.vue'
import AdminFaqs from '@/views/admin/Faqs.vue'
import AdminSources from '@/views/admin/Sources.vue'
import AdminPackages from '@/views/admin/Packages.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/history',
    name: 'History',
    component: History
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: AdminLogin
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: AdminDashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/logs',
    name: 'AdminLogs',
    component: AdminLogs,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/feedbacks',
    name: 'AdminFeedbacks',
    component: AdminFeedbacks,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/faqs',
    name: 'AdminFaqs',
    component: AdminFaqs,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/sources',
    name: 'AdminSources',
    component: AdminSources,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/packages',
    name: 'AdminPackages',
    component: AdminPackages,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('admin_token')
  
  if (to.meta.requiresAuth && !token) {
    next('/admin/login')
  } else {
    next()
  }
})

export default router