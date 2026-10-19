# Gerador de Ofícios de Resposta

Gera os ofícios de resposta do Cartório do 1º Ofício de Notas e Registro de
Imóveis de Morrinhos/GO, no formato que a serventia já usa: timbre, numeração
por setor, bloco do destinatário, assunto, corpo, fecho e assinatura.

O escrevente escolhe o **modelo** (ex.: "Cancelamento de penhora", "Busca
negativa — pessoa física", "Comunica substabelecimento"), escolhe o
**destinatário** no cadastro, preenche os poucos dados do caso e recebe o
`.docx` pronto, com a prévia ao lado mostrando o que falta.

Funciona como o gerador de notas devolutivas: servidor local em Python, tela no
navegador, sem dependência externa.

## Rodando

Dê dois cliques em **`Ofício resposta.bat`**. Na primeira vez ele cria o ambiente
Python (`.venv`); depois abre a ferramenta no navegador. O servidor escuta só em
`127.0.0.1`, numa porta sorteada — nada fica exposto na rede.

Requer Python 3.12 ou mais novo. Não há dependências.

## Como funciona

| Etapa | O que a ferramenta faz |
|---|---|
| Numeração | Sugere o próximo número do setor lendo os nomes de arquivo em `T:\Oficios\Enviados\<SETOR>\<ANO>` (só leitura). O número pode ser alterado. |
| Destinatário | Cadastro com juízes, varas, Promotorias, PGE, AGEHAB, INCRA, Prefeitura, tabelionatos… O tratamento define o pronome do fecho (Vossa Excelência / Vossa Senhoria) e o "cumprimentá-lo/la". |
| Ofício recebido | Número do ofício e do processo — entram na linha "Assunto:" e, quando o modelo pede, no corpo. |
| Dados do modelo | Só o que muda de um caso para outro: matrícula, ato, data… Campos entre colchetes no modelo são opcionais e somem do texto quando ficam vazios. |
| Gerar | Grava `saida\SETOR-ANO-NNN - descrição.docx`, no padrão de nomes da pasta `T:\Oficios` ("Legenda e Padrao Nrs Oficios.txt"). |

**A ferramenta não grava nada em `T:\Oficios`.** O ofício gerado fica em
`saida\`; depois de conferido e assinado, o escrevente o arquiva na pasta do
setor, como hoje.

## Os modelos

São 48 modelos, transcritos dos ofícios expedidos em 2025–2026:

- **RGI** (23): ajuizamento averbado; penhora registrada; cancelamentos (penhora,
  hipoteca, arresto, indisponibilidade, ajuizamento, premonitória, consolidação);
  reversão de doação; indisponibilidade fora da CNIB (com os arts. 320-D e
  320-E do CNN); emolumentos pendentes; exigência/nota devolutiva; pedido de
  esclarecimento; retificação de área; Pró-Morar etc.
- **STC** (10): certidão de inteiro teor; certidão de escritura; busca negativa
  (PF/PJ) e positiva; CAR para a Promotoria; comunicação mensal ao INCRA.
- **STN** (11): comunica substabelecimento, revogação e dissolução de união
  estável; MP — Resolução CNJ 571; Receita (CPF de falecido); CENSEC; ITBI;
  guia de escritura; anuência de banco.
- **ADM** (3): Livro Diário Auxiliar, férias do titular, nomeação de substituto.
- **Resposta livre**: para o caso sem modelo — o corpo é digitado, o resto sai
  pronto.

### Acrescentando ou mudando um modelo

Tudo está em `dados\`, editável sem programar:

- `modelos.json` — os modelos, os campos, os fechos e as citações de norma;
- `destinatarios.json` — o cadastro de destinatários e as formas de tratamento;
- `assinantes.json` — quem assina e com qual cargo.

Depois de editar, rode a conferência:

```
.venv\Scripts\python.exe ferramentas\valida_catalogo.py
.venv\Scripts\python.exe ferramentas\testa_redator.py
```

O primeiro redige **todos** os modelos e reprova se faltar campo, fecho ou
citação, ou se sobrar `{chave}` no texto. O segundo confere regras que já
importam no papel: concordância ("do arresto registrado"), trecho opcional,
pronome do fecho, data por extenso, numeração.

## Formatação

O `.docx` sai de `modelo\molde-oficio.docx`, feito a partir de um ofício real
(`ferramentas\cria_molde.py`): timbre, rodapé "fls. X / Y", estilos, papel A4 e
margens vêm do arquivo do cartório. O molde guarda só a forma: o texto do
ofício de origem é descartado e os metadados, zerados.

Corpo em Arial 12, justificado, entrelinhas 1,5 e recuo de 1,25 cm; cabeçalho
do ofício em entrelinhas 1,15; nome do destinatário em negrito; cidade em
itálico sublinhado; "Assunto:" em negrito com o texto em itálico; assinatura
centralizada.

## Vercel

O mesmo código roda como função (`api\index.py`, `vercel.json`). Lá o disco é
somente leitura e não há `T:\`: o ofício volta como download e a sugestão de
número fica desligada. Mantenha a proteção de implantação ligada — a ferramenta
gera documentos em nome da serventia e não tem controle de acesso próprio.

## Estrutura

| Pasta | |
|---|---|
| `dados/` | modelos, campos, fechos, destinatários, assinantes |
| `oficios/` | catálogo, redator, gerador de `.docx` e servidor |
| `public/` | a tela (HTML, CSS, JS) |
| `ferramentas/` | conferência do catálogo, testes e criação do molde |
| `modelo/` | molde de formatação (timbre, estilos, margens) |
| `saida/` | ofícios gerados — fora do git |
