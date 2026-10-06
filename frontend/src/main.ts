/** 应用入口：按顺序装配 Pinia → Router → Element Plus */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia()) // 必须先于 router：路由守卫里会用到 store
app.use(router)
app.use(ElementPlus, { locale: zhCn }) // Element Plus 组件库 + 中文语言包

app.mount('#app')
