#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py - Gerador de executável portátil.

Gera um único arquivo executável que lê os arquivos .yml externos
localizados na mesma pasta que ele.
"""

import os
import subprocess
import sys
import shutil
import io

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_NAME = "main.py"
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")

# Fix encoding for Windows support with UTF-8 characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def clean_old_builds():
    """Limpa diretórios de build de forma portável."""
    for folder in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(folder):
            print(f"Limpando {folder}...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Aviso: não foi possível remover {folder}: {e}")

def run_pyinstaller():
    """Executa o PyInstaller para gerar o executável único."""
    
    # 1. Verificar se o script principal existe
    main_path = os.path.join(BASE_DIR, SCRIPT_NAME)
    if not os.path.exists(main_path):
        print(f"Erro: {SCRIPT_NAME} não encontrado.")
        sys.exit(1)

    # 2. Construir o comando
    pyi_exec = shutil.which("pyinstaller")
    if pyi_exec:
        cmd = [pyi_exec]
    else:
        cmd = [sys.executable, "-m", "PyInstaller"]

    sep = os.pathsep

    cmd.extend([
        "--noconfirm",
        "--onefile",
        "--name", "cisco_gen",
        "--clean",
        "--add-data", f"src{sep}src",  # Inclui a pasta src no bundle
        main_path
    ])

    try:
        print(f"Executando: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        print("\n" + "="*50)
        print("✓ Executável portátil gerado com sucesso!")
        print(f"Local: {os.path.join(DIST_DIR, 'cisco_gen')}")
        print("\nComo usar no Pendrive:")
        print("1. Copie o arquivo 'cisco_gen' para o pendrive.")
        print("2. Coloque seus arquivos .yml na mesma pasta que o 'cisco_gen'.")
        print("3. O programa lerá os YAMLs externos e gerará a pasta 'configs/'.")
        print("="*50)

    except subprocess.CalledProcessError as e:
        print(f"Erro durante o build com PyInstaller: {e}")
        sys.exit(1)

if __name__ == "__main__":
    clean_old_builds()
    run_pyinstaller()
