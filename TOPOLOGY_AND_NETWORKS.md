# Topology and Networks — Usage

This document explains the fields used in `topology.yml` and `networks.yml` for the project.

## Purpose
- `topology.yml` describes devices (routers, switches), links between them and interface/port details used to generate device configurations.
- `networks.yml` lists named networks and VLANs with optional host entries used to allocate gateways and link hosts to networks.

---

## topology.yml
Root object can contain a `topology:` map or directly the sections shown below.

Sections:
- `routers`: list of router objects
- `switches`: list of switch objects
- `links`: list of link objects
- `notes`: optional array of freeform notes

Router object fields:
- `name` (required): human name used as device identifier
- `connects` (list): each connect entry describes a connection from this router
  - `type`: `lan` | `p2p` | `internet`
  - `network`: network in CIDR (e.g. `172.16.1.64/27`) or omitted if `networks` is used
  - `mask`: optional numeric mask (e.g. `27`) used with `network` when not providing CIDR
  - `networks`: optional list of network CIDRs for router-on-a-stick cases
  - `switch` or `switches`: name(s) of associated switch(es) for LAN connects
  - `link`: name of a `links` entry used for p2p connects
  - `local_ip` / `remote_ip`: IP assigned on this end of the p2p link
  - `interface`: optional explicit interface name (e.g. `Serial0/0/0`, `GigabitEthernet0/1`) to force using that interface

Switch object fields:
- `name` (required)
- `uplink`: router name this switch uplinks to
- `uplink_interface`: optional explicit uplink interface on switch (e.g. `GigabitEthernet0/1`)
- `access_vlan`: default access VLAN for `hosts` entries without per-host VLAN
- `hosts`: list of host objects attached to this switch
  - host object: `name`, `ip`, optional `port` or `interface` (e.g. `FastEthernet0/3`)
- `vlans`: list of VLAN objects
  - VLAN: `id` or `vlan`, `network` (CIDR), optional `hosts` (per-VLAN hosts)
- `notes`: optional description

Link object fields (for p2p links):
- `name` (required)
- `network` (CIDR) used for the point-to-point subnet
- `endpoints`: list with two endpoints
  - endpoint fields: `device` (device name), `ip` (IP on that endpoint), optional `interface` (e.g. `Serial0/0/0`), optional `port` or `if`

Example link endpoint:
- device: REITORIA
  ip: 172.16.1.241
  interface: Serial0/0/0

Notes:
- If `interface` is provided in `links.endpoints` or in `connects` entries, the generator will use that interface (allowing `Serial`, `FastEthernet`, `GigabitEthernet`).
- For router-on-a-stick (`lan` with multiple networks), use `networks:` on the router connect to indicate multiple subnets that will be configured as subinterfaces.

---

## networks.yml
Root has `networks:` map with named network groups.

Structure example:

networks:
  NTI-LAN:
    network: 172.16.1.96
    mask: 27
    hosts:
      - name: PC1
        ip: 172.16.1.97

Fields:
- Key: friendly name for the network block
- `network`: network address (with or without mask)
- `mask`: numeric mask if `network` provided without `/` CIDR
- `vlans`: option to declare multiple VLANs under a group
- `hosts`: optional list of hosts (objects with `name` and optional `ip`)

Gateway assignment:
- The generator chooses an unused host IP within each network to be the gateway. If `hosts` include specific IPs, those are considered used when selecting gateway.

---

## How to run
- Generate configs locally (writes to `configs/`):

```bash
python3 main.py
```

- To set a custom output directory:

```bash
python3 main.py --out-dir ./my-configs
```

- To build a single-file executable (optional):
  - Edit `build.py` to ensure PyInstaller is available in your environment, then:

```bash
python3 build.py
```

Notes about running the bundled `--onefile` binary:
- The single-file binary extracts to a temporary directory at runtime. When writing generated output, prefer passing `--out-dir` pointing to a directory outside the bundle temporary dir, e.g. `./configs`.

---

## Tips and best practices
- Prefer adding explicit `interface` names for p2p links when you want `Serial` or `FastEthernet` to be used.
- Use `vlans` entries in switches to describe VLAN id -> network mapping for router-on-a-stick setups.
- Keep `topology.yml` human-readable and use comments to document choices (YAML supports comments; JSON does not).

---

If you want, I can add schema validation (simple checks) to `main.py` to warn about missing fields or malformed CIDRs.
