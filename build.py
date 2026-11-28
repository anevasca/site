"""Gera as páginas de compartilhamento (m/*.html) e o sitemap.xml de A Nevasca.

Gera páginas completas com endereço canônico próprio e metadados para
compartilhamento. Rode depois de atualizar edicao.json, edicoes/, ultimas/ ou colunas.json:

    python3 build.py
"""
import glob, hashlib, html, json, os, re
from pathlib import Path

BASE = "https://anevasca.com.br"
e = lambda s: html.escape(str(s or ""), quote=True)


_ROTULO_FALA = re.compile(r"^(Junior Neves|Reverendo Jeferson):\s")


def par(texto):
    """Parágrafo em HTML; em entrevistas, o nome de quem fala vai em negrito."""
    m = _ROTULO_FALA.match(str(texto or ""))
    if m:
        return f"<strong>{e(m.group(1))}:</strong> {e(texto[m.end():])}"
    return e(texto)


def resumo(t, n=200):
    t = " ".join(str(t or "").split())
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def artigos(ed):
    """Gera (pid, titulo, descricao, imagem, rotulo do cartão) de cada matéria da edição."""
    pre = f"ed-{ed['data']}-"
    m, ed_ = ed["manchete"], ed["editorial"]
    img = lambda a: (a.get("imagem") or {}).get("arquivo")
    yield pre + "manchete", m["titulo"], m.get("linhaFina") or m["texto"][0], img(m), "Manchete · " + m.get("secao", ""), m
    for i, a in enumerate(ed.get("politica", []), 1):
        yield f"{pre}politica-{i}", a["titulo"], a["resumo"], img(a), "Brasília · " + a.get("secao", ""), a
    for i, a in enumerate(ed.get("destaques", []), 1):
        yield f"{pre}destaque-{i}", a["titulo"], a["resumo"], img(a), "Economia · " + a.get("secao", ""), a
    for i, a in enumerate(ed.get("mundo", []), 1):
        yield f"{pre}mundo-{i}", a["titulo"], a["resumo"], img(a), "Mundo · " + a.get("secao", ""), a
    for i, a in enumerate(ed.get("cultura", []), 1):
        yield f"{pre}cultura-{i}", a["titulo"], a["resumo"], img(a), "Cultura & Games · " + a.get("secao", ""), a
    yield pre + "editorial", "Editorial: " + ed_["titulo"], ed_["texto"][0], None, "Editorial", ed_


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


MAIN = re.compile(r'(<main id="conteudo">).*?(</main>)', re.S)
CARD_HEAD = re.compile(r'<title>.*?</title>\s*<meta name="description"[^>]*>.*?<meta name="twitter:card"[^>]*>', re.S)
LOADING = '<div class="carregando">Carregando a edição de hoje…</div>'


def substituir_conteudo(template, conteudo):
    return MAIN.sub(lambda m: m[1] + conteudo + m[2], template, count=1)


def figura(foto):
    if not foto or not foto.get("arquivo"):
        return ""
    arquivo = "/" + foto["arquivo"].lstrip("/")
    legenda = e(foto.get("legenda"))
    credito = e(foto.get("credito"))
    return (f'<figure class="foto"><img src="{e(arquivo)}" alt="{legenda}">'
            f'<figcaption>{legenda}{(" <span>" + credito + "</span>") if credito else ""}</figcaption></figure>')


def corpo(artigo):
    blocos = []
    for pos, paragrafo in enumerate(artigo.get("texto") or [artigo.get("resumo")], 1):
        if paragrafo:
            blocos.append(f'<p>{par(paragrafo)}</p>')
        for extra in artigo.get("ilustracoes", []):
            if extra["apos"] != pos:
                continue
            blocos.extend(figura(foto) for foto in extra.get("fotos", []))
            if extra.get("intertitulo"):
                blocos.append(f'<h3>{e(extra["intertitulo"])}</h3>')
    fontes = [f'<a href="{e(fonte["url"])}">{e(fonte["nome"])}</a>'
              for fonte in artigo.get("fontes", []) if fonte.get("url")]
    if fontes:
        links = ", ".join(fontes)
        blocos.append(f'<p class="fontes">Fontes: {links}</p>')
    return "".join(blocos)


