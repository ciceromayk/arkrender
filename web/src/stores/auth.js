// Sessão, perfil (plano) e cota do usuário logado.
//
// A cota exibida aqui é lida direto do Supabase (contagem de `geracoes`
// desde o início do mês calendário) — mesma lógica de api/quota.py para
// a Fatia 1 (sem assinatura Stripe, sempre mês calendário). Quem decide
// de verdade se a cota estourou é a API no POST /render (RLS + o próprio
// endpoint) — isto aqui é só para mostrar "quanto falta" na tela, não é
// a fonte de verdade de controle de acesso.
import { defineStore } from 'pinia'
import { supabase } from '../lib/supabase'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    session: null,
    profile: null, // { plano_id, planos: { nome, cota_geracoes_mes } }
    cotaUsada: 0,
    carregando: true,
  }),

  getters: {
    logado: (state) => !!state.session,
    cotaTotal: (state) => state.profile?.planos?.cota_geracoes_mes ?? 0,
    cotaEsgotada: (state) => state.cotaUsada >= (state.profile?.planos?.cota_geracoes_mes ?? 0),
  },

  actions: {
    async iniciar() {
      const { data } = await supabase.auth.getSession()
      this.session = data.session
      if (this.session) await this.carregarPerfil()
      this.carregando = false

      supabase.auth.onAuthStateChange(async (_evento, session) => {
        this.session = session
        if (session) {
          await this.carregarPerfil()
        } else {
          this.profile = null
          this.cotaUsada = 0
        }
      })
    },

    async carregarPerfil() {
      const uid = this.session.user.id
      const { data, error } = await supabase
        .from('profiles')
        .select('plano_id, planos(nome, cota_geracoes_mes)')
        .eq('id', uid)
        .single()
      if (!error) this.profile = data
      await this.atualizarCota()
    },

    async atualizarCota() {
      if (!this.session) return
      const uid = this.session.user.id
      const inicioMes = new Date()
      inicioMes.setDate(1)
      inicioMes.setHours(0, 0, 0, 0)

      const { count } = await supabase
        .from('geracoes')
        .select('id', { count: 'exact', head: true })
        .eq('user_id', uid)
        .gte('created_at', inicioMes.toISOString())

      this.cotaUsada = count ?? 0
    },

    async login(email, senha) {
      const { error } = await supabase.auth.signInWithPassword({ email, password: senha })
      if (error) throw error
    },

    async cadastrar(email, senha) {
      const { error } = await supabase.auth.signUp({ email, password: senha })
      if (error) throw error
    },

    async sair() {
      await supabase.auth.signOut()
    },
  },
})
