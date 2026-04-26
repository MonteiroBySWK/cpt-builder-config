# Referência de Configuração: config.yml

O arquivo `config.yml` armazena as definições globais, parâmetros de segurança e padrões de hardware que regem a geração das configurações Cisco IOS.

## 1. Parâmetros Globais (global)

- **domain_name:** Nome de domínio utilizado para o serviço DNS e geração de chaves SSH (ex: `example.com`).

## 2. Acesso Remoto (ssh)

- **enabled:** Define se o acesso SSH será habilitado (`true`/`false`).
- **vty_range:** Intervalo de linhas virtuais (ex: `0 4`).
- **transport:** Protocolo permitido para entrada (ex: `ssh`).

## 3. Credenciais (credentials)

Diferente de versões anteriores, as senhas agora podem ser definidas diretamente neste arquivo para facilitar o uso portátil:

- **username:** Nome do usuário administrador local.
- **password:** Senha para acesso SSH/VTY.
- **enable_password:** Senha para acesso ao modo privilegiado.

## 4. Padrões de Interface (interfaces)

Define os prefixos e slots padrão caso não sejam especificados no `topology.yml`.

### Roteador (router)
- **default_prefix:** Prefixo para interfaces LAN (ex: `GigabitEthernet`).
- **default_slot:** Slot inicial para interfaces LAN.
- **p2p_prefix:** Prefixo para interfaces de link ponto-a-ponto (ex: `Serial`).
- **p2p_slot:** Slot inicial para interfaces P2P (ex: `0/0`).

### Switch (switch)
- **trunk_default:** Porta padrão para conexões de uplink e trunk.

## 5. Parâmetros de VLAN e Roteamento (vlans / routing)

- **native_vlan:** ID da VLAN sem marcação (nativa) em portas trunk.
- **default_mask:** Máscara padrão para interfaces de gerência de switch.
- **p2p_mask:** Máscara padrão para links P2P (ex: `255.255.255.252`).

## 6. Segurança (security)

- **password_encryption:** Habilita o comando `service password-encryption` para criptografar senhas no arquivo de configuração final.
