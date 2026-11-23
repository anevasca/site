"""Podcast diário "Nevasca em 10 minutos".

Monta o episódio da edição atual (edicao.json) com duas vozes de âncora que se revezam
(Antonio e Francisca) e, no editorial, sempre voz masculina: o Antonio um pouco mais grave
(o serviço gratuito só tem uma voz masculina brasileira; a Macerio não responde nele).
Música só na abertura e no encerramento (trilha/abertura.mp3 e trilha/encerramento.mp3,
gerados por ferramentas/trilha.py); nunca por baixo dos textos. Se a coluna
"O Doido Sensato" do dia tiver áudio gravado pelo Junior (audio/coluna-<id>.mp3 no
repositório), ele entra antes do encerramento.

O episódio vai para a release "audio" como pod-AAAA-MM-DD.mp3 e só é refeito se o texto mudar.
Roda no GitHub Actions (.github/workflows/publicar.yml). Uso local para teste:
    python3 ferramentas/gerar_podcast.py --teste   (gera silêncio no lugar das vozes)
"""
import asyncio, datetime, hashlib, json, os, re, subprocess, sys, tempfile

ANCORAS = ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"]  # homem, mulher (vozes originais, velocidade normal)
EDITORIAL = "pt-BR-AntonioNeural#editorial"  # editorial: sempre voz masculina, mais grave
EDITORIAL_RESERVA = "pt-BR-AntonioNeural"
# tom sóbrio: (velocidade, altura) de cada voz
PROSODIA = {}  # velocidade e altura normais: deixar lento deixou as vozes robóticas
VERSAO = "v3-originais"
USAR_TRILHA = False  # liga quando o Junior aprovar a música (trilha/opcoes/)
TAG = "audio"
REPO = os.environ.get("GITHUB_REPOSITORY", "anevasca/site")
TESTE = "--teste" in sys.argv
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def limpa(t):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t if not t or re.search(r"[.!?…:]$", t) else t + "."


def roteiro(ed):
    """Lista de (voz, texto) na ordem do episódio."""
    d = datetime.date.fromisoformat(ed["data"])
    quando = f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]}"
    A, B = ANCORAS
    R = []
    R.append((B, f"Bom dia. Hoje é {quando}. Este é o Nevasca em 10 minutos, o resumo do dia do jornal A Nevasca."))
    m = ed["manchete"]
    outras = (ed.get("politica", []) + ed.get("destaques", []) + ed.get("mundo", []) + ed.get("cultura", []))
    # Escalada: manchete + até 4 títulos, alternando as vozes
    R.append((A, "Os destaques desta edição."))
    for i, t in enumerate([m["titulo"]] + [x["titulo"] for x in outras[:4]]):
        R.append(([A, B][i % 2], limpa(t)))
    # Manchete: título, linha fina e os dois primeiros parágrafos
    R.append((A, "A manchete. " + limpa(m["titulo"])))
    R.append((A, " ".join(limpa(p) for p in [m.get("linhaFina")] + m.get("texto", [])[:2] if p)))
    # Demais matérias: título e resumo, revezando as vozes
    blocos = [("Em Brasília.", ed.get("politica", [])), ("Na economia.", ed.get("destaques", [])),
              ("No mundo.", ed.get("mundo", [])), ("Cultura e games.", ed.get("cultura", []))]
    vez = 1
    for abertura, itens in blocos:
        for j, a in enumerate(itens):
            voz = ANCORAS[vez % 2]; vez += 1
            txt = limpa(a["titulo"]) + " " + limpa(a.get("resumo") or (a.get("texto") or [""])[0])
            R.append((voz, (abertura + " " if j == 0 else "") + txt))
    # Editorial, com outra voz e anunciado como opinião
    e = ed["editorial"]
    R.append((B, "Agora, a opinião do jornal. O editorial do jornal A Nevasca."))
    R.append((EDITORIAL, limpa(e["titulo"]) + " " + " ".join(limpa(p) for p in e.get("texto", []))))
    R.append((B, "Esta foi a opinião do jornal A Nevasca."))
    return R


def coluna_do_dia(ed):
    try:
        cols = json.load(open("colunas.json", encoding="utf-8"))
    except Exception:
        return None
    for c in cols:
        arq = f"audio/coluna-{c.get('id')}.mp3"
        if c.get("data") == ed["data"] and os.path.exists(arq):
            return c, arq
    return None


