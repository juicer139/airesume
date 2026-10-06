/** 应用入口：按顺序装配 Pinia → Router → Element Plus */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia()) // 必须先于 router：路由守卫里会用到 store
app.use(router)
app.use(ElementPlus, { locale: zhCn }) // Element Plus 组件库 + 中文语言包

// 全局注册所有图标组件，模板里可以直接写 <UploadFilled /> 等
for (const [name, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(name, component)
}

app.mount('#app')
