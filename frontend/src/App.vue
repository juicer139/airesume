<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function onLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="brand" @click="router.push('/')">AI 简历分析平台</div>
      <div class="user-area">
        <template v-if="auth.isLoggedIn">
          <span class="username">{{ auth.user?.username }}</span>
          <el-button link type="danger" @click="onLogout">退出登录</el-button>
        </template>
        <template v-else>
          <el-button link type="primary" @click="router.push('/login')">登录</el-button>
          <el-button link @click="router.push('/register')">注册</el-button>
        </template>
      </div>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--el-border-color-light);
}
.brand {
  font-weight: 600;
  font-size: 17px;
  cursor: pointer;
}
.user-area {
  display: flex;
  align-items: center;
  gap: 4px;
}
.username {
  margin-right: 8px;
  color: var(--el-text-color-secondary);
}
.main {
  width: 100%;
  max-width: 960px;
  margin: 0 auto;
}
</style>
