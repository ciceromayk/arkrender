# ARKITEKT

Ferramenta interna de renderização arquitetônica com IA — IDIBRA / Arkitekt.

**Screenshot de modelo 3D → render fotorrealista → vídeo**, com fidelidade
geométrica medida, não presumida.

---

## Por que não usar Redraw / RenderLAB e pronto

As ferramentas de prateleira são editores multimodais: recebem o screenshot e
**redesenham** a cena. Ficam bonitas e acrescentam um pavimento, mudam o ritmo
da esquadria, "melhoram" o projeto por conta própria. Para peça de marketing
genérica, tudo bem. Para imagem que vai a material de venda, aprovação ou
prestação de contas de incorporadora, não serve.

O ARKITEKT trava a geometria com ControlNet depth antes de deixar qualquer
modelo pintar, e **mede** quanto do projeto sobreviveu.

Existe também um **modo estudo/moodboard** (Gemini, GPT Image, Grok) para
quando você quer variedade e atmosfera, não fidelidade — deliberadamente
separado do render aprovado, sem métrica de aderência nenhuma, pra nunca
fingir uma garantia que esses motores não dão. Ver
[`docs/modo_estudo.md`](docs/modo_estudo.md).

Leia [`docs/arquitetura.md`](docs/arquitetura.md) antes de mexer no pipeline.

---

## Estrutura

```
arkitekt/
├── core/                        módulo reutilizável — o ativo do repo
│   ├── presets.py               estilo × iluminação × câmera (dados, não prompt solto)
│   ├── fidelity.py              métrica objetiva de aderência geométrica
│   ├── pipeline.py              pipeline híbrido de 2 estágios + identidade de projeto
│   ├── estudo.py                modo estudo/moodboard — SEM aderência, de propósito
│   └── engines/
│       ├── fal_engine.py        rota principal (ControlNet) — render aprovado
│       ├── replicate_engine.py  alternativa (ControlNet) — render aprovado
│       ├── comfy_engine.py      self-hosted grátis (ControlNet) — render aprovado
│       └── estudo/              Gemini, GPT Image, Grok — SEM ControlNet, só estudo
├── bench/                       comparação de motores de render aprovado
│   ├── run.py                   runner
│   ├── report.py                grade comparativa HTML
│   └── demo_fixture.py          valida a métrica sem gastar crédito
├── docs/arquitetura.md          decisões, pipeline, custos, como exportar do Revit/SketchUp
├── docs/modo_estudo.md          por que o modo estudo é separado, e como usar
└── app/                         interface Streamlit — casca fina sobre core/
```

## Instalar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # e preencha as chaves
```

## Validar sem gastar nada

```bash
python bench/demo_fixture.py
```

Gera uma torre sintética e dois "renders" — um fiel, um com o volume deslocado
e 4 pavimentos a mais. A métrica devolve **1.00** e **0.57**. Se esses números
mudarem, alguém quebrou `core/fidelity.py`.

## Rodar o benchmark

```bash
export FAL_KEY="..."                  # rota principal
python bench/run.py --in bench/in --out bench/out

# teste barato primeiro
python bench/run.py --in bench/in/fachada.png --engines fal --limit 3
```

Saída: `bench/out/comparativo.html` (grade lado a lado + ranking + custo real) e
`resultados.json` com todos os parâmetros.

## Produzir um render de projeto

```python
from core.pipeline import Projeto, render

p = Projeto(nome="garden-praia-torre-a", seed=1974,
            estilo="alto_padrao_litoraneo", iluminacao="golden_hour",
            camera="veg_entrega", control_weight=0.90, strength=0.75)

log = render(p, "fachada_leste.png", out_dir="renders")
print(log["aderencia"], log["veredito"])
p.salvar("projetos/garden-praia-torre-a.json")
```

O JSON do projeto é a **identidade visual do empreendimento**: mesma seed,
mesmos presets, mesmos pesos. Qualquer ângulo novo, meses depois, sai coerente
com os anteriores. É isso que vira book de projeto em vez de imagens soltas.

---

## As duas métricas

| | O que é | Como usar |
|---|---|---|
| **Aderência** | % das arestas do projeto original preservadas no render | **É o número que decide.** ≥0,80 travado · ≥0,65 fiel · ≥0,45 livre · abaixo, descolado |
| **Invenção** | % das arestas do render que não existem na origem | Sempre alta, e isso é normal (vegetação, pessoas, céu, reflexo). Só compara configurações entre si |

## Regra de ouro do repo

Nenhuma imagem vai para material de venda com aderência abaixo de **0,80** sem
conferência manual de número de pavimentos e ritmo de esquadria contra o projeto.
