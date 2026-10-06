<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// 进入首页时如果还没有用户信息，就调 /me 拉一次
// token 失效的话 axios 拦截器会自动清 token 并跳登录页
onMounted(async () => {
  if (auth.isLoggedIn && !auth.user) {
    await auth.fetchUser()
  }
})
</script>

<template>
  <el-card>
    <h2>欢迎，{{ auth.user?.username }}</h2>
    <el-alert
      type="info"
      :closable="false"
      title="简历上传与分析功能将在后续阶段接入"
      description="当前阶段已完成：注册、登录、JWT 认证、路由守卫、请求拦截器。"
    />
  </el-card>
</template>
