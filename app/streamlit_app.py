"""ARKITEKT — interface Streamlit.

Casca fina sobre core/pipeline.py e core/estudo.py: upload de screenshot,
escolha de preset, roda o pipeline e mostra o resultado.

Duas abas, deliberadamente separadas:
  - Render de projeto: fal.ai/ComfyUI, ControlNet, aderência medida —
    o único caminho que pode virar material aprovado.
  - Estudo / moodboard: Gemini/GPT Image/Grok, sem ControlNet, sem
    aderência — nunca aprovado, ver docs/modo_estudo.md.

Nenhuma lógica de render mora aqui — só coleta input, chama core/ e exibe.

    streamlit run app/streamlit_app.py
"""
import os
import re
import sys
import json
import shutil
import pathlib
import tempfile

import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import presets
from core.pipeline import Projeto, render
from core.engines.fal_engine import FalEngine
from core.engines.comfy_engine import ComfyEngine
from core.estudo import gerar_estudo
from core.engines.estudo.gemini_engine import GeminiEngine
from core.engines.estudo.gptimage_engine import GptImageEngine
from core.engines.estudo.grok_engine import GrokEngine

st.set_page_config(page_title="ARKITEKT", page_icon="🏗️", layout="wide")

MOTORES_ESTUDO = {
    "Gemini (Nano Banana)": ("GEMINI_API_KEY", GeminiEngine),
    "GPT Image (OpenAI)": ("OPENAI_API_KEY", GptImageEngine),
    "Grok Imagine (xAI)": ("XAI_API_KEY", GrokEngine),
}


def _secret_or_env(key: str) -> str:
    # st.secrets lança exceção (não StopIteration/KeyError) quando não existe
    # NENHUM secrets.toml no ambiente — caminho padrão de quem roda local
    # sem configurar segredo nenhum, então não pode deixar a página quebrar.
    try:
        val = st.secrets.get(key, "")
    except Exception:
        val = ""
    return val or os.environ.get(key, "")


def _safe_name(name: str, fallback: str) -> str:
    """Nome de arquivo seguro para path no disco — sem diretórios, sem
    caracteres que permitam escapar de tmpdir/projetos/ (ex.: '../../etc')."""
    base = pathlib.Path(name or "").name
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", base).strip("._")
    return base or fallback


st.title("🏗️ ARKITEKT")
st.caption("Screenshot de modelo 3D → render fotorrealista, com fidelidade geométrica medida.")

tab_render, tab_estudo = st.tabs(["🏗️ Render de projeto", "🎨 Estudo / moodboard"])

