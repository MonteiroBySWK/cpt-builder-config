#!/usr/bin/env python3
"""
main.py

Gera configurações Cisco IOS prontas para copiar/colar em roteadores e switches
a partir de `networks.yml` e `topology.yml`.

Uso:
  python3 main.py

Dependência: PyYAML (`pip install pyyaml`)
"""
import os
import sys
import ipaddress
from collections import defaultdict, deque

try:
    import yaml
except Exception:
    print("PyYAML não está instalado. Instale com: pip install pyyaml")
    sys.exit(1)


BASE_DIR = os.path.dirname(__file__)
def get_resource_path(relative_path):
    """Retorna o caminho absoluto do recurso, compatível com PyInstaller."""
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(BASE_DIR, relative_path)

NETS_FILE = get_resource_path("networks.yml")
TOPO_FILE = get_resource_path("topology.yml")
OUT_DIR = os.path.join(BASE_DIR, "configs")
os.makedirs(OUT_DIR, exist_ok=True)


def get_link_interface(topo, link_name, device_name):
    """Retorna a interface declarada para um endpoint de link, se existir.

    Procura por campos `interface`, `port` ou `if` no endpoint.
    """
    for l in topo.get("links", []) or []:
        if l.get("name") == link_name:
            for ep in l.get("endpoints", []) or []:
                if ep.get("device") == device_name:
                    return ep.get("interface") or ep.get("port") or ep.get("if")
    return None


def iface_from_connect(device_name, connect, topo):
    """Determina a interface a usar para uma entrada `connect`.

    Prioriza a propriedade `interface` em `connect`, depois procura no
    `links` correspondente por um endpoint com interface declarada.
    """
    if not isinstance(connect, dict):
        return None
    if connect.get("interface"):
        return connect.get("interface")
    if connect.get("link"):
        return get_link_interface(topo, connect.get("link"), device_name)
    return None


def find_router_connect_interface_for_switch(topo, switch_name):
    """Procura por interfaces declaradas nos `connects` dos roteadores que
    referenciam este `switch_name`.
    """
    for r in topo.get("routers", []) or []:
        for c in r.get("connects", []) or []:
            if c.get("type") == "lan":
                if c.get("switch") == switch_name:
                    if c.get("interface"):
                        return c.get("interface")
                if switch_name in (c.get("switches") or []):
                    if c.get("interface"):
                        return c.get("interface")
    return None


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def collect_network_entries(nets_yaml):
    entries = []
    host_ips = set()
    for name, data in (nets_yaml.get("networks") or {}).items():
        if not data:
            continue
        if "network" in data:
            e = {"owner": name, "network": data["network"], "mask": int(data["mask"]), "hosts": data.get("hosts", [])}
            entries.append(e)
            for h in e["hosts"]:
                if isinstance(h, dict) and h.get("ip"):
                    host_ips.add(h["ip"])
        elif "vlans" in data:
            for vlan in data["vlans"]:
                e = {"owner": name, "vlan": vlan.get("vlan"), "network": vlan["network"], "mask": int(vlan["mask"]), "hosts": vlan.get("hosts", [])}
                entries.append(e)
                for h in e["hosts"]:
                    if isinstance(h, dict) and h.get("ip"):
                        host_ips.add(h["ip"])
    return entries, host_ips


def build_adjacency(topo):
    adj = defaultdict(list)
    links = topo.get("links") or []
    for l in links:
        eps = l.get("endpoints", [])
        if len(eps) != 2:
            continue
        a, b = eps
        adj[a.get("device")].append({"peer": b.get("device"), "local_ip": a.get("ip"), "peer_ip": b.get("ip"), "link": l.get("name"), "network": l.get("network")})
        adj[b.get("device")].append({"peer": a.get("device"), "local_ip": b.get("ip"), "peer_ip": a.get("ip"), "link": l.get("name"), "network": l.get("network")})
    return adj


