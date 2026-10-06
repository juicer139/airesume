import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // @ 指向 src 目录，import 里写 @/api/user 这种路径
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // 开发代理：前端所有 /api 开头的请求转发给 FastAPI，
    // 同源环境下天然没有跨域问题（生产环境由 nginx 做同样的事）
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
