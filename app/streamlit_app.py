"""ARKITEKT — interface Streamlit.

Casca fina sobre core/pipeline.py: upload de screenshot, escolha de preset,
roda o pipeline híbrido de 2 estágios e mostra o resultado + aderência.

Nenhuma lógica de render mora aqui — só coleta input, chama core/ e exibe.

    streamlit run app/streamlit_app.py
"""
import os
import sys
import json
import pathlib
import tempfile

import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import presets
from core.pipeline import Projeto, render

st.set_page_config(page_title="ARKITEKT", page_icon="🏗️", layout="wide")


def _fal_key() -> str:
    """Chave vem do secrets do Streamlit Cloud, de env var, ou input manual."""
    key = st.secrets.get("FAL_KEY", "") if hasattr(st, "secrets") else ""
    if not key:
        key = os.environ.get("FAL_KEY", "")
    return key


st.title("🏗️ ARKITEKT")
st.caption("Screenshot de modelo 3D → render fotorrealista, com fidelidade geométrica medida.")

with st.sidebar:
    st.header("Chave da API")
    key_from_env = _fal_key()
    if key_from_env:
        st.success("FAL_KEY carregada dos secrets/ambiente.")
        fal_key = key_from_env
    else:
        fal_key = st.text_input("FAL_KEY", type="password",
                                 help="Não é salva — vale só para esta sessão do navegador.")
        st.caption("Pegue em fal.ai → Settings → Keys. ~US$0,10/render.")

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
    refino = st.checkbox("Refino (estágio 2 — acabamento)", value=True)
    refino_strength = st.slider("refino_strength", 0.0, 0.6, 0.25, 0.05,
                                 disabled=not refino,
                                 help="Acima de ~0.35 o refino começa a mexer na forma.")

st.subheader("1. Screenshot de origem")
upload = st.file_uploader("SketchUp/Revit — hidden line ou clay, 2048px no lado maior",
                           type=["png", "jpg", "jpeg", "webp"])

if upload:
    st.image(upload, caption="origem", width=480)

if st.button("Renderizar", type="primary", disabled=not (upload and fal_key)):
    os.environ["FAL_KEY"] = fal_key

    tmpdir = tempfile.mkdtemp(prefix="arkitekt_")
    src_path = pathlib.Path(tmpdir) / upload.name
    src_path.write_bytes(upload.getvalue())

    projeto = Projeto(nome=nome, seed=int(seed), estilo=estilo, iluminacao=iluminacao,
                       camera=camera, control_weight=control_weight, strength=strength,
                       refino=refino, refino_strength=refino_strength, prompt_extra=prompt_extra)

    with st.spinner("Renderizando — estágio 1 (estrutura) + estágio 2 (acabamento)..."):
        try:
            log = render(projeto, str(src_path), out_dir=tmpdir)
        except Exception as e:
            st.error(f"Falhou: {e}")
            st.stop()

    st.subheader("2. Resultado")
    col1, col2 = st.columns(2)
    with col1:
        st.image(log["estrutura"], caption="estágio 1 — estrutura")
    with col2:
        st.image(log["final"], caption="estágio 2 — final" if refino else "final (sem refino)")

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
        st.download_button("Baixar render final", f, file_name=pathlib.Path(log["final"]).name)

    st.download_button("Baixar log (JSON)", json.dumps(log, ensure_ascii=False, indent=2),
                        file_name=f"{nome}.json")

    with st.expander("Prompt usado"):
        st.code(log["prompt"], language=None)

    if st.checkbox("Salvar identidade visual do projeto (projetos/*.json)"):
        dest = projeto.salvar(str(ROOT / "projetos" / f"{nome}.json"))
        st.info(f"Salvo em {dest} — reaproveite para novos ângulos com a mesma coerência visual.")

elif not fal_key:
    st.info("Informe a FAL_KEY na barra lateral para habilitar o botão.")
elif not upload:
    st.info("Envie um screenshot para habilitar o botão.")
