# ARKITEKT — Arquitetura da ferramenta de renderização

Ferramenta interna (IDIBRA / Arkitekt). Escopo do MVP: **screenshot 3D → render fotorrealista** e **render → vídeo**.

---

## 1. O problema central: fidelidade geométrica

Todo produto do mercado (Redraw, RenderLAB/Montani, mnml, Archsynth) resolve a mesma equação:

```
realismo  ×  fidelidade ao projeto  ×  velocidade
```

Ferramenta de marketing pode sacrificar fidelidade — "ficou lindo" basta. **Ferramenta interna de incorporadora não pode.** A imagem que vai para o cliente, para o material de venda ou para a aprovação precisa corresponder ao projeto aprovado: mesmo número de pavimentos, mesmo ritmo de esquadria, mesmo recuo, mesma volumetria.

Isso define a arquitetura inteira. Não é "gerar imagem bonita a partir de um prompt" — é **repintar uma geometria existente sem deixar o modelo inventar**.

---

## 2. Duas famílias de motor (e por que a escolha importa)

### A) Editor multimodal ("redraw")
Nano Banana 2/Pro, GPT Image 2, Seedream. Recebem o screenshot como referência e **redesenham** a cena.

- ✅ Materiais, vegetação, céu e pessoas excelentes; zero setup; prompt em linguagem natural
- ❌ **Deriva geométrica**: acrescenta/remove pavimentos, muda proporção de esquadria, "melhora" o projeto por conta própria
- Uso correto: estudo preliminar, moodboard, teste de atmosfera, imagem de concurso

### B) Difusão com controle estrutural ("ControlNet")
Flux/SDXL + ControlNet depth/canny/lineart. Extrai um **mapa de controle** do screenshot e prende a geração a ele.

- ✅ Geometria travada; `control_weight` e `strength` são botões reais de "quanto pode inventar"
- ✅ Seed fixa → reprodutibilidade → múltiplos ângulos coerentes entre si
- ❌ Prompt engineering mais técnico; qualidade de material inferior ao (A) sem LoRA de arquitetura

### Conclusão de arquitetura
**Pipeline híbrido em dois estágios.** É o que nenhuma das ferramentas de prateleira entrega, e é exatamente a vantagem de construir a sua:

```
Estágio 1 — ESTRUTURA   Flux + ControlNet depth (peso alto)  → geometria correta, material mediano
Estágio 2 — ACABAMENTO  Editor multimodal em img2img fraco   → material/vegetação/céu de alto nível
                        (strength baixo: refina, não redesenha)
```

O estágio 2 só pode "pintar" — a estrutura já está fixada pelo estágio 1.

---

## 3. Pipeline ARKITEKT

```
  ENTRADA                PRÉ                  RENDER                 PÓS               SAÍDA
┌──────────┐      ┌───────────────┐     ┌──────────────┐     ┌────────────┐     ┌──────────┐
│ Screenshot│ ──▶ │ depth-anything│ ──▶ │ Flux + CN    │ ──▶ │ refino     │ ──▶ │ 4K PNG   │
│ SketchUp/ │     │ v2  (depth)   │     │ depth        │     │ multimodal │     │          │
│ Revit     │     │ lineart       │     │ + preset     │     │ (str 0.25) │     └────┬─────┘
└──────────┘     │ (opcional)    │     │ + seed       │     └────────────┘          │
      │           └───────────────┘     └──────────────┘                             │
      │                                        ▲                                     ▼
      │                                        │                            ┌─────────────────┐
      └──── máscara (céu / entorno) ───────────┘                            │ img2video       │
                                                                            │ órbita / dolly  │
                                                                            │ 5s → concat     │
                                                                            └─────────────────┘
```

**Seed + preset + control map = a "identidade visual do projeto".** Guardados juntos, qualquer ângulo novo do mesmo empreendimento sai coerente com os anteriores. Isso é o que transforma imagens soltas em um **book de projeto**.

---

## 4. Entrada: como exportar do modelo

A qualidade do render é decidida **antes** da IA. Regras para quem exporta:

| Origem | Exportar | Por quê |
|---|---|---|
| SketchUp | Estilo *Hidden Line* ou *Shaded sem textura* (clay), sombras ligadas | Sombra dá volume ao depth map; textura do SketchUp atrapalha |
| Revit | Vista 3D, estilo *Sombreado* ou *Linha oculta*, câmera com altura de olho (1,60 m) | Perspectiva de 1 ponto ou 2 pontos; evitar axonometria |
| Ambos | 2048 px no lado maior, 16:9 ou 3:2 | Abaixo de 1024 o ControlNet perde detalhe de esquadria |
| Ambos | Câmera com **contexto**: chão, horizonte, algum entorno | Modelo flutuando no branco gera fundo alucinado |

Regra prática: **quanto mais informação de profundidade a imagem tiver (sombra, oclusão), melhor o depth map** — e o depth map é o que segura o projeto.

