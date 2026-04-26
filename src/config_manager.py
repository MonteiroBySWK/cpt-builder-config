"""
config_manager.py - Gerenciador de configurações centralizado.

Carrega e mescla configurações de múltiplas fontes:
1. Defaults em código
2. config.yml
3. topology.yml (global_config)
4. Variáveis de ambiente
5. CLI arguments
"""
import os
from typing import Any, Dict, Optional
import yaml


class ConfigManager:
    """Gerencia carregamento hierarchico de configurações."""

    # Defaults globais - sensatos para a maioria dos casos
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
            # NUNCA hardcode senha - usar .env
            "enable_password": None,
        },
        "interfaces": {
            "router": {
                "default_prefix": "GigabitEthernet",
                "default_slot": 0,
                "default_port": 0,
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

    def __init__(self, config_file: str = "config.yml", topology_file: str = "topology.yml"):
        """
        Inicializa ConfigManager.

        Args:
            config_file: Caminho do arquivo config.yml
            topology_file: Caminho do arquivo topology.yml
        """
        self.config_file = config_file
        self.topology_file = topology_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Carrega configurações em ordem de prioridade (baixa -> alta).

        Retorna:
            Dict com configuração mesclada
        """
        # 1. Defaults em código
        config = self._deep_copy(self.DEFAULTS)

        # 2. config.yml (se existir)
        if os.path.exists(self.config_file):
            yaml_config = self._load_yaml(self.config_file)
            if yaml_config:
                config = self._deep_merge(config, yaml_config)

        # 3. global_config em topology.yml (se existir)
        if os.path.exists(self.topology_file):
            topo = self._load_yaml(self.topology_file)
            if topo and "global_config" in topo:
                config = self._deep_merge(config, topo["global_config"])

        # 4. Variáveis de ambiente (prefixo: CPT_)
        config = self._merge_env_vars(config)

        return config

    def _load_yaml(self, path: str) -> Optional[Dict[str, Any]]:
        """Carrega arquivo YAML com tratamento de erro."""
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
        """Mescla dicts recursivamente (override sobre base)."""
        result = self._deep_copy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _merge_env_vars(self, config: Dict) -> Dict:
        """
        Mescla variáveis de ambiente com prefixo CPT_.

        Exemplo:
            CPT_DOMAIN_NAME=uema.br → global.domain_name = "uema.br"
            CPT_SSH_ENABLED=false → ssh.enabled = False
        """
        for key, value in os.environ.items():
            if not key.startswith("CPT_"):
                continue

            # Remover prefixo e converter para lowercase
            path = key[4:].lower().split("_")

            # Navegar na config e atribuir
            current = config
            for i, part in enumerate(path[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Converter valor para tipo apropriado
            final_key = path[-1]
            current[final_key] = self._parse_env_value(value)

        return config

    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Converte string de env var para tipo apropriado."""
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False
        if value.isdigit():
            return int(value)
        return value

    def get(self, path: str, default: Any = None) -> Any:
        """
        Obtém valor de configuração via dot-notation.

        Args:
            path: Path separado por ponto (ex: "ssh.enabled", "interfaces.router.default_prefix")
            default: Valor padrão se chave não existir

        Retorna:
            Valor de configuração ou default
        """
        keys = path.split(".")
        current = self.config

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def get_section(self, section: str) -> Dict[str, Any]:
        """Obtém uma seção inteira de configuração."""
        return self.get(section, {})

    def validate(self) -> bool:
        """
        Valida configuração crítica.

        Levanta:
            ValueError: Se configuração for inválida
        """
        # Credenciais sensíveis devem estar em .env, não em arquivo
        if self.get("credentials.username") is None:
            raise ValueError("credentials.username não definido")

        password = os.getenv("CPT_CREDENTIALS_PASSWORD") or os.getenv("CISCO_SSH_PASS")
        if not password:
            raise ValueError("Senha SSH não definida em variáveis de ambiente (CPT_CREDENTIALS_PASSWORD ou CISCO_SSH_PASS)")

        enable_pass = os.getenv("CPT_CREDENTIALS_ENABLE_PASSWORD") or os.getenv("CISCO_ENABLE_PASS")
        if not enable_pass:
            raise ValueError("Enable password não definida (CPT_CREDENTIALS_ENABLE_PASSWORD ou CISCO_ENABLE_PASS)")

        # Validar formato de domínio
        domain = self.get("global.domain_name")
        if not domain or "." not in domain:
            raise ValueError(f"Domain name inválido: {domain}")

        return True

    def __repr__(self) -> str:
        return f"<ConfigManager domain={self.get('global.domain_name')}>"