def pagina(template, pid, titulo, desc, img, artigo, rotulo, data):
    url = f"{BASE}/m/{pid}.html"
    imagem = f"{BASE}/{(img or 'og.png').lstrip('/')}"
    deck = artigo.get("linhaFina")
    noticia = not rotulo.startswith(("Editorial", "O Doido Sensato"))
    autoria = artigo.get("autor")
    if not autoria and pid.startswith("coluna-"):
        autoria = "Doido Neves"
    schema = {"@context": "https://schema.org", "@type": "NewsArticle" if noticia else "Article",
              "headline": titulo, "description": resumo(desc), "image": imagem,
              "datePublished": data, "mainEntityOfPage": url,
              "publisher": {"@type": "Organization", "name": "A Nevasca", "url": BASE}}
    if autoria:
        schema["author"] = {"@type": "Person", "name": autoria}
    jsonld = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
    meta = f"""<title>{e(titulo)} — A Nevasca</title>
<meta name="description" content="{e(resumo(desc))}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="A Nevasca">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(resumo(desc))}">
<meta property="og:image" content="{e(imagem)}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{url}">
<script type="application/ld+json">{jsonld}</script>"""
    html_pagina = CARD_HEAD.sub(lambda _: meta, template, count=1)
    html_pagina = html_pagina.replace("<head>", '<head>\n<base href="/">', 1)
    html_pagina = html_pagina.replace("<body>", f'<body data-artigo="{e(pid)}">', 1)
    linha_fina = f'<p class="fina">{e(deck)}</p>' if deck else ""
    conteudo = (f'<article class="artigo-pag"><p class="migalha"><a href="/">Capa</a></p>'
                f'<p class="kicker">{e(rotulo)}</p><h1>{e(titulo)}</h1>{linha_fina}'
                f'<p class="assinatura">{e(autoria or "Da redação")} · {e(data)}</p>'
                f'{figura(artigo.get("imagem"))}<div class="corpo">{corpo(artigo)}</div></article>')
    return substituir_conteudo(html_pagina, conteudo)


def ultimas_estatico(data):
    """HTML da prévia de "Últimas notícias" de hoje, com links reais (/m/...),
    para quem não executa JavaScript (a versão com JS troca os links por #hash
    depois, sem prejuízo). Vazio se não há ultimas/<data>.json ou está vazio."""
    caminho = Path(f"ultimas/{data}.json")
    if not caminho.exists():
        return ""
    lista = json.loads(caminho.read_text(encoding="utf-8"))
    if not lista:
        return ""
    pre = f"ed-{data}-ultima-"
    selo_urgente = '<span class="selo-urg">Urgente</span>'

    def li(i, u):
        selo = selo_urgente if u.get("urgente") else ""
        resumo_u = e(u.get("resumo") or u.get("linhaFina") or "")
        return (f'<li><span class="hora">{e(u.get("hora"))}</span><div>'
                f'<h4>{selo}<a href="/m/{pre}{i}.html">{e(u["titulo"])}</a></h4>'
                f'<p>{resumo_u}</p></div></li>')

    ver_mais = (f'<a class="mais-secao" href="/m/{pre}1.html">Ver as {len(lista)} atualizações do dia →</a>'
                if len(lista) > 3 else "")
    primeiros = "".join(li(i, u) for i, u in enumerate(lista[:3], 1))
    return (f'<section class="secao"><h3>Últimas notícias</h3>'
            f'<ul class="ultimas-lista">{primeiros}</ul>{ver_mais}</section>')


def arquivo_estatico():
    """HTML da lista de 'Edições anteriores' no rodapé, com links reais
    (/m/ed-AAAA-MM-DD-manchete.html) em vez dos #hash que só funcionam com
    JavaScript. A versão com JS troca pelos #hash sem prejuízo."""
    caminho = Path("arquivo.json")
    if not caminho.exists():
        return ""
    lista = json.loads(caminho.read_text(encoding="utf-8"))
    linhas = "".join(
        f'<a href="/m/ed-{e(x["data"])}-manchete.html">{e(x["rotulo"])}</a>'
        for x in lista[:7]
    )
    return linhas


ORG_SCHEMA = json.dumps({
    "@context": "https://schema.org",
    "@type": "NewsMediaOrganization",
    "name": "A Nevasca",
    "url": BASE,
    "logo": f"{BASE}/og.png",
    "sameAs": ["https://x.com/anevasca_br"],
}, ensure_ascii=False).replace("<", "\\u003c")

WEBSITE_SCHEMA = json.dumps({
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "A Nevasca",
    "url": BASE,
}, ensure_ascii=False).replace("<", "\\u003c")


def capa_estatica(ed):
    items = list(artigos(ed))
    esquerda = []
    grupos = {"Política": [], "Mundo": [], "Cultura & Games": []}
    editorial = ""
    centro = ""
    for pid, titulo, desc, _, rotulo, artigo in items:
        link = f'<a href="/m/{e(pid)}.html">{e(titulo)}</a>'
        if pid.endswith("-manchete"):
            texto = "".join(f'<p>{e(p)}</p>' for p in artigo["texto"][:3])
            centro = (f'<article class="manchete"><p class="kicker">{e(artigo.get("secao"))}</p>'
                      f'<h1>{link}</h1><p class="fina">{e(desc)}</p>{figura(artigo.get("imagem"))}'
                      f'<div class="texto">{texto}</div></article>')
        elif pid.endswith("-editorial"):
            editorial = (f'<aside class="editorial"><div class="selo"><span>Editorial</span>'
                         f'<em>Opinião do jornal</em></div><h2>{link}</h2><p>{e(desc)}</p></aside>')
        elif "-destaque-" in pid:
            esquerda.append(f'<article class="destaque"><p class="kicker azul">{e(artigo.get("secao"))}</p>'
                            f'<h2>{link}</h2><p>{e(desc)}</p></article>')
        else:
            grupo = "Política" if "-politica-" in pid else "Mundo" if "-mundo-" in pid else "Cultura & Games"
            grupos[grupo].append(f'<article><p class="kicker azul">{e(artigo.get("secao"))}</p>'
                                 f'<h4>{link}</h4><p>{e(desc)}</p></article>')
    grades = "".join(f'<section class="secao"><h3>{e(nome)}</h3><div class="grade4">{"".join(cards)}</div></section>'
                     for nome, cards in grupos.items() if cards)
    ultimas = ultimas_estatico(ed["data"])
    return (f'<section class="capa"><div class="col">{"".join(esquerda)}</div>'
            f'<div class="col centro">{centro}</div><div class="col">{editorial}</div></section>'
            f'{ultimas}{grades}')


