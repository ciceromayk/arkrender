# app — interface Streamlit

Casca fina sobre `core/pipeline.py`: upload de screenshot, escolha de preset,
roda o pipeline híbrido de 2 estágios e mostra o resultado + aderência.
Nenhuma lógica de render mora aqui.

## Rodar local

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # e preencha FAL_KEY
streamlit run app/streamlit_app.py
```

Sem `secrets.toml`, o app pede a chave na hora, na barra lateral (vale só
para a sessão do navegador, não é salva em disco).

## Deploy grátis — Streamlit Community Cloud

1. Suba este repositório para o GitHub (branch atual já serve).
2. Entre em [share.streamlit.io](https://share.streamlit.io) com a conta do GitHub.
3. **New app** → escolha o repo e a branch → **Main file path**: `app/streamlit_app.py`.
4. Em **Advanced settings → Secrets**, cole:
   ```toml
   FAL_KEY = "sua-chave-aqui"
   ```
5. Deploy. A URL fica pública por padrão — em **Settings → Sharing** dá para
   restringir a e-mails específicos (grátis, mas exige que quem acessa tenha
   conta Streamlit/Google).

Limites do plano grátis: 1 app privado ativo (mais apps ficam públicos),
~1 GB de RAM, e o app "dorme" depois de um tempo sem uso — a primeira
requisição depois disso demora alguns segundos para acordar. Suficiente para
uso interno esporádico; o custo real é sempre o da API do fal.ai, não o
hosting.

## Etapa 3 (se crescer)

Se o uso virar diário/multiusuário e precisar de histórico, auth por
usuário e storage de renders, migrar para Vue 3 + Supabase (padrão já usado
no MSM Gestão) — mesmo `core/` por baixo, só troca a casca.
