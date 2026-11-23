"""Trilhas do podcast "Nevasca em 10 minutos" (composição própria, sintetizada por modelagem de corda).

Dois estilos para o editor escolher:
  folk   – violão de aço dedilhado (padrão Travis), em sol maior
  jornal – tema de telejornal: base de cordas e tímpano, com guitarra solando o tema, em ré maior
Saída: trilha/opcoes/<estilo>-abertura.mp3 e <estilo>-encerramento.mp3.
O estilo aprovado é copiado para trilha/abertura.mp3 e trilha/encerramento.mp3.
"""
import os, subprocess, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(11)
NOTAS = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(n):
    return 440.0 * 2 ** ((NOTAS[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def corda(nota, dur, brilho=0.5, sustain=0.996):
    """Karplus-Strong: uma corda beliscada."""
    f = hz(nota); N = int(SR / f); total = int(dur * SR)
    ruido = rng.uniform(-1, 1, N)
    # palheta mais macia = ruído filtrado
    for _ in range(int((1 - brilho) * 4)):
        ruido = (ruido + np.roll(ruido, 1)) / 2
    y = np.zeros(total + N)
    y[:N] = ruido - ruido.mean()  # sem componente contínua
    i = N
    while i < total + N:
        j = min(i + N, total + N)
        prev = y[i - N:j - N]; prev2 = y[i - N - 1:j - N - 1] if i - N - 1 >= 0 else np.concatenate(([0], y[i - N:j - N - 1]))
        y[i:j] = sustain * 0.5 * (prev + prev2[: j - i])
        i = j
    s = y[N:N + total]
    s[: int(0.002 * SR)] *= np.linspace(0, 1, int(0.002 * SR))
    s[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return s


def corpo(x):
    """Ressonância do tampo do violão + sala."""
    out = x.copy()
    for atraso, g in ((0.011, 0.25), (0.017, 0.18), (0.029, 0.12), (0.043, 0.08), (0.071, 0.05)):
        d = int(atraso * SR); out[d:] += x[:-d] * g
    return out


def sala(x, tam=0.09, fb=0.35):
    out = x.copy(); d = int(tam * SR)
    for k in range(1, 6):
        out[d * k:] += x[:-d * k] * (fb ** k)
    return out


def poe(buf, s, seg, g):
    i = max(0, int(seg * SR)); j = min(len(buf), i + len(s))
    if i < len(buf): buf[i:j] += s[: j - i] * g


def finaliza(buf, nome, fade_in, fade_out):
    buf = buf - np.convolve(buf, np.ones(441) / 441, mode="same")  # corta graves abaixo de ~100 Hz/DC
    buf = buf / (np.max(np.abs(buf)) + 1e-9) * 0.9
    n = len(buf)
    if fade_in: buf[: int(fade_in * SR)] *= np.linspace(0, 1, int(fade_in * SR))
    buf[n - int(fade_out * SR):] *= np.linspace(1, 0, int(fade_out * SR)) ** 1.6
    os.makedirs("trilha/opcoes", exist_ok=True)
    wav = f"/tmp/{nome}.wav"
    with wave.open(wav, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", "loudnorm=I=-18:TP=-1.5",
                    "-ac", "1", "-ar", "44100", "-b:a", "128k", f"trilha/opcoes/{nome}.mp3"], check=True)
    print("ok", nome)


# ---------------- FOLK: violão dedilhado ----------------
ACORDES_G = {  # (baixo alternado, agudos)
    "G": (["G2", "D3"], ["G3", "B3", "D4", "G4"]),
    "D/F#": (["F#2", "A2"], ["D3", "A3", "D4", "F#4"]),
    "Em": (["E2", "B2"], ["G3", "B3", "E4", "G4"]),
    "C": (["C3", "G2"], ["G3", "C4", "E4", "G4"]),
    "Am": (["A2", "E2"], ["A3", "C4", "E4", "A4"]),
    "D": (["D3", "A2"], ["A3", "D4", "F#4", "A4"]),
}


def dedilhado(seq, bpm=100, final="G", melodia=()):
    colc = 60 / bpm / 2  # colcheia
    total = len(seq) * 8 * colc + 4.5
    buf = np.zeros(int(total * SR)); t = 0.0
    for ac in seq:
        baixos, agudos = ACORDES_G[ac]
        # padrão Travis: polegar nos tempos, dedos nos contratempos
        padrao = [(baixos[0], 0), (agudos[2], 1), (baixos[1], 0), (agudos[3], 1),
                  (baixos[0], 0), (agudos[1], 1), (baixos[1], 0), (agudos[2], 1)]
        for k, (nt, aguda) in enumerate(padrao):
            hum = rng.normal(0, 0.006)
            poe(buf, corda(nt, 2.2, 0.35 if not aguda else 0.6), t + k * colc + hum, 0.55 if not aguda else 0.38)
            if k == 0 and aguda == 0:
                poe(buf, corda(agudos[3], 2.2, 0.6), t + hum + 0.004, 0.32)  # pinça no 1º tempo
        t += 8 * colc
    for nota, beat in melodia:
        poe(buf, corda(nota, 2.5, 0.75, 0.9975), beat * colc + rng.normal(0, 0.004), 0.42)
    # acorde final, rasgueado devagar
    baixos, agudos = ACORDES_G[final]
    for k, nt in enumerate([baixos[0], baixos[1]] + agudos):
        poe(buf, corda(nt, 4.2, 0.5, 0.998), t + k * 0.035, 0.42)
    return sala(corpo(buf))


folk_ab = dedilhado(["G", "D/F#", "Em", "C", "D"], bpm=104,
                    melodia=[("B4", 0), ("D5", 3), ("A4", 8), ("D5", 11), ("G4", 16), ("B4", 19), ("E5", 22),
                             ("E5", 24), ("D5", 27), ("C5", 29), ("A4", 32), ("D5", 35), ("F#4", 38)])
finaliza(folk_ab, "folk-abertura", 0, 2.5)
folk_fim = dedilhado(["C", "D", "Em", "D"], bpm=96,
                     melodia=[("E5", 0), ("G5", 3), ("F#5", 8), ("D5", 11), ("B4", 16), ("G4", 19),
                              ("D5", 24), ("F#4", 27), ("A4", 30)])
finaliza(folk_fim, "folk-encerramento", 0, 3.8)


# ---------------- JORNAL: cordas, tímpano e guitarra solando ----------------
def pad(notas, dur, ataque=0.08):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for nt in notas:
        f = hz(nt)
        for det in (-0.8, 0, 0.8):
            ph = rng.uniform(0, 6.28)
            saw = sum(np.sin(2 * np.pi * (f + det) * h * t + ph) / h for h in range(1, 9))
            s += saw
    e = np.minimum(1, t / ataque) * np.exp(-0.15 * t)
    e[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))
    s = s * e / len(notas)
    k = 9; s = np.convolve(s, np.ones(k) / k, mode="same")  # amacia o brilho
    return s


def timpano(nota, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(nota)
    s = np.sin(2 * np.pi * f * t * (1 + 0.04 * np.exp(-t * 20))) * np.exp(-t * 3.0)
    s += rng.normal(0, 1, n) * np.exp(-t * 40) * 0.3
    return s


def guitarra(nota, dur, slide_de=None):
    """Guitarra elétrica solo: corda longa + vibrato + saturação."""
    base = corda(nota, dur, 0.85, 0.9993)
    t = np.arange(len(base)) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t / 0.35)
    idx = np.clip(np.cumsum(vib) - 1, 0, len(base) - 1)
    base = np.interp(idx, np.arange(len(base)), base)
    base = np.tanh(base * 6) * 0.6  # overdrive
    base = np.convolve(base, np.ones(5) / 5, mode="same")  # caixa do amplificador
    return base


def tema_jornal(acordes, solo, bpm=120, cauda=3.5):
    tempo = 60 / bpm
    total = sum(d for _, d in acordes) * tempo + cauda
    buf = np.zeros(int(total * SR)); t = 0.0
    for notas, batidas in acordes:
        poe(buf, pad(notas, batidas * tempo + 0.4), t, 0.35)
        poe(buf, timpano(notas[0][:-1] + "2"), t, 0.5)
        # baixo em colcheias, pulso de jornal
        for k in range(int(batidas * 2)):
            poe(buf, corda(notas[0][:-1] + "2", 0.35, 0.4, 0.99), t + k * tempo / 2, 0.30)
        t += batidas * tempo
    for nota, beat, dur in solo:
        poe(buf, guitarra(nota, dur * tempo + 0.6), beat * tempo, 0.30)
    # prato no fim
    n = int(3 * SR); tt = np.arange(n) / SR
    prato = np.convolve(rng.normal(0, 1, n), [1, -1], mode="same") * np.exp(-tt * 1.6)
    poe(buf, prato, (sum(d for _, d in acordes) - 1) * tempo, 0.06)
    return sala(buf, 0.11, 0.3)


jornal_ab = tema_jornal(
    [(["D3", "F#3", "A3"], 4), (["B2", "D3", "F#3"], 4), (["G2", "B2", "D3"], 4), (["A2", "C#3", "E3"], 4),
     (["D3", "F#3", "A3"], 6)],
    [("A4", 0, 1), ("D5", 1, 1.5), ("E5", 2.5, 0.5), ("F#5", 3, 1), ("E5", 4, 1), ("D5", 5, 1), ("B4", 6, 2),
     ("D5", 8, 1), ("E5", 9, 1), ("G5", 10, 1.5), ("F#5", 11.5, 0.5), ("E5", 12, 1.5), ("C#5", 13.5, 0.5),
     ("E5", 14, 1), ("A5", 15, 1), ("F#5", 16, 4)])
finaliza(jornal_ab, "jornal-abertura", 0, 2.5)
jornal_fim = tema_jornal(
    [(["G2", "B2", "D3"], 4), (["A2", "C#3", "E3"], 4), (["D3", "F#3", "A3"], 6)],
    [("B4", 0, 1), ("D5", 1, 1), ("G5", 2, 2), ("E5", 4, 1), ("C#5", 5, 1), ("A4", 6, 2), ("F#5", 8, 1),
     ("E5", 9, 0.5), ("D5", 9.5, 4)])
finaliza(jornal_fim, "jornal-encerramento", 0, 3.5)
