# -*- coding: utf-8 -*-
"""Ponto de entrada da implantação no Vercel.

Mesmo arranjo do gerador de notas: reaproveita o manipulador da máquina do
cartório (oficios/servidor.py) e só resolve as diferenças de ambiente. Lá o
disco é somente leitura e não há T:\\ - SOMENTE_LEITURA (variável VERCEL)
desliga a sugestão de número e faz o ofício voltar como download.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from oficios.servidor import Manipulador, Redator          # noqa: E402

Manipulador.redator = Redator()


class handler(Manipulador):
    """O Vercel procura por uma classe chamada 'handler'."""

    def _normaliza(self):
        if self.path.startswith("/api/index"):
            self.path = self.path[len("/api/index"):] or "/"

    def do_GET(self):
        self._normaliza()
        super().do_GET()

    def do_POST(self):
        self._normaliza()
        super().do_POST()
