<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { supabase } from '../lib/supabase'
import { useAuthStore } from '../stores/auth'
import { CAMERAS, ESTILOS, ILUMINACOES } from '../lib/presets'

const auth = useAuthStore()
const router = useRouter()

const projetos = ref([])
const carregando = ref(true)
const erro = ref('')
const mostrarForm = ref(false)
const salvando = ref(false)

const novo = ref({
  nome: '',
  seed: 1974,
  estilo: ESTILOS[0],
  iluminacao: ILUMINACOES[0],
  camera: CAMERAS[0],
  control_weight: 0.9,
  strength: 0.75,
  refino: true,
  refino_strength: 0.25,
  prompt_extra: '',
  notas: '',
})

async function carregar() {
  carregando.value = true
  const { data, error: err } = await supabase
    .from('projetos')
    .select('*')
    .order('updated_at', { ascending: false })
  if (err) erro.value = err.message
  else projetos.value = data
  carregando.value = false
}

async function criar() {
  salvando.value = true
  erro.value = ''
  const { data, error: err } = await supabase
    .from('projetos')
    .insert({ ...novo.value, user_id: auth.session.user.id })
    .select()
    .single()
  salvando.value = false
  if (err) {
    erro.value = err.message
    return
  }
  mostrarForm.value = false
  router.push({ name: 'projeto-detail', params: { id: data.id } })
}

onMounted(carregar)
</script>

<template>
  <div>
    <div class="cabecalho">
      <h2>Projetos</h2>
      <button class="btn-primario" @click="mostrarForm = !mostrarForm">
        {{ mostrarForm ? 'Cancelar' : '+ Novo projeto' }}
      </button>
    </div>

    <form v-if="mostrarForm" class="card form-novo" @submit.prevent="criar">
      <label>Nome do projeto <input v-model="novo.nome" required /></label>
      <label>Seed <input v-model.number="novo.seed" type="number" required /></label>
      <label>
        Estilo
        <select v-model="novo.estilo">
          <option v-for="e in ESTILOS" :key="e" :value="e">{{ e }}</option>
        </select>
      </label>
      <label>
        Iluminação
        <select v-model="novo.iluminacao">
          <option v-for="i in ILUMINACOES" :key="i" :value="i">{{ i }}</option>
        </select>
      </label>
      <label>
        Câmera / atmosfera
        <select v-model="novo.camera">
          <option v-for="c in CAMERAS" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
      <label>
        control_weight ({{ novo.control_weight }})
        <input v-model.number="novo.control_weight" type="range" min="0" max="1" step="0.05" />
      </label>
      <label>
        strength ({{ novo.strength }})
        <input v-model.number="novo.strength" type="range" min="0" max="1" step="0.05" />
      </label>
      <label class="checkbox">
        <input v-model="novo.refino" type="checkbox" /> Refino (estágio 2 — acabamento)
      </label>
      <label v-if="novo.refino">
        refino_strength ({{ novo.refino_strength }})
        <input v-model.number="novo.refino_strength" type="range" min="0" max="0.6" step="0.05" />
      </label>
      <label>Prompt extra (opcional) <input v-model="novo.prompt_extra" /></label>
      <p v-if="erro" class="erro">{{ erro }}</p>
      <button class="btn-primario" :disabled="salvando" type="submit">Criar</button>
    </form>

    <p v-if="carregando">Carregando…</p>
    <p v-else-if="!projetos.length">Nenhum projeto ainda — crie o primeiro acima.</p>
    <ul v-else class="lista">
      <li v-for="p in projetos" :key="p.id" class="card item">
        <RouterLink :to="{ name: 'projeto-detail', params: { id: p.id } }">
          <strong>{{ p.nome }}</strong>
          <span class="detalhe">{{ p.estilo }} · {{ p.iluminacao }} · seed {{ p.seed }}</span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.cabecalho {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.form-novo {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}
.form-novo label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.9rem;
}
.form-novo label.checkbox {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}
.form-novo input,
.form-novo select {
  padding: 6px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.lista {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.item a {
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.detalhe {
  font-size: 0.85rem;
  color: #666;
}
</style>
