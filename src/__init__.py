"""
src - Módulo com classes para geração de configurações Cisco IOS.

Arquitetura:
  ConfigManager
    └─ Carrega config.yml, topology.yml, variáveis de ambiente
  
  YamlLoader
    └─ Carrega networks.yml e topology.yml
  
  NetworkGraph
    └─ Constrói grafo de adjacência e mapeia redes a dispositivos
  
  GatewayManager
    └─ Atribui IPs de gateway automaticamente
  
  RouterConfigGenerator
    └─ Gera configurações de roteadores usando classes acima
  
  SwitchConfigGenerator
    └─ Gera configurações de switches usando classes acima
  
  ConfigBuilder
    └─ Orquestra todo o pipeline: load -> validate -> generate -> save
"""

from src.config_manager import ConfigManager
from src.yaml_loader import YamlLoader
from src.network_graph import NetworkGraph
from src.gateway_manager import GatewayManager
from src.router_config import RouterConfigGenerator
from src.switch_config import SwitchConfigGenerator
from src.config_builder import ConfigBuilder

__all__ = [
    "ConfigManager",
    "YamlLoader",
    "NetworkGraph",
    "GatewayManager",
    "RouterConfigGenerator",
    "SwitchConfigGenerator",
    "ConfigBuilder",
]
