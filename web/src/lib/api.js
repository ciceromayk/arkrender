// Wrapper de fetch para a api/ (FastAPI) — só as chamadas caras (render)
// passam por aqui. CRUD de projetos/histórico fala direto com o Supabase
// (ver views/Projetos.vue e views/Historico.vue).
import { supabase } from './supabase'

const BASE_URL = import.meta.env.VITE_API_BASE_URL

class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function authHeader() {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new ApiError(401, 'sessão expirada — faça login de novo')
  return { Authorization: `Bearer ${token}` }
}

/**
 * Envia um screenshot + preset para POST /render.
 * @param {File} screenshotFile
 * @param {object} campos - nome, seed, estilo, iluminacao, camera,
 *   control_weight, strength, refino, refino_strength, prompt_extra, notas, projeto_id
 */
export async function renderizar(screenshotFile, campos) {
  const headers = await authHeader()
  const form = new FormData()
  form.append('screenshot', screenshotFile)
  for (const [chave, valor] of Object.entries(campos)) {
    if (valor !== null && valor !== undefined) form.append(chave, valor)
  }

  const res = await fetch(`${BASE_URL}/render`, { method: 'POST', headers, body: form })
  const corpo = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new ApiError(res.status, corpo.detail || `erro ${res.status} na API`)
  }
  return corpo
}

export { ApiError }
