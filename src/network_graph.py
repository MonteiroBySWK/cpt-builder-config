"""
network_graph.py - Constrói grafo de adjacência e mapeia redes a devices.
"""
import ipaddress
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple


class NetworkGraph:
    """Gerencia adjacência de dispositivos e mapeamento de redes."""

    def __init__(self, topology: Dict):
        """
        Inicializa grafo de rede.

        Args:
            topology: Dicionário com estrutura de topologia (routers, switches, links)
        """
        self.topology = topology
        self.adjacency = self._build_adjacency()
        self.device_networks = self._build_device_network_map()

    def _build_adjacency(self) -> Dict[str, List[Dict]]:
        """
        Constrói mapa de adjacência a partir de links P2P.

        Retorna:
            Dict[device_name] -> Lista de dicts com peers, IPs e metadados
        """
        adj = defaultdict(list)
        links = self.topology.get("links", [])

        for link in links:
            endpoints = link.get("endpoints", [])
            if len(endpoints) != 2:
                continue

            a, b = endpoints
            device_a = a.get("device")
            device_b = b.get("device")

            # A -> B
            adj[device_a].append({
                "peer": device_b,
                "local_ip": a.get("ip"),
                "peer_ip": b.get("ip"),
                "link": link.get("name"),
                "network": link.get("network"),
            })

            # B -> A
            adj[device_b].append({
                "peer": device_a,
                "local_ip": b.get("ip"),
                "peer_ip": a.get("ip"),
                "link": link.get("name"),
                "network": link.get("network"),
            })

        return adj

    def _build_device_network_map(self) -> Dict[str, List[ipaddress.IPv4Network]]:
        """
        Mapeia cada dispositivo para redes que conhece.

        Retorna:
            Dict[device_name] -> Lista de ipaddress.IPv4Network objects
        """
        device_map = defaultdict(list)

        # Roteadores
        for router in self.topology.get("routers", []):
            name = router.get("name")
            for connect in router.get("connects", []):
                if connect.get("type") != "lan":
                    continue

                netval = connect.get("network")
                if netval:
                    try:
                        if isinstance(netval, str) and "/" in netval:
                            device_map[name].append(ipaddress.ip_network(netval, strict=False))
                        else:
                            mask = connect.get("mask")
                            if mask:
                                device_map[name].append(ipaddress.ip_network(f"{netval}/{mask}", strict=False))
                    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                        pass

                for netstr in connect.get("networks", []):
                    try:
                        device_map[name].append(ipaddress.ip_network(netstr, strict=False))
                    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                        pass

        # Switches (via VLANs)
        for switch in self.topology.get("switches", []):
            name = switch.get("name")
            for vlan in switch.get("vlans", []):
                netstr = vlan.get("network")
                if netstr:
                    try:
                        device_map[name].append(ipaddress.ip_network(netstr, strict=False))
                    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                        pass

        return device_map

    def bfs_next_hop(self, src: str, target_net: ipaddress.IPv4Network) -> Optional[str]:
        """
        Usa BFS para encontrar próximo hop até rede target.

        Args:
            src: Nome do dispositivo source
            target_net: ipaddress.IPv4Network destino

        Retorna:
            IP do próximo hop, ou None se não achado
        """
        if not isinstance(target_net, ipaddress.IPv4Network):
            raise TypeError(f"target_net deve ser IPv4Network, recebido {type(target_net)}")

        # Encontra device que conhece a rede target
        targets = [
            d for d, nets in self.device_networks.items()
            if any((n.network_address == target_net.network_address and n.prefixlen == target_net.prefixlen)
                   for n in nets)
        ]

        if not targets:
            return None

        # BFS para encontrar caminho mais curto
        queue = deque([src])
        parent = {src: None}

        while queue:
            current = queue.popleft()
            if current in targets:
                break
            for edge in self.adjacency.get(current, []):
                neighbor = edge["peer"]
                if neighbor not in parent:
                    parent[neighbor] = current
                    queue.append(neighbor)

        # Reconstrói caminho
        node = next((t for t in targets if t in parent), None)
        if not node:
            return None

        path = []
        while node is not None:
            path.append(node)
            node = parent.get(node)
        path.reverse()

        if len(path) < 2:
            return None

        # Retorna IP do primeiro hop
        first_hop = path[1]
        for edge in self.adjacency.get(src, []):
            if edge["peer"] == first_hop:
                return edge["peer_ip"]

        return None

    def get_adjacency(self) -> Dict[str, List[Dict]]:
        """Retorna mapa de adjacência."""
        return dict(self.adjacency)

    def get_device_networks(self) -> Dict[str, List[ipaddress.IPv4Network]]:
        """Retorna mapa de redes por dispositivo."""
        return dict(self.device_networks)

    def __repr__(self) -> str:
        num_devices = len(self.adjacency)
        return f"<NetworkGraph devices={num_devices}>"
