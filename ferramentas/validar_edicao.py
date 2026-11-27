#!/usr/bin/env python3
"""
Valida o conteúdo de A Nevasca antes de publicar.

Roda sem argumentos, a partir da raiz do repositório. Sai com código 1 e
trava a publicação só quando há um problema estrutural (campo faltando,
JSON inválido, imagem inexistente, ou uma matéria já publicada alterada).
Checagem de fontes insuficientes vira AVISO, não erro: o manual permite
fonte única quando vem de Oeste, Gazeta, grande veículo, fonte oficial, ou
quando é pauta própria do editor — isso é julgamento, não algo que um
script deva decidir sozinho.

Regras que travam a publicação:
  1. edicao.json existe, lê como JSON e tem os campos obrigatórios.
  2. Cada matéria (manchete, editorial, destaques, politica, mundo, cultura)
     tem os campos: secao, titulo, linhaFina, resumo, texto.
  3. Nenhum título ou texto vazio.
  4. Imagens citadas (campo imagem.arquivo) existem de fato no repositório.
  5. ultimas/AAAA-MM-DD.json: cada item tem os campos certos.
  6. Imutabilidade: nenhum item já publicado em ultimas/*.json foi alterado
     ou removido, comparado com o commit anterior (HEAD). Só pode ter sido
     acrescentado no fim.
  7. edicoes/AAAA-MM-DD.json: se já existia no commit anterior, não pode ter
     mudado.
  8. Sem título duplicado dentro da mesma edição.

Regras que só avisam (não travam):
  9. Matéria com menos de 2 fontes (campo `fontes`, lista de objetos
     {"nome": ..., "url": ...}).
"""

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ERROS = []
AVISOS = []


def erro(msg):
    ERROS.append(msg)


def aviso(msg):
    AVISOS.append(msg)


def carregar_json(caminho):
    if not caminho.exists():
        return None, f"{caminho.relative_to(RAIZ)}: arquivo não existe"
    try:
        return json.loads(caminho.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as e:
        return None, f"{caminho.relative_to(RAIZ)}: JSON inválido ({e})"


def _ref_anterior(caminho_relativo):
    """
    Decide contra qual referência de git comparar.

    Se o arquivo ainda tem mudança não commitada (rodando localmente antes do
    commit), o estado "publicado" é o do próprio HEAD. Se o arquivo já está
    idêntico ao HEAD (caso do Actions, que roda depois do commit já feito), o
    estado "publicado" é o do commit anterior, HEAD~1.
    """
    resultado = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", caminho_relativo], cwd=RAIZ
    )
    return "HEAD" if resultado.returncode != 0 else "HEAD~1"


def git_mostrar(caminho_relativo):
    """Conteúdo do arquivo no estado publicado anterior, ou None se não existia."""
    ref = _ref_anterior(caminho_relativo)
    try:
        saida = subprocess.run(
            ["git", "show", f"{ref}:{caminho_relativo}"],
            cwd=RAIZ, capture_output=True, text=True, check=True,
        )
        return json.loads(saida.stdout)
    except subprocess.CalledProcessError:
        return None
    except json.JSONDecodeError:
        return None


CAMPOS_MATERIA = ["secao", "titulo", "linhaFina", "resumo", "texto"]


def validar_materia(item, contexto, checar_fontes=True):
    nome = f"{contexto} ({item.get('titulo', '<sem título>')!r})"
    for campo in CAMPOS_MATERIA:
        if campo not in item:
            erro(f"{nome}: falta o campo '{campo}'")
    if not item.get("titulo", "").strip():
        erro(f"{contexto}: título vazio")
    if not item.get("texto"):
        erro(f"{nome}: texto vazio")
    if checar_fontes:
        n = len(item.get("fontes") or [])
        if n < 2:
            aviso(f"{nome}: tem {n} fonte(s). Confirme se é caso de fonte única "
                  f"permitida (Oeste, Gazeta, grande veículo, fonte oficial, ou pauta própria).")
    img = item.get("imagem")
    if isinstance(img, dict):
        arq = img.get("arquivo")
        if arq and not (RAIZ / arq.lstrip("/")).exists():
            erro(f"{nome}: imagem '{arq}' não existe no repositório")


