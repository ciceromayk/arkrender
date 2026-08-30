import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/', redirect: '/projetos' },
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  {
    path: '/projetos',
    name: 'projetos',
    component: () => import('../views/Projetos.vue'),
    meta: { requerLogin: true },
  },
  {
    path: '/projetos/:id',
    name: 'projeto-detail',
    component: () => import('../views/ProjetoDetail.vue'),
    meta: { requerLogin: true },
    props: true,
  },
  {
    path: '/historico',
    name: 'historico',
    component: () => import('../views/Historico.vue'),
    meta: { requerLogin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requerLogin && !auth.logado) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.logado) {
    return { name: 'projetos' }
  }
})

export default router