---

## 5. Presets

Três eixos independentes, combináveis. Guardar como dados, não como prompt hardcoded.

**Estilo** — `contemporâneo brasileiro`, `alto padrão litorâneo`, `corporativo`, `retrofit/patrimônio`, `industrial/logístico`, `clean nórdico`, `tropical modernista`, `noturno comercial`

**Iluminação** — `manhã 8h`, `meio-dia`, `golden hour`, `blue hour`, `noturno com fachada iluminada`, `nublado difuso` (melhor para leitura de volumetria), `pós-chuva`

**Câmera / atmosfera** — `nível do pedestre`, `drone baixo`, `contra-plongée de esquina`, `com pessoas`, `sem pessoas`, `vegetação madura`, `vegetação recém-plantada` (importante para VGV: mostra a entrega real, não o sonho)

---

## 6. Vídeo

Render aprovado → img2video, clipes de 5 s, movimento de câmera controlado (órbita, dolly-in, tilt-up), concatenados.

Restrição real: **coerência entre clipes**. O modelo de vídeo alucina fachada em movimentos longos. Prática que funciona:
- movimentos curtos e lentos (órbita ≤ 20°, dolly ≤ 15% de aproximação)
- último frame de um clipe = primeiro frame do próximo
- nunca passar por trás do edifício (o modelo inventa a fachada oculta)

---

## 7. Stack

Sem preferência declarada → escolha: **protótipo local em Python (CLI + relatório HTML) primeiro, app depois**.

Motivo: o gargalo do projeto não é interface, é **descobrir qual pipeline dá fidelidade suficiente e a que custo**. Interface antes disso é trabalho jogado fora. Quando o pipeline estiver definido, o app é uma casca fina (Vue 3 + Supabase, seu padrão) sobre o mesmo módulo.

```
arkitekt/
├── bench/                  # etapa atual: comparar motores
│   ├── arkitekt_bench.py   # runner
│   ├── engines/            # 1 adaptador por motor
│   ├── presets.py
│   └── report.py           # grade comparativa HTML
└── app/                    # etapa 2: Vue 3 + Supabase (auth, storage, histórico)
```

Dados a persistir por geração (isto é o ativo real, não a imagem):
`projeto · imagem_origem · control_map · motor · modelo · prompt · preset · seed · strength · control_weight · custo · tempo · aprovado(bool)`

Com esse log, em 3 meses você sabe exatamente qual combinação funciona para fachada de torre litorânea — e nunca mais tenta de novo o que já falhou.

---

## 8. Custos (ordem de grandeza, verificar na contratação)

| Rota | Custo/imagem | Observação |
|---|---|---|
| Flux + ControlNet (fal.ai) | US$ 0,03–0,06 | Melhor custo/controle. Pago por uso, sem assinatura |
| Editor multimodal (refino) | US$ 0,02–0,15 | Depende de resolução (1k/2k/4k) |
| ComfyUI self-hosted | ~US$ 0,4–0,8/h de GPU | Só compensa acima de ~1.500 imagens/mês |
| Vídeo 5 s | US$ 0,20–1,50 | Ordem de grandeza maior. Usar só em render aprovado |

Pipeline híbrido completo ≈ **US$ 0,10/imagem final**. Redraw a US$ 15/mês por 300 renders ≈ US$ 0,05/render — mas **sem** o controle de seed/preset e sem o log.

---

## 9. Status dos motores nesta sessão

| Motor | Situação | Ação |
|---|---|---|
| Magnific (MCP) | ❌ Exige plano premium | Decidir se vale assinar — é forte em upscale/relight, fraco em controle de geometria |
| Higgsfield (MCP) | ⚠️ Plano free, 8 créditos | Dá para 1–2 testes de editor multimodal. Não dá para benchmark |
| fal.ai (Flux + ControlNet) | 🔑 Precisa de `FAL_KEY` | Rota principal. Crédito inicial baixo resolve o benchmark |
| Replicate | 🔑 Precisa de `REPLICATE_API_TOKEN` | Alternativa/controle |
| ComfyUI | 🆓 Grátis via Colab/Kaggle (GPU emprestada) | Ver [`docs/comfyui_gratis.md`](comfyui_gratis.md) — sem custo por imagem no estágio 1, sessão não é permanente |

O harness de benchmark já está escrito e roda os três assim que houver chave
(ou, no caso do ComfyUI, assim que o notebook do Colab estiver no ar).

---

## 10. Próximos passos

1. Você anexa 2 screenshots reais (1 exterior hidden-line, 1 interior)
2. Chave `FAL_KEY` (US$ 5 de crédito cobre o benchmark inteiro com folga)
3. Rodo a mesma imagem em ~8 configurações e gero a grade comparativa
4. Você escolhe olhando lado a lado — fidelidade, realismo, custo
5. Congelo o pipeline vencedor e construo o app
