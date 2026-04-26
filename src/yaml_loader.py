"""
yaml_loader.py - Carrega e valida arquivos YAML de topologia e redes.
"""
import os
from typing import Any, Dict
import yaml


class YamlLoader:
    """Carrega e valida arquivos YAML."""

    def __init__(self, nets_file: str = "networks.yml", topo_file: str = "topology.yml"):
        """
        Inicializa carregador de YAMLs.

        Args:
            nets_file: Caminho de networks.yml
            topo_file: Caminho de topology.yml
        """
        self.nets_file = nets_file
        self.topo_file = topo_file
        self.networks = self._load_yaml(nets_file)
        self.topology = self._load_topology(topo_file)

    @staticmethod
    def _load_yaml(path: str) -> Dict[str, Any]:
        """Carrega arquivo YAML com validação."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    raise ValueError(f"{path} deve conter um dicionário YAML")
                return data
        except yaml.YAMLError as e:
            raise ValueError(f"Erro ao parsear {path}: {e}")

    def _load_topology(self, path: str) -> Dict[str, Any]:
        """Carrega topology.yml e extrai seção 'topology' se existir."""
        data = self._load_yaml(path)
        # Alguns formatos colocam tudo sob chave 'topology', outros não
        return data.get("topology", data)

    def get_networks(self) -> Dict[str, Any]:
        """Retorna dicionário de redes."""
        return self.networks.get("networks", {})

    def get_routers(self) -> list:
        """Retorna lista de roteadores."""
        return self.topology.get("routers", [])

    def get_switches(self) -> list:
        """Retorna lista de switches."""
        return self.topology.get("switches", [])

    def get_links(self) -> list:
        """Retorna lista de links P2P."""
        return self.topology.get("links", [])

    def __repr__(self) -> str:
        return f"<YamlLoader routers={len(self.get_routers())} switches={len(self.get_switches())}>"
