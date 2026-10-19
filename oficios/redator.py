# -*- coding: utf-8 -*-
"""Monta o oficio: data, numero, destinatario, assunto, vocativo, corpo, fecho
e assinatura.

A saida e uma lista de blocos neutros - cada bloco diz seu papel e traz o texto
ja em pedacos com marcas (negrito, italico, sublinhado). Quem transforma isso em
.docx e oficios/documento.py; separar os dois deixa o texto testavel sem abrir
o Word, e a mesma lista alimenta a previa da tela.

Linguagem dos modelos (dados/modelos.json):

  {campo}          valor digitado pelo escrevente. Campo de data ("tipo":
                   "data") sai por extenso ou dd/mm/aaaa, conforme "formato";
  {campo.chave}    variante de um campo de escolha: a opcao escolhida traz o
                   texto de cada chave ("inscrito"/"inscrita", "do de cujus");
  {oficio_recebido}, {processo}
                   os numeros informados no bloco "Ofício recebido" da tela;
  {pronome}        "Vossa Excelência" ou "Vossa Senhoria", conforme o
                   destinatario;
  {lo_la}          "lo" ou "la", conforme o genero do destinatario
                   ("A par de cumprimentá-{lo_la}");
  {quem_assina}    "Nome, Cargo" de quem assina (oficio escrito em 1a pessoa);
  [ ... ]          trecho opcional: some inteiro se algum campo dele ficar vazio.
                   Um paragrafo que fica vazio desaparece.
"""
import re
from dataclasses import dataclass, field
from datetime import date

from .catalogo import Catalogo

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

SEGMENTO = re.compile(r"\[([^\[\]]*)\]")
CAMPO = re.compile(r"\{(\w+)(?:\.(\w+))?\}")
# palavras que vem do destinatario ou de quem assina, nao de campo digitado
DO_CONTEXTO = ("pronome", "lo_la", "quem_assina")
# numeros do bloco "Ofício recebido", comuns a todos os modelos
DO_PEDIDO = ("oficio_recebido", "processo")


@dataclass
class Bloco:
    # data | numero | dest | dest_nome | dest_cidade | assunto | vocativo |
    # corpo | cit_titulo | cit_artigo | atenciosamente | assina_nome |
    # assina_cargo | vazio
    papel: str
    partes: list = field(default_factory=list)      # [(texto, {marcas})]


@dataclass
class Pedido:
    """Tudo que o escrevente informa para um oficio."""
    modelo: str
    setor: str = ""
    ano: str = ""
    numero: str = ""
    data: str = ""                 # AAAA-MM-DD; vazio = hoje
    destinatario: dict = field(default_factory=dict)
    oficio_recebido: str = ""
    processo: str = ""
    valores: dict = field(default_factory=dict)
    assinante: dict = field(default_factory=dict)


class CampoFaltando(ValueError):
    pass


def data_por_extenso(iso=""):
    d = date.fromisoformat(iso) if iso else date.today()
    return f"{d.day:02d} de {MESES[d.month - 1]} de {d.year}"


def data_curta(iso):
    d = date.fromisoformat(iso)
    return f"{d.day:02d}/{d.month:02d}/{d.year}"


def numero_oficio(setor, ano, numero):
    n = str(numero).strip()
    if n.isdigit():
        n = f"{int(n):03d}"
    return f"{setor}/{ano}/{n}"


