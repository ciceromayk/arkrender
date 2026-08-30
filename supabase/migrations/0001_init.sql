-- ARKITEKT — Fase B, Fatia 1: schema multi-usuário.
--
-- Rode isto no SQL Editor do Supabase Studio (ou `supabase db push`).
-- Cria as tabelas, RLS e o plano 'free' de teste. Stripe e planos pagos
-- de verdade entram na Fatia 2 — as colunas stripe_*/ciclo_* já existem
-- aqui pra não precisar de uma segunda migration alterando a tabela depois,
-- mas ficam null/sem uso nesta fatia.

-- --------------------------------------------------------------------------
-- planos: tabela de DADOS, não enum/hardcode — trocar preço ou cota de um
-- plano depois é um UPDATE no Supabase Studio, sem deploy, sem migration.
-- --------------------------------------------------------------------------
create table planos (
  id text primary key,                    -- 'free' | 'basico' | 'pro' | 'enterprise'
  nome text not null,
  preco_centavos int not null default 0,
  cota_geracoes_mes int not null,          -- pool único: render + estudo somados (Fatia 2)
  stripe_price_id text,                    -- null até a Fatia 2
  ativo boolean not null default true
);

insert into planos (id, nome, preco_centavos, cota_geracoes_mes, stripe_price_id) values
  ('free', 'Grátis', 0, 5, null);
-- planos pagos (básico/pro/enterprise) entram na Fatia 2, junto com o Stripe.

-- --------------------------------------------------------------------------
-- profiles: um por usuário do Supabase Auth.
-- --------------------------------------------------------------------------
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  plano_id text not null default 'free' references planos(id),
  stripe_customer_id text,                 -- Fatia 2
  stripe_subscription_id text,             -- Fatia 2
  stripe_status text,                      -- Fatia 2: active | past_due | canceled | ...
  ciclo_inicio timestamptz,                -- Fatia 2: null nesta fatia = usa mês calendário
  ciclo_fim timestamptz,                   -- Fatia 2
  created_at timestamptz not null default now()
);

-- cria o profile automaticamente quando alguém se cadastra no Supabase Auth
create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email) values (new.id, new.email);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- --------------------------------------------------------------------------
-- projetos: espelha o dataclass Projeto de core/pipeline.py.
-- --------------------------------------------------------------------------
create table projetos (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  nome text not null,
  seed int not null,
  estilo text not null,
  iluminacao text not null,
  camera text not null,
  control_weight numeric not null default 0.90,
  strength numeric not null default 0.75,
  refino boolean not null default true,
  refino_strength numeric not null default 0.25,
  prompt_extra text not null default '',
  notas text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index projetos_user_idx on projetos (user_id);

-- --------------------------------------------------------------------------
-- geracoes: uma tabela só para render() e o futuro gerar_estudo() (Fatia 2).
-- Nesta fatia só é gravado modo='render'. Colunas específicas de um modo
-- ficam nullable no outro, de propósito — o dict `log` bruto (jsonb)
-- preserva tudo mesmo assim.
-- --------------------------------------------------------------------------
create table geracoes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  projeto_id uuid references projetos(id) on delete set null,
  modo text not null check (modo in ('render', 'estudo')),
  engine text not null,
  screenshot_path text not null,           -- path no bucket Storage, não a imagem em si
  imagem_final_path text,
  control_map_path text,                   -- null quando modo='estudo', de propósito
  aderencia numeric,                       -- null quando modo='estudo', de propósito
  veredito text,
  aprovado_para_venda boolean not null default false,
  custo_usd numeric,
  segundos numeric,
  prompt text,
  params jsonb,
  log jsonb not null,                      -- dict bruto que render()/gerar_estudo() já devolvem
  created_at timestamptz not null default now()
);
create index geracoes_user_created_idx on geracoes (user_id, created_at desc);

-- --------------------------------------------------------------------------
-- RLS
-- --------------------------------------------------------------------------
alter table planos enable row level security;
alter table profiles enable row level security;
alter table projetos enable row level security;
alter table geracoes enable row level security;

create policy "planos_leitura_publica" on planos
  for select using (true);

create policy "profiles_leitura_da_propria" on profiles
  for select using (auth.uid() = id);
-- sem policy de update/insert para 'authenticated': só a API (client
-- service_role, que ignora RLS) grava plano/stripe_* — impede o usuário
-- de se auto-promover de plano direto no client.

create policy "projetos_crud_do_dono" on projetos
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "geracoes_leitura_do_dono" on geracoes
  for select using (auth.uid() = user_id);
-- sem policy de insert para 'authenticated': só a API grava (evita o
-- usuário forjar aderência/veredito direto no client).

-- --------------------------------------------------------------------------
-- Storage — crie o bucket 'geracoes' (privado) no Studio antes de aplicar
-- esta parte (Storage → New bucket → Private → nome exato "geracoes").
-- Path esperado: {user_id}/{geracao_id}/arquivo.png
-- --------------------------------------------------------------------------
create policy "storage_leitura_do_dono" on storage.objects
  for select using (
    bucket_id = 'geracoes'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
-- sem policy de insert/update para 'authenticated': só a API (service_role)
-- escreve no bucket.
