# Referência de Configuração: topology.yml

O arquivo `topology.yml` define a infraestrutura lógica e física da rede, mapeando a conexão entre roteadores, switches e links ponto-a-ponto.

## 1. Estrutura de Roteadores (routers)

Define as propriedades e interfaces de cada roteador.

- **name (obrigatório):** Identificador do dispositivo (hostname).
- **connects (lista):** Define as conexões de rede do roteador.
    - **type:** Tipo de conexão. Valores aceitos: `lan`, `p2p`, `internet`.
    - **network:** Endereço de rede em formato CIDR (ex: `172.16.1.64/27`).
    - **networks (lista):** Utilizado para configurar múltiplas sub-redes em uma única interface física (Router-on-a-Stick).
    - **interface:** Nome manual da interface (ex: `Serial0/0/0`). Se omitido, o sistema utiliza a numeração automática baseada nos prefixos de `config.yml`.
    - **link:** Nome de referência para um objeto na seção `links`.
    - **local_ip:** Endereço IP local da interface.
    - **remote_ip:** Endereço IP da extremidade remota (usado para rotas e gateway).
    - **switch / switches:** Nome do switch conectado (usado para mapeamento de VLANs).

## 2. Estrutura de Switches (switches)

Define a segmentação de Camada 2 e portas de acesso.

- **name (obrigatório):** Identificador do dispositivo.
- **uplink:** Nome do roteador de upstream.
- **uplink_interface:** Porta física do switch conectada ao roteador.
- **access_vlan:** ID da VLAN padrão para portas de acesso.
- **vlans (lista):** Definição das VLANs presentes no switch.
    - **id / vlan:** ID numérico da VLAN.
    - **network:** Rede CIDR associada à VLAN.
    - **management_ip:** IP opcional para a interface de gerência (SVI).
- **hosts (lista):** Dispositivos finais conectados ao switch.
    - **name:** Nome do host.
    - **ip:** Endereço IP estático.
    - **port / interface:** Porta física de conexão.

## 3. Estrutura de Links (links)

Define os parâmetros globais para conexões ponto-a-ponto.

- **name:** Nome identificador do link.
- **network:** Rede CIDR dedicada ao link (ex: `/30`).
- **endpoints (lista):** Lista de dois objetos contendo:
    - **device:** Nome do dispositivo na extremidade.
    - **ip:** IP atribuído a esta extremidade.
    - **interface:** Nome da interface física.
