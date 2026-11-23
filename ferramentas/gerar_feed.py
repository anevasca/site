"""Gera _site/podcast.xml (feed RSS do podcast "Nevasca em 10 minutos") a partir dos
episódios pod-AAAA-MM-DD.mp3 que já estão em _site/audio/. Cadastre este feed uma vez
no Spotify e no Apple Podcasts: https://anevasca.com.br/podcast.xml"""
import datetime, email.utils, glob, html, json, os, subprocess, sys

BASE = "https://anevasca.com.br"
site = sys.argv[1] if len(sys.argv) > 1 else "_site"
DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def dur(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                       capture_output=True, text=True)
    s = int(float(r.stdout.strip() or 0))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def edicao(data):
    for p in (f"{site}/edicoes/{data}.json", f"edicoes/{data}.json"):
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return None


e = lambda t: html.escape(str(t or ""), quote=True)
itens = []
for arq in sorted(glob.glob(f"{site}/audio/pod-*.mp3"), reverse=True)[:120]:
    data = os.path.basename(arq)[4:14]
    d = datetime.date.fromisoformat(data)
    ed = edicao(data) or {}
    man = (ed.get("manchete") or {}).get("titulo", "")
    outros = [x["titulo"] for k in ("politica", "destaques", "mundo", "cultura") for x in ed.get(k, [])][:5]
    desc = (f"Manchete: {man}. " if man else "") + ("Também: " + "; ".join(outros) + ". " if outros else "") + \
           f"Matérias completas, com fontes: {BASE}/#ed-{data}"
    quando = email.utils.format_datetime(datetime.datetime(d.year, d.month, d.day, 5, 0,
                                                           tzinfo=datetime.timezone(datetime.timedelta(hours=-3))))
    titulo = f"{DIAS[d.weekday()]}, {d.day:02d}/{d.month:02d}/{d.year}" + (f" — {man}" if man else "")
    itens.append(f"""    <item>
      <title>{e(titulo)}</title>
      <description>{e(desc)}</description>
      <link>{BASE}/#ed-{data}</link>
      <guid isPermaLink="false">anevasca-pod-{data}</guid>
      <pubDate>{quando}</pubDate>
      <enclosure url="{BASE}/audio/pod-{data}.mp3?v={os.path.getsize(arq)}" length="{os.path.getsize(arq)}" type="audio/mpeg"/>
      <itunes:duration>{dur(arq)}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:episodeType>full</itunes:episodeType>
    </item>""")

sobre = ("O resumo diário do jornal A Nevasca em cerca de 10 minutos: a manchete, as principais notícias do Brasil e do mundo, "
         "e o editorial, identificado como opinião do jornal. As notícias são checadas em pelo menos dois veículos, com as "
         "fontes no site. As vozes dos apresentadores são sintéticas, geradas por computador. Saiba como fazemos: "
         f"{BASE}/#como-fazemos")
xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Nevasca em 10 minutos</title>
    <link>{BASE}/</link>
    <atom:link href="{BASE}/podcast.xml" rel="self" type="application/rss+xml"/>
    <language>pt-br</language>
    <description>{e(sobre)}</description>
    <itunes:summary>{e(sobre)}</itunes:summary>
    <itunes:author>A Nevasca</itunes:author>
    <itunes:owner><itunes:name>A Nevasca</itunes:name><itunes:email>redacaoanevasca@gmail.com</itunes:email></itunes:owner>
    <itunes:image href="{BASE}/podcast-capa-v2.jpg"/>
    <image><url>{BASE}/podcast-capa-v2.jpg</url><title>Nevasca em 10 minutos</title><link>{BASE}/</link></image>
    <itunes:category text="News"><itunes:category text="Daily News"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{chr(10).join(itens)}
  </channel>
</rss>
"""
open(f"{site}/podcast.xml", "w", encoding="utf-8").write(xml)
print(len(itens), "episódio(s) no feed")
