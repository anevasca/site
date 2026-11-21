"""Gera as páginas de compartilhamento (m/*.html) e o sitemap.xml de A Nevasca.

Cada matéria (da edição e das publicadas ao longo do dia), editorial e coluna ganha uma página curta com título, resumo e
imagem para a prévia do WhatsApp/Facebook/X, que leva o leitor à página
completa no site. Rode depois de atualizar edicao.json, edicoes/, ultimas/ ou colunas.json:

    python3 build.py
"""
import glob, hashlib, html, json, os

BASE = "https://anevasca.com.br"
e = lambda s: html.escape(str(s or ""), quote=True)


def resumo(t, n=200):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def artigos(ed):
    """Gera (pid, titulo, descricao, imagem, rotulo do cartão) de cada matéria da edição."""
    pre = f"ed-{ed['data']}-"
    m, ed_ = ed["manchete"], ed["editorial"]
    img = lambda a: (a.get("imagem") or {}).get("arquivo")
    yield pre + "manchete", m["titulo"], m.get("linhaFina") or m["texto"][0], img(m), "Manchete · " + m.get("secao", "")
    for i, a in enumerate(ed.get("politica", []), 1):
        yield f"{pre}politica-{i}", a["titulo"], a["resumo"], img(a), "Brasília · " + a.get("secao", "")
    for i, a in enumerate(ed.get("destaques", []), 1):
        yield f"{pre}destaque-{i}", a["titulo"], a["resumo"], img(a), "Economia · " + a.get("secao", "")
    for i, a in enumerate(ed.get("mundo", []), 1):
        yield f"{pre}mundo-{i}", a["titulo"], a["resumo"], img(a), "Mundo · " + a.get("secao", "")
    for i, a in enumerate(ed.get("cultura", []), 1):
        yield f"{pre}cultura-{i}", a["titulo"], a["resumo"], img(a), "Cultura & Games · " + a.get("secao", "")
    yield pre + "editorial", "Editorial: " + ed_["titulo"], ed_["texto"][0], None, "Editorial"


# ---------- Cartão de compartilhamento (imagem 1200x630 com o título) ----------
CREME, PRETO, CINZA, VINHO = (251, 250, 246), (17, 17, 17), (90, 90, 90), (122, 31, 31)
USADOS = set()
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _quebra(draw, texto, fonte, largura):
    linhas, atual = [], ""
    for p in texto.split():
        t = (atual + " " + p).strip()
        if draw.textlength(t, font=fonte) <= largura:
            atual = t
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def cartao(pid, titulo, rotulo, data):
    """Desenha cartoes/<pid>.jpg. Devolve o caminho, ou None se o Pillow não estiver instalado."""
    # O nome leva um código do título: se o título for corrigido, nasce um cartão novo.
    cod = hashlib.sha1(f"{titulo}|{rotulo}|{data}".encode("utf-8")).hexdigest()[:8]
    destino = f"cartoes/{pid}-{cod}.jpg"
    USADOS.add(destino)
    if os.path.exists(destino):
        return destino
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    F = lambda nome, tam: ImageFont.truetype(f"fontes/{nome}", tam)
    W, H, X = 1200, 630, 72
    im = Image.new("RGB", (W, H), CREME)
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, W - 40, 43], fill=PRETO)
    d.text((X, 66), "A Nevasca", font=F("PlayfairDisplay-ExtraBold.ttf", 46), fill=PRETO)
    rot = " ".join(rotulo.strip(" ·").upper().split())
    fr = F("LibreFranklin-Bold.ttf", 22)
    lw = d.textlength(rot, font=fr)
    d.rectangle([W - X - lw - 32, 74, W - X, 116], fill=VINHO)
    d.text((W - X - lw - 16, 82), rot, font=fr, fill=CREME)
    d.rectangle([X, 140, W - X, 141], fill=PRETO)
    # Título: maior fonte possível que caiba em até 4 linhas
    area_y0, area_y1 = 168, 496
    for tam in range(70, 33, -2):
        ft = F("PlayfairDisplay-ExtraBold.ttf", tam)
        linhas = _quebra(d, titulo, ft, W - 2 * X)
        alt = int(tam * 1.18)
        if len(linhas) <= 4 and len(linhas) * alt <= area_y1 - area_y0:
            break
    y = area_y0 + (area_y1 - area_y0 - len(linhas) * alt) // 2
    for ln in linhas:
        d.text((X, y), ln, font=ft, fill=PRETO)
        y += alt
    d.rectangle([40, H - 92, W - 40, H - 91], fill=PRETO)
    d.rectangle([40, H - 87, W - 40, H - 86], fill=PRETO)
    try:
        a, mth, dd = data.split("-")
        quando = f"{int(dd)} de {MESES[int(mth) - 1]} de {a}"
    except Exception:
        quando = ""
    fu = F("LibreFranklin-Medium.ttf", 24)
    d.text((X, H - 68), quando, font=fu, fill=CINZA)
    site = "ANEVASCA.COM.BR"
    fs = F("LibreFranklin-Bold.ttf", 24)
    d.text((W - X - d.textlength(site, font=fs), H - 68), site, font=fs, fill=VINHO)
    os.makedirs("cartoes", exist_ok=True)
    im.save(destino, "JPEG", quality=88, optimize=True)
    return destino


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
            pid, t, d, img, rot = item
            img = img or cartao(pid, t.replace("Editorial: ", "", 1), rot, ed["data"])
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(pid, t, d, img))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    # Matérias publicadas ao longo do dia: ultimas/AAAA-MM-DD.json (lista em ordem de publicação)
    for f in sorted(glob.glob("ultimas/*.json")):
        data = os.path.basename(f)[:-5]
        for i, u in enumerate(json.load(open(f, encoding="utf-8")), 1):
            pid = f"ed-{data}-ultima-{i}"
            d = u.get("resumo") or u.get("linhaFina") or (u.get("texto") or [""])[0]
            img = (u.get("imagem") or {}).get("arquivo") or cartao(pid, u["titulo"], "Ao longo do dia · " + u.get("secao", ""), data)
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(pid, u["titulo"], d, img))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    if os.path.exists("colunas.json"):
        for c in json.load(open("colunas.json", encoding="utf-8")):
            pid = "coluna-" + c["id"]
            t = f"{c['titulo']} — Doido Neves"
            d = c.get("linhaFina") or (c.get("texto") or [""])[0]
            img = cartao(pid, c["titulo"], "O Doido Sensato · Doido Neves", c.get("data", ""))
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(pid, t, d, img))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    # Apaga cartões que nenhuma página usa mais (títulos corrigidos)
    for f in glob.glob("cartoes/*.jpg"):
        if f not in USADOS:
            os.remove(f)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{e(u)}</loc></url>" for u in urls]
    sm.append("</urlset>")
    open("sitemap.xml", "w", encoding="utf-8").write("\n".join(sm) + "\n")
    open("robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
    print(f"{n} páginas de compartilhamento geradas")


if __name__ == "__main__":
    main()
