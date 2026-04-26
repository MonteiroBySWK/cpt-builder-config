# Manual Técnico do Gerador de Configurações Cisco

Este documento descreve o funcionamento, a arquitetura e os procedimentos de execução do gerador automatizado de configurações Cisco IOS.

## 1. Visão Geral

O sistema é uma ferramenta de automação que converte definições de rede em formato YAML para arquivos de configuração CLI da Cisco (.cfg). Ele utiliza conceitos de grafos para calcular rotas e gerencia automaticamente a atribuição de interfaces e subinterfaces.

## 2. Instruções de Execução

### Pré-requisitos
* Python 3.8 ou superior.
* Biblioteca PyYAML instalada.

### Configuração de Credenciais
Por motivos de segurança, o sistema não armazena senhas em arquivos de configuração. As credenciais devem ser fornecidas via variáveis de ambiente antes da execução:

**Ambiente Linux/macOS:**
```bash
export CPT_CREDENTIALS_PASSWORD="sua_senha_vty"
export CPT_CREDENTIALS_ENABLE_PASSWORD="sua_senha_enable"
```

**Ambiente Windows (PowerShell):**
```powershell
$env:CPT_CREDENTIALS_PASSWORD="sua_senha_vty"
$env:CPT_CREDENTIALS_ENABLE_PASSWORD="sua_senha_enable"
```

### Execução do Script
Para gerar as configurações, execute o arquivo principal:
```bash
python3 main.py
```
Os arquivos gerados serão salvos no diretório `configs/`.

## 3. Arquitetura e Lógica de Processamento

O processo de geração é dividido em quatro etapas principais:

### 3.1. GatewayManager
Responsável pela atribuição de endereços IP às interfaces dos roteadores. O sistema analisa a lista de hosts definidos para cada rede e seleciona o primeiro endereço IP disponível que não esteja em uso. Caso os endereços iniciais estejam ocupados por hosts, o sistema avança sequencialmente até encontrar um IP livre para o gateway.

### 3.2. NetworkGraph e Roteamento
O sistema constrói um grafo de adjacência representando toda a topologia física e lógica.
* **Cálculo de Rotas:** Utiliza o algoritmo de busca em largura (BFS) para determinar o próximo salto (next-hop) entre qualquer origem e destino.
* **Automação:** Cada roteador recebe automaticamente comandos `ip route` para todas as redes da topologia que não estejam diretamente conectadas a ele.

### 3.3. Router-on-a-Stick
A lógica de subinterfaces é ativada automaticamente quando múltiplas redes são detectadas em uma conexão do tipo LAN. O sistema identifica o ID da VLAN cruzando os dados da rede com as definições dos switches conectados, configurando o encapsulamento dot1Q e os endereços IP correspondentes nas subinterfaces.

### 3.4. Gestão de Interfaces P2P
O gerador prioriza o uso de interfaces Seriais para links ponto-a-ponto, desde que estas estejam explicitamente definidas no arquivo de topologia. Na ausência de definição explícita, o sistema utiliza interfaces GigabitEthernet numeradas sequencialmente, garantindo que não haja colisão com as interfaces utilizadas para LAN.

## 4. Estrutura de Dados (YAML)

* **topology.yml:** Define a hierarquia dos dispositivos, conexões físicas e mapeamento de interfaces.
* **networks.yml:** Contém o inventário de redes, máscaras de sub-rede e endereços IP dos hosts.
* **config.yml:** Armazena parâmetros globais como nome de domínio e prefixos padrão de interface.

## 5. Fluxo de Manutenção

Para adicionar uma nova rede ao projeto:
1. Declare o bloco de rede e hosts no arquivo `networks.yml`.
2. Associe a rede ao roteador e switch correspondentes no arquivo `topology.yml`.
3. Execute o gerador para atualizar as configurações e as tabelas de roteamento estático de todos os dispositivos afetados.
