"""Monta o episódio gravado por Junior e Maressa: limpa o áudio, nivela o volume e põe a vinheta
(trilha/abertura.mp3 antes, trilha/encerramento.mp3 depois).
Uso:  python3 ferramentas/montar_podcast.py <gravação> AAAA-MM-DD [saída.mp3]
O roteiro para gravar fica em https://anevasca.com.br/#roteiro (página oculta)."""
import os, subprocess, sys

grav, data = sys.argv[1], sys.argv[2]
saida = sys.argv[3] if len(sys.argv) > 3 else f"pod-{data}.mp3"
aqui = os.path.dirname(os.path.abspath(__file__))
ab, fim = (os.path.join(aqui, "..", "trilha", n) for n in ("abertura.mp3", "encerramento.mp3"))
voz = ("highpass=f=80,afftdn=nf=-25,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.2,"
       "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.3,areverse,"
       "acompressor=threshold=-20dB:ratio=3:attack=10:release=200:makeup=2,loudnorm=I=-16:TP=-1.5:LRA=9")
tmp = saida + ".tmp"
os.makedirs(tmp, exist_ok=True)
def wav(src, dst, af=None):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", src] + (["-af", af] if af else []) + ["-ac", "1", "-ar", "44100", dst]
    subprocess.run(cmd, check=True)
wav(ab, f"{tmp}/1.wav"); wav(grav, f"{tmp}/3.wav", voz); wav(fim, f"{tmp}/5.wav")
for n, seg in (("2", 0.5), ("4", 0.7)):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", str(seg), f"{tmp}/{n}.wav"], check=True)
open(f"{tmp}/lista.txt", "w").write("".join(f"file '{os.path.abspath(tmp)}/{n}.wav'\n" for n in "12345"))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{tmp}/lista.txt",
                "-ac", "1", "-ar", "44100", "-b:a", "96k", saida], check=True)
for f in os.listdir(tmp): os.remove(f"{tmp}/{f}")
os.rmdir(tmp)
r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", saida],
                   capture_output=True, text=True)
print(f"{saida}: {float(r.stdout) / 60:.1f} min")
