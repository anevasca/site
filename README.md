# A Nevasca

Jornal digital de convicção reformada e conservadora — https://anevasca.com.br

## Como o site funciona
- `index.html` — layout, capa, seções, páginas de matéria, coluna, arquivo e critérios (não mexer na rotina diária).
- `edicao.json` — edição do dia.
- `edicoes/AAAA-MM-DD.json` — cópia de cada edição (arquivo e links permanentes). Nunca apagar.
- `arquivo.json` — lista de edições, a mais recente primeiro.
- `ultimas/AAAA-MM-DD.json` — matérias publicadas ao longo do dia (seção "Últimas notícias"), em ordem de publicação. Só se acrescenta no fim; nunca se altera o que já foi publicado. Cada item: hora, secao, titulo, linhaFina, resumo, texto[], fontes[], e opcionais urgente (true só para fato muito grande) e grafico.
- `grafico` (opcional em qualquer matéria): {tipo: "linha" ou "barras", titulo, subtitulo, prefixo, sufixo, casas, dados: [{rotulo, valor, destaque}], fonte: {nome, url}, nota}. Só com números das fontes citadas.
- `colunas.json` — coluna "O Doido Sensato", de Doido Neves. Só muda quando o Junior manda um texto.
- `pdf/AAAA-MM-DD.pdf` — edição impressa (8 páginas: 2 folhas A4 frente e verso, encaixadas e dobradas ao meio).
- `m/*.html` — páginas de compartilhamento com prévia (WhatsApp, Facebook, X). Geradas por `python3 build.py`.
- `CNAME` — domínio próprio (anevasca.com.br). Não apagar.
- `CONTRATO.md` — contrato de conteúdo para qualquer IA gerar uma edição ou matéria, no formato certo, sem precisar mexer em código ou em git.
- `ESTADO-HOJE.md` — o que já saiu hoje e o que falta, para retomar o trabalho com outra IA sem perder contexto.

## Rotina diária
1. Atualizar `edicao.json`, criar `edicoes/AAAA-MM-DD.json` e pôr a entrada nova no início de `arquivo.json`.
2. Gerar o PDF e salvar em `pdf/AAAA-MM-DD.pdf`.
3. Rodar `python3 build.py`.
4. Commit e push na branch `main`. O GitHub Pages publica sozinho em alguns minutos.

Contato da redação: redacaoanevasca@gmail.com
