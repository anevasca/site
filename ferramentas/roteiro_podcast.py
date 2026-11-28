"""Roteiro do podcast "Nevasca em 10 minutos" separado por apresentador.

Gera, a partir do edicao.json (e do colunas.json):
  roteiro-AAAA-MM-DD-junior.txt   só os blocos do Junior, numerados, na ordem
  roteiro-AAAA-MM-DD-maressa.txt  só os blocos da Maressa, numerados, na ordem
  roteiro-AAAA-MM-DD.json         a ordem completa [{"quem","n","texto"}], usada na montagem
Mesma lógica da página oculta #roteiro do site (index.html, função roteiroPodcast).
Uso: python3 ferramentas/roteiro_podcast.py [edicao.json] [colunas.json] [pasta de saída] [pendentes] [roteiro escrito]
Se existir podcast/roteiro-AAAA-MM-DD.json (ao lado do edicao.json), usa esse roteiro escrito para ouvir (formato novo):
{"data":"AAAA-MM-DD","blocos":[{"quem":"maressa","texto":"..."},{"quem":"junior","tipo":"comentario","tema":"...","pontos":["..."]}]}
Sem ele, monta o roteiro antigo a partir dos títulos e resumos.
pendentes (opcional), ex.: "maressa:2,junior:4" = blocos que ainda vão mudar (ex.: esperando uma votação).
Eles saem marcados para PULAR agora e gravar depois num arquivo à parte.
"""
import datetime, json, os, re, sys

DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]
NOMES = {"JUNIOR": "Junior", "MARESSA": "Maressa"}


def pontua(t):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if not t or re.search(r"[.!?…:]$", t) else t + "."


def deixa_final(txt, livre=False):
    """A deixa é o FIM da fala do outro (a última ou as duas últimas frases), nunca um pedaço cortado."""
    if livre:
        return "(comentário livre, sem texto fixo) entre quando ele terminar a opinião."
    frases = re.split(r"(?<=[.!?…])\s+", txt.strip())
    sel, n = [], 0
    for f in reversed(frases):
        w = len(f.split())
        if sel and n + w > 40:
            break
        sel.insert(0, f)
        n += w
        if n >= 12:
            break
    fim = " ".join(sel)
    return ("… " if len(sel) < len(frases) else "") + fim


def roteiro(ed, colunas):
    d = datetime.date.fromisoformat(ed["data"])
    quando = f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]}"
    M, J, R = "MARESSA", "JUNIOR", []
    m = ed.get("manchete") or {}
    outras = ed.get("politica", []) + ed.get("destaques", []) + ed.get("mundo", []) + ed.get("cultura", [])
    R.append((M, f"Bom dia. Hoje é {quando}. Este é o Nevasca em 10 minutos, o resumo do dia do jornal A Nevasca. Eu sou Maressa Neves."))
    R.append((J, "E eu sou Junior Neves. Os destaques desta edição."))
    for i, t in enumerate([m.get("titulo")] + [x["titulo"] for x in outras[:4]]):
        R.append((J if i % 2 else M, pontua(t)))
    R.append((J, "A manchete. " + pontua(m.get("titulo")) + " " +
              pontua(m.get("resumo") or m.get("linhaFina") or (m.get("texto") or [""])[0])))
    vez = 1
    for abertura, itens in (("Em Brasília.", ed.get("politica")), ("Na economia.", ed.get("destaques")),
                            ("No mundo.", ed.get("mundo")), ("Cultura e games.", ed.get("cultura"))):
        for j, a in enumerate(itens or []):
            quem = M if vez % 2 else J
            vez += 1
            R.append((quem, (abertura + " " if j == 0 else "") + pontua(a["titulo"]) + " " +
                      pontua(a.get("resumo") or (a.get("texto") or [""])[0])))
    col = next((c for c in colunas or [] if c.get("data") == ed["data"]), None)
    if col:
        R.append((M, "E agora, a coluna O Doido Sensato, por Doido Neves: " + pontua(col["titulo"])))
        texto = col.get("texto") or []
        R.append((J, " ".join(pontua(p) for p in (texto if isinstance(texto, list) else [texto]))))
    R.append((M, "Este foi o Nevasca em 10 minutos. As matérias completas, com todas as fontes, estão em anevasca.com.br."))
    R.append((J, "Até amanhã."))
    return R


