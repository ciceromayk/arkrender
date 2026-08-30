-- ARKITEKT — Fatia 1, fix de review: reserva de cota atômica.
--
-- Problema: a checagem "count(*) < cota" seguida de INSERT em requisições
-- separadas tem uma janela de corrida — duas renderizações concorrentes
-- perto do limite podem ambas passar na checagem antes de qualquer uma
-- inserir sua linha, e o usuário termina com mais gerações que a cota
-- permite (ex.: 4/5 usados, duas requisições simultâneas terminam em 6/5).
--
-- Fix: uma função Postgres que faz checagem + reserva (insere uma linha
-- placeholder em `geracoes`) dentro de UMA transação só, travada por
-- usuário com pg_advisory_xact_lock. A API chama isto ANTES de gastar
-- tempo/dinheiro renderizando; se a chamada de render falhar depois, a
-- API apaga a linha placeholder (libera a vaga de volta).

alter table geracoes alter column screenshot_path drop not null;
-- a linha placeholder ainda não tem screenshot no momento da reserva —
-- só existe pra contar contra a cota e ser preenchida depois do render.

create or replace function public.reservar_geracao(
  p_user_id uuid,
  p_modo text,
  p_engine text
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_cota int;
  v_ciclo_inicio timestamptz;
  v_usados int;
  v_id uuid;
begin
  -- serializa reservas do MESMO usuário; libera sozinho no fim da transação
  perform pg_advisory_xact_lock(hashtext(p_user_id::text));

  select pl.cota_geracoes_mes, pr.ciclo_inicio
    into v_cota, v_ciclo_inicio
  from profiles pr
  join planos pl on pl.id = pr.plano_id
  where pr.id = p_user_id;

  if v_cota is null then
    raise exception 'perfil não encontrado' using errcode = 'P0002';
  end if;

  if v_ciclo_inicio is null then
    v_ciclo_inicio := date_trunc('month', now());
  end if;

  select count(*) into v_usados
  from geracoes
  where user_id = p_user_id and created_at >= v_ciclo_inicio;

  if v_usados >= v_cota then
    raise exception 'cota_esgotada' using errcode = 'P0001';
  end if;

  insert into geracoes (user_id, modo, engine, log)
  values (p_user_id, p_modo, p_engine, '{}'::jsonb)
  returning id into v_id;

  return v_id;
end;
$$;

-- SECURITY DEFINER roda com privilégios elevados independente de quem
-- chama — só a API (client service_role) pode chamar isto. Se
-- 'authenticated' pudesse chamar direto, um usuário malicioso passaria
-- um p_user_id de outra pessoa e forjaria reservas na cota alheia.
revoke all on function public.reservar_geracao(uuid, text, text) from public, anon, authenticated;
grant execute on function public.reservar_geracao(uuid, text, text) to service_role;
