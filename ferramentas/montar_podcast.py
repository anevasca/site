"""Monta o episódio do podcast "Nevasca em 10 minutos" gravado por Junior e Maressa.

Dois jeitos:

1) Uma gravação só, com os dois lendo juntos:
   python3 ferramentas/montar_podcast.py <gravação> AAAA-MM-DD [saída.mp3]

2) Cada um grava o seu texto separado (roteiro-AAAA-MM-DD-junior.txt e -maressa.txt, gerados por
   ferramentas/roteiro_podcast.py), com 3 s de silêncio entre os blocos e 8 s antes de repetir um bloco errado:
   python3 ferramentas/montar_podcast.py --separado <gravação do Junior> <gravação da Maressa> \
           roteiro-AAAA-MM-DD.json AAAA-MM-DD [saída.mp3]
   O script corta cada gravação nos silêncios, joga fora os trechos repetidos, confere se o número de
   blocos bate com o roteiro e intercala os blocos na ordem do roteiro.

Nos dois casos: limpa ruído, nivela o volume (cada voz separada, no modo 2) e põe a vinheta
(trilha/abertura.mp3 antes, trilha/encerramento.mp3 depois). Se algo não bater, NÃO monta e explica.
"""
import json, os, re, shutil, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
TRILHA_AB = os.path.join(AQUI, "..", "trilha", "abertura.mp3")
TRILHA_FIM = os.path.join(AQUI, "..", "trilha", "encerramento.mp3")
SR = "44100"
LIMPA = "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=10:release=200:makeup=2"
NIVELA = "loudnorm=I=-16:TP=-1.5:LRA=9"
SEPARADOR_MIN = 1.6   # silêncio a partir disto separa blocos (pedimos 3 s)
REFAZER_MIN = 5.5     # silêncio a partir disto = "errei, vou repetir" (pedimos 8 s)


def ff(*args):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def dur(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def silencio(seg, destino):
    ff("-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", str(seg), destino)


def prepara(src, destino):
    """Converte para WAV mono, limpa e nivela a voz."""
    ff("-i", src, "-af", f"{LIMPA},{NIVELA}", "-ac", "1", "-ar", SR, destino)


def silencios(wav, ruido, minimo):
    r = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=n={ruido}dB:d={minimo}", "-f", "null", "-"],
                       capture_output=True, text=True)
    ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    fim = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    total = dur(wav)
    if len(fim) < len(ini):
        fim.append(total)
    return list(zip(ini, fim)), total


def corta(wav, ruido, minimo):
    """Lista de trechos de fala (início, fim), já sem os trechos refeitos."""
    sil, total = silencios(wav, ruido, minimo)
    trechos, cursor, descartados = [], 0.0, 0
    for a, b in sil:
        if a - cursor > 0.25:                       # houve fala antes deste silêncio
            trechos.append([cursor, a])
            if b - a >= REFAZER_MIN:                # silêncio longo: o trecho anterior foi um erro
                trechos.pop(); descartados += 1
        cursor = b
    if total - cursor > 0.25:
        trechos.append([cursor, total])
    return trechos, descartados


def melhor_corte(wav, esperado):
    tentativas = []
    for ruido in (-35, -40, -30, -45):
        for minimo in (SEPARADOR_MIN, 1.3, 2.0, 2.5):
            t, desc = corta(wav, ruido, minimo)
            tentativas.append((ruido, minimo, len(t)))
            if len(t) == esperado:
                return t, desc, (ruido, minimo)
    return None, 0, tentativas


