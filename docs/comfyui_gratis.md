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

## 2. O workflow já vem pronto (mas nunca rodou numa GPU real)

`workflows/flux_depth.json` já está no repo, montado com base em workflows
públicos conhecidos de Flux + ControlNet Union depth — os ids dos nós já
batem com `core/engines/comfy_engine.py`, não precisa editar nada. **Mas eu
não tenho GPU para rodar de ponta a ponta antes de publicar**, então ele
pode falhar ao carregar ou ao executar.

### Valide sem gastar GPU primeiro

Depois que o servidor subir no Colab (célula nova, no próprio notebook):

```python
!cd /content/ark && python tools/comfy_check.py
```

(`/content/ark` é o clone do repo — se ainda não clonou dentro do Colab,
`!git clone https://github.com/ciceromayk/arkrender /content/ark` antes.)

Isso confere, contra o `/object_info` do próprio ComfyUI, se todo nó do
grafo existe (custom node instalado?) e se cada valor fixo (nome de
checkpoint/modelo) está nas opções válidas — sem carregar modelo nenhum,
em segundos. Se aparecer `[FALHA]`, a mensagem já diz o nó e o campo
exatos. Quando sair **"grafo OK"**, rode a etapa que gasta GPU de verdade:

```python
!cd /content/ark && python tools/comfy_check.py --render
```

Isso renderiza a fixture sintética de `bench/in/torre_hidden_line.png`
pelo `core.engines.comfy_engine.ComfyEngine` de verdade (a mesma classe
que o app e o `bench/run.py` usam) e imprime a aderência — primeira
execução carrega o modelo, conte alguns minutos. Se falhar, a mensagem
de erro agora vem com o nó que quebrou (ex.: `ComfyUI: nó 11
(DepthAnythingV2Preprocessor) falhou — ...`), não mais vazia.

Rode os dois **de dentro do Colab** — o egress de alguns ambientes de
execução (incluindo o desta sessão) bloqueia domínios como
`trycloudflare.com`, então bater na URL do túnel de fora tende a falhar
por rede, não por bug no workflow.

`comfy_check.py` também confere inputs **obrigatórios ausentes**, não só
valores inválidos — pega, por exemplo, o nó `ControlNetApplyAdvanced`
(id `12`) precisando de uma entrada extra `vae` em algumas versões do
ComfyUI, que o grafo do repo não fornece. Se aparecer `[FALHA] ... inputs
obrigatórios ausentes ['vae']`, a correção é manual:

1. Abra a URL do túnel no navegador (interface do ComfyUI).
2. **Workflow → Open** e selecione `workflows/flux_depth.json`.
3. No nó `ControlNetApplyAdvanced`, ligue a entrada `vae` à saída do
   `VAELoader` (nó `4`).
4. Exporte de novo em **Save (API Format)**, sobrescreva
   `workflows/flux_depth.json` e mande o arquivo pra mim (ou commite
   direto) — assim o próximo uso já sai certo.

Para qualquer outra coisa que o `comfy_check.py` não pegue (é uma
checagem estática — não substitui rodar de verdade), rode manualmente
pela interface do ComfyUI (botão de fila) e leia a mensagem de erro que
aparece embaixo à direita.

Se preferir montar do zero em vez de depurar o pronto, a tabela abaixo tem
a lista completa de nós e conexões.

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

## 3. Conectar ao ARKITEKT

1. Cole a URL do túnel:
   ```bash
   export ARKITEKT_COMFY_URL="https://xxxx.trycloudflare.com"
   ```
   (ou cole na barra lateral do app Streamlit, ou em
   `.streamlit/secrets.toml` como `ARKITEKT_COMFY_URL`)
2. Teste a conexão:
   ```bash
   python -c "from core.engines.comfy_engine import ComfyEngine as C; print(C().available())"
   ```
   `(True, '')` quer dizer que o ComfyUI está acessível e o
   `workflows/flux_depth.json` foi encontrado — não garante que a
   renderização em si vai funcionar, só que dá pra tentar.
3. Rode de verdade:
   ```bash
   python bench/run.py --in bench/in/sua_fachada.png --engines comfy --limit 1
   ```
   ou no app Streamlit: motor **ComfyUI (grátis, self-hosted)**. Se falhar
   na hora de renderizar (não na conexão), volte pra seção 2 — é sinal de
   que o workflow precisa do ajuste manual.

Se você montar o grafo do zero (ou editar o que já existe) e os ids dos
nós mudarem, ajuste `NODE` em `core/engines/comfy_engine.py` para apontar
para os novos ids — é a chave de nível superior de cada nó no JSON
exportado:
```python
NODE = {
    "positive": "6",      # id do CLIPTextEncode positivo
    "negative": "7",      # id do CLIPTextEncode negativo
    "load_image": "10",   # id do LoadImage
    "controlnet": "12",   # id do ControlNetApplyAdvanced
    "sampler": "3",       # id do KSampler
}
```

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
