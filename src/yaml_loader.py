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

        # Extrair variáveis de substituição (x, y, w, z)
        self.variables = self.networks.get("base", {})

        # Aplicar substituição nas redes e topologia
        self.networks = self._apply_variables(self.networks)

        self.topology = self._load_topology(topo_file)
        self.topology = self._apply_variables(self.topology)

    def _apply_variables(self, data: Any) -> Any:
        """Recursivamente substitui variáveis (x, y, w, z) nos valores."""
        if isinstance(data, dict):
            return {k: self._apply_variables(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._apply_variables(i) for i in data]
        elif isinstance(data, str):
            # Substitui cada variável definida no bloco base
            original = data
            for var_name, var_value in self.variables.items():
                if not isinstance(var_name, str):
                    continue
                # Substitui a letra isolada (ex: .x. por .1.)
                # Tratamos tanto o caso de estar no meio quanto no fim/início
                # Ex: 172.16.x.1 ou x.y.w.z
                parts = data.split('.')
                new_parts = []
                for p in parts:
                    # Se a parte for exatamente o nome da variável (ou contiver a variável antes da máscara /)
                    if "/" in p:
                        octet, mask = p.split("/", 1)
                        if octet.lower() == var_name.lower():
                            new_parts.append(f"{var_value}/{mask}")
                        else:
                            new_parts.append(p)
                    elif p.lower() == var_name.lower():
                        new_parts.append(str(var_value))
                    else:
                        new_parts.append(p)
                data = ".".join(new_parts)
            return data
        return data

    @staticmethod


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
