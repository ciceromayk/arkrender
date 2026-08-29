# Modo estudo/moodboard — Gemini, GPT Image, Grok

Segunda família de motores do ARKITEKT, deliberadamente separada do render
aprovado. Existe pra atender casos onde o que importa é variedade e
atmosfera rápida — não fidelidade ao projeto.

## Por que é um módulo separado, não "mais um motor" no seletor

`core/pipeline.py` (render aprovado) e `core/estudo.py` (este módulo) têm
a mesma forma superficial — screenshot entra, imagem sai — mas resolvem
problemas opostos:

| | Render aprovado (`core/pipeline.py`) | Estudo (`core/estudo.py`) |
|---|---|---|
| Motores | fal.ai, Replicate, ComfyUI — todos ControlNet depth | Gemini, GPT Image, Grok — editores multimodais |
| Trava geometria? | Sim — `control_weight` é o botão disso | Não — não existe esse botão nessa família |
| Métrica de aderência | Sempre calculada | **Nunca calculada** — não faria sentido |
| Pode virar material de venda? | Sim, se aderência ≥ 0,80 (golden rule do README) | **Nunca** |

Gemini, GPT Image e Grok são exatamente a família "redraw" que o
`docs/arquitetura.md` já descreve na seção 2 como o que as ferramentas de
prateleira (Redraw, RenderLAB, mnml, Archsynth) fazem — e a razão de
existir do ARKITEKT é justamente não fazer isso quando a imagem precisa
corresponder ao projeto aprovado.

Misturar os dois no mesmo seletor de motor tornaria a golden rule
inaplicável: você não consegue avisar "não aprove essa imagem" se ela sai
do mesmo fluxo, com a mesma cara, do render que É aprovável. Por isso
`core/estudo.py` marca **todo** log de saída com
`"aprovado_para_venda": False`, sempre, sem exceção — e nenhuma função do
módulo calcula `fidelity.score()`.

## Motores disponíveis

| Motor | Arquivo | Chave | Observação |
|---|---|---|---|
| Gemini (Nano Banana) | `core/engines/estudo/gemini_engine.py` | `GEMINI_API_KEY` | Recebe o screenshot como referência de verdade |
| GPT Image (OpenAI) | `core/engines/estudo/gptimage_engine.py` | `OPENAI_API_KEY` | Idem — usa `images.edit` |
| Grok Imagine (xAI) | `core/engines/estudo/grok_engine.py` | `XAI_API_KEY` | Recebe o screenshot como referência via `POST /v1/images/edits` (HTTP cru, sem SDK) |

**Nenhum dos três foi testado contra a API real nesta sessão** — sem
chaves disponíveis no ambiente de desenvolvimento. Gemini e GPT Image
seguem a documentação pública de cada SDK (`google-genai` e `openai`).
**Grok é o de maior risco**: `docs.x.ai` está bloqueado pelo proxy de
egress deste ambiente, então o formato exato do corpo da requisição em
`grok_engine.py` é uma tentativa fundamentada (confirmei via busca na web
que o endpoint de edição existe, não consegui ler a documentação oficial
pra confirmar o formato do payload) — confira contra
https://docs.x.ai/developers/model-capabilities/images/editing na
primeira tentativa real. Em qualquer um dos três, se algo mudou desde
então, o erro aparece em `available()` (pacote/chave ausente) ou na
exceção capturada por `StudyResult.error` — nunca falha muda.

## Uso

```python
from core.estudo import gerar_estudo
from core.engines.estudo.gemini_engine import GeminiEngine

log = gerar_estudo(GeminiEngine(), "fachada_leste.png",
                    "torre litorânea ao entardecer, luz dourada, poucas nuvens")
print(log["aprovado_para_venda"])  # sempre False
```

Ou pela aba **Estudo / moodboard** do app Streamlit.

## Custo

Ordem de grandeza por imagem (confira no painel de cada provedor — muda
com resolução/qualidade):

| Motor | Custo aproximado |
|---|---|
| Gemini (Nano Banana) | ~US$ 0,04 |
| GPT Image | ~US$ 0,07 |
| Grok Imagine | ~US$ 0,07 |

Nenhum dos três tem rota gratuita hoje no repo — diferente do render
aprovado, que tem o ComfyUI self-hosted (`docs/comfyui_gratis.md`).
