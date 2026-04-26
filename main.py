#!/usr/bin/env python3
"""
main.py - Refatorizado com arquitetura OOP.

Gera configurações Cisco IOS prontas para copiar/colar em roteadores e switches
a partir de `networks.yml`, `topology.yml` e `config.yml`.

Uso:
  python3 main.py

Configuração:
  1. Editar config.yml para defaults globais
  2. Editar .env para credenciais sensíveis (ssh_pass, enable_pass)
  3. Editar networks.yml e topology.yml para topologia específica

Dependências:
  - PyYAML (pip install pyyaml)
"""
import sys
import os

# Adicionar src ao path
sys.path.insert(0, os.path.dirname(__file__))

from src.config_builder import ConfigBuilder


def main():
    """Função principal."""
    try:
        builder = ConfigBuilder(
            output_dir="configs",
            config_file="config.yml",
            nets_file="networks.yml",
            topo_file="topology.yml",
        )
        builder.build_and_save()

    except ImportError as e:
        print(f"Erro: dependência não instalada: {e}")
        print("Instale com: pip install pyyaml")
        sys.exit(1)

    except FileNotFoundError as e:
        print(f"Erro: arquivo não encontrado: {e}")
        sys.exit(1)

    except ValueError as e:
        print(f"Erro de validação: {e}")
        sys.exit(1)

    except Exception as e:
        print(f"Erro inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
