# -*- coding: utf-8 -*-
"""Regressao do redator: o texto que sai para cada situacao conhecida.

    .venv\\Scripts\\python.exe ferramentas\\testa_redator.py

Cada caso fixa uma regra que, se quebrar, sai errada num oficio assinado:
concordancia, trecho opcional, pronome do fecho, numeracao, data por extenso.
"""
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from oficios.catalogo import Catalogo                      # noqa: E402
from oficios.redator import CampoFaltando, Pedido, Redator  # noqa: E402
from oficios import documento                              # noqa: E402

CAT = Catalogo()
R = Redator(CAT)
JUIZ = CAT.destinatarios["juiz-1vara-anddre"]
TABELIA = CAT.destinatarios["tabelia-maria-helena"]
QUEM = CAT.assinantes["matheus-antonio"]

falhas = []


def pedido(modelo, valores, dest=JUIZ, **extra):
    base = dict(modelo=modelo, setor="", ano="2026", numero="4", data="2026-01-30",
                destinatario=dest, valores=valores, assinante=QUEM)
    base.update(extra)
    return Pedido(**base)


def texto(p):
    return Redator.em_texto(R.redige(p))


def confere(nome, condicao, detalhe=""):
    if not condicao:
        falhas.append(f"{nome}: {detalhe}")


# --- cabecalho: data por extenso com dia de dois digitos, numero com 3 digitos
t = texto(pedido("rgi-penhora-registrada", {"matricula": "2.646", "ato": "R.40"}))
confere("data", "Morrinhos/GO, 30 de janeiro de 2026." in t, t[:200])
confere("numero", "Ofício nº RGI/2026/004" in t, "esperava RGI/2026/004")

# --- trecho opcional: sem fracao, "sobre o imovel"; com fracao, "sobre 25% ... do imovel"
confere("penhora sem fração", "registro da Penhora sobre o imóvel, conforme" in t, t)
confere("penhora sem proprietário", "de propriedade de" not in t, "trecho opcional ficou")
t2 = texto(pedido("rgi-penhora-registrada", {"matricula": "8.209", "ato": "R.09",
                                             "fracao": "25% (vinte e cinco por cento)"}))
confere("penhora com fração",
        "sobre 25% (vinte e cinco por cento) do imóvel, conforme" in t2, t2)

# --- pronome do fecho segue o destinatario
confere("fecho juiz", "renovar a Vossa Excelência nossos sentimentos" in t, "pronome do juiz")
pref = dict(JUIZ, tratamento="senhor")
t3 = texto(pedido("rgi-penhora-registrada", {"matricula": "1", "ato": "R.1"}, dest=pref))
confere("fecho senhoria", "renovar a Vossa Senhoria nossos sentimentos" in t3, "pronome Senhoria")

# --- genero do destinatario: cumprimenta-la
t4 = texto(pedido("stn-comunica-revogacao",
                  {"livro_procuracao": "00033-P", "folhas_procuracao": "096F/096V",
                   "data_procuracao": "2017-03-16", "outorgante": "FULANO DE TAL",
                   "data_nosso_ato": "2026-09-23", "livro_nosso_ato": "121",
                   "folhas_nosso_ato": "151F/152F"}, dest=TABELIA, setor="STN"))
confere("cumprimentá-la", "A par de cumprimentá-la," in t4, t4)
confere("data curta", "em data de 16/03/2017" in t4, "data curta da procuração")
confere("tratamento tabeliã", "À Ilustríssima Senhora" in t4, "tratamento")
confere("sem referência", "Ofício n.º" not in t4.split("Assunto:")[1].split("\n")[0],
        "modelo sem referência não pode citar ofício recebido no assunto")

# --- concordancia do onus: arresto e masculino
t5 = texto(pedido("rgi-cancelamento-constricao",
                  {"onus": "arresto", "matricula": "8.208", "ato_cancelado": "R.05",
                   "ato_cancelamento": "AV.06", "data_ato": "2026-09-14"}))
confere("arresto", "o cancelamento do arresto registrado à margem" in t5, t5)
confere("arresto 2", "correspondente ao arresto anteriormente registrado" in t5, t5)
confere("parágrafo opcional some", "Cumpre-nos informar, ainda" not in t5, "parágrafo vazio ficou")
confere("data extenso campo", "lançada em 14 de setembro de 2026" in t5, "data do ato por extenso")

