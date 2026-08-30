<script setup>
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { supabase } from '../lib/supabase'
import { renderizar, ApiError } from '../lib/api'
import { useAuthStore } from '../stores/auth'

const props = defineProps({ id: String })
const auth = useAuthStore()

const projeto = ref(null)
const carregandoProjeto = ref(true)
const arquivo = ref(null)
const previewUrl = ref('')
const renderizando = ref(false)
const erro = ref('')
const resultado = ref(null) // { aderencia, veredito, aprovado_para_venda, imagem_final_path, custo_usd, segundos }
const imagemResultadoUrl = ref('')

async function carregarProjeto() {
  carregandoProjeto.value = true
  const { data, error: err } = await supabase.from('projetos').select('*').eq('id', props.id).single()
  if (err) erro.value = err.message
  else projeto.value = data
  carregandoProjeto.value = false
}

function aoEscolherArquivo(evento) {
  const f = evento.target.files[0]
  arquivo.value = f
  previewUrl.value = f ? URL.createObjectURL(f) : ''
}

async function renderizarAgora() {
  if (!arquivo.value || !projeto.value) return
  renderizando.value = true
  erro.value = ''
  resultado.value = null
  imagemResultadoUrl.value = ''

  try {
    const p = projeto.value
    const log = await renderizar(arquivo.value, {
      nome: p.nome,
      seed: p.seed,
      estilo: p.estilo,
      iluminacao: p.iluminacao,
      camera: p.camera,
      control_weight: p.control_weight,
      strength: p.strength,
      refino: p.refino,
      refino_strength: p.refino_strength,
      prompt_extra: p.prompt_extra,
      notas: p.notas,
      projeto_id: p.id,
    })
    resultado.value = log

    const { data: assinada } = await supabase.storage
      .from('geracoes')
      .createSignedUrl(log.imagem_final_path, 3600)
    imagemResultadoUrl.value = assinada?.signedUrl || ''

    await auth.atualizarCota()
  } catch (e) {
    erro.value = e instanceof ApiError ? e.message : e.message || 'Falhou.'
  } finally {
    renderizando.value = false
  }
}

onMounted(carregarProjeto)
</script>

<template>
  <div>
    <RouterLink to="/projetos">← Projetos</RouterLink>

    <p v-if="carregandoProjeto">Carregando…</p>
    <template v-else-if="projeto">
      <h2>{{ projeto.nome }}</h2>
      <p class="detalhe">
        {{ projeto.estilo }} · {{ projeto.iluminacao }} · {{ projeto.camera }} · seed {{ projeto.seed }}
      </p>

      <div class="card">
        <h3>1. Screenshot de origem</h3>
        <input type="file" accept="image/png,image/jpeg,image/webp" @change="aoEscolherArquivo" />
        <img v-if="previewUrl" :src="previewUrl" alt="origem" class="preview" />

        <p v-if="auth.cotaEsgotada" class="aviso erro">
          Cota do plano esgotada ({{ auth.cotaUsada }}/{{ auth.cotaTotal }} este mês).
        </p>

        <button
          class="btn-primario"
          :disabled="!arquivo || renderizando || auth.cotaEsgotada"
          @click="renderizarAgora"
        >
          {{ renderizando ? 'Renderizando…' : 'Renderizar' }}
        </button>
        <p v-if="erro" class="erro">{{ erro }}</p>
      </div>

      <div v-if="resultado" class="card resultado">
        <h3>2. Resultado</h3>
        <img v-if="imagemResultadoUrl" :src="imagemResultadoUrl" alt="resultado" class="preview" />

        <div class="metricas">
          <span :class="['aderencia', resultado.aprovado_para_venda ? 'ok' : 'alerta']">
            Aderência {{ resultado.aderencia.toFixed(2) }} — {{ resultado.veredito }}
          </span>
          <span>{{ resultado.segundos }}s</span>
          <span>US$ {{ resultado.custo_usd.toFixed(3) }}</span>
        </div>
        <p class="detalhe">
          {{ resultado.cota_usada }}/{{ resultado.cota_total }} gerações usadas neste ciclo.
        </p>
      </div>
    </template>
    <p v-else class="erro">Projeto não encontrado.</p>
  </div>
</template>

<style scoped>
.detalhe {
  font-size: 0.85rem;
  color: #666;
}
.card {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.preview {
  max-width: 100%;
  max-height: 420px;
  border-radius: 6px;
  border: 1px solid #eee;
}
.metricas {
  display: flex;
  gap: 16px;
  font-size: 0.9rem;
  flex-wrap: wrap;
}
.aderencia.ok {
  color: #1a7f37;
  font-weight: 600;
}
.aderencia.alerta {
  color: #b08500;
  font-weight: 600;
}
</style>
