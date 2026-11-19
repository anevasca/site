"""Gera as páginas de compartilhamento (m/*.html) e o sitemap.xml de A Nevasca.

Cada matéria, editorial e coluna ganha uma página curta com título, resumo e
imagem para a prévia do WhatsApp/Facebook/X, que leva o leitor à página
completa no site. Rode depois de atualizar edicao.json, edicoes/ ou colunas.json:

    python3 build.py
"""
import glob, html, json, os

BASE = "https://anevasca.com.br"
e = lambda s: html.escape(str(s or ""), quote=True)


def resumo(t, n=200):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def artigos(ed):
    pre = f"ed-{ed['data']}-"
    m, ed_ = ed["manchete"], ed["editorial"]
    yield pre + "manchete", m["titulo"], m.get("linhaFina") or m["texto"][0]
    for i, a in enumerate(ed.get("politica", []), 1):
        yield f"{pre}politica-{i}", a["titulo"], a["resumo"]
    for i, a in enumerate(ed.get("destaques", []), 1):
        yield f"{pre}destaque-{i}", a["titulo"], a["resumo"]
    for i, a in enumerate(ed.get("mundo", []), 1):
        yield f"{pre}mundo-{i}", a["titulo"], a["resumo"]
    for i, a in enumerate(ed.get("cultura", []), 1):
        yield f"{pre}cultura-{i}", a["titulo"], a["resumo"], (a.get("imagem") or {}).get("arquivo")
    yield pre + "editorial", "Editorial: " + ed_["titulo"], ed_["texto"][0]


def pagina(pid, titulo, desc, img=None):
    destino = f"{BASE}/#{pid}"
    url = f"{BASE}/m/{pid}.html"
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>{e(titulo)} — A Nevasca</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(resumo(desc))}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="A Nevasca">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(resumo(desc))}">
<meta property="og:image" content="{BASE}/{img or 'og.png'}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{destino}">
<meta http-equiv="refresh" content="0; url={destino}">
<script>(function(){{var r="";try{{r=document.referrer?new URL(document.referrer).hostname:""}}catch(e){{}}location.replace({json.dumps(BASE + "/")}+(r?"?ref="+encodeURIComponent(r):"")+{json.dumps("#" + pid)});}})();</script>
</head><body style="font-family:Georgia,serif;max-width:640px;margin:40px auto;padding:0 16px">
<p><a href="{destino}">{e(titulo)}</a> — A Nevasca</p>
</body></html>
"""


def main():
    os.makedirs("m", exist_ok=True)
    urls = [BASE + "/"]
    n = 0
    for f in sorted(glob.glob("edicoes/*.json")):
        ed = json.load(open(f, encoding="utf-8"))
        for item in artigos(ed):
            pid, t, d = item[:3]
            img = item[3] if len(item) > 3 else None
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(pid, t, d, img))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    if os.path.exists("colunas.json"):
        for c in json.load(open("colunas.json", encoding="utf-8")):
            pid = "coluna-" + c["id"]
            t = f"{c['titulo']} — Doido Neves"
            d = c.get("linhaFina") or (c.get("texto") or [""])[0]
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(pid, t, d))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{e(u)}</loc></url>" for u in urls]
    sm.append("</urlset>")
    open("sitemap.xml", "w", encoding="utf-8").write("\n".join(sm) + "\n")
    open("robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"{n} páginas de compartilhamento geradas")


if __name__ == "__main__":
    main()
