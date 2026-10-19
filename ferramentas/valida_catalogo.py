# -*- coding: utf-8 -*-
"""Confere o catalogo antes de confiar em qualquer oficio gerado.

    .venv\\Scripts\\python.exe ferramentas\\valida_catalogo.py

Reprova (codigo de saida 1) quando:
  - um modelo cita campo, fecho, citacao ou destinatario que nao existe;
  - um destinatario usa tratamento que nao existe;
  - algum modelo nao fecha com todos os campos preenchidos, ou sobra chave
    {assim} ou colchete no texto final;
  - o .docx gerado nao e um zip/XML valido.
Cada modelo e redigido com os exemplos dos campos e gravado num .docx em
memoria - e o mesmo caminho que a tela usa.
"""
import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from oficios.catalogo import Catalogo                      # noqa: E402
from oficios.redator import (CAMPO, DO_CONTEXTO, DO_PEDIDO,  # noqa: E402
                             Pedido, Redator)
from oficios import documento                              # noqa: E402

MOLDE = BASE / "modelo" / "molde-oficio.docx"


def valor_de_teste(nome, info):
    if info.get("opcoes"):
        op = info["opcoes"]
        return next(iter(op)) if isinstance(op, dict) else op[0]
    if info.get("tipo") == "data":
        return "2026-10-19"
    return info.get("exemplo") or info.get("padrao") or f"<{nome}>"


def main():
    erros = []
    cat = Catalogo()
    r = Redator(cat)

    for d in cat.destinatarios.values():
        if d["tratamento"] not in cat.tratamentos:
            erros.append(f"destinatário {d['id']}: tratamento '{d['tratamento']}' não existe")

    for m in cat.modelos.values():
        mid = m["id"]
        if m["setor"] != "*" and m["setor"] not in cat.setores:
            erros.append(f"{mid}: setor '{m['setor']}' não existe")
        fecho = m.get("fecho", "f1")
        if fecho not in (None, "escolha") and fecho not in cat.fechos:
            erros.append(f"{mid}: fecho '{fecho}' não existe")
        if m.get("destinatario") and m["destinatario"] not in cat.destinatarios:
            erros.append(f"{mid}: destinatário sugerido '{m['destinatario']}' não existe")
        for p in m["corpo"]:
            if isinstance(p, dict) and p.get("citacao") not in cat.citacoes:
                erros.append(f"{mid}: citação '{p.get('citacao')}' não existe")
        textos = [m.get("assunto", ""), m.get("arquivo", "")] + [
            p for p in m["corpo"] if isinstance(p, str)]
        for t in textos:
            if t.count("[") != t.count("]"):
                erros.append(f"{mid}: colchete sem par em: {t[:60]}…")
            for nome, chave in CAMPO.findall(t):
                if nome in DO_CONTEXTO + DO_PEDIDO:
                    continue
                info = cat.campos.get(nome)
                if info is None:
                    erros.append(f"{mid}: campo '{nome}' não está em 'campos'")
                    continue
                if chave:
                    op = info.get("opcoes")
                    if not isinstance(op, dict) or any(chave not in v for v in op.values()):
                        erros.append(f"{mid}: '{nome}.{chave}' — nem toda opção tem a chave '{chave}'")

        # redige de verdade, com todos os campos preenchidos
        valores = {c: valor_de_teste(c, cat.campos.get(c, {})) for c in r.campos_do_modelo(m)}
        destinatario = cat.destinatarios.get(m.get("destinatario")) or cat.destinatarios["juiz-1vara-anddre"]
        pedido = Pedido(modelo=mid, setor=m["setor"] if m["setor"] != "*" else "RGI",
                        ano="2026", numero="7", data="2026-10-19", destinatario=destinatario,
                        oficio_recebido="100/2026", processo="5000000-00.2026.8.09.0107",
                        valores=valores, assinante=cat.assinantes["matheus-antonio"])
        try:
            blocos = r.redige(pedido)
            texto = Redator.em_texto(blocos)
            sobra = re.findall(r"\{\w+(?:\.\w+)?\}|[\[\]«»]", texto)
            if sobra:
                erros.append(f"{mid}: sobrou no texto final: {sorted(set(sobra))}")
            conteudo = documento.monta(blocos, MOLDE)
            with zipfile.ZipFile(BytesIO(conteudo)) as z:
                ET.fromstring(z.read("word/document.xml"))
            r.nome_arquivo(pedido)
        except Exception as e:                                # noqa: BLE001
            erros.append(f"{mid}: não redige — {type(e).__name__}: {e}")

    if erros:
        print(f"REPROVADO — {len(erros)} problema(s):")
        for e in erros:
            print("  -", e)
        sys.exit(1)
    print(f"OK — {len(cat.modelos)} modelos, {len(cat.destinatarios)} destinatários, "
          f"{len(cat.assinantes)} assinantes, {len(cat.fechos)} fechos.")


if __name__ == "__main__":
    main()
