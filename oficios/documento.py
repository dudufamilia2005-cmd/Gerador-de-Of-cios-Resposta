# -*- coding: utf-8 -*-
"""Escreve o oficio em .docx reaproveitando um oficio real como molde.

Mesma escolha do gerador de notas: nada de python-docx. Um .docx e um zip de
XML; copiamos todas as pecas do molde (timbre no cabecalho, rodape com "fls.",
estilos, tema, imagens) e trocamos so word/document.xml, mantendo o <w:sectPr>
original - papel, margens e a ligacao com cabecalho e rodape vem do arquivo do
cartorio, nao de numeros escritos aqui.

As medidas de paragrafo foram lidas dos oficios de 2026 (RGI/2026/014 e
vizinhos), em twips (1 cm = 566,93) e entrelinhas em 240 avos.
"""
import re
import zipfile
from pathlib import Path

ARIAL_12 = 24                     # meio-pontos
SIMPLES, UM_E_QUINZE, UM_E_MEIO = 240, 276, 360
RECUO_CORPO = 708                 # 1,25 cm na 1a linha
RECUO_VOCATIVO = 1440             # 2,54 cm na 1a linha
RECUO_CITACAO = 1416              # 2,50 cm a esquerda

FORMATO = {
    #                alinhamento  recuo                                         entrelinhas  depois
    "data":         ("right",  "",                                              UM_E_MEIO,   0),
    "numero":       ("both",   "",                                              UM_E_QUINZE, 0),
    "dest":         ("both",   "",                                              UM_E_QUINZE, 0),
    "dest_nome":    ("both",   "",                                              UM_E_QUINZE, 0),
    "dest_cidade":  ("both",   "",                                              UM_E_QUINZE, 0),
    "assunto":      ("both",   "",                                              UM_E_QUINZE, 0),
    "vocativo":     ("both",   f'<w:ind w:firstLine="{RECUO_VOCATIVO}"/>',      UM_E_QUINZE, 0),
    "corpo":        ("both",   f'<w:ind w:firstLine="{RECUO_CORPO}"/>',         UM_E_MEIO,   0),
    "cit_titulo":   ("both",   f'<w:ind w:left="{RECUO_CITACAO}"/>',            SIMPLES,     60),
    "cit_artigo":   ("both",   f'<w:ind w:left="{RECUO_CITACAO}"/>',            SIMPLES,     120),
    "atenciosamente": ("both", f'<w:ind w:firstLine="{RECUO_VOCATIVO}"/>',      UM_E_QUINZE, 0),
    "assina_nome":  ("center", "",                                              UM_E_QUINZE, 0),
    "assina_cargo": ("center", "",                                              UM_E_QUINZE, 0),
    "vazio":        ("both",   "",                                              UM_E_QUINZE, 0),
}


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _run(texto, marcas):
    prop = ('<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
            f'<w:sz w:val="{ARIAL_12}"/><w:szCs w:val="{ARIAL_12}"/>')
    if "negrito" in marcas:
        prop = "<w:b/><w:bCs/>" + prop
    if "italico" in marcas:
        prop = prop.replace("<w:sz ", "<w:i/><w:iCs/><w:sz ")
    if "sublinhado" in marcas:
        prop += '<w:u w:val="single"/>'
    # ordem do esquema: rFonts, b, i, ..., sz, szCs, u
    prop = _ordena(prop)
    return f'<w:r><w:rPr>{prop}</w:rPr><w:t xml:space="preserve">{_esc(texto)}</w:t></w:r>'


ORDEM = ["rFonts", "b", "bCs", "i", "iCs", "sz", "szCs", "u"]


def _ordena(prop):
    pecas = re.findall(r"<w:(\w+)[^>]*/>", prop)
    inteiras = re.findall(r"<w:\w+[^>]*/>", prop)
    pares = sorted(zip(pecas, inteiras), key=lambda x: ORDEM.index(x[0]))
    return "".join(p for _, p in pares)


def _paragrafo(bloco):
    jc, ind, linha, depois = FORMATO[bloco.papel]
    ppr = (f'<w:pPr><w:spacing w:after="{depois}" w:line="{linha}" w:lineRule="auto"/>'
           f'{ind}<w:jc w:val="{jc}"/>'
           '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
           f'<w:sz w:val="{ARIAL_12}"/><w:szCs w:val="{ARIAL_12}"/></w:rPr></w:pPr>')
    runs = "".join(_run(t, m) for t, m in bloco.partes if t)
    return f"<w:p>{ppr}{runs}</w:p>"


def _abertura_e_sect(molde_xml):
    abertura = re.search(r"<w:document[^>]*>", molde_xml).group(0)
    sect = re.search(r"<w:sectPr[ >].*?</w:sectPr>", molde_xml, re.S)
    return abertura, (sect.group(0) if sect else "")


def monta(blocos, molde):
    """Bytes do .docx pronto."""
    molde = Path(molde)
    if not molde.is_file():
        raise FileNotFoundError(f"molde nao encontrado: {molde}")
    with zipfile.ZipFile(molde) as z:
        original = z.read("word/document.xml").decode("utf-8")
        pecas = [(i, z.read(i.filename)) for i in z.infolist()
                 if i.filename != "word/document.xml"]

    abertura, sect = _abertura_e_sect(original)
    corpo = "".join(_paragrafo(b) for b in blocos)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
           f"{abertura}<w:body>{corpo}{sect}</w:body></w:document>")

    import io
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        for info, dados in pecas:
            z.writestr(info, dados)
        z.writestr("word/document.xml", doc.encode("utf-8"))
    return saida.getvalue()


def grava(blocos, molde, destino):
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(monta(blocos, molde))
    return destino
