# Changelog

All notable changes to **NFS Free Edition** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.0] - 2023-07-31

### Added

#### Backend — `nfs_free_main.py`
- `create_share` / `modify_share` / `remove_share` — full CRUD for NFS exports; writes `/etc/exports` and reloads via `exportfs -ra` on every change
- `get_share_list` / `get_share_find` — list and lookup configured shares
- `show_ip_share_list` — query exports available on a remote server via `showmount -e`
- `create_mount` / `modify_mount` / `remove_mount` — full CRUD for remote NFS mounts with all protocol options (NFSv3/v4, rsize/wsize, timeo, retrans, hard/soft, TCP/UDP, noresvport)
- `to_mount` / `to_umount` — execute mount and unmount operations with live status
- `auto_mount` — boot-time service that mounts all entries with `auto_mount=1`
- `get_mount_list` — enriches configured mounts with live kernel state (`/proc/mounts`) and I/O metrics
- `get_server_status` — checks `nfs-server` and `rpcbind` via `systemctl is-active` and returns registered RPC services via `rpcinfo -p`
- `server_admin` — start / stop / restart / reload NFS services
- `get_overview` — aggregates all dashboard data in a single call (server health, share count, mount status, I/O totals, recent log)
- `get_nfsstat` — parses `/proc/net/rpc/nfsd` and `/proc/net/rpc/nfs` into structured NFSv3/v4 operation counters
- `get_nfsiostat` / `_parse_nfsiostat` — parses `nfsiostat` output into per-mount read/write metrics (ops/s, KB/s, retransmissions, avg RTT/exe)
- `get_connections` — returns active outgoing mounts and incoming clients via `showmount -a`
- `_scan_connection_changes` — detects mount/unmount events that occurred outside the plugin and logs them automatically
- `get_disk_mounts` — lists all NFS mounts active in the kernel from `/proc/mounts`
- `_diagnose_mount_failure` — 7-step intelligent diagnostics: reachability (ping), outgoing IP detection (`ip route get`), port checks (111/2049/20048 via `/dev/tcp`), export enumeration (`showmount -e`), path validation, CIDR-aware IP access control matching, and kernel error keyword analysis
- `fix_mountd_port` / `_ensure_mountd_port` — pins mountd to port 20048, statd to 32876 and lockd to 32874 in `/etc/nfs.conf` for predictable firewall rules
- `_log` — thread-safe activity log using `fcntl.LOCK_EX`; stores up to 1000 entries in `config/activity.log.json`
- `get_log` / `clear_log` — retrieve log with filters (event, result, IP) and truncate

#### Service bootstrap — `nfs_free_service`
- Lightweight Python entry point executed at boot by the SysV init service
- Configures Python module paths for the panel environment and calls `auto_mount()`
- Silent fail on exception to avoid blocking system startup

#### Scripts
- `install.sh` — installs NFS system packages (apt / yum / dnf), pins daemon ports, registers `/etc/init.d/nfs_free`, enables systemd services, sets plugin permissions and signals panel reload; supports `install` and `uninstall` subcommands
- `init.sh` — SysV-compatible init script (`/etc/init.d/nfs_free`); supports `start`, `stop`, `restart`, `reload`, `status`; auto-detects aaPanel Python virtualenv
- `repair.sh` — re-applies fixed-port configuration and restarts the init service; use when mountd reverts to a random port after a reboot or package upgrade
- `upgrade.sh` — upgrades NFS system packages and re-applies port configuration

#### Frontend — `index.html`
- **Overview tab** — dashboard with four metric cards (shares, mounts, disk usage, I/O ops), live service status indicators, last 8 activity log entries, and quick-action buttons
- **Shared list tab** — table of NFS exports with inline add / edit / delete; port requirements panel with security warning
- **Mount list tab** — table of remote mounts with live mounted/unmounted status badge, per-mount I/O indicators (ops/s, read KB/s, write KB/s, retransmissions) and detection of untracked mounts
- **Service status tab** — animated service cards for `nfs-server` and `rpcbind` with start / stop / restart / reload controls; filterable RPC service chips; NFSv3/v4 statistics tabs sourced from `/proc/net/rpc`
- **Activity log tab** — full audit log with filters by event type, result and IP, colour-coded event badges and configurable auto-refresh

#### Documentation
- `README.md` — social README with banner, shields.io badges (license, version, Python, platform, aaPanel, NFS, stars, forks, issues), ASCII UI mockups for all 5 panels, quick-install block and contributor footer
- `README_ES.md` — complete documentation in Spanish (16 sections)
- `README_PT.md` — complete documentation in Portuguese (16 sections)
- `README_EN.md` — complete documentation in English (16 sections)
- `README_JA.md` — complete documentation in Japanese (16 sections)
- `README_DE.md` — complete documentation in German (16 sections)
- `README_RU.md` — complete documentation in Russian (16 sections)

#### Repository infrastructure
- `LICENSE` — MIT License, copyright 2023 Jose Alexis Correa Valencia
- `.gitignore` — excludes `__pycache__/`, `*.pyc`, `*.pyo`, `*.bak*`
- `.github/workflows/release.yml` — automated release pipeline: builds a clean `nfs_free-{version}.zip` with plugin files only, stamps the version into `info.json`, and publishes a GitHub release with the zip as an asset and notes extracted from this changelog

---

[Unreleased]: https://github.com/jalexiscv/aaPanel-nfs-free/compare/v1.0...HEAD
[1.0]: https://github.com/jalexiscv/aaPanel-nfs-free/releases/tag/v1.0
