# workflows

`flux_depth.json` é o grafo do ComfyUI em formato API, usado pelo motor
self-hosted grátis (`core/engines/comfy_engine.py`).

Já vem pronto no repo (montado a partir de workflows públicos conhecidos
de Flux + ControlNet Union depth), mas **nunca foi testado numa GPU real**
— não há uma disponível neste ambiente de desenvolvimento. Se ele falhar
ao carregar ou ao rodar no seu ComfyUI, o guia de depuração e a lista
completa de nós (caso prefira montar do zero) estão em
[`docs/comfyui_gratis.md`](../docs/comfyui_gratis.md).

Se você editar o grafo e os ids dos nós mudarem, ajuste `NODE` em
`core/engines/comfy_engine.py` para apontar para os novos ids.
