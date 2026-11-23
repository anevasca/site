"""Gera a trilha de abertura e de encerramento do podcast (composição própria, sintetizada).

Tom sóbrio de telejornal: acordes graves em lá menor, notas de piano espaçadas e um
"tique" discreto de relógio (o relógio da capa do "em 10 minutos").
Saída: trilha/abertura.mp3 e trilha/encerramento.mp3. Rodar uma vez e versionar os MP3.
Para trocar por uma música licenciada, basta substituir os dois arquivos.
"""
import subprocess, sys, wave
import numpy as np

SR = 44100
rng = np.random.default_rng(7)
NOTA = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def hz(n):  # "A3"
    return 440.0 * 2 ** ((NOTA[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)


def envelope(n, a, r):
    e = np.ones(n)
    ka, kr = int(a * SR), int(r * SR)
    e[:ka] = np.linspace(0, 1, ka)
    e[-kr:] *= np.linspace(1, 0, kr)
    return e


def pad(notas, dur):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for nt in notas:
        f = hz(nt)
        for det in (-0.12, 0.0, 0.12):  # cordas levemente desafinadas entre si
            for h, amp in ((1, 1.0), (2, 0.35), (3, 0.15), (4, 0.06)):
                s += amp * np.sin(2 * np.pi * (f + det) * h * t + rng.uniform(0, 6.28))
    s *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t) * 0.15 + 0.5
    return s / len(notas) * envelope(n, 1.2, 1.4)


def piano(nota, dur=3.0):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(nota); s = np.zeros(n)
    for h, amp, dec in ((1, 1.0, 1.6), (2, 0.45, 2.4), (3, 0.2, 3.2), (4, 0.1, 4.0), (5, 0.05, 5.0)):
        s += amp * np.sin(2 * np.pi * f * h * t * (1 + 0.0004 * h * h)) * np.exp(-dec * t)
    s[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return s


def tique(forte=False):
    n = int(0.05 * SR); x = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (0.004 * SR))
    x = np.convolve(x, np.ones(6) / 6, mode="same")  # tira o chiado
    t = np.arange(n) / SR
    return (x * 0.5 + np.sin(2 * np.pi * (2600 if forte else 2000) * t) * np.exp(-t / 0.006)) * (1.0 if forte else 0.6)


def poe(buf, sinal, seg, ganho):
    i = int(seg * SR); j = min(len(buf), i + len(sinal))
    buf[i:j] += sinal[: j - i] * ganho


def compoe(acordes, melodia, total, ticks_ate):
    buf = np.zeros(int(total * SR))
    pos = 0.0
    for notas, dur in acordes:
        poe(buf, pad(notas, dur + 1.2), pos, 0.20); pos += dur
    for nota, seg in melodia:
        poe(buf, piano(nota), seg, 0.22)
    b = 0.0
    while b < ticks_ate:
        poe(buf, tique(abs(b % 4) < 1e-6), b, 0.05); b += 1.0  # 60 bpm, como um relógio
    # graves de reforço no primeiro tempo de cada acorde
    pos = 0.0
    for notas, dur in acordes:
        poe(buf, piano(notas[0][:-1] + "2", 3.5), pos, 0.18); pos += dur
    # eco curto (sala)
    eco = np.zeros_like(buf); d = int(0.23 * SR); eco[d:] = buf[:-d] * 0.22
    buf = buf + eco
    buf = np.tanh(buf * 1.4) / np.tanh(1.4)
    return buf / np.max(np.abs(buf)) * 0.8


def salva(buf, nome, fade_in, fade_out):
    n = len(buf)
    buf[: int(fade_in * SR)] *= np.linspace(0, 1, int(fade_in * SR))
    buf[n - int(fade_out * SR):] *= np.linspace(1, 0, int(fade_out * SR)) ** 1.5
    wav = f"/tmp/{nome}.wav"
    with wave.open(wav, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", "loudnorm=I=-20:TP=-2",
                    "-ac", "1", "-ar", "24000", "-b:a", "64k", f"trilha/{nome}.mp3"], check=True)
    print("ok", nome)


# Abertura (~11 s): Am – F – C – E, melodia descendente
ab = compoe([(["A3", "C4", "E4"], 2.6), (["F3", "A3", "C4"], 2.6), (["C3", "E3", "G3"], 2.6), (["E3", "G#3", "B3"], 3.0)],
            [("E5", 0.0), ("C5", 1.3), ("A4", 2.6), ("C5", 3.9), ("G4", 5.2), ("E4", 6.5), ("B4", 7.8), ("G#4", 9.1)],
            12.5, 10.5)
salva(ab, "abertura", 0.3, 2.2)

# Encerramento (~10 s): F – G – Am, resolve em lá
en = compoe([(["F3", "A3", "C4"], 2.6), (["G3", "B3", "D4"], 2.6), (["A3", "C4", "E4"], 4.5)],
            [("C5", 0.0), ("A4", 1.3), ("D5", 2.6), ("B4", 3.9), ("E5", 5.2), ("A4", 6.0)],
            11.0, 5.5)
salva(en, "encerramento", 0.8, 4.0)