def separado(grav_j, grav_m, roteiro_json, data, saida, pendentes=""):
    """grav_j/grav_m: um arquivo, ou "principal,extra" quando alguns blocos (pendentes) foram gravados depois.
    pendentes: ex. "maressa:2,junior:4" = blocos que estão no arquivo extra, não no principal."""
    ordem = json.load(open(roteiro_json, encoding="utf-8"))
    pend = {tuple(x.split(":")) for x in pendentes.split(",") if x}
    tmp = tempfile.mkdtemp()
    blocos, avisos = {}, []
    tarefas = []
    for quem, grav in (("junior", grav_j), ("maressa", grav_m)):
        meus = [b for b in ordem if b["quem"] == quem]
        arquivos = grav.split(",")
        depois = [b for b in meus if (quem, str(b["n"])) in pend]
        if depois and len(arquivos) < 2:
            raise SystemExit(f"NÃO MONTEI: faltou a gravação dos blocos refeitos de {quem.capitalize()} "
                             f"({', '.join(str(b['n']) for b in depois)}).")
        tarefas.append((quem, arquivos[0], [b for b in meus if b not in depois], "gravação principal"))
        if depois:
            tarefas.append((quem, arquivos[1], depois, "gravação dos blocos refeitos"))
    for k, (quem, grav, meus, nome) in enumerate(tarefas):
        wav = f"{tmp}/{quem}-{k}.wav"
        prepara(grav, wav)
        trechos, desc, info = melhor_corte(wav, len(meus))
        if trechos is None:
            achados = sorted({n for _, _, n in info})
            raise SystemExit(f"NÃO MONTEI: na {nome} de {quem.capitalize()} achei {achados} blocos, "
                             f"mas deviam ser {len(meus)}. Provavelmente faltou ou sobrou uma pausa de 3 s "
                             f"entre blocos, ou um bloco ficou de fora. Peça para regravar ou dizer qual bloco ficou faltando.")
        if desc:
            avisos.append(f"{quem.capitalize()}: {desc} trecho(s) repetido(s) descartado(s) (pausa de 8 s).")
        for b, (a, z) in zip(meus, trechos):
            arq = f"{tmp}/{quem}-{b['n']:02d}.wav"
            ini, fim = max(0, a - 0.08), z + 0.12      # folga para não cortar a respiração/final da palavra
            ff("-i", wav, "-ss", f"{ini:.3f}", "-to", f"{fim:.3f}",
               "-af", "afade=t=in:d=0.03,areverse,afade=t=in:d=0.05,areverse", arq)
            palavras = len(b["texto"].split())
            seg_por_palavra = (fim - ini) / max(palavras, 1)
            if not 0.22 <= seg_por_palavra <= 0.75:
                avisos.append(f"{quem.capitalize()} bloco {b['n']}: {fim - ini:.1f} s para {palavras} palavras "
                              f"(confira se o corte pegou o bloco certo).")
            blocos[(quem, b["n"])] = arq
    pausa, abre, fecha = f"{tmp}/pausa.wav", f"{tmp}/abre.wav", f"{tmp}/fecha.wav"
    silencio(0.45, pausa); silencio(0.6, f"{tmp}/p_ab.wav"); silencio(0.8, f"{tmp}/p_fim.wav")
    partes = []
    if os.path.exists(TRILHA_AB):
        ff("-i", TRILHA_AB, "-ac", "1", "-ar", SR, abre); partes += [abre, f"{tmp}/p_ab.wav"]
    for i, b in enumerate(ordem):
        partes.append(blocos[(b["quem"], b["n"])])
        if i < len(ordem) - 1:
            partes.append(pausa)
    if os.path.exists(TRILHA_FIM):
        ff("-i", TRILHA_FIM, "-ac", "1", "-ar", SR, fecha); partes += [f"{tmp}/p_fim.wav", fecha]
    junta(partes, saida, tmp)
    for a in avisos:
        print("AVISO:", a)
    shutil.rmtree(tmp, ignore_errors=True)


def junta(partes, saida, tmp):
    lista = f"{tmp}/lista.txt"
    open(lista, "w").write("".join(f"file '{p}'\n" for p in partes))
    ff("-f", "concat", "-safe", "0", "-i", lista, "-ac", "1", "-ar", SR, "-b:a", "96k", saida)
    print(f"{saida}: {dur(saida) / 60:.1f} min")


def unico(grav, data, saida):
    tmp = tempfile.mkdtemp()
    voz = f"{tmp}/voz.wav"
    ff("-i", grav, "-af", f"{LIMPA},silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.2,"
       f"areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.3,areverse,{NIVELA}",
       "-ac", "1", "-ar", SR, voz)
    partes = []
    if os.path.exists(TRILHA_AB):
        ff("-i", TRILHA_AB, "-ac", "1", "-ar", SR, f"{tmp}/abre.wav"); silencio(0.5, f"{tmp}/p1.wav")
        partes += [f"{tmp}/abre.wav", f"{tmp}/p1.wav"]
    partes.append(voz)
    if os.path.exists(TRILHA_FIM):
        ff("-i", TRILHA_FIM, "-ac", "1", "-ar", SR, f"{tmp}/fecha.wav"); silencio(0.7, f"{tmp}/p2.wav")
        partes += [f"{tmp}/p2.wav", f"{tmp}/fecha.wav"]
    junta(partes, saida, tmp)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--separado":
        pend = ""
        if "--pendentes" in a:
            i = a.index("--pendentes"); pend = a[i + 1]; a = a[:i] + a[i + 2:]
        _, gj, gm, rot, data, *resto = a
        separado(gj, gm, rot, data, resto[0] if resto else f"pod-{data}.mp3", pend)
    else:
        grav, data, *resto = a
        unico(grav, data, resto[0] if resto else f"pod-{data}.mp3")
