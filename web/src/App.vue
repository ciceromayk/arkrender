<script setup>
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div v-if="auth.carregando" class="carregando">Carregando…</div>
  <div v-else class="app">
    <header class="topo">
      <RouterLink to="/projetos" class="marca">🏗️ ARKITEKT</RouterLink>
      <nav v-if="auth.logado">
        <RouterLink to="/projetos">Projetos</RouterLink>
        <RouterLink to="/historico">Histórico</RouterLink>
        <span class="cota" :class="{ esgotada: auth.cotaEsgotada }">
          {{ auth.cotaUsada }}/{{ auth.cotaTotal }} gerações neste mês
        </span>
        <button class="sair" @click="auth.sair()">Sair</button>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.topo {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  border-bottom: 1px solid #ddd;
}
.marca {
  font-weight: 700;
  text-decoration: none;
  color: inherit;
}
nav {
  display: flex;
  align-items: center;
  gap: 16px;
}
nav a {
  color: inherit;
  text-decoration: none;
}
nav a.router-link-active {
  font-weight: 600;
}
.cota {
  font-size: 0.85rem;
  color: #666;
}
.cota.esgotada {
  color: #b00;
  font-weight: 600;
}
.sair {
  padding: 6px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
main {
  padding: 24px;
  max-width: 960px;
  margin: 0 auto;
}
.carregando {
  padding: 60px;
  text-align: center;
  color: #666;
}
</style>
