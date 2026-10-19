# -*- coding: utf-8 -*-
"""Le os cadastros de dados/: modelos de oficio, destinatarios e assinantes.

Tudo que e texto do oficio mora em JSON, editavel sem programar. Este modulo so
carrega, indexa e aponta erro de digitacao no cadastro - quem monta o oficio e
oficios/redator.py.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DADOS = BASE / "dados"


def _le(nome):
    return json.loads((DADOS / nome).read_text(encoding="utf-8"))


class Catalogo:
    def __init__(self):
        m = _le("modelos.json")
        self.setores = m["setores"]
        self.campos = m["campos"]
        self.fechos = {k: v["texto"] for k, v in m["fechos"].items()}
        self.citacoes = m.get("citacoes", {})
        # Modelo com "fecho": "escolha" (a resposta livre) pede o fecho na
        # tela; a lista sai dos proprios fechos cadastrados.
        self.campos["fecho"] = {
            "rotulo": "Fecho",
            "opcoes": {v["rotulo"]: {"id": k} for k, v in m["fechos"].items()},
        }
        self.modelos = {}
        for t in m["modelos"]:
            if t["id"] in self.modelos:
                raise ValueError(f"modelo repetido em modelos.json: {t['id']}")
            self.modelos[t["id"]] = t

        d = _le("destinatarios.json")
        self.tratamentos = d["tratamentos"]
        self.destinatarios = {x["id"]: x for x in d["destinatarios"]}

        a = _le("assinantes.json")
        self.assinantes = {x["id"]: x for x in a["assinantes"]}

    def modelo(self, mid):
        try:
            return self.modelos[mid]
        except KeyError:
            raise KeyError(f"o modelo '{mid}' não existe mais no catálogo — "
                           "atualize a página") from None

    def destinatario(self, did):
        return self.destinatarios.get(did)
