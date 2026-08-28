# app — etapa 2

Interface só depois que o pipeline vencedor estiver congelado pelo `bench/`.
Construir interface antes disso é trabalho jogado fora: o gargalo do projeto é
descobrir qual rota dá fidelidade suficiente e a que custo, não a tela.

Quando chegar a hora — Vue 3 + Supabase (padrão já usado no MSM Gestão):
- Supabase Auth + RLS (uso interno, poucos usuários)
- Storage para screenshots de origem, control maps e renders
- tabela `geracoes` espelhando o log de `core/pipeline.render()`
- tabela `projetos` guardando o JSON de identidade visual (seed + presets + pesos)
- a tela é uma casca fina sobre `core/` — nenhuma lógica de render aqui