def device_network_map(topo):
    m = defaultdict(list)
    for r in topo.get("routers", []) or []:
        name = r.get("name")
        for c in r.get("connects", []) or []:
            if c.get("type") == "lan":
                netval = c.get("network")
                if netval:
                    if isinstance(netval, str) and "/" in netval:
                        m[name].append(ipaddress.ip_network(netval, strict=False))
                    else:
                        mask = c.get("mask")
                        if mask:
                            m[name].append(ipaddress.ip_network(f"{netval}/{mask}", strict=False))
                for nn in c.get("networks") or []:
                    m[name].append(ipaddress.ip_network(nn, strict=False))
    for s in topo.get("switches", []) or []:
        for v in s.get("vlans", []) or []:
            if v.get("network"):
                m[s.get("name")].append(ipaddress.ip_network(v.get("network"), strict=False))
    return m


def assign_gateways(net_entries, host_ips):
    gateway_map = {}
    assigned = set()
    for e in net_entries:
        net = ipaddress.ip_network(f"{e['network']}/{e['mask']}", strict=False)
        gw = None
        for h in net.hosts():
            hip = str(h)
            if hip not in host_ips and hip not in assigned:
                gw = hip
                assigned.add(gw)
                break
        if not gw:
            gw = str(next(net.hosts()))
        gateway_map[f"{net.network_address}/{net.prefixlen}"] = {"gateway": gw, "net": net}
    return gateway_map


def bfs_next_hop(adj, device_to_netobjs, src, target_net):
    targets = [d for d, nets in device_to_netobjs.items() if any((n.network_address == target_net.network_address and n.prefixlen == target_net.prefixlen) for n in nets)]
    if not targets:
        return None
    q = deque([src])
    parent = {src: None}
    while q:
        cur = q.popleft()
        if cur in targets:
            break
        for edge in adj.get(cur, []):
            nb = edge["peer"]
            if nb not in parent:
                parent[nb] = cur
                q.append(nb)
    # reconstruct first hop
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
    first_hop = path[1]
    for edge in adj.get(src, []):
        if edge["peer"] == first_hop:
            return edge["peer_ip"]
    return None