def validar_edicao_json():
    caminho = RAIZ / "edicao.json"
    ed, err = carregar_json(caminho)
    if err:
        erro(err)
        return None
    obrigatorios = ["data", "dataExtenso", "numero", "manchete", "editorial",
                    "destaques", "politica", "mundo", "cultura", "indicadores",
                    "paraEntender"]
    for campo in obrigatorios:
        if campo not in ed:
            erro(f"edicao.json: falta o campo '{campo}'")

    if "manchete" in ed:
        validar_materia(ed["manchete"], "edicao.json · manchete")
    if "editorial" in ed:
        validar_materia(ed["editorial"], "edicao.json · editorial", checar_fontes=False)

    titulos = []
    for secao in ["destaques", "politica", "mundo", "cultura"]:
        for item in ed.get(secao, []) or []:
            validar_materia(item, f"edicao.json · {secao}")
            titulos.append(item.get("titulo", "").strip().lower())
    if "manchete" in ed:
        titulos.append(ed["manchete"].get("titulo", "").strip().lower())

    vistos = set()
    for t in titulos:
        if t and t in vistos:
            erro(f"edicao.json: título duplicado na mesma edição: {t!r}")
        vistos.add(t)

    return ed


def validar_ultimas():
    pasta = RAIZ / "ultimas"
    if not pasta.exists():
        return
    for caminho in sorted(pasta.glob("*.json")):
        rel = caminho.relative_to(RAIZ).as_posix()
        atual, err = carregar_json(caminho)
        if err:
            erro(err)
            continue
        if not isinstance(atual, list):
            erro(f"{rel}: deveria ser uma lista de itens")
            continue

        for i, item in enumerate(atual):
            contexto = f"{rel}[{i}]"
            for campo in ["hora", "secao", "titulo", "linhaFina", "resumo", "texto"]:
                if campo not in item:
                    erro(f"{contexto}: falta o campo '{campo}'")
            if not item.get("titulo", "").strip():
                erro(f"{contexto}: título vazio")
            n = len(item.get("fontes") or [])
            if n < 2:
                aviso(f"{contexto} ({item.get('titulo','?')!r}): tem {n} fonte(s). "
                      f"Confirme se é caso de fonte única permitida.")

        anterior = git_mostrar(rel)
        if anterior is not None:
            if not isinstance(anterior, list):
                continue
            if len(atual) < len(anterior):
                erro(f"{rel}: tinha {len(anterior)} item(ns) publicado(s) e agora tem {len(atual)} — "
                     f"item removido. Matéria publicada não se apaga.")
                continue
            for i, item_antigo in enumerate(anterior):
                if i >= len(atual) or atual[i] != item_antigo:
                    titulo = item_antigo.get("titulo", "?")
                    erro(f"{rel}[{i}] ({titulo!r}): item já publicado foi alterado. "
                         f"Matéria publicada não se muda — crie uma matéria nova.")


def validar_edicoes_antigas():
    pasta = RAIZ / "edicoes"
    if not pasta.exists():
        return
    for caminho in sorted(pasta.glob("*.json")):
        rel = caminho.relative_to(RAIZ).as_posix()
        atual, err = carregar_json(caminho)
        if err:
            erro(err)
            continue
        anterior = git_mostrar(rel)
        if anterior is not None and anterior != atual:
            erro(f"{rel}: edição antiga foi alterada. Edição publicada não se muda.")


def main():
    validar_edicao_json()
    validar_ultimas()
    validar_edicoes_antigas()

    if AVISOS:
        print(f"⚠️  {len(AVISOS)} aviso(s) (não travam a publicação):\n")
        for a in AVISOS:
            print(f"  - {a}")
        print()

    if ERROS:
        print(f"❌ {len(ERROS)} problema(s) encontrado(s):\n")
        for e in ERROS:
            print(f"  - {e}")
        print("\nA publicação foi interrompida. Corrija e tente de novo.")
        sys.exit(1)

    print("✅ Sem erros. Pode publicar.")
    sys.exit(0)


if __name__ == "__main__":
    main()
