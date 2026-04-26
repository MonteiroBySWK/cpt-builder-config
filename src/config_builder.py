"""
config_builder.py - Orquestra todo o processo de geração de configurações.
"""
import os
from typing import Dict

from src.config_manager import ConfigManager
from src.yaml_loader import YamlLoader
from src.gateway_manager import GatewayManager
from src.network_graph import NetworkGraph
from src.router_config import RouterConfigGenerator
from src.switch_config import SwitchConfigGenerator


class ConfigBuilder:
    """Orquestra carregamento, validação e geração de configs."""

    def __init__(
        self,
        output_dir: str = "configs",
        config_file: str = "config.yml",
        nets_file: str = "networks.yml",
        topo_file: str = "topology.yml",
    ):
        """
        Inicializa builder.

        Args:
            output_dir: Diretório para salvar configs geradas
            config_file: Caminho de config.yml
            nets_file: Caminho de networks.yml
            topo_file: Caminho de topology.yml
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Carregar YAMLs primeiro para obter variáveis (x, y, w, z)
        self.yaml_loader = YamlLoader(nets_file, topo_file)
        self.topology = self.yaml_loader.topology
        self.variables = self.yaml_loader.variables

        # Carregar configurações globais passando as variáveis
        self.config = ConfigManager(config_file, topo_file, variables=self.variables)

        # Processar dados
        self.network_entries, self.host_ips = self._collect_network_entries()
        self.gateway_mgr = GatewayManager(self.network_entries, self.host_ips)
        self.network_graph = NetworkGraph(self.topology)

        # Validar
        self.config.validate()

    def _collect_network_entries(self) -> tuple:
        """
        Coleta entradas de rede do networks.yml.

        Retorna:
            (network_entries: list, host_ips: set)
        """
        entries = []
        host_ips = set()

        for name, data in self.yaml_loader.get_networks().items():
            if not data:
                continue

            # Rede única
            if "network" in data:
                entry = {
                    "owner": name,
                    "network": data["network"],
                    "mask": int(data["mask"]),
                    "hosts": data.get("hosts", []),
                }
                entries.append(entry)
                for h in entry["hosts"]:
                    if isinstance(h, dict) and h.get("ip"):
                        host_ips.add(h["ip"])

            # Múltiplas VLANs
            elif "vlans" in data:
                for vlan in data["vlans"]:
                    entry = {
                        "owner": name,
                        "vlan": vlan.get("vlan"),
                        "network": vlan["network"],
                        "mask": int(vlan["mask"]),
                        "hosts": vlan.get("hosts", []),
                    }
                    entries.append(entry)
                    for h in entry["hosts"]:
                        if isinstance(h, dict) and h.get("ip"):
                            host_ips.add(h["ip"])

        return entries, host_ips

    def build(self) -> Dict[str, str]:
        """
        Constrói e retorna todas as configurações.

        Retorna:
            Dict[device_name] -> config_string
        """
        configs = {}

        # Gerar configs de roteadores
        router_gen = RouterConfigGenerator(
            self.config,
            self.topology,
            self.gateway_mgr.get_all(),
            self.network_graph,
        )
        configs.update(router_gen.generate_all())

        # Gerar configs de switches
        switch_gen = SwitchConfigGenerator(
            self.config,
            self.topology,
            self.gateway_mgr.get_all(),
        )
        configs.update(switch_gen.generate_all())

        return configs

    def save(self, configs: Dict[str, str]) -> None:
        """
        Salva configurações em arquivos.

        Args:
            configs: Dict[device_name] -> config_string
        """
        for name, cfg in configs.items():
            safe = name.replace("/", "_").replace(" ", "_")
            path = os.path.join(self.output_dir, f"{safe}.cfg")
            with open(path, "w", encoding="utf-8") as f:
                f.write(cfg)

        print(f"✓ Configs gerados em: {self.output_dir}")

    def build_and_save(self) -> None:
        """Build e salva em uma única chamada."""
        configs = self.build()
        self.save(configs)
