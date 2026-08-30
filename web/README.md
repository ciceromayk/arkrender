# ARKITEKT — web

Frontend Vue 3 + Vite do SaaS multi-usuário (Fase B). CRUD de projetos e
histórico fala direto com o Supabase; só a renderização passa pela `api/`
(FastAPI), que é quem chama `core/pipeline.py`.

Setup completo: [`docs/fase_b_setup.md`](../docs/fase_b_setup.md).

```bash
npm install
cp .env.example .env   # preencha VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY
npm run dev
```
