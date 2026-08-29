# ComfyUI grátis — motor self-hosted sem custo por imagem

Alternativa ao fal.ai para o **estágio 1 (estrutura)** do pipeline: mesma
rota ControlNet depth, rodando numa GPU gratuita (Colab/Kaggle) em vez de
uma API paga. `core/engines/comfy_engine.py` já implementa o adaptador —
falta só um servidor ComfyUI rodando e o workflow montado uma vez.

**Importante:** o **estágio 2 (refino)** sempre roda no fal.ai, mesmo com
esse motor (é a única rota do repo com o editor multimodal img2img fraco
que o acabamento usa — ver `core/pipeline.py`). Pra ficar 100% grátis,
desligue o refino (`refino=False` / checkbox "Refino" desmarcado no app).
Estágio 1 sozinho já dá a estrutura travada com a métrica de aderência —
só fica sem o polimento de material/vegetação do estágio 2.

---

## 1. Subir o servidor

Abra `colab/arkitekt_comfyui.ipynb` no [Google Colab](https://colab.research.google.com)
(upload do arquivo, ou Kaggle Notebooks como alternativa — mesma lógica,
ajustando os comandos de GPU) e rode as células em ordem. Ela:

1. Ativa GPU T4 grátis
2. Instala ComfyUI + `comfyui_controlnet_aux` (nó de depth)
3. Monta seu **Google Drive** e faz `models/` apontar pra lá — os ~25 GB de
   Flux.1-dev (fp8) + ControlNet Union + text encoders ficam salvos
   permanentemente numa pasta `arkitekt_comfy_models/` no seu Drive
4. Confere o que já está no Drive: **na primeira vez** baixa tudo (pede
   login/token Hugging Face, porque o Flux.1-dev é *gated*); **da segunda
   vez em diante**, detecta que já está tudo lá e pula download e login
5. Sobe o servidor e expõe uma URL pública temporária via `cloudflared`

No fim você tem uma URL tipo `https://xxxx.trycloudflare.com`. Ela muda
toda vez que você reinicia o notebook — não é uma URL fixa de produção —
mas os modelos no Drive não somem: reabrir o notebook depois vira só
"rodar as células, esperar o servidor subir", sem rebaixar nada.

---

## 2. Montar o workflow (uma vez só)

Abra a URL do túnel no navegador — é a interface do ComfyUI rodando no
Colab. Monte o grafo abaixo (arraste os nós, plugue as saídas nas
entradas correspondentes):

| Nó | O que faz | Observação |
|---|---|---|
| `UNETLoader` | carrega `flux1-dev-fp8.safetensors` | weight_dtype: `fp8_e4m3fn` |
| `DualCLIPLoader` | carrega `t5xxl_fp8_e4m3fn.safetensors` + `clip_l.safetensors` | type: `flux` |
| `VAELoader` | carrega `ae.safetensors` | |
| `LoadImage` | o screenshot de entrada | **este é o nó `load_image`** |
| `DepthAnythingV2Preprocessor` | gera o mapa de profundidade a partir do `LoadImage` | do pacote `comfyui_controlnet_aux` |
| `ControlNetLoader` | carrega `flux-controlnet-union.safetensors` | |
| `SetUnionControlNetType` | seleciona modo `depth` no ControlNet Union | plugue a saída do `ControlNetLoader` |
| `CLIPTextEncode` (positivo) | texto do prompt | **este é o nó `positive`** |
| `CLIPTextEncode` (negativo) | texto negativo | **este é o nó `negative`** — Flux dev é guidance-distilled e ignora CFG negativo de verdade; mantenha o nó só por completude do grafo |
| `FluxGuidance` | guidance embutido (valor ~3.5) | plugue depois do `CLIPTextEncode` positivo |
| `ControlNetApplyAdvanced` | aplica o depth map às condicionantes | entradas: positive, negative, control_net (do `SetUnionControlNetType`), image (do preprocessor), `strength` — **este é o nó `controlnet`**, é nele que o runner sobrescreve o `control_weight` |
| `VAEEncode` | codifica o screenshot em latent (para img2img) | usa o mesmo `LoadImage` + `VAELoader` |
| `KSampler` | amostragem | `seed` e `denoise` (=`strength` do projeto) são sobrescritos pelo runner — **este é o nó `sampler`** |
| `VAEDecode` | decodifica o latent final em imagem | |
| `SaveImage` | salva o resultado | |

Ligação geral: `LoadImage → DepthAnythingV2Preprocessor → SetUnionControlNetType
(via ControlNetLoader) → ControlNetApplyAdvanced (junto com CLIPTextEncode
positivo/negativo) → KSampler (latent vindo do VAEEncode do próprio
LoadImage) → VAEDecode → SaveImage`.

## 3. Exportar e conectar ao ARKITEKT

1. No ComfyUI, ative o modo desenvolvedor (**Settings → Enable Dev mode
   Options**) e use **Save (API Format)** — isso baixa um `.json`.
2. Salve como `workflows/flux_depth.json` no repo (substitui o arquivo
   vazio hoje ausente — `workflows/README.md` já documentava esse passo).
3. Abra o JSON exportado, ache o id numérico de cada nó da tabela acima
   (é a chave de nível superior no JSON) e ajuste `NODE` em
   `core/engines/comfy_engine.py`:
   ```python
   NODE = {
       "positive": "6",      # id do CLIPTextEncode positivo
       "negative": "7",      # id do CLIPTextEncode negativo
       "load_image": "10",   # id do LoadImage
       "controlnet": "12",   # id do ControlNetApplyAdvanced
       "sampler": "3",       # id do KSampler
   }
   ```
4. Exporte a URL do túnel:
   ```bash
   export ARKITEKT_COMFY_URL="https://xxxx.trycloudflare.com"
   ```
   (ou cole na barra lateral do app Streamlit, ou em
   `.streamlit/secrets.toml` como `ARKITEKT_COMFY_URL`)
5. Teste a conexão:
   ```bash
   python -c "from core.engines.comfy_engine import ComfyEngine as C; print(C().available())"
   ```
6. Rode de verdade:
   ```bash
   python bench/run.py --in bench/in/sua_fachada.png --engines comfy --limit 1
   ```
   ou no app Streamlit: motor **ComfyUI (grátis, self-hosted)**.

---

## Limitações a aceitar

- **Sessão não é permanente.** Colab grátis cai por ociosidade ou depois
  de ~12h; a URL muda a cada reinício do notebook — reabra e cole a nova
  URL onde for usar.
- **Fila única.** Uma GPU T4 grátis não paraleliza — rodar a matriz
  inteira do benchmark (8 configs) é sequencial e mais lento que a fal.ai.
- **Sem CFG negativo de verdade.** Flux.1-dev é guidance-distilled; o
  prompt negativo no grafo local não tem o mesmo efeito que na rota fal
  (que usa um pipeline com CFG completo). Geometria e composição continuam
  travadas pelo ControlNet — a diferença é mais em quanto o negativo evita
  artefatos de textura/estilo.
- **Refino ainda custa.** Ver aviso no topo — estágio 2 é fal.ai sempre.
