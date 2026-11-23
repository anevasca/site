"""Baixa da release "audio" os MP3 dos últimos DIAS dias para a pasta _site/audio/.
Assim o site serve os áudios no próprio domínio (anevasca.com.br/audio/...),
com o tipo certo (audio/mpeg), que funciona também no iPhone."""
import datetime, json, os, re, subprocess, sys

DIAS = int(os.environ.get("AUDIO_DIAS", "14"))
REPO = os.environ.get("GITHUB_REPOSITORY", "anevasca/site")
destino = sys.argv[1] if len(sys.argv) > 1 else "_site/audio"
os.makedirs(destino, exist_ok=True)
limite = (datetime.date.today() - datetime.timedelta(days=DIAS)).isoformat()
r = subprocess.run(["gh", "api", "--paginate", f"repos/{REPO}/releases/tags/audio", "-q", ".assets[].name"],
                   capture_output=True, text=True)
if r.returncode != 0:
    print("sem release de áudio ainda"); sys.exit(0)
nomes = [n for n in r.stdout.split() if re.match(r"ed-(\d{4}-\d{2}-\d{2})-.*\.mp3$", n)
         and re.match(r"ed-(\d{4}-\d{2}-\d{2})", n).group(1) >= limite]
for i in range(0, len(nomes), 40):
    args = ["gh", "release", "download", "audio", "--repo", REPO, "-D", destino, "--clobber"]
    for n in nomes[i:i + 40]:
        args += ["-p", n]
    subprocess.run(args, check=False)
print(len(nomes), "áudio(s) no site")
