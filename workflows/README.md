# workflows

`flux_depth.json` é o grafo do ComfyUI em formato API, usado pelo motor
self-hosted grátis (`core/engines/comfy_engine.py`).

Passo a passo completo — quais nós montar, como conectá-los e como exportar
— está em [`docs/comfyui_gratis.md`](../docs/comfyui_gratis.md). Resumo:

1. Suba um servidor ComfyUI grátis com `colab/arkitekt_comfyui.ipynb`.
2. Monte o workflow uma vez na interface (lista de nós no guia acima).
3. **Settings → Enable Dev mode Options** → **Save (API Format)** → salve
   aqui como `flux_depth.json`.
4. Confira os ids dos nós em `core/engines/comfy_engine.py` (dict `NODE`)
   — eles mudam conforme o grafo que você montou.
