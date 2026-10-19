@echo off
title Oficios de resposta - 1 Oficio de Morrinhos
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Preparando o ambiente pela primeira vez...
  py -3 -m venv .venv
)
".venv\Scripts\python.exe" -m oficios.servidor
