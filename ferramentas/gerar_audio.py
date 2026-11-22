"""Gera o áudio (voz neural) de cada matéria da edição atual e guarda na release "audio" do GitHub.

Roda sozinho no GitHub Actions (.github/workflows/audio.yml). Para cada matéria:
  - monta o texto (título, linha fina e corpo);
  - se o texto mudou desde a última vez (ou se o áudio ainda não existe), gera o MP3
    com a voz pt-BR-FranciscaNeural e envia como <id>.mp3 para a release "audio".
O site toca https://github.com/<repo>/releases/download/audio/<id>.mp3 e, se não houver
áudio, usa a voz do próprio aparelho do leitor.
"""
import asyncio, hashlib, json, os, re, subprocess, sys

VOZ = "pt-BR-FranciscaNeural"
TAG = "audio"
REPO = os.environ.get("GITHUB_REPOSITORY", "anevasca/site")
PASTA = "/tmp/audios"


def gh(*args, check=True):
    return subprocess.run(["gh", *args, "--repo", REPO], check=check, capture_output=True, text=True)


def limpa(t):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t


def itens():
    ed = json.load(open("edicao.json", encoding="utf-8"))
    pre = f"ed-{ed['data']}-"
    L = []
    m, e = ed["manchete"], ed["editorial"]
    L.append((pre + "manchete", [m["titulo"], m.get("linhaFina")] + m.get("texto", [])))
    for chave, nome in (("politica", "politica"), ("destaques", "destaque"), ("mundo", "mundo"), ("cultura", "cultura")):
        for i, a in enumerate(ed.get(chave, []), 1):
            L.append((f"{pre}{nome}-{i}", [a["titulo"], a.get("linhaFina")] + (a.get("texto") or [a.get("resumo")])))
    L.append((pre + "editorial", ["Editorial. " + e["titulo"]] + e.get("texto", [])))
    arq = f"ultimas/{ed['data']}.json"
    if os.path.exists(arq):
        for i, u in enumerate(json.load(open(arq, encoding="utf-8")), 1):
            L.append((f"{pre}ultima-{i}", [u["titulo"], u.get("linhaFina")] + (u.get("texto") or [u.get("resumo")])))
    out = []
    for pid, partes in L:
        txt = " ".join(p if re.search(r"[.!?…:]$", p) else p + "." for p in (limpa(x) for x in partes) if p)
        out.append((pid, txt))
    return out


async def falar(texto, destino):
    import edge_tts
    await edge_tts.Communicate(texto, VOZ, rate="+0%").save(destino)


def main():
    os.makedirs(PASTA, exist_ok=True)
    if gh("release", "view", TAG, check=False).returncode != 0:
        gh("release", "create", TAG, "--title", "Áudios das matérias",
           "--notes", "Áudios gerados automaticamente para o botão Ouvir notícia do site. Não apague.", "--latest=false")
    marcas = {}
    if gh("release", "download", TAG, "-p", "marcas.json", "-D", PASTA, "--clobber", check=False).returncode == 0:
        try:
            marcas = json.load(open(f"{PASTA}/marcas.json", encoding="utf-8"))
        except Exception:
            marcas = {}
    feitos = 0
    for pid, txt in itens():
        h = hashlib.sha1((VOZ + "|" + txt).encode("utf-8")).hexdigest()[:12]
        if marcas.get(pid) == h:
            continue
        mp3 = f"{PASTA}/{pid}.mp3"
        for tentativa in range(3):
            try:
                asyncio.run(falar(txt, mp3))
                break
            except Exception as ex:
                print("falhou", pid, ex, file=sys.stderr)
        else:
            continue
        gh("release", "upload", TAG, mp3, "--clobber")
        marcas[pid] = h
        feitos += 1
        print("áudio:", pid)
    json.dump(marcas, open(f"{PASTA}/marcas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    gh("release", "upload", TAG, f"{PASTA}/marcas.json", "--clobber")
    print(f"{feitos} áudio(s) novo(s)")


if __name__ == "__main__":
    main()
