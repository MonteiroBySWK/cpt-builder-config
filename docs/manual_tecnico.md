# Manual Técnico do Gerador de Configurações Cisco

Este documento descreve o funcionamento, a arquitetura e os procedimentos de execução do gerador automatizado de configurações Cisco IOS.

## 1. Visão Geral

O sistema é uma ferramenta de automação que converte definições de rede em formato YAML para arquivos de configuração CLI da Cisco (.cfg). Ele utiliza conceitos de grafos para calcular rotas e gerencia automaticamente a atribuição de interfaces e subinterfaces.

## 2. Instruções de Execução

O gerador foi projetado para ser portátil, podendo ser executado diretamente de um pendrive sem a necessidade de instalar dependências na máquina de destino.

### Requisitos para Execução Portátil
Para rodar o programa em um novo ambiente, certifique-se de que os seguintes arquivos estejam no mesmo diretório:
1. `cisco_gen` (Executável)
2. `topology.yml` (Mapa da rede)
3. `networks.yml` (Inventário de IPs)
4. `config.yml` (Parâmetros globais e senhas)

### Procedimento
1. Abra o terminal no diretório onde os arquivos estão localizados.
2. Execute o binário:
   ```bash
   ./cisco_gen
   ```
3. As configurações geradas serão salvas automaticamente na subpasta `configs/`.

## 3. Arquitetura e Lógica de Processamento

O processo de geração é dividido em etapas principais:

### 3.1. GatewayManager
Responsável pela atribuição de endereços IP às interfaces dos roteadores. O sistema analisa a lista de hosts definidos para cada rede e seleciona o primeiro endereço IP utilizável da sub-rede que não esteja em uso.

### 3.2. NetworkGraph e Roteamento
O sistema constrói um grafo de adjacência representando toda a topologia.
* **Cálculo de Rotas:** Utiliza o algoritmo de busca em largura (BFS) para determinar o próximo salto (next-hop) entre dispositivos.
* **Automação:** Cada roteador recebe automaticamente comandos `ip route` para todas as redes da topologia que não estejam diretamente conectadas a ele.

### 3.3. Router-on-a-Stick
A lógica de subinterfaces é ativada automaticamente quando múltiplas redes são detectadas em uma conexão do tipo LAN. O sistema configura o encapsulamento dot1Q e os endereços IP correspondentes nas subinterfaces (ex: `GigabitEthernet0/0.10`).

## 4. Segurança e Credenciais

As credenciais de acesso (usuário, senha SSH e senha de enable) são lidas diretamente do arquivo `config.yml`. Caso deseje alterar as senhas para a prova, edite a seção `credentials` no referido arquivo antes de executar o gerador.

## 5. Fluxo de Manutenção

Para adicionar uma nova rede:
1. Declare o bloco de rede e hosts em `networks.yml`.
2. Associe a rede ao roteador e switch correspondentes em `topology.yml`.
3. Execute o `cisco_gen` para atualizar as configurações de todos os dispositivos.
