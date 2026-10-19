# -*- coding: utf-8 -*-
"""Serve a tela do gerador de oficios no navegador, a partir da propria maquina.

Mesma arquitetura do gerador de notas devolutivas: http.server da biblioteca
padrao, so em 127.0.0.1 e em porta sorteada - nada fica exposto na rede do
cartorio. A aparencia e HTML e CSS em public/.

A pasta de oficios enviados (T:\\Oficios\\Enviados) e so LIDA: dela sai o
proximo numero sugerido para cada setor. O oficio gerado vai para saida/, e o
escrevente o leva para a pasta do setor depois de conferir.
"""
import base64
import json
import os
import re
import subprocess
import threading
import urllib.parse
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .catalogo import BASE
from .redator import CampoFaltando, Pedido, Redator
from . import documento

WEB = BASE / "public"
MOLDE = BASE / "modelo" / "molde-oficio.docx"
SAIDA = BASE / "saida"

# No Vercel o disco e somente leitura e nao ha T:\: o oficio volta como
# download e a sugestao de numero fica desligada.
SOMENTE_LEITURA = bool(os.environ.get("VERCEL"))
ENVIADOS = Path(os.environ.get("OFICIOS_ENVIADOS", r"T:\Oficios\Enviados"))

TIPOS = {".html": "text/html; charset=utf-8",
         ".css": "text/css; charset=utf-8",
         ".js": "text/javascript; charset=utf-8",
         ".svg": "image/svg+xml"}


def catalogo_para_tela(r):
    cat = r.cat
    return {
        "somente_leitura": SOMENTE_LEITURA,
        "ano": date.today().year,
        "hoje": date.today().isoformat(),
        "setores": cat.setores,
        "campos": cat.campos,
        "tratamentos": cat.tratamentos,
        "destinatarios": list(cat.destinatarios.values()),
        "assinantes": list(cat.assinantes.values()),
        "modelos": [{"id": m["id"], "rotulo": m["rotulo"], "setor": m["setor"],
                     "grupo": m.get("grupo", ""), "descricao": m.get("descricao", ""),
                     "destinatario": m.get("destinatario", ""),
                     "referencia": m.get("referencia", True),
                     "campos": r.campos_do_modelo(m),
                     "obrigatorios": r.campos_obrigatorios(m)}
                    for m in cat.modelos.values()],
    }


def _numeros_em(pasta, setor, ano):
    """Numeros ja usados, lidos dos nomes de arquivo (RGI-2026-014 - ...)."""
    if not pasta.is_dir():
        return []
    padrao = re.compile(rf"^(?:Of[ií]cio n\.?º\s*)?{setor}I?[-\s/]?{ano}[-\s/]?0*(\d{{1,4}})\b",
                        re.I)
    usados = []
    for f in pasta.iterdir():
        m = padrao.match(f.name)
        if m:
            usados.append((int(m.group(1)), f.name))
    return usados


def proximo_numero(setor, ano):
    """Sugere o proximo numero do setor: o maior ja usado + 1.

    Olha a pasta do setor no ano (somente leitura) e tambem saida/, para nao
    sugerir de novo um numero gerado hoje e ainda nao arquivado.
    """
    if SOMENTE_LEITURA:
        return {"numero": "", "motivo": "sem acesso à pasta de ofícios enviados"}
    usados = _numeros_em(ENVIADOS / setor / str(ano), setor, ano)
    pasta_lida = (ENVIADOS / setor / str(ano)).is_dir()
    usados += _numeros_em(SAIDA, setor, ano)
    if not usados:
        motivo = ("nenhum ofício deste setor no ano" if pasta_lida
                  else f"pasta {ENVIADOS / setor / str(ano)} não encontrada")
        return {"numero": "1" if pasta_lida else "", "motivo": motivo}
    n, ultimo = max(usados)
    return {"numero": str(n + 1), "ultimo": ultimo}