with st.sidebar:
    st.header("Motor (estágio 1 — estrutura)")
    motor = st.radio("Motor", ["fal.ai (pago, ~US$0,05/img)", "ComfyUI (grátis, self-hosted)"],
                      label_visibility="collapsed")
    usa_comfy = motor.startswith("ComfyUI")

    st.divider()
    st.header("Chave da API — fal.ai")
    key_from_env = _secret_or_env("FAL_KEY")
    if key_from_env:
        st.success("FAL_KEY carregada dos secrets/ambiente.")
        fal_key = key_from_env
    else:
        fal_key = st.text_input("FAL_KEY", type="password",
                                 help="Não é salva — vale só para esta sessão do navegador.")
        st.caption("Pegue em fal.ai → Settings → Keys. ~US$0,10/render.")
    if usa_comfy:
        st.caption("Só é obrigatória se o Refino (estágio 2) ficar ligado — ele sempre roda no fal.ai.")

    comfy_url = ""
    if usa_comfy:
        st.divider()
        st.header("ComfyUI (Colab/Kaggle grátis)")
        comfy_url = _secret_or_env("ARKITEKT_COMFY_URL")
        if comfy_url:
            st.success("URL do ComfyUI carregada dos secrets/ambiente.")
        else:
            comfy_url = st.text_input("URL do túnel", placeholder="https://xxxx.trycloudflare.com",
                                       help="Suba com colab/arkitekt_comfyui.ipynb — a URL muda a cada sessão do Colab.")
        st.caption("Veja docs/comfyui_gratis.md para subir o servidor de graça.")

    st.divider()
    st.header("Identidade do projeto")
    nome = st.text_input("Nome do projeto", value="meu-projeto")
    seed = st.number_input("Seed", value=1974, step=1,
                            help="Mesma seed em ângulos diferentes = coerência visual entre eles.")

    st.divider()
    st.header("Preset")
    estilo = st.selectbox("Estilo", list(presets.ESTILO.keys()))
    iluminacao = st.selectbox("Iluminação", list(presets.ILUMINACAO.keys()))
    camera = st.selectbox("Câmera / atmosfera", list(presets.CAMERA.keys()))
    prompt_extra = st.text_input("Prompt extra (opcional)")

    st.divider()
    st.header("Controle")
    control_weight = st.slider("control_weight (quanto trava a geometria)", 0.0, 1.0, 0.90, 0.05)
    strength = st.slider("strength (estágio 1)", 0.0, 1.0, 0.75, 0.05)
    refino = st.checkbox("Refino (estágio 2 — acabamento)", value=not usa_comfy,
                          help="Sempre roda no fal.ai, mesmo com motor ComfyUI. Desligue para ficar 100% grátis.")
    refino_strength = st.slider("refino_strength", 0.0, 0.6, 0.25, 0.05,
                                 disabled=not refino,
                                 help="Acima de ~0.35 o refino começa a mexer na forma.")
    if usa_comfy and refino:
        st.warning("Refino ligado + motor ComfyUI: o estágio 1 é grátis, mas o estágio 2 cobra do fal.ai.")