async def _fala(texto, voz, destino, rate, pitch):
    import edge_tts
    await edge_tts.Communicate(texto, voz, rate=rate, pitch=pitch).save(destino)


def fala(texto, voz, destino):
    if TESTE:
        seg = max(1.0, len(texto) / 15)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                        "-t", f"{seg:.1f}", "-q:a", "9", destino], check=True)
        return
    vozes = [EDITORIAL_RESERVA] if voz == EDITORIAL else [voz]
    for v in vozes:
        rate, pitch = PROSODIA.get(v, ("+0%", "+0Hz"))
        if v == EDITORIAL_RESERVA and voz == EDITORIAL:
            rate, pitch = "+0%", "-4Hz"  # editorial: Antonio um pouco mais grave, na velocidade normal
        for _ in range(3):
            try:
                asyncio.run(_fala(texto, v, destino, rate, pitch)); return
            except Exception as ex:
                print(f"tentando de novo ({v}):", ex, file=sys.stderr)
    raise RuntimeError("não consegui gerar a voz")


def duracao(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def gh(*args, check=True):
    return subprocess.run(["gh", *args, "--repo", REPO], check=check, capture_output=True, text=True)


def main():
    ed = json.load(open("edicao.json", encoding="utf-8"))
    nome = f"pod-{ed['data']}.mp3"
    R = roteiro(ed)
    col = coluna_do_dia(ed)
    assinatura = hashlib.sha1(json.dumps([VERSAO, R, col[1] if col else None], ensure_ascii=False).encode()).hexdigest()[:12]
    marcas = {}
    pasta = tempfile.mkdtemp()
    if not TESTE:
        if gh("release", "download", TAG, "-p", "marcas-podcast.json", "-D", pasta, "--clobber", check=False).returncode == 0:
            try:
                marcas = json.load(open(f"{pasta}/marcas-podcast.json", encoding="utf-8"))
            except Exception:
                marcas = {}
        if marcas.get(nome) == assinatura:
            print("episódio já está em dia:", nome); return
    pausa = f"{pasta}/pausa.mp3"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", "0.7", "-q:a", "9", pausa], check=True)
    trilha_ab, trilha_fim = os.path.abspath("trilha/abertura.mp3"), os.path.abspath("trilha/encerramento.mp3")
    partes = [trilha_ab, pausa] if USAR_TRILHA and os.path.exists(trilha_ab) else []
    for i, (voz, txt) in enumerate(R):
        arq = f"{pasta}/p{i:03d}.mp3"
        fala(txt, voz, arq)
        partes += [arq, pausa]
        if i == len(R) - 1 and col:
            pass
    if col:
        c, arq = col
        apres = f"{pasta}/col.mp3"
        fala(f"E agora, a coluna O Doido Sensato, por Doido Neves: {limpa(c['titulo'])}", ANCORAS[1], apres)
        partes += [apres, pausa, os.path.abspath(arq), pausa]
    fim = f"{pasta}/fim.mp3"
    fala("Este foi o Nevasca em 10 minutos. As matérias completas, com todas as fontes, estão em anevasca ponto com ponto b r. "
         "As vozes dos apresentadores são sintéticas, geradas por computador. Até amanhã.", ANCORAS[1], fim)
    partes.append(fim)
    if USAR_TRILHA and os.path.exists(trilha_fim):
        partes += [pausa, trilha_fim]
    lista = f"{pasta}/lista.txt"
    open(lista, "w").write("".join(f"file '{p}'\n" for p in partes))
    saida = f"{pasta}/{nome}"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista,
                    "-ac", "1", "-ar", "24000", "-b:a", "48k", saida], check=True)
    print(f"episódio {nome}: {duracao(saida) / 60:.1f} min")
    if TESTE:
        os.replace(saida, f"/tmp/{nome}"); print("teste salvo em /tmp/" + nome); return
    gh("release", "upload", TAG, saida, "--clobber")
    marcas[nome] = assinatura
    json.dump(marcas, open(f"{pasta}/marcas-podcast.json", "w", encoding="utf-8"))
    gh("release", "upload", TAG, f"{pasta}/marcas-podcast.json", "--clobber")


if __name__ == "__main__":
    main()
