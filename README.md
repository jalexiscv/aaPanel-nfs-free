<div align="center">

<img src="icon.png" width="128" alt="NFS Free Edition"/>

# Network File System (NFS) — Free Edition

**Free, open-source aaPanel plugin for complete NFS management**

Share directories, mount remote filesystems, monitor your NFS server<br/>
and diagnose mount failures — all from a graphical panel interface.

<br/>

[![License](https://img.shields.io/github/license/jalexiscv/aaPanel-nfs-free?color=blue&style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1-brightgreen?style=flat-square)](https://github.com/jalexiscv/aaPanel-nfs-free/releases)
[![Python](https://img.shields.io/badge/python-3.6%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux-FCC624?style=flat-square&logo=linux&logoColor=black)](https://github.com/jalexiscv/aaPanel-nfs-free)
[![aaPanel](https://img.shields.io/badge/aaPanel-plugin-4A90D9?style=flat-square)](https://www.aapanel.com/)
[![NFS](https://img.shields.io/badge/NFS-v3%20%7C%20v4-informational?style=flat-square)](README_EN.md#1-about-the-nfs-protocol)

<br/>

[![Stars](https://img.shields.io/github/stars/jalexiscv/aaPanel-nfs-free?style=social)](https://github.com/jalexiscv/aaPanel-nfs-free/stargazers)
[![Forks](https://img.shields.io/github/forks/jalexiscv/aaPanel-nfs-free?style=social)](https://github.com/jalexiscv/aaPanel-nfs-free/network/members)
[![Issues](https://img.shields.io/github/issues/jalexiscv/aaPanel-nfs-free?style=social)](https://github.com/jalexiscv/aaPanel-nfs-free/issues)

</div>

---

## Features

| | |
|---|---|
| 📂 **NFS Shares** | Create and manage exports with per-client IP/CIDR control, rw/ro modes and squash policies |
| 🔗 **Remote Mounts** | Mount remote NFS paths with full protocol options: NFSv3/v4, rsize/wsize, TCP/UDP, hard/soft |
| 📊 **Server Monitoring** | Live status of `nfs-server` and `rpcbind`, RPC service list, `/proc/net/rpc` stats, `nfsiostat` I/O metrics |
| 🚀 **Auto-mount at Boot** | SysV init service mounts all `auto_mount=1` entries automatically on system startup |
| 🔍 **Intelligent Diagnostics** | 7-step failure analysis — ping, IP detection, port check, showmount, CIDR matching — with actionable suggestions |
| 📋 **Activity Log** | Thread-safe audit log of every operation, filterable by event type, result and IP address |
| 🔄 **Connection Tracking** | Detects mounts and client connections that happen outside the plugin in real time |

---

## Quick Install

```bash
# 1. Copy plugin files to the aaPanel plugin directory
cp -r nfs_free/ /www/server/panel/plugin/nfs_free/

# 2. Run the installer
sudo bash /www/server/panel/plugin/nfs_free/install.sh install
```

The installer handles NFS packages, fixed-port configuration for mountd (20048),
firewall rules, SysV init service and systemd service activation automatically.

---

## Screenshots

### Dashboard

![NFS Free Edition — Dashboard](assets/Snap-2023-08-29T11:20:00-05:00.png)

### Shared List

![NFS Free Edition — Shared List](assets/nfs-shared-list.png)

### Mount List

![NFS Free Edition — Mount List](assets/nfs-mount-list.png)

### Service Status

![NFS Free Edition — Service Status](assets/nfs-service-status.png)

### Activity Log

![NFS Free Edition — Activity Log](assets/nfs-activity-log.png)

---

## Ports Required on the Server

| Port  | Service | Protocol | Role |
|-------|---------|----------|------|
| 111   | rpcbind | TCP/UDP  | Port mapper |
| 2049  | nfs     | TCP      | NFS data transfer |
| 20048 | mountd  | TCP/UDP  | Mount requests (pinned) |
| 32874 | lockd   | TCP/UDP  | File locking |
| 32876 | statd   | TCP/UDP  | State recovery |

---

## Documentation

<div align="center">

| Language | File |
|----------|------|
| 🇪🇸 Español | [README_ES.md](README_ES.md) |
| 🇧🇷 Português | [README_PT.md](README_PT.md) |
| 🇬🇧 English | [README_EN.md](README_EN.md) |
| 🇯🇵 日本語 | [README_JA.md](README_JA.md) |
| 🇩🇪 Deutsch | [README_DE.md](README_DE.md) |
| 🇷🇺 Русский | [README_RU.md](README_RU.md) |

</div>

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'Add: my feature'`
4. Push and open a Pull Request

See [README_EN.md](README_EN.md#12-contributing) for full contribution guidelines.

---

<div align="center">

Made with care by **[Jose Alexis Correa Valencia](https://github.com/jalexiscv)** · Colombia 🇨🇴

[![GitHub](https://img.shields.io/badge/GitHub-jalexiscv-181717?style=flat-square&logo=github)](https://github.com/jalexiscv)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-jalexiscv-0A66C2?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/jalexiscv/)
[![Email](https://img.shields.io/badge/Email-jalexiscv%40gmail.com-EA4335?style=flat-square&logo=gmail)](mailto:jalexiscv@gmail.com)

*Network File System (NFS) Free Edition — Copyright © 2023 Jose Alexis Correa Valencia — Published July 31, 2023 — MIT License*

</div>
