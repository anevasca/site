# Estado de hoje — A Nevasca

Este arquivo existe para você trocar de IA no meio do dia sem perder contexto. Antes de
pedir a qualquer IA para continuar o trabalho, cole junto o `CONTRATO.md` e este arquivo.
Atualize-o sempre que uma etapa do dia for concluída (edição da manhã, uma notícia em
"Últimas notícias", um ajuste no site). Não precisa ser longo — só o suficiente para a
próxima IA não começar do zero.

## Hoje

- **Data:** 2026-11-27
- **Edição da manhã (`edicao.json`):** publicada. Número 10. Manchete: "Da oração à mesa,
  a Ação de Graças em Tupã".
- **Últimas notícias (`ultimas/2026-11-27.json`):** nenhuma ainda.
- **Pendências do dia:** nenhuma registrada.
- **Última IA que trabalhou no jornal:** Claude, nesta sessão — criou `CONTRATO.md` e
  este arquivo, e trocou o rótulo "Ao longo do dia" por "Últimas notícias" no site.
- **Créditos:** inventário ainda não preenchido (ver seção 4 de `Arquitetura-A-Nevasca`,
  no projeto do Claude).

## Como usar isto (para a próxima IA, de qualquer ferramenta)

1. Leia o `CONTRATO.md` primeiro: ele tem o formato dos arquivos e as regras do jornal.
2. Leia a seção "Hoje" acima para saber o que já saiu e o que falta.
3. Gere só o JSON pedido. Não tente publicar, não rode git, não peça PowerShell: isso é
   problema de outra etapa, que o Junior resolve separadamente.
4. Quando terminar, se puder, atualize a seção "Hoje" deste arquivo com o que voce fez.

## Pendências gerais (não mudam todo dia)

Ver a lista completa em `Manual-da-Redacao-A-Nevasca.md` e `Arquitetura-A-Nevasca.md`, no
projeto "A Nevasca" do Claude. Resumo:

- Canal do WhatsApp: aguardando o Junior mandar o link.
- Dia fixo da coluna "O Doido Sensato": não definido.
- Nota de transparência sobre uso de IA: não definida.
- Validador de edição (`ferramentas/validar_edicao.py`): a criar.
