# 🇬🇧 Network File System (NFS) — Free Edition

> [🇪🇸 Español](README_ES.md) · [🇧🇷 Português](README_PT.md) · [🇯🇵 日本語](README_JA.md) · [🇩🇪 Deutsch](README_DE.md) · [🇷🇺 Русский](README_RU.md)

A free, open-source aaPanel plugin that provides complete NFS management through a graphical interface: create exports (shares), mount remote directories, monitor the NFS server, and automatically diagnose mount failures.

```
Author:  Jose Alexis Correa Valencia (jalexiscv)
Version: 1.0
License: MIT — Free Software
```

---

## Table of Contents

1. [About the NFS Protocol](#1-about-the-nfs-protocol)
2. [Plugin Features](#2-plugin-features)
3. [System Requirements](#3-system-requirements)
4. [Installation](#4-installation)
5. [File Structure](#5-file-structure)
6. [Ports and Firewall](#6-ports-and-firewall)
7. [Configuration Files](#7-configuration-files)
8. [Auto-Mount at Boot](#8-auto-mount-at-boot)
9. [Failure Diagnostics](#9-failure-diagnostics)
10. [Maintenance Scripts](#10-maintenance-scripts)
11. [Backend API](#11-backend-api)
12. [Contributing](#12-contributing)
13. [Support and Community](#13-support-and-community)
14. [License](#14-license)
15. [Author](#15-author)
16. [Donations](#16-donations)

---

## 1. About the NFS Protocol

**Network File System (NFS)** is a distributed file system protocol originally developed by Sun Microsystems in 1984. It allows an operating system to access files stored on a remote machine over a network in the same way it would access local files, making the physical location of storage transparent to applications.

NFS operates on a client/server model: the server **exports** a directory and makes it available on the network; the client **mounts** it locally as if it were its own volume. Communication is carried out through Remote Procedure Calls (RPC) over TCP or UDP.

### Protocol Versions

| Version | Year | Key Features |
|---------|------|-------------|
| NFSv2   | 1989 | First widely deployed version; UDP only; max 2 GB files |
| NFSv3   | 1995 | TCP support; large file support (64-bit offsets); asynchronous writes |
| NFSv4   | 2003 | Stateful protocol; strong authentication (Kerberos); single port (2049); ACL support |
| NFSv4.1 | 2010 | pNFS (parallel access); resilient sessions; improved cluster support |

### Common Use Cases

- Shared storage between application servers
- Centralized home directories in Linux/Unix environments
- Distributed backup infrastructure
- Shared storage for HPC clusters and Kubernetes
- Static asset sharing (images, videos) between web servers

> **Security:** NFS does not encrypt data in transit (unless using Kerberos + RPCSEC_GSS). Always restrict access to trusted subnets and never expose NFS ports to the public Internet.

---

## 2. Plugin Features

- **Shares (NFS exports):** define which local directories are accessible to remote clients, with authorized IP control (CIDR), read/write mode, synchronization, and permission squash policy.
- **Mounts (remote mounts):** connect shared resources from other NFS servers with full protocol options: version (NFSv3/NFSv4), block size (rsize/wsize), timeouts, TCP/UDP, hard/soft mount.
- **Server monitoring:** `nfs-server` and `rpcbind` status, registered RPC services, protocol statistics from `/proc/net/rpc`, per-mount I/O metrics via `nfsiostat`.
- **Auto-mount at boot:** automatically mounts resources configured with `auto_mount=1` via a system init service.
- **Connection tracking:** monitors active mounts and incoming clients in real time; detects state changes that occur outside the plugin.
- **Intelligent failure diagnostics:** 7-step verification sequence (ping, IP detection, port checks, showmount, CIDR matching) with exact cause and actionable suggestions.
- **Activity log:** thread-safe log of all operations with filters by event type, result, and IP address.

---

## 3. System Requirements

| Component | Requirement |
|---|---|
| Panel | aaPanel (BT Panel) installed |
| Operating system | Ubuntu/Debian 16.04+ · CentOS/RHEL/Rocky/Alma 7+ |
| Python | 3.6+ (included in the panel environment) |
| System packages | `nfs-kernel-server` + `nfs-common` (Debian/Ubuntu) · `nfs-utils` (RHEL/CentOS) |

---

## 4. Installation

```bash
# 1. Copy the plugin to the panel directory
cp -r nfs_free/ /www/server/panel/plugin/nfs_free/

# 2. Run the installer
sudo bash /www/server/panel/plugin/nfs_free/install.sh install
```

The installer automatically handles:

- NFS package installation
- Pinning mountd to fixed port 20048
- Opening firewall ports in ufw (if active)
- Registering the init service at `/etc/init.d/nfs_free`
- Enabling `nfs-server` and `rpcbind` via systemd
- Reloading the aaPanel

**Uninstallation:**

```bash
sudo bash /www/server/panel/plugin/nfs_free/install.sh uninstall
```

> System NFS packages and `/etc/exports` are **not modified** on uninstall.

**Manual dependency installation (if the automatic installer fails):**

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y nfs-kernel-server nfs-common rpcbind

# RHEL/CentOS/Rocky/Alma
sudo yum install -y nfs-utils rpcbind
```

---

## 5. File Structure

```
nfs_free/
├── info.json              # Plugin metadata (name, version, author)
├── icon.png               # 48×48 RGBA icon
├── index.html             # Frontend: CSS + HTML + JavaScript
├── nfs_free_main.py       # Backend: nfs_free_main class (32 methods)
├── nfs_free_service       # Python wrapper for auto_mount() at boot
├── install.sh             # Installation and uninstallation
├── init.sh                # /etc/init.d script for auto-mount
├── upgrade.sh             # Updates NFS packages and restarts services
├── repair.sh              # Reconfigures mountd port and restarts
└── config/
    ├── share.json             # Configured NFS exports
    ├── mount.json             # Configured remote mounts
    ├── connection_state.json  # Current connection state snapshot
    └── activity.log.json      # Activity log (last 1000 entries)
```

---

## 6. Ports and Firewall

NFS requires the following ports open on the **server**:

| Port  | Service  | Protocol | Description |
|-------|----------|----------|-------------|
| 111   | rpcbind  | TCP/UDP  | Port mapper — discovers RPC services |
| 2049  | nfs      | TCP      | Main NFS protocol |
| 20048 | mountd   | TCP/UDP  | Mount requests (fixed port) |
| 32874 | lockd    | TCP/UDP  | File locking |
| 32876 | statd    | TCP/UDP  | State recovery |

By default, mountd uses a random port assigned by rpcbind. The plugin configures `/etc/nfs.conf` to pin it to port **20048**, enabling predictable firewall rules between servers.

```bash
# Open ports for a specific subnet with ufw
sudo ufw allow from 192.168.1.0/24 to any port 111
sudo ufw allow from 192.168.1.0/24 to any port 2049
sudo ufw allow from 192.168.1.0/24 to any port 20048
```

---

## 7. Configuration Files

### share.json — NFS Exports

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
    "ps": "Daily backups"
  }
]
```

### mount.json — Remote Mounts

```json
[
  {
    "mount_name": "production",
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

## 8. Auto-Mount at Boot

The `/etc/init.d/nfs_free` service automatically mounts all resources with `auto_mount=1` at system startup.

```
System boots
  → /etc/init.d/nfs_free start
    → nfs_free_service (Python)
      → nfs_free_main.auto_mount()
        → for each mount with auto_mount=1:
            check if already mounted (mountpoint -q)
            if not: run mount -t nfs -o ...
```

```bash
/etc/init.d/nfs_free start    # Start
/etc/init.d/nfs_free stop     # Stop
/etc/init.d/nfs_free restart  # Restart
/etc/init.d/nfs_free status   # Status
```

---

## 9. Failure Diagnostics

When a mount fails, the system automatically runs a 7-step verification sequence:

| Step | Check | Tool |
|------|-------|------|
| 1    | Server reachability | `ping -c 1 -W 2` |
| 2    | Client outgoing IP | `ip route get` |
| 3    | Ports 111, 2049, 20048 | `/dev/tcp` |
| 4    | Server export list | `showmount -e` |
| 5    | Path present in exports | showmount output parsing |
| 6    | Client IP in access rules | `ipaddress.ip_network()` CIDR |
| 7    | Clues from kernel error message | keyword analysis |

**Example output:**

```
Mount failed: mount.nfs: access denied by server while mounting 192.168.1.10:/data

Diagnostic:
  • Server 192.168.1.10 rejected IP 10.0.0.5:
    export '/data' only allows [192.168.1.0/24]

Suggestions:
  → On the server, add '10.0.0.5' to 'Allowed IPs' for share '/data', then click 'Save'
```

---

## 10. Maintenance Scripts

```bash
# Repair mountd port and restart services
sudo bash /www/server/panel/plugin/nfs_free/repair.sh

# Update NFS system packages
sudo bash /www/server/panel/plugin/nfs_free/upgrade.sh
```

---

## 11. Backend API

The `nfs_free_main` class exposes 32 methods in 5 categories:

| Category | Main Methods |
|---|---|
| Shares | `get_share_list`, `create_share`, `modify_share`, `remove_share`, `show_ip_share_list` |
| Mounts | `get_mount_list`, `create_mount`, `modify_mount`, `remove_mount`, `to_mount`, `to_umount`, `auto_mount` |
| Server | `get_server_status`, `server_admin`, `get_overview`, `get_nfsstat`, `get_nfsiostat` |
| Connections | `get_connections`, `get_disk_mounts`, `get_nfs_ports`, `fix_mountd_port` |
| Log | `get_log`, `clear_log` |

---

## 12. Contributing

This project is **Open Source** and lives thanks to the community. Your contributions are welcome!

### How to Contribute

1. **Fork** the repository
2. Create your feature branch:
   ```bash
   git checkout -b feature/new-feature
   ```
3. Make your changes and verify the plugin works in aaPanel
4. Commit your changes:
   ```bash
   git commit -m 'Add: clear description of the change'
   ```
5. Push to your branch:
   ```bash
   git push origin feature/new-feature
   ```
6. Open a **Pull Request**

### Contribution Guidelines

- Follow the [PEP-8](https://pep8.org/) style guide for Python code
- Document all public methods with docstrings
- Add tests for new features
- Update relevant documentation
- Maintain compatibility with the aaPanel plugin interface

### Areas That Need Help

- 📝 Documentation improvements
- 🧪 Unit and integration tests
- 🎨 Panel UI improvements
- 🔧 New NFS features (Kerberos support, additional metrics)
- 🌍 Documentation translations
- 🐛 Bug reports

---

## 13. Support and Community

### Need Help?

- 🐛 **Report bugs:** Open an [issue on GitHub](https://github.com/jalexiscv/nfs_free/issues)
- 💡 **Request features:** Use [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)
- 📧 **Direct contact:** jalexiscv@gmail.com

### Community

- Join the conversations on [GitHub Discussions](https://github.com/jalexiscv/nfs_free/discussions)
- Check [issues labeled "good first issue"](https://github.com/jalexiscv/nfs_free/labels/good%20first%20issue)

---

## 14. License

Distributed under the **MIT** License.

> The MIT License allows you to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software without restriction, provided the original copyright notice is included.

---

## 15. Author

**Jose Alexis Correa Valencia**
*Full Stack Developer & Software Architect*

Over 25 years of experience in enterprise software development, specialized in scalable architectures and Linux infrastructure.

- **GitHub:** [@jalexiscv](https://github.com/jalexiscv)
- **LinkedIn:** [Jose Alexis Correa Valencia](https://www.linkedin.com/in/jalexiscv/)
- **Email:** jalexiscv@gmail.com
- **Location:** Colombia 🇨🇴

---

## 16. Donations

If this plugin has helped you or your business, consider supporting its ongoing development and maintenance.

| Method | Details |
|--------|---------|
| **PayPal** | [jalexiscv@gmail.com](https://www.paypal.com/paypalme/jalexiscv) |
| **Nequi (Colombia)** | `3117977281` |

Your support helps to:
- Accelerate the development of new features
- Create more documentation and examples
- Improve test coverage
- Keep the project active and up to date

*Thank you for your support!*

---

*Network File System (NFS) Free Edition — Copyright © 2023 Jose Alexis Correa Valencia — Published July 13, 2023 — MIT License*