COMO = ("COMO GRAVAR\n"
        "- Grave tudo num arquivo só, na ordem dos blocos, no celular, num cômodo silencioso.\n"
        "- Entre um bloco e outro, fique 3 SEGUNDOS EM SILÊNCIO (conte até 3 de cabeça). É assim que eu separo os blocos.\n"
        "- Errou? Pare, fique 8 SEGUNDOS EM SILÊNCIO e leia o bloco de novo desde o começo. Eu jogo fora o trecho errado.\n"
        "- Não fale o número do bloco nem comente entre os blocos.\n"
        "- Quando terminar, mande o arquivo na mesma conversa em que recebeu este texto, dizendo de quem é (ex.: 'gravação da Maressa').\n")


def pdf(destino, titulo, quem, blocos, pend):
    """PDF de leitura: letra grande, um bloco por vez, marcação da pausa."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.colors import HexColor
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether, Table, TableStyle
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
    except ImportError:
        return False
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fontes")
    pdfmetrics.registerFont(TTFont("Franklin", os.path.join(f, "LibreFranklin-Medium.ttf")))
    pdfmetrics.registerFont(TTFont("FranklinB", os.path.join(f, "LibreFranklin-Bold.ttf")))
    pdfmetrics.registerFontFamily("Franklin", normal="Franklin", bold="FranklinB", italic="Franklin", boldItalic="FranklinB")
    cor = HexColor("#7a1f1f") if quem == "MARESSA" else HexColor("#1b2a41")
    corpo = ParagraphStyle("c", fontName="Franklin", fontSize=22, leading=33, textColor=HexColor("#121212"))
    cab = ParagraphStyle("h", fontName="FranklinB", fontSize=16, leading=20, textColor=cor, spaceAfter=6)
    pausa = ParagraphStyle("p", fontName="FranklinB", fontSize=13, leading=16, textColor=HexColor("#8a8a8a"), spaceBefore=8)
    topo = ParagraphStyle("t", fontName="FranklinB", fontSize=26, leading=30, textColor=cor)
    dica = ParagraphStyle("d", fontName="Franklin", fontSize=15, leading=21, textColor=HexColor("#333333"))
    deixa = ParagraphStyle("x", fontName="Franklin", fontSize=13, leading=17, textColor=HexColor("#8a8a8a"), spaceAfter=4)
    el = [Paragraph(titulo, topo), Spacer(1, 4 * mm),
          Paragraph("Entre um bloco e outro: <b>3 segundos de silêncio</b>. Errou: <b>8 segundos de silêncio</b> e repita o bloco. "
                    "Ou grave <b>um áudio para cada bloco</b> (errou, apaga e grava de novo).", dica), Spacer(1, 8 * mm)]
    for b in blocos:
        if b in pend:
            t = Table([[Paragraph(f"BLOCO {b['n']} — PULE AGORA (muda depois da votação)", cab)]], colWidths=[170 * mm])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), HexColor("#eeeeee")), ("BOX", (0, 0), (-1, -1), 1, HexColor("#bbbbbb")),
                                   ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
            el += [t, Spacer(1, 10 * mm)]
            continue
        if b.get("livre"):
            t = Table([[Paragraph(f"BLOCO {b['n']} — COMENTÁRIO LIVRE (opinião, com as suas palavras)", cab)],
                       [Paragraph(b["texto"].split("] ", 1)[-1].replace("; ", "<br/>• ").replace("Pontos: ", "<br/>• "), dica)]],
                      colWidths=[170 * mm])
            t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.5, cor), ("TOPPADDING", (0, 0), (-1, -1), 8),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
            el += [KeepTogether([t, Paragraph("— pausa de 3 segundos —", pausa)]), Spacer(1, 10 * mm)]
            continue
        antes = [Paragraph("Deixa — " + b["antes"], deixa)] if b.get("antes") else []
        el.append(KeepTogether(antes + [Paragraph(f"BLOCO {b['n']}", cab), Paragraph(b["texto"], corpo),
                                Paragraph("— pausa de 3 segundos —", pausa)]))
        el.append(Spacer(1, 10 * mm))
    SimpleDocTemplate(destino, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=titulo).build(el)
    return True


def main():
    ed_path = sys.argv[1] if len(sys.argv) > 1 else "edicao.json"
    col_path = sys.argv[2] if len(sys.argv) > 2 else "colunas.json"
    saida = sys.argv[3] if len(sys.argv) > 3 else "."
    pend = {tuple(x.split(":")) for x in (sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] else [])}
    ed = json.load(open(ed_path, encoding="utf-8"))
    try:
        cols = json.load(open(col_path, encoding="utf-8"))
    except Exception:
        cols = []
    data = ed["data"]
    escrito = os.path.join(os.path.dirname(os.path.abspath(ed_path)), "podcast", f"roteiro-{data}.json")
    if len(sys.argv) > 5:
        escrito = sys.argv[5]
    livres = set()
    if os.path.exists(escrito):
        # FORMATO NOVO (desde 24/11/2026): roteiro escrito para ouvir, com "Para entender" e "Comentário do Doido"
        blocos = json.load(open(escrito, encoding="utf-8"))["blocos"]
        R = []
        for i, b in enumerate(blocos):
            quem = b["quem"].upper()
            if b.get("tipo") == "comentario":
                pontos = "; ".join(b.get("pontos", []))
                R.append((quem, f"[COMENTÁRIO LIVRE — fale com as suas palavras, 1 a 2 minutos] Tema: {b.get('tema','')}. Pontos: {pontos}"))
                livres.add(i)
            else:
                R.append((quem, b["texto"]))
    else:
        R = roteiro(ed, cols)
    d = datetime.date.fromisoformat(data)
    ordem, cont = [], {"JUNIOR": 0, "MARESSA": 0}
    for i, (quem, txt) in enumerate(R):
        cont[quem] += 1
        item = {"quem": quem.lower(), "n": cont[quem], "texto": txt}
        if i in livres:
            item["livre"] = True
        if i > 0 and R[i - 1][0] != quem:
            item["antes"] = f"{R[i - 1][0].capitalize()}: {deixa_final(R[i - 1][1], (i - 1) in livres)}"
        ordem.append(item)
    os.makedirs(saida, exist_ok=True)
    json.dump(ordem, open(f"{saida}/roteiro-{data}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for quem in ("JUNIOR", "MARESSA"):
        meus = [b for b in ordem if b["quem"] == quem.lower()]
        meus_pend = [b for b in meus if (b["quem"], str(b["n"])) in pend]
        aviso = ""
        if meus_pend:
            aviso = (f"\nATENÇÃO: o(s) bloco(s) {', '.join(str(b['n']) for b in meus_pend)} ainda vai(ão) mudar. PULE agora "
                     f"(grave os outros {len(meus) - len(meus_pend)} em sequência, com os 3 s entre eles). "
                     "Depois eu mando o texto novo e você grava só ele(s) num arquivo à parte.\n")
        corpo = "\n".join(
            (f"[{b['n']}]  ⏳ PULE ESTE BLOCO AGORA (muda depois da votação)\n" if b in meus_pend
             else (f"(deixa — {b['antes']})\n" if b.get("antes") else "") + f"[{b['n']}]\n{b['texto']}\n") for b in meus)
        txt = (f"NEVASCA EM 10 MINUTOS · {d.day:02d}/{d.month:02d}/{d.year}\n"
               f"TEXTO DE {quem} ({len(meus)} blocos)\n\n{COMO}{aviso}\n" + corpo)
        open(f"{saida}/roteiro-{data}-{quem.lower()}.txt", "w", encoding="utf-8").write(txt)
        pdf(f"{saida}/Podcast {d.day:02d}-{d.month:02d} - {quem}.pdf",
            f"Nevasca em 10 minutos · {d.day:02d}/{d.month:02d} · {quem.capitalize()}", quem, meus, meus_pend)
        print(f"{quem}: {len(meus)} blocos, {sum(len(b['texto'].split()) for b in meus)} palavras")


if __name__ == "__main__":
    main()