def generate_router_configs(topo, net_entries, gateway_map, adj, device_to_netobjs):
    cfgs = {}
    for r in topo.get("routers", []) or []:
        name = r.get("name")
        lines = []
        lines.append("configure terminal")
        lines.append(f"hostname {name}")
        lines.append("ip domain-name uema.br")
        lines.append("username admin secret adminssh")
        lines.append("enable secret root")
        lines.append("service password-encryption")
        iface_idx = 0
        lan_connects = [c for c in r.get("connects", []) or [] if c.get("type") == "lan"]
        p2p_connects = [c for c in r.get("connects", []) or [] if c.get("type") == "p2p"]

        # Router-on-a-stick (subinterfaces) when multiple LANs
        if len(lan_connects) > 1:
            # prefira interface física declarada na topologia
            phys_if = None
            for c in lan_connects:
                if c.get("interface"):
                    phys_if = c.get("interface")
                    break
            if not phys_if:
                phys_if = "GigabitEthernet0/0"
            for c in lan_connects:
                nets = []
                netval = c.get("network")
                if netval:
                    if isinstance(netval, str) and "/" in netval:
                        nets = [netval]
                    else:
                        mask = c.get("mask")
                        if mask:
                            nets = [f"{netval}/{mask}"]
                else:
                    nets = c.get("networks") or []
                for netstr in nets:
                    netobj = ipaddress.ip_network(netstr, strict=False)
                    vlan_id = None
                    for s in topo.get("switches", []) or []:
                        for v in s.get("vlans", []) or []:
                            if v.get("network"):
                                try:
                                    vnet = ipaddress.ip_network(v.get("network"), strict=False)
                                except Exception:
                                    continue
                                if vnet.network_address == netobj.network_address and vnet.prefixlen == netobj.prefixlen:
                                    vlan_id = v.get("id") or v.get("vlan")
                    if not vlan_id:
                        vlan_id = int(str(netobj.network_address).split('.')[-1])
                    gw_entry = gateway_map.get(f"{netobj.network_address}/{netobj.prefixlen}")
                    gw_ip = gw_entry["gateway"] if gw_entry else str(next(netobj.hosts()))
                    lines.append(f"interface {phys_if}.{vlan_id}")
                    lines.append(f" encapsulation dot1Q {vlan_id}")
                    lines.append(f" ip address {gw_ip} {str(netobj.netmask)}")
                    lines.append(" no shutdown")

        else:
            for c in lan_connects:
                nets = []
                netval = c.get("network")
                if netval:
                    if isinstance(netval, str) and "/" in netval:
                        nets = [netval]
                    else:
                        mask = c.get("mask")
                        if mask:
                            nets = [f"{netval}/{mask}"]
                else:
                    nets = c.get("networks") or []
                for netstr in nets:
                    netobj = ipaddress.ip_network(netstr, strict=False)
                    gw_entry = gateway_map.get(f"{netobj.network_address}/{netobj.prefixlen}")
                    gw_ip = gw_entry["gateway"] if gw_entry else str(next(netobj.hosts()))
                    # interface: priorize declaram 'interface' na conexão, senão aloca dinamicamente
                    if c.get("interface"):
                        phys_if = c.get("interface")
                    else:
                        phys_if = f"GigabitEthernet0/{iface_idx}"
                        iface_idx += 1
                    lines.append(f"interface {phys_if}")
                    lines.append(f" ip address {gw_ip} {str(netobj.netmask)}")
                    lines.append(" no shutdown")

        # point-to-point links
        for c in p2p_connects:
            link = c.get("link")
            local_ip = c.get("local_ip")
            link_net = None
            for l in topo.get("links", []) or []:
                if l.get("name") == link:
                    link_net = l.get("network")
            if link_net:
                netobj = ipaddress.ip_network(link_net, strict=False)
                mask = str(netobj.netmask)
            else:
                mask = "255.255.255.252"
            # determina interface: prioridade -> connect.interface -> link endpoint.interface -> alocação dinâmica
            if c.get("interface"):
                phys_if = c.get("interface")
            else:
                phys_if = get_link_interface(topo, link, name) or f"GigabitEthernet0/{iface_idx}"
                if phys_if.startswith("GigabitEthernet0/"):
                    iface_idx += 1
            lines.append(f"interface {phys_if}")
            lines.append(f" description {link}")
            lines.append(f" ip address {local_ip} {mask}")
            lines.append(" no shutdown")

        # default route (internet)
        for c in r.get("connects", []) or []:
            if c.get("type") == "internet":
                remote = c.get("remote_ip") or c.get("remote")
                if remote:
                    lines.append(f"ip route 0.0.0.0 0.0.0.0 {remote}")

        # static routes for other networks
        direct_nets = set()
        for c in r.get("connects", []) or []:
            if c.get("type") == "lan":
                netval = c.get("network")
                if netval:
                    if isinstance(netval, str) and "/" in netval:
                        n = ipaddress.ip_network(netval, strict=False)
                    else:
                        mask = c.get("mask")
                        if mask:
                            n = ipaddress.ip_network(f"{netval}/{mask}", strict=False)
                        else:
                            n = ipaddress.ip_network(str(netval), strict=False)
                    direct_nets.add((n.network_address, n.prefixlen))
                for nn in c.get("networks") or []:
                    n = ipaddress.ip_network(nn, strict=False)
                    direct_nets.add((n.network_address, n.prefixlen))
            if c.get("type") == "p2p":
                for l in topo.get("links", []) or []:
                    if l.get("name") == c.get("link"):
                        n = ipaddress.ip_network(l.get("network"), strict=False)
                        direct_nets.add((n.network_address, n.prefixlen))

        for e in net_entries:
            netobj = ipaddress.ip_network(f"{e['network']}/{e['mask']}", strict=False)
            key = (netobj.network_address, netobj.prefixlen)
            if key in direct_nets:
                continue
            next_hop = bfs_next_hop(adj, device_to_netobjs, name, netobj)
            if next_hop:
                lines.append(f"ip route {netobj.network_address} {str(netobj.netmask)} {next_hop}")

        # SSH on vty
        lines.append("line vty 0 4")
        lines.append(" login local")
        lines.append(" transport input ssh")
        lines.append("end")
        lines.append("!")
        cfgs[name] = "\n".join(lines)
    return cfgs


