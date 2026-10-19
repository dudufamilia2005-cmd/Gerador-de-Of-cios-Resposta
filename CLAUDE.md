# Gerador de ofícios de resposta

Ferramenta do Cartório do 1º Ofício de Morrinhos/GO para redigir ofícios de
resposta (a juízos, Promotorias, órgãos, outros cartórios) a partir de modelos.
Projeto irmão do gerador de notas devolutivas (`..\Notas`), com a mesma
arquitetura: servidor `http.server` local, tela em `public/`, `.docx` escrito
com `zipfile` sobre um molde real.

## Ambiente

Python 3.14 em `%LOCALAPPDATA%\Programs\Python\Python314`, venv em `.venv`.
**Nenhuma dependência.** Não introduza `python-docx`: a escrita com `zipfile`
copia as peças do molde e garante a formatação idêntica por construção.

```
.venv\Scripts\python.exe -m oficios.servidor           # a tela (o .bat faz isso)
.venv\Scripts\python.exe ferramentas\valida_catalogo.py  # antes de confiar no catálogo
.venv\Scripts\python.exe ferramentas\testa_redator.py    # regressão do texto
```

## Fonte da verdade

- **`T:\Oficios` é só leitura. Nunca grave, renomeie nem apague nada lá**
  (pedido expresso da serventia). O servidor só lista nomes de arquivo de
  `T:\Oficios\Enviados\<SETOR>\<ANO>` para sugerir o próximo número; o caminho
  pode ser trocado pela variável `OFICIOS_ENVIADOS`.
- A redação dos modelos foi transcrita dos ofícios de 2025–2026 de
  `T:\Oficios\Enviados` (levantamento de 19/10/2026: 407 .docx lidos). Ao mudar
  um modelo, compare com ofícios reais — a ferramenta existe para padronizar o
  que a serventia já escreve, não para inventar redação.
- Correções feitas na transcrição, de propósito: crase ("à disposição",
  "À Senhora"), "SUBSTABELECIDO" (os originais tinham "SUSBTABELECIDO"),
  "de cujus", "a {substabelecido}" (era "à" diante de nome masculino),
  "à disposição de Vossa Excelência" (era "da"). O resto é verbatim, inclusive
  "conforme exame cálculo em anexo" — confirmar com a serventia se é o nome do
  documento.
- Citação de norma vive em `citacoes` de `dados/modelos.json`, com o texto
  oficial. Os arts. 320-D e 320-E do CNN foram conferidos com o índice do CNN do
  gerador de notas (`..\Notas\dados\artigos.json`). Não cite artigo que não
  tenha sido conferido contra a norma.

## Repositório público

O GitHub (`dudufamilia2005-cmd/Gerador-de-Of-cios-Resposta`) é **público**.
Nada de dado de parte no repositório: exemplos de campo são fictícios
("Fulano de Tal", CPF 000.000.000-00), `saida/` é ignorada, e o molde não
carrega o texto do ofício de origem. O cadastro tem nomes de autoridades e de
quem assina — dados funcionais, mantidos de propósito; se a serventia preferir,
mover `destinatarios.json`/`assinantes.json` para fora do git.

## Invariantes

1. **A formatação sai do molde, não de código.** `modelo/molde-oficio.docx`
   tem o timbre (header1 + 4 imagens), o rodapé "fls. PAGE / NUMPAGES", os
   estilos e o `sectPr` (A4, margens 2,85/2,00/1,59/2,50 cm). `documento.py`
   troca só `word/document.xml`. As medidas de parágrafo foram lidas do
   RGI/2026/014: corpo entrelinhas 360 e recuo 708; cabeçalho 276; vocativo e
   "Atenciosamente" com recuo 1440; citação com recuo esquerdo 1416.
2. **Campo entre colchetes é opcional por construção.** `[, de propriedade de
   {proprietario}]` some inteiro se o campo ficar vazio; parágrafo que fica
   vazio desaparece. Campo fora de colchetes é obrigatório, salvo se tiver
   `padrao`.
3. **Concordância vem de escolha, não de adivinhação.** "do arresto
   registrado" / "da penhora registrada", "inscrito/inscrita", "do de cujus":
   o campo de escolha traz o texto de cada variante (`{onus.do}`,
   `{pessoa.inscrito}`). O pronome do fecho e o "cumprimentá-lo/la" vêm do
   tratamento do destinatário.
4. **A prévia informa o erro com status 200**, em `{"html": "", "erro": …}`,
   como no gerador de notas. A tela mostra o `erro`.
5. **Mesmo código local e no Vercel.** `SOMENTE_LEITURA` (variável `VERCEL`)
   desliga a sugestão de número e devolve o `.docx` em base64.
6. **Quem assina começa em branco.** Assinatura errada é pior que campo vazio;
   a tela lembra (localStorage, por máquina) a última pessoa escolhida.

## Pendências conhecidas

- **Cobrança mensal à Prefeitura (ADM, "Encaminha NFE")** ficou de fora: tem
  tabela de O.S./recibos/valores e valor por extenso. Pede um campo de tabela.
- Ofício a **vários destinatários** no mesmo bloco (Prefeito + Procurador +
  Secretário, STC-2026-011) não é suportado — hoje sai um destinatário só.
- Numeração do STN é irregular no acervo (`STN/2026/001`, `008/2026 STN`,
  `STNI/2026/018`); a ferramenta padroniza em `STN/AAAA/NNN`. O sufixo `STNI`
  (ofícios de RI assinados pelo STN) é reconhecido na sugestão de número.
- A sugestão de número é "maior usado + 1" — não detecta números pulados nem
  reservados na planilha de controle.
- Nenhum modelo foi revisado formalmente por registrador/tabelião.
