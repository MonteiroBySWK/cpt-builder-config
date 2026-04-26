"""
gateway_manager.py - Atribui gateways automaticamente para redes.
"""
import ipaddress
from typing import Dict, Set, Tuple


class GatewayManager:
    """Gerencia atribuição de IPs de gateway."""

    def __init__(self, net_entries: list, host_ips: Set[str]):
        """
        Inicializa gerenciador de gateways.

        Args:
            net_entries: Lista de dicts com estrutura {'network', 'mask', 'hosts', ...}
            host_ips: Conjunto de IPs já alocados para hosts
        """
        self.net_entries = net_entries
        self.host_ips = host_ips
        self.gateway_map = self.assign_gateways()

    def assign_gateways(self) -> Dict[str, Dict]:
        """
        Atribui IPs de gateway para cada rede.

        Estratégia:
        1. Procura primeiro IP disponível não alocado para host
        2. Se nenhum disponível, usa primeiro IP da rede
        3. Levanta erro se rede /31 ou /32 (sem hosts)

        Retorna:
            Dict[network/mask] -> {'gateway': ip, 'net': IPv4Network}
        """
        gateway_map = {}
        assigned = set()

        for entry in self.net_entries:
            net = ipaddress.ip_network(
                f"{entry['network']}/{entry['mask']}",
                strict=False
            )

            gw = None

            # Procura primeiro IP livre
            try:
                for host_ip in net.hosts():
                    hip = str(host_ip)
                    if hip not in self.host_ips and hip not in assigned:
                        gw = hip
                        assigned.add(gw)
                        break
            except StopIteration:
                pass

            # Se nenhum livre, usa primeiro
            if not gw:
                try:
                    gw = str(next(net.hosts()))
                except StopIteration:
                    raise ValueError(
                        f"Rede {net} não possui hosts disponíveis para gateway (máscara muito pequena: /{net.prefixlen})"
                    )

            gateway_map[f"{net.network_address}/{net.prefixlen}"] = {
                "gateway": gw,
                "net": net,
            }

        return gateway_map

    def get_gateway(self, network_str: str) -> str:
        """Obtém IP de gateway para uma rede."""
        try:
            net = ipaddress.ip_network(network_str, strict=False)
            key = f"{net.network_address}/{net.prefixlen}"
            if key in self.gateway_map:
                return self.gateway_map[key]["gateway"]
            return str(next(net.hosts()))
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, StopIteration):
            raise ValueError(f"Não foi possível atribuir gateway para {network_str}")

    def get_all(self) -> Dict[str, Dict]:
        """Retorna mapa completo de gateways."""
        return self.gateway_map

    def __repr__(self) -> str:
        return f"<GatewayManager networks={len(self.gateway_map)}>"
