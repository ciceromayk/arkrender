<script setup>
import { onMounted, ref } from 'vue'
import { supabase } from '../lib/supabase'

const geracoes = ref([])
const carregando = ref(true)
const erro = ref('')
const urls = ref({}) // geracao_id -> signed url (thumbnail)

async function carregar() {
  carregando.value = true
  const { data, error: err } = await supabase
    .from('geracoes')
    .select('id, modo, engine, aderencia, veredito, aprovado_para_venda, imagem_final_path, custo_usd, created_at')
    .order('created_at', { ascending: false })
    .limit(50)

  if (err) {
    erro.value = err.message
    carregando.value = false
    return
  }
  geracoes.value = data

  for (const g of data) {
    if (!g.imagem_final_path) continue
    const { data: assinada } = await supabase.storage
      .from('geracoes')
      .createSignedUrl(g.imagem_final_path, 3600)
    if (assinada?.signedUrl) urls.value[g.id] = assinada.signedUrl
  }
  carregando.value = false
}

onMounted(carregar)
</script>

<template>
  <div>
    <h2>Histórico</h2>
    <p v-if="erro" class="erro">{{ erro }}</p>
    <p v-if="carregando">Carregando…</p>
    <p v-else-if="!geracoes.length">Nenhuma geração ainda.</p>
    <ul v-else class="grade">
      <li v-for="g in geracoes" :key="g.id" class="card item">
        <img v-if="urls[g.id]" :src="urls[g.id]" alt="" class="thumb" />
        <div class="info">
          <span :class="['aderencia', g.aprovado_para_venda ? 'ok' : 'alerta']">
            {{ g.modo === 'render' ? `Aderência ${g.aderencia?.toFixed(2)}` : 'Estudo' }}
          </span>
          <span class="detalhe">{{ g.engine }} · {{ new Date(g.created_at).toLocaleString('pt-BR') }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.grade {
  list-style: none;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
}
.thumb {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  border-radius: 4px;
  background: #eee;
}
.info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 0.85rem;
}
.detalhe {
  color: #666;
  font-size: 0.75rem;
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