def generate_switch_configs(topo, gateway_map):
    cfgs = {}
    for s in topo.get("switches", []) or []:
        name = s.get("name")
        lines = []
        lines.append("configure terminal")
        lines.append(f"hostname {name}")
        lines.append("ip domain-name uema.br")
        lines.append("username admin secret adminssh")
        lines.append("enable secret root")
        # create VLANs
        for v in s.get("vlans", []) or []:
            vid = v.get("id") or v.get("vlan")
            if not vid:
                continue
            lines.append(f"vlan {vid}")
            lines.append(f" name VLAN{vid}")

        # management interface
        mgmt_ip = s.get("management_ip")
        if mgmt_ip:
            mgmt_vlan = None
            for v in s.get("vlans", []) or []:
                if v.get("network"):
                    netobj = ipaddress.ip_network(v.get("network"), strict=False)
                    if str(mgmt_ip).startswith(str(netobj.network_address)):
                        mgmt_vlan = v.get("id") or v.get("vlan")
            if not mgmt_vlan:
                mgmt_vlan = 1
            mask = "255.255.255.0"
            for v in s.get("vlans", []) or []:
                if (v.get("id") or v.get("vlan")) == mgmt_vlan and v.get("network"):
                    n = ipaddress.ip_network(v.get("network"), strict=False)
                    mask = str(n.netmask)
            lines.append(f"interface Vlan{mgmt_vlan}")
            lines.append(f" ip address {mgmt_ip} {mask}")
            lines.append(" no shutdown")
            netkey = None
            for v in s.get("vlans", []) or []:
                if (v.get("id") or v.get("vlan")) == mgmt_vlan and v.get("network"):
                    netobj = ipaddress.ip_network(v.get("network"), strict=False)
                    netkey = f"{netobj.network_address}/{netobj.prefixlen}"
            if netkey and netkey in gateway_map:
                lines.append(f"ip default-gateway {gateway_map[netkey]['gateway']}")

        # configurar portas de hosts (se port/interface declarada)
        for h in s.get("hosts", []) or []:
            port = h.get("port") or h.get("interface")
            if port:
                vlan = s.get("access_vlan") or 1
                lines.append(f"interface {port}")
                lines.append(f" description host {h.get('name')}")
                lines.append(f" switchport access vlan {vlan}")
                lines.append(" no shutdown")

        # configurar portas de hosts dentro de vlans (se declaradas)
        for v in s.get("vlans", []) or []:
            for host in v.get("hosts", []) or []:
                port = host.get("port") or host.get("interface")
                if port:
                    vid = v.get("id") or v.get("vlan")
                    lines.append(f"interface {port}")
                    lines.append(f" description host {host.get('name')}")
                    lines.append(f" switchport access vlan {vid}")
                    lines.append(" no shutdown")

        # trunk to uplink router
        if s.get("uplink"):
            uplink_iface = s.get("uplink_interface") or find_router_connect_interface_for_switch(topo, name) or "GigabitEthernet0/1"
            lines.append(f"interface {uplink_iface}")
            lines.append(f" description trunk to {s.get('uplink')}")
            lines.append(" switchport trunk encapsulation dot1q")
            lines.append(" switchport mode trunk")
            # native vlan
            native = None
            for v in s.get("vlans", []) or []:
                if v.get("id") == 99 or v.get("vlan") == 99:
                    native = 99
            if native:
                lines.append(" switchport trunk native vlan 99")
            allowed = ",".join(str((v.get("id") or v.get("vlan"))) for v in s.get("vlans", []) or [])
            if allowed:
                lines.append(f" switchport trunk allowed vlan {allowed}")
            lines.append(" no shutdown")

        lines.append("end")
        lines.append("!")
        cfgs[name] = "\n".join(lines)
    return cfgs


def main():
    nets_yaml = load_yaml(NETS_FILE)
    topo_yaml = load_yaml(TOPO_FILE)
    net_entries, host_ips = collect_network_entries(nets_yaml)
    topo = topo_yaml.get("topology") or topo_yaml
    adj = build_adjacency(topo)
    device_to_netobjs = device_network_map(topo)
    gateway_map = assign_gateways(net_entries, host_ips)

    r_cfgs = generate_router_configs(topo, net_entries, gateway_map, adj, device_to_netobjs)
    sw_cfgs = generate_switch_configs(topo, gateway_map)

    # write only router and switch IOS configs
    for name, cfg in {**r_cfgs, **sw_cfgs}.items():
        safe = name.replace("/", "_").replace(" ", "_")
        path = os.path.join(OUT_DIR, f"{safe}.cfg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(cfg)
    print("Configs IOS gerados em:", OUT_DIR)


if __name__ == "__main__":
    main()
