"""Grade comparativa em HTML — decisão se toma olhando lado a lado."""
import pathlib
import base64
import html as H

CSS = """
:root{--bg:#0e1013;--panel:#171a1f;--line:#282d35;--fg:#e8eaed;--dim:#9aa1ab;
      --good:#4ec9a0;--warn:#e0b34a;--bad:#e0685a;--accent:#7aa2f7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
     font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:1.5rem;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:.9rem;margin-bottom:28px}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
      border-radius:6px;padding:14px 16px;margin:0 0 28px;font-size:.88rem;color:var(--dim)}
.note b{color:var(--fg)}
h2{font-size:1.05rem;margin:36px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.card img{width:100%;display:block;aspect-ratio:16/10;object-fit:cover;background:#000}
.card .body{padding:12px 14px}
.cfg{font:600 .82rem/1.3 ui-monospace,monospace;color:var(--accent);margin-bottom:8px}
.row{display:flex;justify-content:space-between;font-size:.8rem;color:var(--dim);
     padding:3px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.row span:last-child{color:var(--fg);font-variant-numeric:tabular-nums}
.verdict{margin-top:10px;font-size:.78rem;padding:6px 9px;border-radius:4px;line-height:1.35}
.v-good{background:rgba(78,201,160,.11);color:var(--good)}
.v-warn{background:rgba(224,179,74,.11);color:var(--warn)}
.v-bad{background:rgba(224,104,90,.11);color:var(--bad)}
.bar{height:4px;background:rgba(255,255,255,.07);border-radius:2px;overflow:hidden;margin:6px 0 2px}
.bar i{display:block;height:100%;background:var(--good)}
table{width:100%;border-collapse:collapse;font-size:.82rem;margin-top:10px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--dim);font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.04em}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.fail{color:var(--bad);font-size:.8rem}
.src{max-width:420px;border-radius:6px;border:1px solid var(--line)}
.skip{font-size:.83rem;color:var(--warn);margin:4px 0}
"""


def _b64(p):
    try:
        return "data:image/png;base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()
    except Exception:
        return ""


def _cls(a):
    return "v-good" if a >= 0.65 else ("v-warn" if a >= 0.45 else "v-bad")


def build(meta: dict, out_dir) -> str:
    out_dir = pathlib.Path(out_dir)
    res = meta["resultados"]
    ok = [r for r in res if r.get("ok")]

    p = [f"<style>{CSS}</style><div class='wrap'>",
         "<h1>ARKITEKT — comparativo de motores de render</h1>",
         f"<div class='sub'>{H.escape(meta['gerado_em'])} · seed fixa "
         f"{meta['seed']} · tolerância {meta['tau']} px · {len(ok)}/{len(res)} renders concluídos</div>"]

    p.append(
        "<div class='note'><b>Como ler.</b> <b>Aderência</b> = quanto da geometria do seu "
        "projeto sobreviveu ao render. É o número que decide se a imagem pode ir para "
        "material de venda. <b>Invenção</b> = arestas que o modelo criou; é sempre alta e "
        "isso é normal (vegetação, pessoas, céu, reflexo) — serve só para comparar "
        "configurações entre si, nunca como valor absoluto.</div>")

    for name, why in [(d["motor"], d["motivo"]) for d in meta.get("indisponiveis", [])]:
        p.append(f"<div class='skip'>⚠ {H.escape(name)} não rodou — {H.escape(why)}</div>")

    # ranking
    if ok:
        p.append("<h2>Ranking por aderência geométrica</h2><table><tr>"
                 "<th>Motor</th><th>Config</th><th>Preset</th>"
                 "<th class='num'>Aderência</th><th class='num'>Invenção</th>"
                 "<th class='num'>Tempo</th><th class='num'>Custo</th></tr>")
        for r in sorted(ok, key=lambda x: -x.get("fidelidade", {}).get("aderencia", 0)):
            f = r.get("fidelidade", {})
            pr = r.get("preset", {})
            p.append(
                f"<tr><td>{H.escape(r['engine'])}</td>"
                f"<td>{H.escape(r['config_id'])}</td>"
                f"<td style='color:var(--dim)'>{H.escape(pr.get('estilo',''))} · "
                f"{H.escape(pr.get('iluminacao',''))}</td>"
                f"<td class='num'>{f.get('aderencia','—')}</td>"
                f"<td class='num'>{f.get('invencao','—')}</td>"
                f"<td class='num'>{r.get('seconds','—')}s</td>"
                f"<td class='num'>${r.get('cost_usd') or '—'}</td></tr>")
        p.append("</table>")

        total = sum(r.get("cost_usd") or 0 for r in ok)
        p.append(f"<div class='sub' style='margin-top:10px'>Custo total do benchmark: "
                 f"<b style='color:var(--fg)'>US$ {total:.2f}</b> · "
                 f"média US$ {total/max(len(ok),1):.3f}/imagem</div>")

    # por imagem de origem
    for src in sorted({r["source"] for r in res}):
        p.append(f"<h2>{H.escape(pathlib.Path(src).name)}</h2>")
        img = _b64(src)
        if img:
            p.append(f"<img class='src' src='{img}' alt='origem'>")
        dm = next((r.get("control_map_path") for r in res
                   if r["source"] == src and r.get("control_map_path")), None)
        if dm and (d := _b64(dm)):
            p.append(f"<img class='src' src='{d}' alt='depth' style='margin-left:12px'>")

        p.append("<div class='grid'>")
        for r in [x for x in res if x["source"] == src]:
            if not r.get("ok"):
                p.append(f"<div class='card'><div class='body'><div class='cfg'>"
                         f"{H.escape(r['config_id'])}</div>"
                         f"<div class='fail'>{H.escape(str(r.get('error'))[:180])}</div>"
                         f"</div></div>")
                continue
            f = r.get("fidelidade", {})
            a = f.get("aderencia", 0)
            pm = r.get("params", {})
            p.append(
                f"<div class='card'><img src='{_b64(r['image_path'])}' loading='lazy'>"
                f"<div class='body'><div class='cfg'>{H.escape(r['config_id'])}</div>"
                f"<div class='row'><span>motor</span><span>{H.escape(r['engine'].split('_')[0])}</span></div>"
                f"<div class='row'><span>strength / control</span>"
                f"<span>{pm.get('strength','—')} / {pm.get('control_weight','—')}</span></div>"
                f"<div class='row'><span>aderência</span><span>{a}</span></div>"
                f"<div class='bar'><i style='width:{a*100:.0f}%'></i></div>"
                f"<div class='row'><span>invenção</span><span>{f.get('invencao','—')}</span></div>"
                f"<div class='row'><span>tempo / custo</span>"
                f"<span>{r.get('seconds','—')}s · ${r.get('cost_usd') or '—'}</span></div>"
                f"<div class='verdict {_cls(a)}'>{H.escape(r.get('veredito',''))}</div>"
                f"</div></div>")
        p.append("</div>")

    p.append("</div>")
    dest = out_dir / "comparativo.html"
    dest.write_text("\n".join(p), encoding="utf-8")
    return str(dest)
