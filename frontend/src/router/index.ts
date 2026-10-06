import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true }, // 需要登录才能访问
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      // 分析报告页：动态路由参数 id = 分析记录 ID
      path: '/analysis/:id',
      name: 'analysis',
      component: () => import('@/views/AnalysisView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
    },
  ],
})

/** 全局前置守卫：没登录就踢去登录页，并记住来源页面方便登录后跳回 */
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
})

export default router
