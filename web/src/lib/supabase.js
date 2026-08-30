// Client Supabase do navegador — usa a chave "anon public", que respeita
// RLS. Nunca importe a service_role key aqui (essa fica só na api/).
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!url || !anonKey) {
  console.error(
    'VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY ausentes — copie web/.env.example para web/.env e preencha.'
  )
}

export const supabase = createClient(url, anonKey)
