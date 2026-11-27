#!/usr/bin/env python3
"""
Coleta candidatas a pauta dos feeds RSS em fontes_rss.json e grava o
resultado em pauta/candidatas-AAAA-MM-DD.json.

Isso substitui a pesquisa que a IA fazia do zero na rotina das 6h43: a IA
só escolhe e redige a partir da lista pronta, em vez de buscar na web.

Não trava nada: se uma fonte falhar (fora do ar, bloqueou o robô, XML
quebrado), o script avisa e segue com as outras. Só falha de verdade (sai
com código 1) se NENHUMA fonte respondeu.

Uso:
    python3 ferramentas/coletar_pauta.py [--horas 20] [--data AAAA-MM-DD]

--horas: só guarda itens publicados nas últimas N horas (padrão: 20,
         pensado para cobrir desde a rotina do dia anterior). Item sem
         data reconhecida entra mesmo assim, marcado como tal.
--data:  nome do arquivo de saída; padrão é a data de hoje em
         America/Sao_Paulo.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "ferramentas" / "fontes_rss.json"
PASTA_SAIDA = RAIZ / "pauta"

USER_AGENT = "Mozilla/5.0 (compatible; ANevascaColetorDePauta/1.0; +https://anevasca.com.br)"
TIMEOUT_SEGUNDOS = 20
FUSO_BR = timezone(timedelta(hours=-3))


def buscar_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SEGUNDOS) as resp:
        return resp.read()


_TAG_HTML = re.compile(r"<[^>]+>")


def texto_simples(html, limite=300):
    if not html:
        return ""
    t = _TAG_HTML.sub(" ", html)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limite]


def parsear_data(valor):
    if not valor:
        return None
    try:
        return parsedate_to_datetime(valor)
    except (TypeError, ValueError):
        return None


def extrair_itens_elementtree(conteudo):
    raiz = ElementTree.fromstring(conteudo)
    itens = []
    # RSS 2.0: rss/channel/item ; Atom: feed/entry
    for item in raiz.iter():
        tag = item.tag.split("}")[-1]  # ignora namespace
        if tag not in ("item", "entry"):
            continue
        titulo = link = pub = desc = None
        for filho in item:
            ftag = filho.tag.split("}")[-1]
            if ftag == "title" and titulo is None:
                titulo = (filho.text or "").strip()
            elif ftag == "link" and link is None:
                link = (filho.text or filho.get("href") or "").strip()
            elif ftag in ("pubDate", "published", "updated") and pub is None:
                pub = (filho.text or "").strip()
            elif ftag in ("description", "summary") and desc is None:
                desc = filho.text or ""
        if titulo:
            itens.append({"titulo": titulo, "link": link, "pub_raw": pub, "resumo": texto_simples(desc)})
    return itens


_ITEM_BLOCO = re.compile(r"<item\b.*?</item>", re.DOTALL | re.IGNORECASE)
_CAMPO = {
    "titulo": re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE),
    "link": re.compile(r"<link[^>]*>(.*?)</link>", re.DOTALL | re.IGNORECASE),
    "pub_raw": re.compile(r"<pubDate[^>]*>(.*?)</pubDate>", re.DOTALL | re.IGNORECASE),
    "resumo": re.compile(r"<description[^>]*>(.*?)</description>", re.DOTALL | re.IGNORECASE),
}


def extrair_itens_regex(conteudo_texto):
    """Reserva para quando o XML não é bem formado (tag solta, HTML cru sem CDATA)."""
    itens = []
    for bloco in _ITEM_BLOCO.findall(conteudo_texto):
        valores = {}
        for campo, padrao in _CAMPO.items():
            m = padrao.search(bloco)
            valores[campo] = m.group(1).strip() if m else None
        if valores.get("titulo"):
            valores["titulo"] = texto_simples(valores["titulo"], limite=500)
            valores["resumo"] = texto_simples(valores.get("resumo"))
            itens.append(valores)
    return itens


def coletar_fonte(fonte, avisos):
    nome, url = fonte["nome"], fonte["url"]
    try:
        bruto = buscar_feed(url)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        avisos.append(f"{nome}: não deu para buscar ({e})")
        return []

    try:
        itens = extrair_itens_elementtree(bruto)
    except ElementTree.ParseError as e:
        avisos.append(f"{nome}: XML não bem formado, tentando modo tolerante ({e})")
        try:
            itens = extrair_itens_regex(bruto.decode("utf-8", errors="replace"))
        except Exception as e2:
            avisos.append(f"{nome}: falhou também no modo tolerante ({e2})")
            return []

    if not itens:
        avisos.append(f"{nome}: feed respondeu, mas sem itens reconhecíveis")
    return itens


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horas", type=int, default=20)
    ap.add_argument("--data", type=str, default=None)
    args = ap.parse_args()

    agora = datetime.now(FUSO_BR)
    data_saida = args.data or agora.strftime("%Y-%m-%d")
    desde = agora - timedelta(hours=args.horas)

    fontes = json.loads(FONTES.read_text(encoding="utf-8"))
    avisos = []
    candidatas = []
    fontes_ok = 0

    for fonte in fontes:
        itens = coletar_fonte(fonte, avisos)
        if itens:
            fontes_ok += 1
        for item in itens:
            pub = parsear_data(item.get("pub_raw"))
            if pub is not None:
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=FUSO_BR)
                if pub < desde:
                    continue
            candidatas.append({
                "fonte": fonte["nome"],
                "prioridade": fonte.get("prioridade", 9),
                "titulo": item["titulo"],
                "link": item.get("link"),
                "resumo": item.get("resumo") or "",
                "publicado_em": pub.isoformat() if pub else None,
            })

    # remove duplicados (mesmo link, ou mesmo título normalizado)
    vistos = set()
    unicas = []
    for c in candidatas:
        chave = (c["link"] or "") or c["titulo"].strip().lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        unicas.append(c)

    unicas.sort(key=lambda c: (c["prioridade"], c["publicado_em"] or ""))

    PASTA_SAIDA.mkdir(exist_ok=True)
    saida = PASTA_SAIDA / f"candidatas-{data_saida}.json"
    saida.write_text(
        json.dumps({
            "gerado_em": agora.isoformat(),
            "janela_horas": args.horas,
            "avisos": avisos,
            "candidatas": unicas,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        caminho_exibido = saida.relative_to(RAIZ)
    except ValueError:
        caminho_exibido = saida
    print(f"{fontes_ok}/{len(fontes)} fonte(s) responderam. {len(unicas)} candidata(s) salvas em {caminho_exibido}.")
    if avisos:
        print("Avisos:")
        for a in avisos:
            print(f"  - {a}")

    if fontes_ok == 0:
        print("Nenhuma fonte respondeu. Nada travado, mas a lista de hoje está vazia — "
              "a rotina precisa pesquisar por conta própria.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
