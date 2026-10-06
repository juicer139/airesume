/** axios 实例：全项目唯一的 HTTP 出口。
 *
 * 两个拦截器是前端认证的核心：
 * - 请求拦截器：每次请求自动带上 Authorization: Bearer <token>
 * - 响应拦截器：401 统一清 token 踢回登录页，其他错误统一弹提示
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  // 成功：直接把 response.data 交出去，调用方少写一层 .data
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    if (status === 401) {
      localStorage.removeItem('token')
      if (router.currentRoute.value.name !== 'login') {
        ElMessage.error('登录已过期，请重新登录')
        router.push({ name: 'login' })
      }
    } else {
      ElMessage.error(detail || '请求失败，请稍后再试')
    }
    return Promise.reject(error)
  },
)

export default request
