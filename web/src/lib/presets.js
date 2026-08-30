// Espelha as chaves de core/presets.py (ESTILO/ILUMINACAO/CAMERA).
// Duplicação deliberada para não precisar de um endpoint novo na Fatia 1
// (fora de escopo) — se core/presets.py ganhar/perder uma chave, atualize
// aqui também. Fatia 2: expor GET /presets na api/ elimina essa duplicação.
export const ESTILOS = [
  'contemporaneo_br',
  'alto_padrao_litoraneo',
  'corporativo',
  'retrofit',
  'logistico',
  'nordico',
  'tropical_modernista',
  'noturno_comercial',
]

export const ILUMINACOES = [
  'manha',
  'meio_dia',
  'golden_hour',
  'blue_hour',
  'noturno',
  'nublado',
  'pos_chuva',
]

export const CAMERAS = [
  'pedestre',
  'drone_baixo',
  'esquina',
  'com_pessoas',
  'sem_pessoas',
  'veg_madura',
  'veg_entrega',
]