def pedido_de(dados):
    return Pedido(modelo=dados.get("modelo", ""), setor=dados.get("setor", ""),
                  ano=str(dados.get("ano", "")), numero=str(dados.get("numero", "")),
                  data=dados.get("data", ""), destinatario=dados.get("destinatario", {}),
                  oficio_recebido=dados.get("oficio_recebido", ""),
                  processo=dados.get("processo", ""), valores=dados.get("valores", {}),
                  assinante=dados.get("assinante", {}))


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def previa(r, dados):
    """O oficio como vai sair. Campo em branco aparece como «rótulo»."""
    blocos = r.redige(pedido_de(dados), rascunho=True)
    html = []
    for b in blocos:
        if b.papel == "vazio":
            html.append('<div class="p-vazio"></div>')
            continue
        corpo = ""
        for texto, marcas in b.partes:
            t = _esc(texto).replace("«", '<span class="falta">«').replace("»", "»</span>")
            if "italico" in marcas:
                t = f"<em>{t}</em>"
            if "sublinhado" in marcas:
                t = f"<u>{t}</u>"
            if "negrito" in marcas:
                t = f"<strong>{t}</strong>"
            corpo += t
        html.append(f'<div class="p-{b.papel}">{corpo}</div>')
    faltando = sorted(set(re.findall(r"«([^»]+)»", "".join(
        t for b in blocos for t, _ in b.partes))))
    return {"html": "".join(html), "faltando": faltando}


class Manipulador(BaseHTTPRequestHandler):
    redator = None

    def log_message(self, *a):
        pass                      # o console fica limpo para o usuario

    def _envia(self, corpo, tipo="application/json; charset=utf-8", codigo=200):
        if isinstance(corpo, (dict, list)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        elif isinstance(corpo, str):
            corpo = corpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        caminho = url.path.lstrip("/") or "index.html"
        q = urllib.parse.parse_qs(url.query)
        if caminho == "api/catalogo":
            return self._envia(catalogo_para_tela(self.redator))
        if caminho == "api/proximo":
            setor = re.sub(r"\W", "", q.get("setor", [""])[0]).upper()
            ano = re.sub(r"\D", "", q.get("ano", [""])[0]) or str(date.today().year)
            return self._envia(proximo_numero(setor, ano))

        arquivo = (WEB / caminho).resolve()
        if not arquivo.is_file() or WEB.resolve() not in arquivo.parents:
            return self._envia({"erro": "não encontrado"}, codigo=404)
        self._envia(arquivo.read_bytes(), TIPOS.get(arquivo.suffix, "application/octet-stream"))

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tamanho) or b"{}")
        rota = urllib.parse.urlparse(self.path).path.strip("/")

        if rota == "api/abrir-pasta":
            if SOMENTE_LEITURA:
                return self._envia({"ok": False, "erro": "sem pasta local"})
            alvo = Path(dados.get("caminho", ""))
            if alvo.exists() and SAIDA.resolve() in alvo.resolve().parents:
                subprocess.Popen(["explorer", "/select,", str(alvo)])
            return self._envia({"ok": True})

        # A previa informa o erro com status 200, em 'erro': e por ele que chega
        # a tela o modelo que saiu do catalogo (aba antiga depois de mudanca).
        if rota == "api/previa":
            try:
                return self._envia(previa(self.redator, dados))
            except (ValueError, KeyError) as erro:
                return self._envia({"html": "", "erro": str(erro).strip("'\"")})

        if rota != "api/gerar":
            return self._envia({"erro": "rota desconhecida"}, codigo=404)

        pedido = pedido_de(dados)
        try:
            blocos = self.redator.redige(pedido)
            nome = self.redator.nome_arquivo(pedido)
        except (CampoFaltando, ValueError, KeyError) as erro:
            return self._envia({"ok": False, "erro": str(erro).strip("'\"")})

        conteudo = documento.monta(blocos, MOLDE)
        resposta = {"ok": True, "arquivo": nome}
        if SOMENTE_LEITURA:
            resposta["conteudo"] = base64.b64encode(conteudo).decode()
        else:
            SAIDA.mkdir(exist_ok=True)
            destino = SAIDA / nome
            if destino.exists() and not dados.get("sobrescrever"):
                return self._envia({"ok": False, "existe": True, "arquivo": nome,
                                    "erro": f"já existe um ofício com este nome em saida: {nome}"})
            destino.write_bytes(conteudo)
            resposta["caminho"] = str(destino)
        self._envia(resposta)


def main():
    if not MOLDE.is_file():
        raise SystemExit(f"molde de formatação ausente: {MOLDE}")
    Manipulador.redator = Redator()

    servidor = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORTA_OFICIO", 0))),
                                   Manipulador)
    endereco = f"http://127.0.0.1:{servidor.server_address[1]}/"
    print(f"Gerador de ofícios rodando em {endereco}")
    print("Feche esta janela para encerrar.")
    if not os.environ.get("SEM_NAVEGADOR"):
        threading.Timer(0.4, lambda: webbrowser.open(endereco)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
