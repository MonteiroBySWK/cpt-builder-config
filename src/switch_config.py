"""
switch_config.py - Gera configurações de switches Cisco IOS.
"""
import ipaddress
import os
from typing import Dict, List

from src.config_manager import ConfigManager


class SwitchConfigGenerator:
    """Gera configurações de switches."""

    def __init__(self, config: ConfigManager, topology: Dict, gateway_map: Dict):
        """
        Inicializa gerador de config de switch.

        Args:
            config: ConfigManager com configurações globais
            topology: Dicionário de topologia
            gateway_map: Mapa de gateways por rede
        """
        self.config = config
        self.topology = topology
        self.gateway_map = gateway_map

    def generate_all(self) -> Dict[str, str]:
        """
        Gera configs para todos os switches.

        Retorna:
            Dict[switch_name] -> config_ios_string
        """
        configs = {}
        for switch in self.topology.get("switches", []):
            name = switch.get("name")
            configs[name] = self.generate(switch)
        return configs

    def generate(self, switch: Dict) -> str:
        """
        Gera config para um switch específico.

        Args:
            switch: Dicionário de configuração do switch

        Retorna:
            String com comandos IOS
        """
        name = switch.get("name")
        lines = []

        # Header
        lines.append("configure terminal")
        lines.append(f"hostname {name}")

        # Globais
        domain = self.config.get("global.domain_name")
        lines.append(f"ip domain-name {domain}")

        # Credenciais
        username = self.config.get("credentials.username")
        ssh_pass = os.getenv("CPT_CREDENTIALS_PASSWORD") or os.getenv("CISCO_SSH_PASS", "adminssh")
        enable_pass = os.getenv("CPT_CREDENTIALS_ENABLE_PASSWORD") or os.getenv("CISCO_ENABLE_PASS", "root")

        lines.append(f"username {username} secret {ssh_pass}")
        lines.append(f"enable secret {enable_pass}")

        # VLANs
        lines.extend(self._generate_vlans(switch))

        # Management interface
        lines.extend(self._generate_management_interface(switch))

        # Host ports (access)
        lines.extend(self._generate_host_ports(switch))

        # Uplink trunk
        lines.extend(self._generate_uplink_trunk(switch))

        # SSH/VTY
        if self.config.get("ssh.enabled"):
            vty_range = self.config.get("ssh.vty_range")
            start, end = map(int, vty_range.split())
            lines.append(f"line vty {start} {end}")
            lines.append(" login local")
            transport = self.config.get("ssh.transport")
            lines.append(f" transport input {transport}")

        lines.append("end")
        lines.append("!")

        return "\n".join(lines)

    def _generate_vlans(self, switch: Dict) -> List[str]:
        """Gera configuração de VLANs."""
        lines = []
        for vlan in switch.get("vlans", []):
            vid = vlan.get("id") or vlan.get("vlan")
            if vid:
                lines.append(f"vlan {vid}")
                lines.append(f" name VLAN{vid}")
        return lines

    def _generate_management_interface(self, switch: Dict) -> List[str]:
        """Gera interface de management."""
        lines = []
        mgmt_ip = switch.get("management_ip")

        if not mgmt_ip:
            return lines

        # Encontra VLAN da interface de management
        mgmt_vlan = None
        for vlan in switch.get("vlans", []):
            netstr = vlan.get("network")
            if netstr:
                try:
                    netobj = ipaddress.ip_network(netstr, strict=False)
                    if str(mgmt_ip).startswith(str(netobj.network_address)):
                        mgmt_vlan = vlan.get("id") or vlan.get("vlan")
                        break
                except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                    pass

        if not mgmt_vlan:
            mgmt_vlan = 1

        # Máscara
        mask = self.config.get("vlans.default_mask")
        for vlan in switch.get("vlans", []):
            if (vlan.get("id") or vlan.get("vlan")) == mgmt_vlan and vlan.get("network"):
                try:
                    netobj = ipaddress.ip_network(vlan.get("network"), strict=False)
                    mask = str(netobj.netmask)
                except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                    pass

        lines.append(f"interface Vlan{mgmt_vlan}")
        lines.append(f" ip address {mgmt_ip} {mask}")
        lines.append(" no shutdown")

        # Default gateway
        for vlan in switch.get("vlans", []):
            if (vlan.get("id") or vlan.get("vlan")) == mgmt_vlan and vlan.get("network"):
                try:
                    netobj = ipaddress.ip_network(vlan.get("network"), strict=False)
                    netkey = f"{netobj.network_address}/{netobj.prefixlen}"
                    if netkey in self.gateway_map:
                        gw = self.gateway_map[netkey]["gateway"]
                        lines.append(f"ip default-gateway {gw}")
                except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                    pass

        return lines

    def _generate_host_ports(self, switch: Dict) -> List[str]:
        """Gera configuração de portas para hosts."""
        lines = []

        # Hosts diretos no switch
        for host in switch.get("hosts", []):
            port = host.get("port") or host.get("interface")
            if port:
                vlan = switch.get("access_vlan", 1)
                lines.append(f"interface {port}")
                lines.append(f" description host {host.get('name')}")
                lines.append(f" switchport access vlan {vlan}")
                lines.append(" no shutdown")

        # Hosts dentro de VLANs
        for vlan in switch.get("vlans", []):
            for host in vlan.get("hosts", []):
                port = host.get("port") or host.get("interface")
                if port:
                    vid = vlan.get("id") or vlan.get("vlan")
                    lines.append(f"interface {port}")
                    lines.append(f" description host {host.get('name')}")
                    lines.append(f" switchport access vlan {vid}")
                    lines.append(" no shutdown")

        return lines

    def _generate_uplink_trunk(self, switch: Dict) -> List[str]:
        """Gera configuração de trunk para uplink."""
        lines = []

        if not switch.get("uplink"):
            return lines

        # Interface do uplink
        uplink_iface = switch.get("uplink_interface") or self.config.get("interfaces.switch.trunk_default")
        lines.append(f"interface {uplink_iface}")
        lines.append(f" description trunk to {switch.get('uplink')}")
        lines.append(" switchport trunk encapsulation dot1q")
        lines.append(" switchport mode trunk")

        # Native VLAN
        native_vlan = self.config.get("vlans.native_vlan")
        for vlan in switch.get("vlans", []):
            vid = vlan.get("id") or vlan.get("vlan")
            if vid == native_vlan:
                lines.append(f" switchport trunk native vlan {native_vlan}")
                break

        # Allowed VLANs
        allowed = ",".join(str(v.get("id") or v.get("vlan")) for v in switch.get("vlans", []))
        if allowed:
            lines.append(f" switchport trunk allowed vlan {allowed}")

        lines.append(" no shutdown")

        return lines
