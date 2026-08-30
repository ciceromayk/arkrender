import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// resolve a sessão antes de montar, pra não piscar a tela de login com o
// usuário já logado (evita o beforeEach do router redirecionar errado)
const auth = useAuthStore()
auth.iniciar().then(() => app.mount('#app'))
