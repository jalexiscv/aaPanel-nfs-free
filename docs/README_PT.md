# 🇧🇷 Network File System (NFS) — Free Edition

> [🇪🇸 Español](README_ES.md) · [🇬🇧 English](README_EN.md) · [🇯🇵 日本語](README_JA.md) · [🇩🇪 Deutsch](README_DE.md) · [🇷🇺 Русский](README_RU.md)

Plugin gratuito e de código aberto para aaPanel que fornece gerenciamento completo de NFS por meio de interface gráfica: criar exportações (compartilhamentos), montar diretórios remotos, monitorar o servidor NFS e diagnosticar falhas automaticamente.

```
Autor:   Jose Alexis Correa Valencia (jalexiscv)
Versão:  1.0
Licença: MIT — Software Livre
```

---

## Índice

1. [Sobre o protocolo NFS](#1-sobre-o-protocolo-nfs)
2. [Funcionalidades do plugin](#2-funcionalidades-do-plugin)
3. [Requisitos do sistema](#3-requisitos-do-sistema)
4. [Instalação](#4-instalação)
5. [Estrutura de arquivos](#5-estrutura-de-arquivos)
6. [Portas e firewall](#6-portas-e-firewall)
7. [Arquivos de configuração](#7-arquivos-de-configuração)
8. [Auto-mount na inicialização](#8-auto-mount-na-inicialização)
9. [Diagnóstico de falhas](#9-diagnóstico-de-falhas)
10. [Scripts de manutenção](#10-scripts-de-manutenção)
11. [API do backend](#11-api-do-backend)
12. [Contribuição](#12-contribuição)
13. [Suporte e comunidade](#13-suporte-e-comunidade)
14. [Licença](#14-licença)
15. [Autor](#15-autor)
16. [Doações](#16-doações)

---

## 1. Sobre o protocolo NFS

**Network File System (NFS)** é um protocolo de sistema de arquivos distribuído desenvolvido originalmente pela Sun Microsystems em 1984. Permite que um sistema operacional acesse arquivos localizados em outro computador da rede da mesma forma que acessaria arquivos locais, tornando a localização física do armazenamento transparente para as aplicações.

O NFS opera no modelo cliente/servidor: o servidor **exporta** um diretório e o disponibiliza na rede; o cliente o **monta** localmente como se fosse um volume próprio. A comunicação é realizada por meio de chamadas de procedimento remoto (RPC) sobre TCP ou UDP.

### Versões do protocolo

| Versão  | Ano  | Principais características |
|---------|------|---------------------------|
| NFSv2   | 1989 | Primeira versão amplamente implantada; somente UDP; arquivos máx. 2 GB |
| NFSv3   | 1995 | Suporte a TCP; arquivos de grande porte (64-bit); escrita assíncrona |
| NFSv4   | 2003 | Protocolo com estado (_stateful_); autenticação forte (Kerberos); porta única (2049); suporte a ACL |
| NFSv4.1 | 2010 | pNFS (acesso paralelo); sessões resilientes; melhor suporte a clusters |

### Casos de uso comuns

- Armazenamento compartilhado entre servidores de aplicação
- Diretórios home centralizados em ambientes Linux/Unix
- Infraestrutura de backup distribuído
- Armazenamento compartilhado em clusters HPC e Kubernetes
- Compartilhamento de assets estáticos entre servidores web

> **Segurança:** O NFS não criptografa o tráfego de dados em trânsito (salvo com Kerberos + RPCSEC_GSS). Recomenda-se sempre restringir o acesso a sub-redes confiáveis e nunca expor as portas NFS à Internet.

---

## 2. Funcionalidades do plugin

Este plugin gratuito e de código aberto para aaPanel simplifica a administração do Sistema de Arquivos de Rede (NFS) por meio de uma interface gráfica. Permite que administradores gerenciem exportações NFS, montem diretórios remotos e configurem a inicialização automática de compartilhamentos na inicialização do sistema. Um mecanismo de diagnóstico inteligente identifica falhas de conexão e sugere soluções específicas para problemas de rede. Os usuários podem monitorar o desempenho do servidor em tempo real e revisar registros de atividade detalhados para garantir a segurança operacional. Scripts de instalação automatizados e suporte multilíngue tornam a implantação global em ambientes Linux simples e acessível.

- **Shares (exportações NFS):** define quais diretórios locais são acessíveis por clientes remotos, com controle de IPs autorizados (CIDR), modo leitura/escrita, sincronização e política de squash de permissões.
- **Mounts (montagens remotas):** conecta recursos compartilhados de outros servidores NFS com opções completas de protocolo: versão (NFSv3/NFSv4), tamanho de bloco (rsize/wsize), timeouts, TCP/UDP, hard/soft mount.
- **Monitoramento do servidor:** estado de `nfs-server` e `rpcbind`, serviços RPC registrados, estatísticas de protocolo do `/proc/net/rpc`, métricas de I/O por montagem via `nfsiostat`.
- **Auto-mount na inicialização:** monta automaticamente os recursos configurados com `auto_mount=1` por meio de um serviço init do sistema.
- **Detecção de conexões:** monitora montagens ativas e clientes conectados em tempo real; detecta mudanças de estado fora do plugin.
- **Diagnóstico inteligente de falhas:** sequência de 7 verificações (ping, IP, portas, showmount, CIDR-matching) com causa exata e sugestões acionáveis.
- **Registro de atividade:** log thread-safe de todas as operações com filtros por tipo de evento, resultado e IP.

---

## 3. Requisitos do sistema

| Componente | Requisito |
|---|---|
| Painel | aaPanel (BT Panel) instalado |
| Sistema operacional | Ubuntu/Debian 16.04+ · CentOS/RHEL/Rocky/Alma 7+ |
| Python | 3.6+ (incluído no ambiente do painel) |
| Pacotes do SO | `nfs-kernel-server` + `nfs-common` (Debian/Ubuntu) · `nfs-utils` (RHEL/CentOS) |

---

## 4. Instalação

```bash
# 1. Copiar o plugin para o diretório do painel
cp -r nfs_free/ /www/server/panel/plugin/nfs_free/

# 2. Executar o instalador
sudo bash /www/server/panel/plugin/nfs_free/install.sh install
```

O instalador realiza automaticamente:

- Instalação dos pacotes NFS do sistema operacional
- Fixação do mountd na porta fixa 20048
- Abertura de portas no ufw (se ativo)
- Registro do serviço init `/etc/init.d/nfs_free`
- Ativação de `nfs-server` e `rpcbind` via systemd
- Recarregamento do painel aaPanel

**Desinstalação:**

```bash
sudo bash /www/server/panel/plugin/nfs_free/install.sh uninstall
```

> Os pacotes NFS do sistema e `/etc/exports` **não são modificados** na desinstalação.

**Instalação manual de dependências (se o instalador automático falhar):**

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y nfs-kernel-server nfs-common rpcbind

# RHEL/CentOS/Rocky/Alma
sudo yum install -y nfs-utils rpcbind
```

---

## 5. Estrutura de arquivos

```
nfs_free/
├── info.json              # Metadados do plugin (nome, versão, autor)
├── icon.png               # Ícone 512×512 RGBA
├── index.html             # Frontend: CSS + HTML + JavaScript
├── nfs_free_main.py       # Backend: classe nfs_free_main (32 métodos)
├── nfs_free_service       # Wrapper Python para auto_mount() no boot
├── install.sh             # Instalação e desinstalação
├── init.sh                # Script /etc/init.d para auto-mount
├── upgrade.sh             # Atualiza pacotes NFS e reinicia serviços
├── repair.sh              # Reconfigura porta mountd e reinicia
└── config/
    ├── share.json             # Exportações NFS configuradas
    ├── mount.json             # Montagens remotas configuradas
    ├── connection_state.json  # Estado atual das conexões
    └── activity.log.json      # Log de atividade (últimas 1000 entradas)
```

---

## 6. Portas e firewall

O NFS requer as seguintes portas abertas no **servidor**:

| Porta  | Serviço  | Protocolo | Descrição |
|--------|----------|-----------|-----------|
| 111    | rpcbind  | TCP/UDP   | Mapeador de portas — descobre serviços RPC |
| 2049   | nfs      | TCP       | Protocolo principal NFS |
| 20048  | mountd   | TCP/UDP   | Solicitações de montagem (porta fixa) |
| 32874  | lockd    | TCP/UDP   | Bloqueio de arquivos |
| 32876  | statd    | TCP/UDP   | Recuperação de estado |

Por padrão, o mountd usa uma porta aleatória atribuída pelo rpcbind. O plugin configura `/etc/nfs.conf` para fixá-lo na porta **20048**, permitindo regras de firewall previsíveis entre servidores.

```bash
# Abrir portas para uma sub-rede específica com ufw
sudo ufw allow from 192.168.1.0/24 to any port 111
sudo ufw allow from 192.168.1.0/24 to any port 2049
sudo ufw allow from 192.168.1.0/24 to any port 20048
```

---

## 7. Arquivos de configuração

### share.json — Exportações NFS

```json
[
  {
    "share_name": "backups",
    "path": "/www/backup",
    "rw_mode": "rw",
    "sync_mode": "async",
    "squash": "all_squash",
    "user": "nfsnobody",
    "limit_address": "192.168.1.0/24",
    "ps": "Backups diários"
  }
]
```

### mount.json — Montagens remotas

```json
[
  {
    "mount_name": "producao",
    "server_address": "192.168.1.100",
    "nfs_path": "/data/app",
    "mount_path": "/mnt/nfs-prod",
    "proto": "tcp",
    "rw_mode": "rw",
    "hard": 1,
    "rsize": 1048576,
    "wsize": 1048576,
    "timeo": 600,
    "vers": 4,
    "auto_mount": 1
  }
]
```

---

## 8. Auto-mount na inicialização

O serviço `/etc/init.d/nfs_free` monta automaticamente todos os recursos com `auto_mount=1` na inicialização do sistema.

```
Sistema inicia
  → /etc/init.d/nfs_free start
    → nfs_free_service (Python)
      → nfs_free_main.auto_mount()
        → para cada mount com auto_mount=1:
            verifica se já está montado (mountpoint -q)
            se não: executa mount -t nfs -o ...
```

```bash
/etc/init.d/nfs_free start    # Iniciar
/etc/init.d/nfs_free stop     # Parar
/etc/init.d/nfs_free restart  # Reiniciar
/etc/init.d/nfs_free status   # Ver estado
```

---

## 9. Diagnóstico de falhas

Quando uma montagem falha, o sistema executa automaticamente uma sequência de 7 verificações:

| Etapa | Verificação | Ferramenta |
|-------|------------|------------|
| 1     | Acessibilidade do servidor | `ping -c 1 -W 2` |
| 2     | IP de saída do cliente | `ip route get` |
| 3     | Portas 111, 2049, 20048 | `/dev/tcp` |
| 4     | Lista de exports do servidor | `showmount -e` |
| 5     | Caminho presente nos exports | análise do showmount |
| 6     | IP do cliente nas regras de acesso | `ipaddress.ip_network()` CIDR |
| 7     | Pistas da mensagem de erro do kernel | análise de palavras-chave |

---

## 10. Scripts de manutenção

```bash
# Reparar porta mountd e reiniciar serviços
sudo bash /www/server/panel/plugin/nfs_free/repair.sh

# Atualizar pacotes NFS do sistema
sudo bash /www/server/panel/plugin/nfs_free/upgrade.sh
```

---

## 11. API do backend

A classe `nfs_free_main` expõe 32 métodos em 5 categorias:

| Categoria | Métodos principais |
|---|---|
| Shares | `get_share_list`, `create_share`, `modify_share`, `remove_share`, `show_ip_share_list` |
| Mounts | `get_mount_list`, `create_mount`, `modify_mount`, `remove_mount`, `to_mount`, `to_umount`, `auto_mount` |
| Servidor | `get_server_status`, `server_admin`, `get_overview`, `get_nfsstat`, `get_nfsiostat` |
| Conexões | `get_connections`, `get_disk_mounts`, `get_nfs_ports`, `fix_mountd_port` |
| Log | `get_log`, `clear_log` |

---

## 12. Contribuição

Este projeto é **Open Source** e vive graças à comunidade. Suas contribuições são bem-vindas!

### Como contribuir

1. Faça um **fork** do repositório
2. Crie sua branch de funcionalidade:
   ```bash
   git checkout -b feature/nova-funcionalidade
   ```
3. Realize suas alterações e verifique o funcionamento no aaPanel
4. Faça commit das suas mudanças:
   ```bash
   git commit -m 'Add: descrição clara da mudança'
   ```
5. Faça push para sua branch:
   ```bash
   git push origin feature/nova-funcionalidade
   ```
6. Abra um **Pull Request**

### Diretrizes de contribuição

- Siga o guia de estilo [PEP-8](https://pep8.org/) para código Python
- Documente todos os métodos públicos com docstrings
- Adicione testes para novas funcionalidades
- Atualize a documentação relevante
- Mantenha a compatibilidade com a interface de plugins do aaPanel

### Áreas que precisam de ajuda

- 📝 Melhorias na documentação
- 🧪 Testes unitários e de integração
- 🎨 Melhorias na interface do painel
- 🔧 Novas funcionalidades NFS (suporte Kerberos, métricas adicionais)
- 🌍 Traduções de documentação
- 🐛 Relatórios de bugs

---

## 13. Suporte e comunidade

### Precisa de ajuda?

- 🐛 **Reportar bugs:** Abra uma [issue no GitHub](https://github.com/jalexiscv/nfs_free/issues)
- 💡 **Solicitar funcionalidades:** Use as [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)
- 📧 **Contato direto:** jalexiscv@gmail.com

### Comunidade

- Participe das conversas nas [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)
- Verifique as [issues marcadas como "good first issue"](https://github.com/jalexiscv/nfs_free/labels/good%20first%20issue)

---

## 14. Licença

Distribuído sob a Licença **MIT**.

> A licença MIT permite usar, copiar, modificar, mesclar, publicar, distribuir, sublicenciar e/ou vender cópias do software sem restrições, desde que o aviso de copyright original seja incluído.

---

## 15. Autor

**Jose Alexis Correa Valencia**
*Full Stack Developer & Software Architect*

Mais de 25 anos de experiência em desenvolvimento de software empresarial, especializado em arquiteturas escaláveis e infraestrutura Linux.

- **GitHub:** [@jalexiscv](https://github.com/jalexiscv)
- **LinkedIn:** [Jose Alexis Correa Valencia](https://www.linkedin.com/in/jalexiscv/)
- **Email:** jalexiscv@gmail.com
- **Localização:** Colômbia 🇨🇴

---

## 16. Doações

Se este plugin foi útil para você ou seu negócio, considere apoiar seu desenvolvimento e manutenção contínuos.

| Método | Detalhes |
|--------|----------|
| **PayPal** | [jalexiscv@gmail.com](https://www.paypal.com/paypalme/jalexiscv) |
| **Nequi (Colômbia)** | `3117977281` |

Seu apoio ajuda a:
- Acelerar o desenvolvimento de novas funcionalidades
- Criar mais documentação e exemplos
- Melhorar a cobertura de testes
- Manter o projeto ativo e atualizado

*Obrigado pelo seu apoio!*

---

*Network File System (NFS) Free Edition — Copyright © 2023 Jose Alexis Correa Valencia — Publicado em 9 de julho de 2023 — MIT License*
