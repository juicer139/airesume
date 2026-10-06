/** 认证状态仓库（Pinia setup store 写法）。
 *
 * 职责：保存 token 和当前用户，向外暴露 login / register / fetchUser / logout。
 * token 同步存 localStorage，刷新页面不掉登录态。
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  fetchMe,
  login as apiLogin,
  register as apiRegister,
  type LoginPayload,
  type RegisterPayload,
  type UserInfo,
} from '@/api/user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') ?? '')
  const user = ref<UserInfo | null>(null)
  const isLoggedIn = computed(() => !!token.value)

  async function register(payload: RegisterPayload) {
    await apiRegister(payload)
  }

  async function login(payload: LoginPayload) {
    const data = await apiLogin(payload)
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    await fetchUser()
  }

  async function fetchUser() {
    user.value = await fetchMe()
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, register, login, fetchUser, logout }
})
