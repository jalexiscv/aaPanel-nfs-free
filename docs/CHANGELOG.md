# Changelog

All notable changes to **NFS Free Edition** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Documentation

#### Repository
- `README.md` — version badge corrected from `1.1` to `1.2`

### Fixed

#### Backend — `nfs_free_main.py`
- `create_share` / `modify_share` — add IP/CIDR format validation before writing to `/etc/exports`; currently any string is accepted without verification
- `get_overview` — wrap each data source (`nfsiostat`, `get_server_status`, `get_share_list`, etc.) in individual try/except blocks so a failure in one section does not take down the entire dashboard
- `exec_shell` — audit all call sites to ensure no user-supplied input reaches the shell string unescaped; `shell=True` combined with unsanitised parameters is a potential command-injection vector

### Changed

#### Backend — `nfs_free_main.py`
- `_diagnose_mount_failure` — refactor into named sub-steps (reachability, port check, export enumeration, CIDR validation, kernel error analysis) to reduce method length and improve readability

#### Scripts
- `upgrade.sh` — extend to also upgrade the plugin itself: download the latest release zip from GitHub Releases, extract over the current installation, and restart the init service; currently only updates NFS system packages
- `repair.sh` — additionally verify and restore plugin file permissions in addition to re-applying fixed-port configuration

### Added

#### Repository infrastructure
- `SECURITY.md` — document the vulnerability reporting process (contact channel, expected response time, supported versions)
- `.github/workflows/ci.yml` — add a CI workflow triggered on every push to `main` that runs `flake8` and `pylint` against `nfs_free_main.py`

---

## [1.2] - 2024-06-03

### Changed

#### Documentation — `nfs_free_main.py`
- File header version corrected from `1.0` to `1.1`
- `__init__` — added missing docstring describing the four file paths it initialises and why `_ensure_mountd_port` is called at construction time
- `_ensure_mountd_port` — expanded docstring to cover all three daemons it pins (mountd 20048, lockd 32874, statd 32876) and the silent-exception behaviour
- `save_share_config` / `save_mount_config` — removed `@return void` annotation (not valid Python)
- `get_share_list` — return value now documents both the `list` and the `ports` keys
- `write_mount_conf` — docstring now honestly describes it as a no-op stub kept for API compatibility, explaining that boot persistence is handled by `auto_mount()` reading `config/mount.json`
- `get_nfsiostat` — clarified that this public endpoint returns raw text lines for the frontend; structured per-mount metrics are provided by the internal `_parse_nfsiostat()`
- `get_nfs_ports` / `fix_mountd_port` — moved from the `# INTERNAL` section banner to a dedicated `# PORT CONFIGURATION` section, reflecting their public API status
- `check_update` — return dict is now fully documented (`status`, `current`, `latest`, `has_update`, `release_url`, `release_name`, `msg`)
- `__get_mod` — added docstring noting it is an unused named-mangled stub retained for potential future introspection by aaPanel
- All 38 remaining docstrings — converted from `@param name<type>` / `@return type` Javadoc style to standard Python prose; parameter and return information is now expressed as plain text within the docstring body

#### Repository
- Documentation files (`CHANGELOG.md`, `README_*.md`) moved to `docs/` directory; `README.md` links updated accordingly

---

## [1.1] - 2023-10-23

### Added

#### Backend — `nfs_free_main.py`
- `check_update` — queries the GitHub Releases API (`/repos/jalexiscv/aaPanel-nfs-free/releases/latest`) to compare the installed version against the latest published release; result cached for 1 hour in `config/update_cache.json` to respect GitHub's unauthenticated rate limit

#### Frontend — `index.html`
- Update banner in the Overview tab: shown automatically when `check_update` reports a newer version; displays current vs. latest version numbers and a direct link to the GitHub release page

#### Repository infrastructure
- `info.json` — `home` field updated to point to the GitHub Releases page instead of the author profile
- `.gitignore` — added `.claude/` to prevent session data from being committed
- `assets/` — real UI screenshots added for all five plugin tabs (Overview, Shared list, Mount list, Service status, Activity log)
- `README.md` — ASCII UI mockups replaced with actual screenshots; plugin icon updated to a server-rack and network-tree design at 512×512 px; icon display size bumped to 128 px in the banner
- `README_*.md` — icon dimension annotation corrected from 48×48 to 512×512 in all six language files
- `.github/workflows/release.yml` — release step now extracts the matching `## [x.y]` section from `CHANGELOG.md` via `awk` and passes it as `--notes-file` instead of using `--generate-notes`

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

[Unreleased]: https://github.com/jalexiscv/aaPanel-nfs-free/compare/v1.2...HEAD
[1.2]: https://github.com/jalexiscv/aaPanel-nfs-free/compare/v1.1...v1.2
[1.1]: https://github.com/jalexiscv/aaPanel-nfs-free/compare/v1.0...v1.1
[1.0]: https://github.com/jalexiscv/aaPanel-nfs-free/releases/tag/v1.0
