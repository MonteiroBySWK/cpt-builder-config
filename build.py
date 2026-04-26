#!/usr/bin/env python3
"""
build.py

Script para automatizar o processo de geração de executáveis com PyInstaller.

Uso:
  python3 build.py

Dependências:
  - PyInstaller (instalado no ambiente virtual)
"""
import os
import subprocess
import sys
import shutil

BASE_DIR = os.path.dirname(__file__)
SCRIPT_NAME = "main.py"
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")


def run_pyinstaller():
    """Executa o PyInstaller para gerar o executável."""
    # localizar o executável do PyInstaller: preferir .venv, depois PATH, depois módulo
    venv_pyi = os.path.join(BASE_DIR, ".venv", "bin", "pyinstaller")
    if os.path.exists(venv_pyi):
        pyi_exec = venv_pyi
    else:
        pyi_exec = shutil.which("pyinstaller")
        if not pyi_exec:
            # fallback para executar como módulo com o mesmo interpretador usado para o build
            pyi_exec = f"{sys.executable} -m PyInstaller"

    sep = os.pathsep  # ':' em Unix, ';' em Windows

    pyinstaller_cmd = []
    # se pyi_exec contém espaço (ex: 'python -m PyInstaller'), devemos passar como lista ao shell
    if pyi_exec.startswith(sys.executable):
        # chamar via interprete -m PyInstaller
        pyinstaller_cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile"]
    else:
        pyinstaller_cmd = [pyi_exec, "--noconfirm", "--onefile"]

    # adicionar arquivos de dados (YAMLs) ao bundle
    for fname in ("networks.yml", "topology.yml"):
        src = os.path.join(BASE_DIR, fname)
        if os.path.exists(src):
            pyinstaller_cmd.extend(["--add-data", f"{src}{sep}."])
        else:
            print(f"Aviso: não encontrou {src}; o arquivo não será incluído no bundle.")

    # alvo: script principal
    pyinstaller_cmd.append(os.path.join(BASE_DIR, SCRIPT_NAME))

    try:
        print("Executando PyInstaller...")
        subprocess.run(pyinstaller_cmd, check=True)
        print(f"Executável gerado em: {DIST_DIR}")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar PyInstaller: {e}")
        sys.exit(1)


def main():
    """Função principal para orquestrar o build."""
    if not os.path.exists(os.path.join(BASE_DIR, ".venv")):
        print("Ambiente virtual não encontrado. Certifique-se de ativá-lo antes de executar este script.")
        sys.exit(1)

    if not os.path.exists(os.path.join(BASE_DIR, SCRIPT_NAME)):
        print(f"Script {SCRIPT_NAME} não encontrado no diretório base.")
        sys.exit(1)

    # Limpar diretórios antigos
    if os.path.exists(DIST_DIR):
        print("Limpando diretório dist/...")
        subprocess.run(["rm", "-rf", DIST_DIR])

    if os.path.exists(BUILD_DIR):
        print("Limpando diretório build/...")
        subprocess.run(["rm", "-rf", BUILD_DIR])

    # Executar o PyInstaller
    run_pyinstaller()


if __name__ == "__main__":
    main()