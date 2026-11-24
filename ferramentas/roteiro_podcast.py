"""Roteiro do podcast "Nevasca em 10 minutos" separado por apresentador.

Gera, a partir do edicao.json (e do colunas.json):
  roteiro-AAAA-MM-DD-junior.txt   só os blocos do Junior, numerados, na ordem
  roteiro-AAAA-MM-DD-maressa.txt  só os blocos da Maressa, numerados, na ordem
  roteiro-AAAA-MM-DD.json         a ordem completa [{"quem","n","texto"}], usada na montagem
Mesma lógica da página oculta #roteiro do site (index.html, função roteiroPodcast).
Uso: python3 ferramentas/roteiro_podcast.py [edicao.json] [colunas.json] [pasta de saída] [pendentes]
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
    R = roteiro(ed, cols)
    data = ed["data"]
    d = datetime.date.fromisoformat(data)
    ordem, cont = [], {"JUNIOR": 0, "MARESSA": 0}
    for quem, txt in R:
        cont[quem] += 1
        ordem.append({"quem": quem.lower(), "n": cont[quem], "texto": txt})
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
             else f"[{b['n']}]\n{b['texto']}\n") for b in meus)
        txt = (f"NEVASCA EM 10 MINUTOS · {d.day:02d}/{d.month:02d}/{d.year}\n"
               f"TEXTO DE {quem} ({len(meus)} blocos)\n\n{COMO}{aviso}\n" + corpo)
        open(f"{saida}/roteiro-{data}-{quem.lower()}.txt", "w", encoding="utf-8").write(txt)
        print(f"{quem}: {len(meus)} blocos, {sum(len(b['texto'].split()) for b in meus)} palavras")


if __name__ == "__main__":
    main()
