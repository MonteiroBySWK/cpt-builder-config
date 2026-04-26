"""
config_manager.py - Gerenciador de configurações centralizado.
"""
import os
from typing import Any, Dict, Optional
import yaml


class ConfigManager:
    """Gerencia carregamento hierarchico de configurações."""

    # Defaults globais
    DEFAULTS = {
        "global": {
            "domain_name": "example.com",
        },
        "ssh": {
            "enabled": True,
            "vty_range": "0 4",
            "transport": "ssh",
        },
        "credentials": {
            "username": "admin",
            "password": "adminssh",
            "enable_password": "root",
        },
        "interfaces": {
            "router": {
                "default_prefix": "GigabitEthernet",
                "default_slot": 0,
                "default_port": 0,
                "p2p_prefix": "Serial",
                "p2p_slot": "0/0",
            },
            "switch": {
                "trunk_default": "GigabitEthernet0/1",
            },
        },
        "vlans": {
            "native_vlan": 99,
            "default_mask": "255.255.255.0",
        },
        "routing": {
            "p2p_mask": "255.255.255.252",
        },
        "security": {
            "password_encryption": True,
            "aaa_enabled": False,
        },
    }

    def __init__(self, config_file: str = "config.yml", topology_file: str = "topology.yml", variables: Optional[Dict] = None):
        """Inicializa ConfigManager."""
        self.config_file = config_file
        self.topology_file = topology_file
        self.variables = variables or {}
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações em ordem de prioridade."""
        config = self._deep_copy(self.DEFAULTS)

        if os.path.exists(self.config_file):
            yaml_config = self._load_yaml(self.config_file)
            if yaml_config:
                config = self._deep_merge(config, yaml_config)

        if os.path.exists(self.topology_file):
            topo = self._load_yaml(self.topology_file)
            if topo and "global_config" in topo:
                config = self._deep_merge(config, topo["global_config"])

        config = self._merge_env_vars(config)
        
        # Aplicar substituição de variáveis
        if self.variables:
            config = self._apply_variables(config)
            
        return config

    def _apply_variables(self, data: Any) -> Any:
        """Recursivamente substitui variáveis (x, y, w, z) nos valores."""
        if isinstance(data, dict):
            return {k: self._apply_variables(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._apply_variables(i) for i in data]
        elif isinstance(data, str):
            for var_name, var_value in self.variables.items():
                if not isinstance(var_name, str):
                    continue
                parts = data.split('.')
                new_parts = []
                for p in parts:
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

    def _load_yaml(self, path: str) -> Optional[Dict[str, Any]]:
        """Carrega arquivo YAML."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else None
        except Exception as e:
            raise ValueError(f"Erro ao carregar {path}: {e}")

    def _deep_copy(self, d: Dict) -> Dict:
        """Cópia profunda de dicionário."""
        return {k: (self._deep_copy(v) if isinstance(v, dict) else v) for k, v in d.items()}

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Mescla dicts recursivamente."""
        result = self._deep_copy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _merge_env_vars(self, config: Dict) -> Dict:
        """Mescla variáveis de ambiente."""
        for key, value in os.environ.items():
            if not key.startswith("CPT_"):
                continue
            path = key[4:].lower().split("_")
            current = config
            for i, part in enumerate(path[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[path[-1]] = self._parse_env_value(value)
        return config

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Converte string de env var para tipo."""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        if value.isdigit():
            return int(value)
        return value

    def get(self, path: str, default: Any = None) -> Any:
        """Obtém valor via dot-notation."""
        keys = path.split(".")
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def get_section(self, section: str) -> Dict[str, Any]:
        """Obtém uma seção inteira."""
        return self.get(section, {})

    def validate(self) -> bool:
        """Valida configuração crítica."""
        if self.get("credentials.username") is None:
            raise ValueError("credentials.username não definido")
        if self.get("credentials.password") is None:
            raise ValueError("credentials.password não definido")
        if self.get("credentials.enable_password") is None:
            raise ValueError("credentials.enable_password não definido")
        return True

    def __repr__(self) -> str:
        return f"<ConfigManager domain={self.get('global.domain_name')}>"
