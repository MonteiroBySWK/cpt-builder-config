# Referência de Configuração: networks.yml

O arquivo `networks.yml` funciona como um inventário centralizado de endereçamento IP e definições de hosts da infraestrutura.

## 1. Estrutura de Redes (networks)

As redes são agrupadas por blocos lógicos. Cada bloco pode conter:

- **network:** Endereço base da sub-rede (ex: `172.16.1.64`).
- **mask:** Máscara de sub-rede em formato decimal (ex: `27`).
- **vlans (lista):** Define sub-redes segmentadas por VLAN dentro de um grupo.
    - **vlan:** ID numérico da VLAN.
    - **network:** Endereço IP da rede.
    - **mask:** Máscara decimal.
    - **hosts (lista):** Lista de dispositivos pertencentes à VLAN.

## 2. Estrutura de Hosts (hosts)

Define os endereços IPs ocupados por dispositivos finais.

- **name:** Nome descritivo do dispositivo (ex: `SERVERWEB`).
- **ip:** Endereço IP estático atribuído.

## 3. Lógica de Alocação de Gateway

O sistema utiliza a lista de hosts para evitar conflitos de endereçamento:
1. Analisa todos os IPs listados na seção `hosts` de uma rede.
2. Identifica o primeiro IP utilizável da sub-rede que não esteja presente na lista de hosts.
3. Atribui este IP como o gateway (interface do roteador) para aquela rede.
