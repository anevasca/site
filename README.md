# A Nevasca

Jornal digital de convicção reformada e conservadora — https://anevasca.com.br

## Como o site funciona
- `index.html` — layout, capa, seções, páginas de matéria, coluna, arquivo e critérios (não mexer na rotina diária).
- `edicao.json` — edição do dia.
- `edicoes/AAAA-MM-DD.json` — cópia de cada edição (arquivo e links permanentes). Nunca apagar.
- `arquivo.json` — lista de edições, a mais recente primeiro.
- `colunas.json` — coluna "O Doido Sensato", de Doido Neves. Só muda quando o Junior manda um texto.
- `pdf/AAAA-MM-DD.pdf` — edição impressa (8 páginas: 2 folhas A4 frente e verso, encaixadas e dobradas ao meio).
- `m/*.html` — páginas de compartilhamento com prévia (WhatsApp, Facebook, X). Geradas por `python3 build.py`.
- `CNAME` — domínio próprio (anevasca.com.br). Não apagar.

## Rotina diária
1. Atualizar `edicao.json`, criar `edicoes/AAAA-MM-DD.json` e pôr a entrada nova no início de `arquivo.json`.
2. Gerar o PDF e salvar em `pdf/AAAA-MM-DD.pdf`.
3. Rodar `python3 build.py`.
4. Commit e push na branch `main`. O GitHub Pages publica sozinho em alguns minutos.

Contato da redação: redacaoanevasca@gmail.com