class Redator:
    def __init__(self, catalogo=None):
        self.cat = catalogo or Catalogo()

    # ---------------------------------------------------------------- campos

    @staticmethod
    def _textos(m):
        textos = [m.get("assunto", ""), m.get("arquivo", "")]
        textos += [p for p in m["corpo"] if isinstance(p, str)]
        return textos

    def campos_do_modelo(self, m):
        """Campos que a tela pede para este modelo, na ordem em que aparecem."""
        vistos = []
        for t in self._textos(m):
            for nome, _ in CAMPO.findall(t):
                if nome not in DO_CONTEXTO + DO_PEDIDO and nome not in vistos:
                    vistos.append(nome)
        if m.get("fecho") == "escolha":
            vistos.append("fecho")
        return vistos

    def campos_obrigatorios(self, m):
        """Os campos fora de colchetes - faltando, o oficio nao fecha."""
        textos = [m.get("assunto", "")] + [p for p in m["corpo"] if isinstance(p, str)]
        fora = SEGMENTO.sub("", " ".join(textos))
        usados = {nome for nome, _ in CAMPO.findall(fora)}
        if m.get("fecho") == "escolha":
            usados.add("fecho")
        return [c for c in self.campos_do_modelo(m)
                if c in usados and not self.cat.campos.get(c, {}).get("padrao")]

    def _rotulo(self, nome):
        return self.cat.campos.get(nome, {}).get("rotulo", nome)

    def _valor(self, nome, chave, valores, contexto, rascunho):
        if nome in DO_CONTEXTO:
            v = contexto.get(nome, "")
            if not v:
                if rascunho:
                    return "«quem assina»"
                raise CampoFaltando("falta escolher quem assina")
            return v
        info = self.cat.campos.get(nome, {})
        bruto = str(valores.get(nome, "") or "").strip()
        if not bruto:
            if info.get("padrao"):
                bruto = info["padrao"]
            elif rascunho:
                return f"«{self._rotulo(nome)}»"
            else:
                raise CampoFaltando(f"falta preencher: {self._rotulo(nome)}")
        if chave:
            opcoes = info.get("opcoes")
            if not isinstance(opcoes, dict) or bruto not in opcoes:
                if rascunho:
                    return f"«{self._rotulo(nome)}»"
                raise CampoFaltando(f"escolha uma opção em: {self._rotulo(nome)}")
            return opcoes[bruto][chave]
        if info.get("tipo") == "data" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", bruto):
            return data_curta(bruto) if info.get("formato") == "curta" else data_por_extenso(bruto)
        return bruto

    def preenche(self, texto, valores, contexto, rascunho=False):
        def decide(m):
            dentro = m.group(1)
            for nome, _ in CAMPO.findall(dentro):
                if nome in DO_CONTEXTO:
                    continue
                v = str(valores.get(nome, "") or "").strip()
                if not v and not self.cat.campos.get(nome, {}).get("padrao"):
                    return ""
            return dentro
        texto = SEGMENTO.sub(decide, texto)
        return CAMPO.sub(lambda m: self._valor(m.group(1), m.group(2), valores,
                                               contexto, rascunho), texto)

    # ------------------------------------------------------------------ oficio

    def contexto(self, dest, assinante=None):
        """Palavras que concordam com o destinatario, nao com o modelo."""
        trat = self.cat.tratamentos.get(dest.get("tratamento", "")) or {}
        genero = dest.get("genero") or trat.get("genero") or "M"
        a = assinante or {}
        quem = ", ".join(x for x in (a.get("nome", "").strip(), a.get("cargo", "").strip()) if x)
        return {"pronome": dest.get("pronome") or trat.get("pronome") or "Vossa Senhoria",
                "lo_la": {"F": "la", "N": "lo(a)"}.get(genero, "lo"),
                "quem_assina": quem}

    def assunto(self, pedido, m, valores, contexto, rascunho=False):
        partes = []
        if m.get("referencia", True):
            if pedido.oficio_recebido.strip():
                partes.append(f"Ofício n.º {pedido.oficio_recebido.strip()}")
            if pedido.processo.strip():
                partes.append(f"Processo n.º {pedido.processo.strip()}")
        proprio = self.preenche(m.get("assunto", ""), valores, contexto, rascunho).strip()
        if proprio:
            partes.append(proprio)
        texto = " / ".join(partes)
        if texto and not texto.endswith("."):
            texto += "."
        return texto

    def _fecho(self, m, valores, rascunho):
        chave = m.get("fecho", "f1")
        if chave == "escolha":
            escolhido = str(valores.get("fecho", "") or "").strip()
            opcoes = self.cat.campos["fecho"]["opcoes"]
            if escolhido not in opcoes:
                if rascunho:
                    return "«Fecho»"
                raise CampoFaltando("escolha o fecho do ofício")
            chave = opcoes[escolhido]["id"]
        return self.cat.fechos[chave] if chave else ""

    def redige(self, pedido, rascunho=False):
        """Lista de blocos do oficio. Em rascunho, campo vazio vira «rótulo»."""
        m = self.cat.modelo(pedido.modelo)
        dest = pedido.destinatario or {}
        trat = self.cat.tratamentos.get(dest.get("tratamento", ""))
        contexto = self.contexto(dest, pedido.assinante)
        valores = dict(pedido.valores)
        if m.get("referencia", True):
            valores.update(oficio_recebido=pedido.oficio_recebido, processo=pedido.processo)

        def falta(rotulo):
            if rascunho:
                return f"«{rotulo}»"
            raise CampoFaltando(f"falta preencher: {rotulo}")

        setor = pedido.setor or (m["setor"] if m["setor"] != "*" else "") or falta("setor")
        numero = pedido.numero.strip() or falta("número do ofício")
        blocos = [
            Bloco("data", [(f"Morrinhos/GO, {data_por_extenso(pedido.data)}.", set())]),
            Bloco("numero", [("Ofício nº ", set()),
                             (numero_oficio(setor, pedido.ano or str(date.today().year), numero),
                              {"negrito"})]),
            Bloco("vazio"),
        ]

        # destinatario: tratamento, nome em negrito, linhas, cidade grifada. O
        # tratamento "orgao" nao tem linha propria: o orgao ja e o nome
        # ("À Receita Federal").
        if trat is None:
            tratamento = dest.get("tratamento", "").strip() or falta("tratamento")
        else:
            tratamento = trat["texto"]
        if tratamento:
            blocos.append(Bloco("dest", [(tratamento, set())]))
        blocos.append(Bloco("dest_nome", [(dest.get("nome", "").strip()
                                           or falta("nome do destinatário"), {"negrito"})]))
        for linha in dest.get("linhas", []):
            if linha.strip():
                blocos.append(Bloco("dest", [(linha.strip(), set())]))
        if dest.get("cidade", "").strip():
            blocos.append(Bloco("dest_cidade", [(dest["cidade"].strip(),
                                                 {"italico", "sublinhado"})]))
        blocos.append(Bloco("vazio"))

        assunto = self.assunto(pedido, m, valores, contexto, rascunho)
        if assunto:
            blocos.append(Bloco("assunto", [(m.get("rotulo_assunto", "Assunto:") + " ",
                                             {"negrito"}), (assunto, {"italico"})]))
            blocos += [Bloco("vazio"), Bloco("vazio")]

        vocativo = (dest.get("vocativo", "").strip() or (trat or {}).get("vocativo")
                    or falta("vocativo"))
        blocos += [Bloco("vocativo", [(vocativo, set())]), Bloco("vazio"), Bloco("vazio")]

        # corpo: paragrafos do modelo, citacoes de norma e o fecho
        for p in m["corpo"]:
            if isinstance(p, dict) and "citacao" in p:
                cit = self.cat.citacoes[p["citacao"]]
                blocos.append(Bloco("vazio"))
                blocos.append(Bloco("cit_titulo", [(cit["titulo"], {"negrito", "italico"})]))
                for rotulo, texto in cit["artigos"]:
                    blocos.append(Bloco("cit_artigo", [(rotulo + " ", {"negrito", "italico"}),
                                                       (texto, {"italico"})]))
                blocos.append(Bloco("vazio"))
                continue
            texto = self.preenche(p, valores, contexto, rascunho)
            # campo de texto longo: cada linha digitada vira um paragrafo
            for linha in texto.split("\n"):
                if linha.strip():
                    blocos.append(Bloco("corpo", [(linha.strip(), set())]))

        fecho = self._fecho(m, valores, rascunho)
        for linha in self.preenche(fecho, {}, contexto, rascunho).split("\n"):
            if linha.strip():
                blocos.append(Bloco("corpo", [(linha.strip(), set())]))

        assinante = pedido.assinante or {}
        blocos += [Bloco("vazio"), Bloco("vazio"),
                   Bloco("atenciosamente", [(m.get("despedida", "Atenciosamente,"), set())]),
                   Bloco("vazio"), Bloco("vazio"), Bloco("vazio"),
                   Bloco("assina_nome", [(assinante.get("nome", "").strip()
                                          or falta("quem assina"), set())]),
                   Bloco("assina_cargo", [(assinante.get("cargo", "").strip()
                                           or falta("cargo de quem assina"), set())])]
        return blocos

    def nome_arquivo(self, pedido):
        """SETOR-ANO-NNN - descricao.docx, como na legenda de T:\\Oficios."""
        m = self.cat.modelo(pedido.modelo)
        setor = pedido.setor or m["setor"]
        n = pedido.numero.strip()
        n = f"{int(n):03d}" if n.isdigit() else n
        valores = dict(pedido.valores, oficio_recebido=pedido.oficio_recebido,
                       processo=pedido.processo)
        try:
            desc = self.preenche(m.get("arquivo") or m["rotulo"], valores,
                                 {"pronome": "", "lo_la": "", "quem_assina": ""})
        except CampoFaltando:
            desc = m["rotulo"]
        nome = f"{setor}-{pedido.ano or date.today().year}-{n} - {desc}"
        nome = re.sub(r'[\\/:*?"<>|]', "-", nome)
        return re.sub(r"\s+", " ", nome).strip()[:150] + ".docx"

    @staticmethod
    def em_texto(blocos):
        """Versao em texto puro, para conferir sem abrir o Word."""
        linhas = []
        for b in blocos:
            t = "".join(p for p, _ in b.partes)
            if b.papel == "data":
                t = t.rjust(90)
            elif b.papel in ("cit_titulo", "cit_artigo"):
                t = "        " + t
            elif b.papel in ("assina_nome", "assina_cargo"):
                t = t.center(90).rstrip()
            elif b.papel in ("corpo", "vocativo", "atenciosamente"):
                t = "    " + t
            linhas.append(t)
        return "\n".join(linhas)