# --- assunto: oficio recebido / processo / assunto do modelo
p6 = pedido("rgi-cancelamento-constricao",
            {"onus": "penhora", "matricula": "2.665", "ato_cancelado": "R.30",
             "ato_cancelamento": "AV.31", "data_ato": "2026-09-14"},
            oficio_recebido="276/2025", processo="5111111-11.2025.8.09.0107")
t6 = texto(p6)
confere("assunto", "Assunto: Ofício n.º 276/2025 / Processo n.º 5111111-11.2025.8.09.0107 / "
        "Cancelamento de Penhora – Matr. 2.665." in t6, t6)
confere("nome do arquivo", R.nome_arquivo(p6) == "RGI-2026-004 - cancelamento de penhora - matr. 2.665.docx",
        R.nome_arquivo(p6))

# --- campo obrigatorio vazio: o oficio nao sai
try:
    R.redige(pedido("rgi-penhora-registrada", {"matricula": "1"}))
    falhas.append("campo vazio: deveria recusar sem o ato")
except CampoFaltando:
    pass
# ...mas a previa sai, marcando o que falta
prev = Redator.em_texto(R.redige(pedido("rgi-penhora-registrada", {"matricula": "1"}), rascunho=True))
confere("rascunho", "«Ato lançado»" in prev, prev)

# --- citacao de norma: CNIB
t7 = texto(pedido("rgi-indisponibilidade-fora-cnib", {"matricula": "35.663"}))
confere("citação", "Art. 320-E. Todas as ordens de indisponibilidade" in t7, "citação CNIB")

# --- escolha com paragrafo inteiro
t8 = texto(pedido("rgi-custas-sem-contato",
                  {"pedido_juizo": "o cancelamento da penhora", "matricula": "1.000",
                   "motivo_sem_contato": "Processo em segredo de justiça"}))
confere("motivo", "tramitam sob segredo de justiça" in t8, t8)
confere("pronome no corpo", "no qual Vossa Excelência solicita" in t8, "pronome no corpo")

# --- resposta livre: varias linhas viram paragrafos; fecho escolhido
fecho = next(k for k, v in CAT.campos["fecho"]["opcoes"].items() if v["id"] == "ensejo")
t9 = texto(pedido("resposta-livre", {"texto_livre": "Primeiro parágrafo.\nSegundo parágrafo.",
                                     "fecho": fecho, "arquivo_livre": "teste"}, setor="ADM"))
confere("livre", "    Primeiro parágrafo.\n    Segundo parágrafo." in t9, t9)
confere("livre fecho", "No ensejo, apresentamos nossos votos" in t9, "fecho escolhido")
confere("livre setor", "ADM/2026/004" in t9, "setor da tela")

# --- quem assina dentro do texto (CENSEC)
t10 = texto(pedido("stn-censec-exclusao-testamento",
                   {"testador": "FULANO", "data_testamento": "2017-04-20", "livro": "004",
                    "folhas": "024"}, dest=CAT.destinatarios["censec"], setor="STN"))
confere("quem assina", "Eu, Matheus Antônio Alves dos Santos, Escrevente, abaixo assinado" in t10, t10)
confere("órgão sem tratamento", "\nÀ Central Notarial" in t10 and "Ao Excelentíssimo" not in t10, t10)

# --- o .docx abre e mantem timbre do molde
conteudo = documento.monta(R.redige(p6), BASE / "modelo" / "molde-oficio.docx")
with zipfile.ZipFile(BytesIO(conteudo)) as z:
    nomes = z.namelist()
    xml = z.read("word/document.xml")
    ET.fromstring(xml)
confere("timbre", "word/header1.xml" in nomes and "word/media/image1.jpeg" in nomes, nomes)
confere("sectPr", b"<w:pgSz" in xml and b"headerReference" in xml, "papel/margens")
confere("negrito número", b"<w:b/>" in xml, "número do ofício em negrito")

if falhas:
    print(f"FALHOU — {len(falhas)} caso(s):")
    for f in falhas:
        print("  -", f)
    sys.exit(1)
print("OK — todos os casos do redator conferem.")
