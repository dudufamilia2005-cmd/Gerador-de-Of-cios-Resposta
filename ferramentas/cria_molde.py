# -*- coding: utf-8 -*-
"""Faz o molde de formatacao a partir de um oficio real do cartorio.

    .venv\\Scripts\\python.exe ferramentas\\cria_molde.py "T:\\Oficios\\Enviados\\RGI\\2026\\<oficio>.docx"

Copia do oficio o que e forma - timbre (cabecalho com as imagens), rodape com a
numeracao de folhas, estilos, tema, fontes, papel e margens - e joga fora o que
e conteudo: o corpo vira um documento vazio que so guarda o <w:sectPr>. Os
metadados (autor, ultimo a salvar, datas) sao zerados.

O oficio de origem so e lido. O molde sai em modelo/molde-oficio.docx, e e ele
que vai para o repositorio - nunca o oficio real, que traz dados de partes.
"""
import re
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DESTINO = BASE / "modelo" / "molde-oficio.docx"

CORE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>Ofício</dc:title><dc:creator>1º Ofício de Morrinhos/GO</dc:creator>'
        '<cp:lastModifiedBy>Gerador de Ofícios</cp:lastModifiedBy>'
        '<cp:revision>1</cp:revision>'
        '</cp:coreProperties>')


def corpo_vazio(document_xml):
    """Mantem a abertura de <w:document> (com todos os namespaces) e o sectPr."""
    abertura = re.search(r"<w:document[^>]*>", document_xml).group(0)
    sect = re.search(r"<w:sectPr[ >].*?</w:sectPr>", document_xml, re.S)
    if not sect:
        raise SystemExit("o oficio de origem nao tem <w:sectPr>: sem papel nem margens")
    # rsid identifica a sessao de edicao do Word; nao serve a nada no molde
    sect = re.sub(r' w:rsid\w*="[^"]*"', "", sect.group(0))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            f"{abertura}<w:body><w:p/>{sect}</w:body></w:document>")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    origem = Path(sys.argv[1])
    with zipfile.ZipFile(origem) as z:
        pecas = {i.filename: z.read(i.filename) for i in z.infolist()}

    pecas["word/document.xml"] = corpo_vazio(
        pecas["word/document.xml"].decode("utf-8")).encode("utf-8")
    if "docProps/core.xml" in pecas:
        pecas["docProps/core.xml"] = CORE.encode("utf-8")

    # Os cabecalhos e rodapes so podem ter forma, nunca dado de parte: se
    # aparecer CPF ou numero de processo ali, o oficio escolhido nao serve.
    for nome, dados in pecas.items():
        if re.match(r"word/(header|footer)\d*\.xml$", nome):
            texto = re.sub(r"<[^>]+>", " ", dados.decode("utf-8"))
            if re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{7}-\d{2}\.\d{4}", texto):
                raise SystemExit(f"{nome} tem CPF ou numero de processo - escolha outro oficio")

    DESTINO.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(DESTINO, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, dados in pecas.items():
            z.writestr(nome, dados)
    print(f"molde gravado em {DESTINO}")


if __name__ == "__main__":
    main()
