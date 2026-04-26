"""
router_config.py - Gera configurações de roteadores Cisco IOS.
"""
import ipaddress
import os
from typing import Dict, List, Optional

from src.config_manager import ConfigManager
from src.network_graph import NetworkGraph


class RouterConfigGenerator:
    """Gera configurações de roteadores."""

    def __init__(self, config: ConfigManager, topology: Dict, gateway_map: Dict, network_graph: NetworkGraph):
        """
        Inicializa gerador de config de router.

        Args:
            config: ConfigManager com configurações globais
            topology: Dicionário de topologia
            gateway_map: Mapa de gateways por rede
            network_graph: NetworkGraph para routing
        """
        self.config = config
        self.topology = topology
        self.gateway_map = gateway_map
        self.network_graph = network_graph

    def generate_all(self) -> Dict[str, str]:
        """
        Gera configs para todos os roteadores.

        Retorna:
            Dict[router_name] -> config_ios_string
        """
        configs = {}
        for router in self.topology.get("routers", []):
            name = router.get("name")
            configs[name] = self.generate(router)
        return configs

    def generate(self, router: Dict) -> str:
        """
        Gera config para um roteador específico.

        Args:
            router: Dicionário de configuração do roteador

        Retorna:
            String com comandos IOS
        """
        name = router.get("name")
        lines = []

        # Header
        lines.append("configure terminal")
        lines.append(f"hostname {name}")

        # Globais
        domain = self.config.get("global.domain_name")
        lines.append(f"ip domain-name {domain}")

        # Credenciais
        username = self.config.get("credentials.username")
        ssh_pass = self.config.get("credentials.password")
        enable_pass = self.config.get("credentials.enable_password")

        lines.append(f"username {username} secret {ssh_pass}")
        lines.append(f"enable secret {enable_pass}")

        if self.config.get("security.password_encryption"):
            lines.append("service password-encryption")

        # Interfaces LAN e P2P
        lines.extend(self._generate_interfaces(router))

        # Default route
        lines.extend(self._generate_default_route(router))

        # Static routes
        lines.extend(self._generate_static_routes(router))

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

    def _generate_interfaces(self, router: Dict) -> List[str]:
        """Gera configuração de interfaces (LAN, P2P e Internet)."""
        lines = []
        name = router.get("name")

        lan_connects = [c for c in router.get("connects", []) if c.get("type") == "lan"]
        p2p_connects = [c for c in router.get("connects", []) if c.get("type") == "p2p"]
        internet_connects = [c for c in router.get("connects", []) if c.get("type") == "internet"]

        # Conta total de redes em todas as LANs
        total_lan_networks = sum(len(self._extract_networks(c)) for c in lan_connects)

        # Router-on-a-stick (múltiplas redes na mesma LAN ou múltiplos LANs)
        if total_lan_networks > 1:
            lines.extend(self._generate_subinterfaces(router, lan_connects))
        else:
            lines.extend(self._generate_simple_lan_interfaces(router, lan_connects))

        # Links P2P (com contador persistente para evitar colisão)
        lan_iface_count = self._count_lan_interfaces(lan_connects)
        lines.extend(self._generate_p2p_interfaces(router, p2p_connects, lan_iface_count))
        
        # Links Internet
        p2p_iface_count = lan_iface_count + len(p2p_connects)
        lines.extend(self._generate_internet_interfaces(router, internet_connects, p2p_iface_count))

        return lines

    def _generate_subinterfaces(self, router: Dict, lan_connects: List[Dict]) -> List[str]:
        """Gera configuração com subinterfaces (router-on-a-stick)."""
        lines = []
        name = router.get("name")

        router_prefix = self.config.get("interfaces.router.default_prefix")
        router_slot = self.config.get("interfaces.router.default_slot")
        phys_if = f"{router_prefix}{router_slot}/0"

        for connect in lan_connects:
            nets = self._extract_networks(connect)
            for netstr in nets:
                try:
                    netobj = ipaddress.ip_network(netstr, strict=False)
                    vlan_id = self._get_vlan_id(netobj)
                    gw_ip = self._get_gateway_ip(netobj)

                    lines.append(f"interface {phys_if}.{vlan_id}")
                    lines.append(f" encapsulation dot1Q {vlan_id}")
                    lines.append(f" ip address {gw_ip} {str(netobj.netmask)}")
                    lines.append(" no shutdown")
                except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                    pass

        return lines

    def _generate_simple_lan_interfaces(self, router: Dict, lan_connects: List[Dict]) -> List[str]:
        """Gera configuração simples de LANs (sem subinterfaces)."""
        lines = []
        iface_idx = 0

        router_prefix = self.config.get("interfaces.router.default_prefix")
        router_slot = self.config.get("interfaces.router.default_slot")

        for connect in lan_connects:
            nets = self._extract_networks(connect)
            for netstr in nets:
                try:
                    netobj = ipaddress.ip_network(netstr, strict=False)
                    gw_ip = self._get_gateway_ip(netobj)

                    if connect.get("interface"):
                        phys_if = connect.get("interface")
                    else:
                        phys_if = f"{router_prefix}{router_slot}/{iface_idx}"
                        iface_idx += 1

                    lines.append(f"interface {phys_if}")
                    lines.append(f" ip address {gw_ip} {str(netobj.netmask)}")
                    lines.append(" no shutdown")
                except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                    pass

        return lines

    def _generate_p2p_interfaces(self, router: Dict, p2p_connects: List[Dict], start_idx: int = 0) -> List[str]:
        """Gera configuração de links P2P."""
        lines = []
        name = router.get("name")
        iface_idx = start_idx

        router_prefix = self.config.get("interfaces.router.p2p_prefix", "Serial")
        router_slot = self.config.get("interfaces.router.p2p_slot", "0/0")

        for connect in p2p_connects:
            link = connect.get("link")
            local_ip = connect.get("local_ip")

            if not local_ip:
                raise ValueError(f"Link P2P '{link}' sem IP local em {name}")

            mask = self._get_p2p_mask(link)

            # Tenta obter interface da definição do link
            phys_if = self._get_p2p_interface(link, name)
            if not phys_if:
                # Fallback: auto-numera
                phys_if = f"{router_prefix}{router_slot}/{iface_idx}"
                iface_idx += 1

            lines.append(f"interface {phys_if}")
            lines.append(f" description {link}")
            lines.append(f" ip address {local_ip} {mask}")
            lines.append(" no shutdown")

        return lines

    def _generate_default_route(self, router: Dict) -> List[str]:
        """Gera default route para internet."""
        lines = []
        for connect in router.get("connects", []):
            if connect.get("type") == "internet":
                remote = connect.get("remote_ip") or connect.get("remote")
                if remote:
                    lines.append(f"ip route 0.0.0.0 0.0.0.0 {remote}")
        return lines

    def _generate_static_routes(self, router: Dict) -> List[str]:
        """Gera rotas estáticas para redes não-diretas."""
        lines = []
        name = router.get("name")
        direct_nets = self._get_direct_networks(router)
        
        # Obtém todas as redes conhecidas
        all_networks = {}
        for switch in self.topology.get("switches", []):
            for vlan in switch.get("vlans", []):
                net_str = vlan.get("network")
                if net_str:
                    all_networks[net_str] = switch.get("name")
            
            if switch.get("access_vlan") == 1 and switch.get("uplink"):
                # Switch com VLAN 1 em acesso tem rede do uplink
                for router_cfg in self.topology.get("routers", []):
                    if router_cfg.get("name") == switch.get("uplink"):
                        for connect in router_cfg.get("connects", []):
                            if connect.get("type") == "lan":
                                nets = self._extract_networks(connect)
                                for net_str in nets:
                                    if "/" in net_str:
                                        all_networks[net_str] = switch.get("name")
        
        # Gera rota para cada rede não-direta
        for net_str in all_networks:
            try:
                net = ipaddress.ip_network(net_str, strict=False)
                net_key = (net.network_address, net.prefixlen)
                
                # Se não é rede direta, tenta calcular next hop
                if net_key not in direct_nets:
                    next_hop = self.network_graph.bfs_next_hop(name, net)
                    if next_hop:
                        lines.append(f"ip route {net.network_address} {net.netmask} {next_hop}")
            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                pass
        
        return lines

    def _extract_networks(self, connect: Dict) -> List[str]:
        """Extrai lista de redes de um 'connect'."""
        nets = []
        netval = connect.get("network")

        if netval:
            if isinstance(netval, str) and "/" in netval:
                nets = [netval]
            else:
                mask = connect.get("mask")
                if mask:
                    nets = [f"{netval}/{mask}"]
        else:
            nets = connect.get("networks", [])

        return nets

    def _get_gateway_ip(self, netobj: ipaddress.IPv4Network) -> str:
        """Obtém IP do gateway para uma rede."""
        key = f"{netobj.network_address}/{netobj.prefixlen}"
        if key in self.gateway_map:
            return self.gateway_map[key]["gateway"]
        return str(next(netobj.hosts()))

    def _get_vlan_id(self, netobj: ipaddress.IPv4Network) -> int:
        """Obtém VLAN ID para uma rede (procura em switches)."""
        for switch in self.topology.get("switches", []):
            for vlan in switch.get("vlans", []):
                vnet_str = vlan.get("network")
                if vnet_str:
                    try:
                        vnet = ipaddress.ip_network(vnet_str, strict=False)
                        if vnet.network_address == netobj.network_address and vnet.prefixlen == netobj.prefixlen:
                            return vlan.get("id") or vlan.get("vlan")
                    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                        pass

        # Fallback: usar último octeto da rede
        return int(str(netobj.network_address).split(".")[-1])

    def _get_p2p_mask(self, link_name: str) -> str:
        """Obtém máscara para link P2P."""
        for link in self.topology.get("links", []):
            if link.get("name") == link_name:
                netstr = link.get("network")
                if netstr:
                    try:
                        netobj = ipaddress.ip_network(netstr, strict=False)
                        return str(netobj.netmask)
                    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                        pass

        # Fallback
        return self.config.get("routing.p2p_mask")

    def _get_direct_networks(self, router: Dict) -> set:
        """Obtém conjunto de redes diretas do roteador."""
        direct = set()
        name = router.get("name")

        for connect in router.get("connects", []):
            if connect.get("type") == "lan":
                for netstr in self._extract_networks(connect):
                    try:
                        net = ipaddress.ip_network(netstr, strict=False)
                        direct.add((net.network_address, net.prefixlen))
                    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                        pass

            elif connect.get("type") == "p2p":
                link_name = connect.get("link")
                for link in self.topology.get("links", []):
                    if link.get("name") == link_name:
                        netstr = link.get("network")
                        if netstr:
                            try:
                                net = ipaddress.ip_network(netstr, strict=False)
                                direct.add((net.network_address, net.prefixlen))
                            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                                pass

        return direct

    def _count_lan_interfaces(self, lan_connects: List[Dict]) -> int:
        """Conta o número de interfaces físicas LAN geradas."""
        if not lan_connects:
            return 0
        
        total_networks = sum(len(self._extract_networks(c)) for c in lan_connects)
        
        # Se router-on-a-stick (múltiplas redes), usa apenas uma interface física
        if total_networks > 1:
            return 1
        else:
            # Se LANs simples, uma interface por rede
            return total_networks

    def _get_p2p_interface(self, link_name: str, device_name: str) -> Optional[str]:
        """Obtém interface para um link P2P a partir da definição do link."""
        for link in self.topology.get("links", []):
            if link.get("name") == link_name:
                for endpoint in link.get("endpoints", []):
                    if endpoint.get("device") == device_name:
                        return endpoint.get("interface")
        return None

    def _generate_internet_interfaces(self, router: Dict, internet_connects: List[Dict], start_idx: int = 0) -> List[str]:
        """Gera configuração de interfaces internet."""
        lines = []
        name = router.get("name")
        iface_idx = start_idx

        router_prefix = self.config.get("interfaces.router.p2p_prefix", "Serial")
        router_slot = self.config.get("interfaces.router.p2p_slot", "0/0")

        for connect in internet_connects:
            link = connect.get("link", "INTERNET")
            local_ip = connect.get("local_ip")

            if not local_ip:
                raise ValueError(f"Link internet sem IP local em {name}")

            # Tenta obter máscara da rede
            netstr = connect.get("network")
            if netstr:
                try:
                    netobj = ipaddress.ip_network(netstr, strict=False)
                    mask = str(netobj.netmask)
                except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                    mask = self.config.get("routing.p2p_mask")
            else:
                mask = self.config.get("routing.p2p_mask")

            # Tenta obter interface da definição do link
            phys_if = self._get_p2p_interface(link, name)
            if not phys_if:
                # Fallback: auto-numera
                phys_if = f"{router_prefix}{router_slot}/{iface_idx}"
                iface_idx += 1

            lines.append(f"interface {phys_if}")
            lines.append(f" description {link}")
            lines.append(f" ip address {local_ip} {mask}")
            lines.append(" no shutdown")

        return lines
