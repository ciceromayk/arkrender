# Fase B, Fatia 1 — setup e teste

Multi-usuário real: login, projetos salvos, render via `api/` (FastAPI),
cota mensal por plano. Sem Stripe ainda (Fatia 2) — todo mundo entra no
plano `free` (5 gerações/mês, valor de teste).

`core/` não foi tocado. `app/streamlit_app.py` continua funcionando do
jeito que sempre funcionou — esta é uma stack nova, em paralelo, não uma
substituição ainda.

---

## 1. Supabase (você já tem conta)

1. No painel do seu projeto, abra **SQL Editor** → cole o conteúdo de
   [`supabase/migrations/0001_init.sql`](../supabase/migrations/0001_init.sql) → **Run**.
2. **Storage** → **New bucket** → nome exatamente `geracoes` → **Private**.
3. **Settings → API**, anote:
   - `Project URL` → vira `SUPABASE_URL` (api/) e `VITE_SUPABASE_URL` (web/)
   - `anon public` key → vira `VITE_SUPABASE_ANON_KEY` (só no web/)
   - `service_role` key → vira `SUPABASE_SERVICE_ROLE_KEY` (só no api/ —
     **nunca** cole essa no `web/.env`, ela ignora toda a segurança RLS)
   - **Settings → API → JWT Settings** → `JWT Secret` → vira `SUPABASE_JWT_SECRET` (api/)

## 2. `api/` (FastAPI)

**Rode tudo a partir da RAIZ do repo, não de dentro de `api/`** — os
imports internos (`from .config import ...`) são relativos ao pacote
`api`, então `uvicorn` precisa enxergar a raiz do repo no `sys.path`.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r api/requirements.txt
cp api/.env.example api/.env   # preencha SUPABASE_URL / SERVICE_ROLE_KEY / JWT_SECRET / FAL_KEY
uvicorn api.main:app --reload
```

`FAL_KEY` aqui é a chave **do operador** (você) — paga a geração de todos
os usuários. É a mudança de modelo em relação ao `app/streamlit_app.py`,
onde cada um colava a própria chave.

Confirme que subiu: `curl http://localhost:8000/health` → `{"status":"ok"}`.

## 3. `web/` (Vue 3)

```bash
cd web
npm install
cp .env.example .env         # preencha VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY
                              # VITE_API_BASE_URL já vem certo (http://localhost:8000)
npm run dev
```

Abra a URL que o Vite imprimir (geralmente `http://localhost:5173`).

## 4. Testar de ponta a ponta

1. **Cadastre-se** na tela de login (e-mail + senha). Se o Supabase pedir
   confirmação de e-mail (padrão em projeto novo), confirme antes de
   entrar — ou desligue essa exigência em **Authentication → Providers →
   Email → Confirm email** enquanto testa.
2. **Crie um projeto** (nome, seed, estilo, iluminação, câmera).
3. Abra o projeto, envie um screenshot (`bench/in/torre_hidden_line.png`
   do repo serve para teste) e clique **Renderizar**. Isso gasta um
   crédito de verdade na sua `FAL_KEY` (~US$0,05–0,10).
4. Confirme que apareceu em **Histórico**.
5. **Teste o bloqueio de cota:** renderize 5 vezes (o plano `free` da
   migration vem com cota=5) — na 6ª tentativa, a API deve devolver
   HTTP 402 e a tela deve mostrar o aviso de cota esgotada, com o botão
   desabilitado.
6. Pra liberar de novo sem esperar o mês virar, mude a cota temporariamente
   no Supabase Studio: `update planos set cota_geracoes_mes = 999 where id = 'free';`

## Erros comuns

- **401 em toda chamada à API**: `SUPABASE_JWT_SECRET` errado no `api/.env`
  (confira contra Settings → API → JWT Settings, não confunda com a
  `service_role` key).
- **RLS bloqueando um select que deveria funcionar**: confirme que rodou a
  migration inteira (as `create policy` do final são fáceis de esquecer
  se colar o SQL em pedaços).
- **Upload falha com 403/permission denied**: o bucket precisa se chamar
  exatamente `geracoes` (bate com `ARKITEKT_STORAGE_BUCKET` em
  `api/config.py`) e ser **privado** (as policies de Storage da migration
  assumem isso).
- **CORS bloqueando a chamada do Vue pra API**: confira `CORS_ORIGINS` no
  `api/.env` — precisa bater exatamente com a URL que o Vite está usando
  (porta incluída).
