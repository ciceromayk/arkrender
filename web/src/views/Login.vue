<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const senha = ref('')
const modo = ref('login') // 'login' | 'cadastro'
const mensagem = ref('')
const erro = ref(false)
const carregando = ref(false)

async function enviar() {
  mensagem.value = ''
  erro.value = false
  carregando.value = true
  try {
    if (modo.value === 'login') {
      await auth.login(email.value, senha.value)
      router.push({ name: 'projetos' })
      return
    }
    await auth.cadastrar(email.value, senha.value)
    mensagem.value = 'Conta criada — confirme o e-mail (se exigido) e entre.'
    modo.value = 'login'
  } catch (e) {
    erro.value = true
    mensagem.value = e.message || 'Falhou.'
  } finally {
    carregando.value = false
  }
}
</script>

<template>
  <div class="login">
    <h1>🏗️ ARKITEKT</h1>
    <form @submit.prevent="enviar">
      <label>
        E-mail
        <input v-model="email" type="email" required autocomplete="email" />
      </label>
      <label>
        Senha
        <input v-model="senha" type="password" required minlength="6" autocomplete="current-password" />
      </label>
      <p v-if="mensagem" :class="erro ? 'erro' : 'aviso'">{{ mensagem }}</p>
      <button class="btn-primario" :disabled="carregando" type="submit">
        {{ modo === 'login' ? 'Entrar' : 'Criar conta' }}
      </button>
    </form>
    <button class="link" type="button" @click="modo = modo === 'login' ? 'cadastro' : 'login'">
      {{ modo === 'login' ? 'Não tem conta? Cadastre-se' : 'Já tem conta? Entrar' }}
    </button>
  </div>
</template>

<style scoped>
.login {
  max-width: 360px;
  margin: 80px auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.9rem;
}
input {
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}
.link {
  background: none;
  border: none;
  color: #555;
  text-decoration: underline;
  cursor: pointer;
  font-size: 0.85rem;
}
</style>