LISTA_ARQUIVO = re.compile(r'(<div id="lista-arquivo">).*?(</div>)', re.S)
# index.html é lido como molde E é o próprio arquivo que build.py escreve de
# volta (a home). Por isso o que só vale pra home (o JSON-LD abaixo) precisa
# ser removido antes de reler o arquivo, senão duplica a cada rodada.
SCHEMA_HOME = re.compile(
    r'<script type="application/ld\+json">\{"@context": "https://schema\.org", '
    r'"@type": "(?:NewsMediaOrganization|WebSite)".*?</script>\n?', re.S)


def main():
    os.makedirs("m", exist_ok=True)
    urls = [BASE + "/"]
    n = 0
    index = Path("index.html")
    atual = json.loads(Path("edicao.json").read_text(encoding="utf-8"))
    bruto = SCHEMA_HOME.sub("", index.read_text(encoding="utf-8"))
    # Lista de edições anteriores no rodapé: links reais (não #hash), para quem
    # não executa JavaScript. Vale para a home e para toda página de matéria
    # (o rodapé é o mesmo em todas, via "template" mais abaixo).
    link_arquivo = arquivo_estatico()
    if link_arquivo:
        bruto = LISTA_ARQUIVO.sub(lambda m: m[1] + link_arquivo + m[2], bruto, count=1)
    template = substituir_conteudo(bruto, LOADING)
    if '<link rel="canonical"' not in template:
        template = template.replace("</head>", f'<link rel="canonical" href="{BASE}/">\n</head>', 1)
    # JSON-LD da organização e do site: só na home, não em cada matéria
    # (cada matéria já tem o próprio NewsArticle, gerado por pagina()).
    # "template" (sem o schema) segue puro pro resto da função, que o reusa
    # como molde de toda página de matéria.
    schema_home = (f'<script type="application/ld+json">{ORG_SCHEMA}</script>\n'
                   f'<script type="application/ld+json">{WEBSITE_SCHEMA}</script>\n</head>')
    template_home = template.replace("</head>", schema_home, 1)
    index.write_text(substituir_conteudo(template_home, capa_estatica(atual)), encoding="utf-8")
    template = template.replace(f'<link rel="canonical" href="{BASE}/">\n', "", 1)
    for f in sorted(glob.glob("edicoes/*.json")):
        ed = json.load(open(f, encoding="utf-8"))
        for item in artigos(ed):
            pid, t, d, img, rot, artigo = item
            img = img or cartao(pid, t.replace("Editorial: ", "", 1), rot, ed["data"])
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(template, pid, t, d, img, artigo, rot, ed["data"]))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    # Matérias publicadas ao longo do dia: ultimas/AAAA-MM-DD.json (lista em ordem de publicação)
    for f in sorted(glob.glob("ultimas/*.json")):
        data = os.path.basename(f)[:-5]
        for i, u in enumerate(json.load(open(f, encoding="utf-8")), 1):
            pid = f"ed-{data}-ultima-{i}"
            d = u.get("resumo") or u.get("linhaFina") or (u.get("texto") or [""])[0]
            img = (u.get("imagem") or {}).get("arquivo") or cartao(pid, u["titulo"], "Últimas notícias · " + u.get("secao", ""), data)
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(template, pid, u["titulo"], d, img, u, "Últimas notícias · " + u.get("secao", ""), data))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    if os.path.exists("colunas.json"):
        for c in json.load(open("colunas.json", encoding="utf-8")):
            pid = "coluna-" + c["id"]
            t = f"{c['titulo']} — Doido Neves"
            d = c.get("linhaFina") or (c.get("texto") or [""])[0]
            img = cartao(pid, c["titulo"], "O Doido Sensato · Doido Neves", c.get("data", ""))
            open(f"m/{pid}.html", "w", encoding="utf-8").write(pagina(template, pid, t, d, img, c, "O Doido Sensato · Opinião", c.get("data", "")))
            urls.append(f"{BASE}/m/{pid}.html"); n += 1
    # Apaga cartões que nenhuma página usa mais (títulos corrigidos)
    for f in glob.glob("cartoes/*.jpg"):
        if Path(f).as_posix() not in USADOS:
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