# ---------------------------------------------------------------------------
# Aba 1 — Render de projeto (fal.ai/ComfyUI, ControlNet, aderência medida)
# ---------------------------------------------------------------------------
with tab_render:
    st.subheader("1. Screenshot de origem")
    upload = st.file_uploader("SketchUp/Revit — hidden line ou clay, 2048px no lado maior",
                               type=["png", "jpg", "jpeg", "webp"], key="upload_render")

    if upload:
        st.image(upload, caption="origem", width=480)

    need_fal = fal_key if (not usa_comfy or refino) else True   # obrigatória exceto comfy sem refino
    need_comfy = comfy_url if usa_comfy else True
    pronto = bool(upload) and bool(need_fal) and bool(need_comfy)

    if st.button("Renderizar", type="primary", disabled=not pronto, key="btn_render"):
        # limpa o tmpdir da renderização anterior desta sessão — sem isso o
        # disco acumula screenshot+control_map+render de todo clique
        tmpdir_anterior = st.session_state.get("_tmpdir")
        if tmpdir_anterior:
            shutil.rmtree(tmpdir_anterior, ignore_errors=True)

        tmpdir = tempfile.mkdtemp(prefix="arkitekt_")
        st.session_state["_tmpdir"] = tmpdir
        src_name = _safe_name(upload.name, "screenshot.png")
        src_path = pathlib.Path(tmpdir) / src_name
        src_path.write_bytes(upload.getvalue())

        projeto = Projeto(nome=nome, seed=int(seed), estilo=estilo, iluminacao=iluminacao,
                           camera=camera, control_weight=control_weight, strength=strength,
                           refino=refino, refino_strength=refino_strength, prompt_extra=prompt_extra)

        if usa_comfy:
            os.environ["ARKITEKT_COMFY_URL"] = comfy_url
            engine = ComfyEngine()
        else:
            engine = FalEngine()

        # o SDK da fal lê a chave de os.environ (é assim que fal_client funciona) —
        # janela de exposição fica restrita à chamada, valor anterior é restaurado
        # depois. Processo é compartilhado entre sessões do Streamlit, então evite
        # deploys multiusuário simultâneo com chaves diferentes por sessão.
        fal_key_anterior = os.environ.get("FAL_KEY")
        if fal_key:
            os.environ["FAL_KEY"] = fal_key

        with st.spinner("Renderizando — estágio 1 (estrutura)"
                         + (" + estágio 2 (acabamento)..." if refino else "...")):
            try:
                log = render(projeto, str(src_path), out_dir=tmpdir, engine=engine)
            except Exception as e:
                st.error(f"Falhou: {e}")
                st.stop()
            finally:
                if fal_key_anterior is not None:
                    os.environ["FAL_KEY"] = fal_key_anterior
                elif fal_key:
                    os.environ.pop("FAL_KEY", None)

        st.session_state["log"] = log
        st.session_state["projeto"] = projeto
        st.session_state["refino_usado"] = refino

    elif not upload:
        st.info("Envie um screenshot para habilitar o botão.")
    elif usa_comfy and not comfy_url:
        st.info("Informe a URL do ComfyUI na barra lateral para habilitar o botão.")
    elif not need_fal:
        st.info("Informe a FAL_KEY na barra lateral para habilitar o botão "
                 "(obrigatória com motor fal.ai, ou com Refino ligado).")

    # Fora do bloco do botão de propósito: marcar a checkbox "salvar" abaixo
    # dispara um rerun do script em que st.button() volta a False, então o
    # resultado só sobrevive se vier do session_state, não de uma variável local.
    if "log" in st.session_state:
        log = st.session_state["log"]
        projeto = st.session_state["projeto"]
        refino_usado = st.session_state["refino_usado"]
        nome_seguro = _safe_name(projeto.nome, "projeto")

        st.subheader("2. Resultado")
        col1, col2 = st.columns(2)
        with col1:
            st.image(log["estrutura"], caption="estágio 1 — estrutura")
        with col2:
            st.image(log["final"], caption="estágio 2 — final" if refino_usado else "final (sem refino)")

        aderencia = log["aderencia"]
        cor = "🟢" if aderencia >= 0.80 else ("🟡" if aderencia >= 0.45 else "🔴")
        st.metric("Aderência geométrica", f"{aderencia:.2f}", help=log["veredito"])
        st.caption(f"{cor} {log['veredito']}")

        if log.get("alerta"):
            st.warning(log["alerta"])

        c1, c2, c3 = st.columns(3)
        c1.metric("Tempo", f"{log['segundos']}s")
        c2.metric("Custo", f"US$ {log['custo_usd']:.3f}")
        c3.metric("Invenção", "—")

        with open(log["final"], "rb") as f:
            st.download_button("Baixar render final", f, file_name=pathlib.Path(log["final"]).name,
                                key="dl_render_img")

        st.download_button("Baixar log (JSON)", json.dumps(log, ensure_ascii=False, indent=2),
                            file_name=f"{nome_seguro}.json", key="dl_render_json")

        with st.expander("Prompt usado"):
            st.code(log["prompt"], language=None)

        if st.checkbox("Salvar identidade visual do projeto (projetos/*.json)", key="chk_salvar_projeto"):
            dest = projeto.salvar(str(ROOT / "projetos" / f"{nome_seguro}.json"))
            st.info(f"Salvo em {dest} — reaproveite para novos ângulos com a mesma coerência visual.")

# ---------------------------------------------------------------------------
# Aba 2 — Estudo / moodboard (Gemini/GPT Image/Grok, SEM ControlNet)
# ---------------------------------------------------------------------------
with tab_estudo:
    st.warning(
        "⚠️ **Sem controle de geometria — nunca use para material aprovado.** "
        "Estes motores reinterpretam a cena livremente (podem mudar pavimento, "
        "esquadria, volumetria). Sirva só de referência de atmosfera/moodboard. "
        "Ver [docs/modo_estudo.md](https://github.com/ciceromayk/arkrender/blob/main/docs/modo_estudo.md)."
    )

    nome_motor = st.radio("Motor", list(MOTORES_ESTUDO.keys()), key="motor_estudo")
    env_var, EngineCls = MOTORES_ESTUDO[nome_motor]

    chave_estudo = _secret_or_env(env_var)
    if chave_estudo:
        st.success(f"{env_var} carregada dos secrets/ambiente.")
    else:
        chave_estudo = st.text_input(env_var, type="password", key="input_chave_estudo",
                                      help="Não é salva — vale só para esta sessão do navegador.")

    upload_estudo = st.file_uploader("Screenshot de referência", type=["png", "jpg", "jpeg", "webp"],
                                      key="upload_estudo")
    if upload_estudo:
        st.image(upload_estudo, caption="referência", width=480)
        if nome_motor.startswith("Grok"):
            st.caption("Grok Imagine hoje é texto→imagem — este screenshot NÃO é enviado à API, "
                       "só ajuda você a descrever a cena no prompt abaixo.")

    prompt_estudo = st.text_area("Prompt", key="prompt_estudo",
                                  placeholder="ex.: torre litorânea ao entardecer, luz dourada, poucas nuvens")
    seed_estudo = st.number_input("Seed (opcional, 0 = aleatório)", value=0, step=1, key="seed_estudo")

    pronto_estudo = bool(upload_estudo) and bool(chave_estudo) and bool(prompt_estudo.strip())

    if st.button("Gerar estudo", type="primary", disabled=not pronto_estudo, key="btn_estudo"):
        tmpdir_estudo_anterior = st.session_state.get("_tmpdir_estudo")
        if tmpdir_estudo_anterior:
            shutil.rmtree(tmpdir_estudo_anterior, ignore_errors=True)

        tmpdir_estudo = tempfile.mkdtemp(prefix="arkitekt_estudo_")
        st.session_state["_tmpdir_estudo"] = tmpdir_estudo
        src_name_estudo = _safe_name(upload_estudo.name, "referencia.png")
        src_path_estudo = pathlib.Path(tmpdir_estudo) / src_name_estudo
        src_path_estudo.write_bytes(upload_estudo.getvalue())

        chave_anterior = os.environ.get(env_var)
        os.environ[env_var] = chave_estudo

        with st.spinner(f"Gerando com {nome_motor}..."):
            try:
                log_estudo = gerar_estudo(EngineCls(), str(src_path_estudo), prompt_estudo,
                                           seed=int(seed_estudo) or None, out_dir=tmpdir_estudo)
            except Exception as e:
                st.error(f"Falhou: {e}")
                st.stop()
            finally:
                if chave_anterior is not None:
                    os.environ[env_var] = chave_anterior
                else:
                    os.environ.pop(env_var, None)

        st.session_state["log_estudo"] = log_estudo

    elif not upload_estudo:
        st.info("Envie um screenshot de referência para habilitar o botão.")
    elif not chave_estudo:
        st.info(f"Informe a {env_var} acima para habilitar o botão.")
    elif not prompt_estudo.strip():
        st.info("Escreva um prompt para habilitar o botão.")

    if "log_estudo" in st.session_state:
        le = st.session_state["log_estudo"]
        st.subheader("Resultado")
        st.image(le["imagem"], caption=f"{le['engine']} — NÃO aprovado para venda", width=480)
        st.caption(f"🔴 {le['motivo']}")

        c1, c2 = st.columns(2)
        c1.metric("Tempo", f"{le['segundos']}s")
        c2.metric("Custo", f"US$ {le['custo_usd']:.3f}")

        with open(le["imagem"], "rb") as f:
            st.download_button("Baixar imagem", f, file_name=pathlib.Path(le["imagem"]).name,
                                key="dl_estudo_img")

        st.download_button("Baixar log (JSON)", json.dumps(le, ensure_ascii=False, indent=2),
                            file_name="estudo.json", key="dl_estudo_json")
