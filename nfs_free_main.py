#!/www/server/panel/pyenv/bin/python3
# coding: utf-8
# =============================================================================
#  Network File System (NFS) — Free Edition
#  Main Plugin Module
# =============================================================================
#  Description : Core backend class for the nfs_free aaPanel plugin.
#                Provides a complete NFS management API: creating and managing
#                local NFS exports (shares), mounting remote NFS filesystems,
#                monitoring nfs-server / rpcbind service health, parsing
#                protocol statistics from /proc/net/rpc and nfsiostat, and
#                running step-by-step diagnostics when a mount fails.
#
#                The aaPanel request router maps HTTP calls of the form
#                  plugin?action=<method>&name=nfs_free
#                directly to public methods of this class.
#
#  Architecture:
#    - State persisted as JSON in config/ (no database required)
#    - /etc/exports written on every share create / modify / delete
#    - mountd pinned to port 20048 via /etc/nfs.conf for firewall stability
#    - Activity log is thread-safe (fcntl.LOCK_EX), capped at 1000 entries
#
#  Public API groups:
#    Shares      : get_share_list, get_share_find, create_share,
#                  modify_share, remove_share, show_ip_share_list
#    Mounts      : get_mount_list, get_mount_find, get_mount, get_mount_cmd,
#                  create_mount, modify_mount, remove_mount,
#                  to_mount, to_umount, auto_mount, set_mount, set_umount
#    Server      : get_server_status, server_admin, get_overview,
#                  get_nfsstat, get_nfsiostat, check_update
#    Connections : get_connections, get_disk_mounts, get_nfs_ports,
#                  fix_mountd_port
#    Log         : get_log, clear_log
#
#  Author      : Jose Alexis Correa Valencia (jalexiscv)
#  Email       : jalexiscv@gmail.com
#  GitHub      : https://github.com/jalexiscv
#  LinkedIn    : https://www.linkedin.com/in/jalexiscv/
#  Version     : 1.1
#  License     : MIT — Free Software
#  Date        : July 3, 2023
#  Copyright   : © 2023 Jose Alexis Correa Valencia
#  Note        : Based on the aaPanel plugin architecture, reimplemented
#                as free and open-source software.
# =============================================================================

import os, sys, json, subprocess, time, re, uuid, datetime, fcntl

PANEL_PATH = '/www/server/panel'
PLUGIN_PATH = PANEL_PATH + '/plugin/nfs_free'

class nfs_free_main:
    """Network File System (NFS) Manager v1.1 — Free Edition
    File sharing based on NFS service.
    Features: share creation, remote mount, auto-mount at boot, server monitoring.
    """

    def __init__(self):
        """Initialise paths and ensure daemon ports are pinned.

        Sets up the four file paths used throughout the plugin (config dir,
        share JSON, mount JSON, activity log) and calls _ensure_mountd_port so
        that mountd/lockd/statd are always on their fixed ports from the first
        request onward.
        """
        self._config_path = os.path.join(PLUGIN_PATH, 'config')
        self._share_file = os.path.join(self._config_path, 'share.json')
        self._mount_file = os.path.join(self._config_path, 'mount.json')
        self._log_file   = os.path.join(self._config_path, 'activity.log.json')
        self._exports_file = '/etc/exports'
        self._ensure_mountd_port()

    # ════════════════════════════════════════════════════════════
    # UTILITIES
    # ════════════════════════════════════════════════════════════

    def _ensure_mountd_port(self):
        """Pin mountd, lockd and statd to fixed ports on first load.

        Writes /etc/nfs.conf only when mountd is not already set to 20048.
        Also pins lockd to 32874 (TCP+UDP) and statd to 32876 so all three
        NFS helper daemons use predictable ports that can be whitelisted in a
        firewall without dynamic port ranges.  Restarts nfs-server and rpcbind
        after writing.  Any exception is silently swallowed to avoid blocking
        the panel request that triggered __init__.
        """
        import configparser
        nfs_conf = "/etc/nfs.conf"
        try:
            config = configparser.ConfigParser()
            if os.path.exists(nfs_conf):
                config.read(nfs_conf)
            if config.has_section("mountd") and config.get("mountd", "port", fallback="") == "20048":
                return
            if not config.has_section("mountd"):
                config.add_section("mountd")
            config.set("mountd", "port", "20048")
            if not config.has_section("lockd"):
                config.add_section("lockd")
            config.set("lockd", "port", "32874")
            config.set("lockd", "udp-port", "32874")
            if not config.has_section("statd"):
                config.add_section("statd")
            config.set("statd", "port", "32876")
            with open(nfs_conf, "w") as f:
                config.write(f)
            self.exec_shell("systemctl restart nfs-server 2>/dev/null")
            self.exec_shell("systemctl restart rpcbind 2>/dev/null")
        except Exception:
            pass

    def exec_shell(self, cmdstring, timeout=60):
        """Execute a shell command and return (success, output).

        success is True when the exit code is 0.  output combines stdout and
        stderr, stripped of leading/trailing whitespace.
        """
        try:
            result = subprocess.run(
                cmdstring, shell=True, capture_output=True,
                text=True, timeout=timeout
            )
            return (result.returncode == 0, (result.stdout + result.stderr).strip())
        except subprocess.TimeoutExpired:
            return (False, 'command timed out')
        except Exception as e:
            return (False, str(e))

    def exists_args(self, get, *args):
        """Return True only if every name in args is a non-empty key in get."""
        d = self._to_dict(get)
        if d is None:
            return False
        for k in args:
            val = d.get(k, '')
            if not str(val).strip():
                return False
        return True

    def _to_dict(self, get):
        """Normalize get parameter to a plain dict."""
        if get is None:
            return {}
        if isinstance(get, dict):
            return get
        if hasattr(get, '__dict__'):
            return {k: v for k, v in get.__dict__.items() if not k.startswith('_')}
        try:
            return dict(get)
        except Exception:
            return None

    def get_user_id(self, username='nfsnobody'):
        """Return (uid, gid) for username, falling back to nobody then 65534."""
        import pwd
        for name in (username, 'nfsnobody', 'nobody'):
            try:
                u = pwd.getpwnam(name)
                return (u.pw_uid, u.pw_gid)
            except (KeyError, ImportError):
                continue
        return (65534, 65534)

    # ════════════════════════════════════════════════════════════
    # SHARE CONFIGURATION I/O
    # ════════════════════════════════════════════════════════════

    def get_share_config(self):
        """Read and return the share list from config/share.json ([] on error)."""
        try:
            if os.path.exists(self._share_file):
                with open(self._share_file, 'r') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def save_share_config(self, shares):
        """Persist share configuration to disk (config/share.json)."""
        os.makedirs(self._config_path, exist_ok=True)
        with open(self._share_file, 'w') as f:
            json.dump(shares, f, indent=2)

    # ════════════════════════════════════════════════════════════
    # MOUNT CONFIGURATION I/O
    # ════════════════════════════════════════════════════════════

    def get_mount_config(self):
        """Read and return the mount list from config/mount.json ([] on error)."""
        try:
            if os.path.exists(self._mount_file):
                with open(self._mount_file, 'r') as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def save_mount_config(self, mounts):
        """Persist mount configuration to disk (config/mount.json)."""
        os.makedirs(self._config_path, exist_ok=True)
        with open(self._mount_file, 'w') as f:
            json.dump(mounts, f, indent=2)

    # ════════════════════════════════════════════════════════════
    # SHARE API — Local NFS Exports
    # ════════════════════════════════════════════════════════════

    def get_share_list(self, get=None):
        """Return all configured NFS shares plus the required firewall ports.

        Returns a dict with two keys:
          list  — array of share dicts from config/share.json
          ports — string listing the ports that must be open on the server
                  firewall for NFS to work ('111/2049/20048/32874-65535')
        """
        shares = self.get_share_config()
        for s in shares:
            if 'path' not in s and 'nfs_path' in s:
                s['path'] = s['nfs_path']
        return {'list': shares, 'ports': '111/2049/20048/32874-65535'}

    def get_share_find(self, get=None):
        """Return the share dict for share_name, or {} if not found.

        get may be a bare string (the share name) or a request dict with a
        share_name key.
        """
        if isinstance(get, str):
            share_name = get
        else:
            d = self._to_dict(get)
            share_name = d.get("share_name") if d else None
        if not share_name:
            return {}
        for s in self.get_share_config():
            if s.get('share_name') == share_name:
                return s
        return {}

    def create_share(self, get):
        """Create a new NFS export and reload /etc/exports.

        Required fields: share_name, path (or nfs_path).
        Optional: rw_mode (rw|ro), sync_mode (sync|async),
                  squash (all_squash|root_squash|no_root_squash|no_all_squash),
                  limit_address (IP/CIDR), user, ps.
        Returns {status, msg}.
        """
        d = self._to_dict(get)
        if not d:
            return {'status': False, 'msg': 'Invalid parameters'}
        
        # Frontend sends 'path' as the share directory field
        share_name = d.get('share_name', '').strip()
        dir_path = d.get('path', '').strip() or d.get('nfs_path', '').strip()
        
        if not share_name or not dir_path:
            return {'status': False, 'msg': 'Missing required parameter: share_name or share path'}

        if not os.path.isdir(dir_path):
            return {'status': False, 'msg': f'Directory does not exist: {dir_path}'}

        if self.get_share_find(share_name):
            return {'status': False, 'msg': f'Share already exists: {share_name}'}

        shares = self.get_share_config()
        shares.append({
            'share_name': share_name,
            'path': dir_path,
            'rw_mode': d.get('rw_mode', 'rw').strip(),
            'sync_mode': d.get('sync_mode', 'async').strip(),
            'squash': d.get('squash', 'all_squash').strip(),
            'user': d.get('user', 'nfsnobody').strip(),
            'limit_address': d.get('limit_address', '').strip(),
            'ps': d.get('ps', '').strip(),
        })
        self._write_exports(shares)
        self.save_share_config(shares)
        self._reload_exports()
        self._log('share_create', 'success',
                  path=dir_path, share_name=share_name,
                  allowed_ips=d.get('limit_address', '').strip() or '*',
                  rw_mode=d.get('rw_mode', 'rw'), squash=d.get('squash', 'all_squash'))
        return {'status': True, 'msg': f'Share created successfully: {share_name}'}

    def modify_share(self, get):
        """Update fields of an existing share and reload /etc/exports.

        share_name is required; only supplied fields are updated.
        Returns {status, msg}.
        """
        d = self._to_dict(get)
        if not d:
            return {'status': False, 'msg': 'Invalid parameters'}
        
        share_name = d.get('share_name', '').strip()
        if not share_name:
            return {'status': False, 'msg': 'Missing required parameter: share_name'}
        shares = self.get_share_config()
        found = False

        for i, s in enumerate(shares):
            if s.get('share_name') == share_name:
                for key in ('path', 'nfs_path', 'rw_mode', 'sync_mode', 'squash', 'user'):
                    if key in d and str(d[key]).strip():
                        shares[i][key] = str(d[key]).strip()
                for key in ('limit_address', 'ps'):
                    if key in d:
                        shares[i][key] = str(d[key]).strip()
                found = True
                break

        if not found:
            return {'status': False, 'msg': f'Share not found: {share_name}'}

        self._write_exports(shares)
        self.save_share_config(shares)
        self._reload_exports()
        changed = {k: str(d[k]).strip() for k in
                   ('path','rw_mode','sync_mode','squash','user','limit_address','ps')
                   if k in d}
        self._log('share_modify', 'success', share_name=share_name, changes=changed)
        return {'status': True, 'msg': f'Share modified successfully: {share_name}'}

    def remove_share(self, get=None):
        """Remove a share from config and reload /etc/exports.

        get may be a bare string (share name) or a request dict with share_name.
        Returns {status, msg}.
        """
        if isinstance(get, str):
            share_name = get
        else:
            d = self._to_dict(get)
            share_name = d.get("share_name") if d else None
        if not share_name:
            return {'status': False, 'msg': 'Missing share_name'}
        name = share_name.strip()
        shares = self.get_share_config()
        new_shares = [s for s in shares if s.get('share_name') != name]
        if len(new_shares) == len(shares):
            return {'status': False, 'msg': f'Share not found: {name}'}
        removed = next((s for s in shares if s.get('share_name') == name), {})
        self._write_exports(new_shares)
        self.save_share_config(new_shares)
        self._reload_exports()
        self._log('share_delete', 'success',
                  share_name=name, path=removed.get('path', ''))
        return {'status': True, 'msg': f'Delete NFS directory share: {name}'}

    def _write_exports(self, shares):
        """Rebuild /etc/exports from the given share list.

        Writes an empty file when shares is empty so stale exports are cleared.
        """
        lines = []
        for s in shares:
            p = s.get('path', '') or s.get('nfs_path', '')
            if not p:
                continue
            uid, gid = self.get_user_id(s.get('user', 'nfsnobody'))
            opts = f"{s.get('rw_mode','rw')},{s.get('sync_mode','async')}"
            squash = s.get('squash', '')
            if squash:
                opts += f",{squash}"
            opts += f",anonuid={uid},anongid={gid}"
            clients = s.get('limit_address', '').strip() or '*'
            lines.append(f"{p} {clients}({opts})")
        if lines:
            with open(self._exports_file, 'w') as f:
                f.write('\n'.join(lines) + '\n')
        elif os.path.exists(self._exports_file):
            with open(self._exports_file, 'w') as f:
                f.write('')

    def show_ip_share_list(self, get=None):
        """Return the export paths advertised by a remote NFS server.

        Queries the server via showmount -e.  get may be a bare IP/hostname
        string or a request dict with a server_address key.
        Returns a list of {path: ...} dicts, or [] on failure.
        """
        if isinstance(get, str):
            server_address = get
        else:
            d = self._to_dict(get)
            server_address = d.get("server_address") if d else None
        if not server_address:
            return []
        ok, out = self.exec_shell(f"showmount -e {server_address} 2>/dev/null")
        if not ok:
            return []
        result = []
        for line in out.split('\n'):
            line = line.strip()
            if line and not line.startswith('Export') and not line.startswith('showmount'):
                parts = line.split()
                if parts:
                    result.append({'path': parts[0]})
        return result

    # ════════════════════════════════════════════════════════════
    # MOUNT API — Remote NFS Mounts
    # ════════════════════════════════════════════════════════════

    def get_mount_list(self, get=None):
        """Return configured mounts enriched with live kernel state and I/O metrics.

        Each entry gains mount_info (from /proc/mounts, None if not mounted) and
        iostat (from nfsiostat, None if not mounted).  Mounts active in the
        kernel but absent from config are appended with _untracked=True.
        Connection changes since the last call are written to the activity log.
        Returns {list: [...]}.
        """
        active = self._get_active_mounts()       # mount_path → mount_info dict
        iostat = self._parse_nfsiostat()         # mount_path → iostat dict
        self._scan_connection_changes(active)    # log new/gone connections

        mounts = self.get_mount_config()
        configured_paths = set()
        for m in mounts:
            mpath = m.get('mount_path', '')
            configured_paths.add(mpath)
            m['mount_info'] = active.get(mpath)  # None = not mounted
            m['iostat'] = iostat.get(mpath) if m['mount_info'] else None

        # Expose untracked mounts (mounted outside the plugin)
        for mpath, info in active.items():
            if mpath not in configured_paths:
                device = info.get('filesystem', ':')
                server, _, nfs_path = device.partition(':')
                mounts.append({
                    'mount_name': '',
                    'server_address': server,
                    'nfs_path': nfs_path,
                    'mount_path': mpath,
                    'mount_info': info,
                    'iostat': iostat.get(mpath),
                    '_untracked': True,
                })
        return {'list': mounts}

    def get_mount_find(self, get=None):
        """Return mount dicts matching mount_name, or all mounts if name is empty.

        get may be a bare string (mount name) or a request dict with mount_name.
        """
        if isinstance(get, str):
            mount_name = get
        else:
            d = self._to_dict(get)
            mount_name = d.get("mount_name") if d else None
        if not mount_name:
            return self.get_mount_config()
        return [m for m in self.get_mount_config() if m.get('mount_name') == mount_name]

    def get_mount(self, get=None):
        """Return the mount config dict for the given local path, or {}.

        get may be a bare path string or a request dict with mount_path.
        """
        if isinstance(get, str):
            mount_path = get
        else:
            d = self._to_dict(get)
            mount_path = d.get("mount_path") if d else None
        if not mount_path:
            return {}
        for m in self.get_mount_config():
            if m.get('mount_path') == mount_path:
                return m
        return {}

    def get_mount_cmd(self, info):
        """Build the mount command string from a mount configuration dict.

        Produces: mount -t nfs -o <opts> server:/remote /local
        Numeric options (rsize, wsize, timeo, retrans, vers) are included only
        when present and non-empty in info.
        """
        server = info.get('server_address', '')
        remote = info.get('nfs_path', '')
        local = info.get('mount_path', '')

        opts = [
            info.get('proto', 'tcp'),
            info.get('rw_mode', 'rw'),
        ]
        if info.get('sync_mode'):
            opts.append(info['sync_mode'])
        opts.append('hard' if int(info.get('hard', 1)) else 'soft')

        for k, flag in [('retrans', 'retrans'), ('rsize', 'rsize'),
                        ('wsize', 'wsize'), ('timeo', 'timeo')]:
            if info.get(k) is not None and str(info[k]).strip():
                opts.append(f"{flag}={int(info[k])}")

        if info.get('vers') is not None and str(info['vers']).strip():
            opts.append(f"nfsvers={int(info['vers'])}")
        if str(info.get('noresvport', '')).strip() == '1':
            opts.append('noresvport')

        return f"mount -t nfs -o {','.join(opts)} {server}:{remote} {local}"

    def create_mount(self, get):
        """Save a new NFS mount entry and create the local mount directory.

        Required fields: mount_name, server_address, nfs_path, mount_path.
        Optional: proto, rw_mode, sync_mode, hard, retrans, rsize, wsize,
                  timeo, vers, noresvport, auto_mount (0|1), ps.
        Returns {status, msg}.
        """
        d = self._to_dict(get)
        if not d:
            return {'status': False, 'msg': 'Invalid parameters'}

        required = ['mount_name', 'server_address', 'nfs_path', 'mount_path']
        for k in required:
            if not d.get(k, '').strip():
                return {'status': False, 'msg': f'Missing required parameter: {k}'}

        name = d['mount_name'].strip()
        mpath = d['mount_path'].strip()

        if self.get_mount_find(name):
            return {'status': False, 'msg': f'Mount already exists: {name}'}

        os.makedirs(mpath, exist_ok=True)

        mounts = self.get_mount_config()
        mounts.append({
            'mount_name': name,
            'server_address': d['server_address'].strip(),
            'nfs_path': d['nfs_path'].strip(),
            'mount_path': mpath,
            'proto': str(d.get('proto', 'tcp')).strip(),
            'rw_mode': str(d.get('rw_mode', 'rw')).strip(),
            'sync_mode': str(d.get('sync_mode', 'async')).strip(),
            'hard': int(d.get('hard', 1)),
            'retrans': int(d.get('retrans', 3)) if str(d.get('retrans', '')).strip() else 3,
            'rsize': int(d.get('rsize', 1048576)) if str(d.get('rsize', '')).strip() else 1048576,
            'wsize': int(d.get('wsize', 1048576)) if str(d.get('wsize', '')).strip() else 1048576,
            'timeo': int(d.get('timeo', 600)) if str(d.get('timeo', '')).strip() else 600,
            'vers': int(d.get('vers', 4)) if str(d.get('vers', '')).strip() else 4,
            'noresvport': str(d.get('noresvport', '')).strip(),
            'auto_mount': int(d.get('auto_mount', 0)),
            'ps': str(d.get('ps', '')).strip(),
        })
        self.save_mount_config(mounts)
        self.write_mount_conf(mounts)
        self._log('mount_create', 'success',
                  mount_name=name, server=d['server_address'].strip(),
                  path=d['nfs_path'].strip(), local=mpath,
                  vers=int(d.get('vers', 4) or 4))
        return {'status': True, 'msg': f'Mount configuration created: {name}'}

    def modify_mount(self, get):
        """Update fields of an existing mount configuration.

        mount_name is required; only supplied fields are overwritten.
        Returns {status, msg}.
        """
        d = self._to_dict(get)
        if not d:
            return {'status': False, 'msg': 'Invalid parameters'}
        if not d.get('mount_name', '').strip():
            return {'status': False, 'msg': 'Missing required parameter: mount_name'}

        name = d['mount_name'].strip()
        mounts = self.get_mount_config()
        found = False

        int_fields = ('hard', 'retrans', 'rsize', 'wsize', 'timeo', 'vers', 'auto_mount')
        required_str = ('server_address', 'nfs_path', 'mount_path', 'proto', 'rw_mode', 'sync_mode')
        optional_str = ('noresvport', 'ps')

        for i, m in enumerate(mounts):
            if m.get('mount_name') == name:
                for k in int_fields:
                    if k in d and str(d[k]).strip():
                        mounts[i][k] = int(d[k])
                for k in required_str:
                    if k in d and str(d[k]).strip():
                        mounts[i][k] = str(d[k]).strip()
                for k in optional_str:
                    if k in d:
                        mounts[i][k] = str(d[k]).strip()
                found = True
                break

        if not found:
            return {'status': False, 'msg': f'Mount not found: {name}'}

        self.save_mount_config(mounts)
        self.write_mount_conf(mounts)
        changed = {k: d[k] for k in
                   ('server_address','nfs_path','mount_path','proto','rw_mode',
                    'sync_mode','noresvport','ps','vers','hard','auto_mount')
                   if k in d}
        self._log('mount_modify', 'success', mount_name=name, changes=changed)
        return {'status': True, 'msg': f'Mount configuration modified: {name}'}

    def remove_mount(self, get=None):
        """Unmount and delete a mount configuration.

        Attempts umount before removing the config entry.
        get may be a bare string (mount name) or a request dict with mount_name.
        Returns {status, msg}.
        """
        if isinstance(get, str):
            mount_name = get
        else:
            d = self._to_dict(get)
            mount_name = d.get("mount_name") if d else None
        if not mount_name:
            return {'status': False, 'msg': 'Missing mount_name'}
        name = mount_name.strip()
        info = self.get_mount_find(name)
        if info and len(info) > 0:
            self.to_umount(info[0])
        removed_cfg = next((m for m in self.get_mount_config() if m.get('mount_name') == name), {})
        mounts = [m for m in self.get_mount_config() if m.get('mount_name') != name]
        self.save_mount_config(mounts)
        self.write_mount_conf(mounts)
        self._log('mount_delete', 'success',
                  mount_name=name,
                  server=removed_cfg.get('server_address', ''),
                  path=removed_cfg.get('nfs_path', ''),
                  local=removed_cfg.get('mount_path', ''))
        return {'status': True, 'msg': f'Delete NFS mount configuration: {name}'}

    def to_mount(self, get=None):
        """Execute the mount command for a configured NFS mount.

        get may contain just {mount_name} (config is looked up) or a full
        mount config dict.  On failure, _diagnose_mount_failure is called and
        its issues/hints are included in the response.
        Returns {status, msg} on success, {status, msg, issues, hints} on failure.
        """
        d = self._to_dict(get)
        if not d:
            return {'status': False, 'msg': 'Invalid parameters'}
        # If only mount_name is given, look up full config
        mount_name = d.get('mount_name', '')
        if mount_name and not d.get('server_address'):
            found = self.get_mount_find(mount_name)
            if not found:
                return {'status': False, 'msg': f'Mount not found: {mount_name}'}
            info = found[0] if isinstance(found, list) else found
        else:
            info = d
        mpath = info.get('mount_path', '')
        if not mpath:
            return {'status': False, 'msg': 'Mount path is empty'}
        if self.is_exists_mount_path(mpath):
            return {'status': False, 'msg': f'Already mounted: {mpath}'}
        os.makedirs(mpath, exist_ok=True)
        cmd = self.get_mount_cmd(info)
        _t0 = time.time()
        ok, out = self.exec_shell(cmd)
        _duration = int((time.time() - _t0) * 1000)
        client_ip = self._get_client_ip_towards(info.get('server_address', ''))
        if ok:
            self._log('mount', 'success',
                      client_ip=client_ip,
                      server=info.get('server_address', ''),
                      path=info.get('nfs_path', ''),
                      local=mpath,
                      duration=_duration)
            return {'status': True, 'msg': f'Mounted successfully: {mpath}'}

        raw_error = out.strip() or 'unknown error'
        issues, hints = self._diagnose_mount_failure(info, raw_error)

        lines = [f'Mount failed: {raw_error}', '']
        if issues:
            lines.append('Diagnostic:')
            for issue in issues:
                lines.append(f'  • {issue}')
            lines.append('')
        if hints:
            lines.append('Suggestions:')
            for hint in hints:
                lines.append(f'  → {hint}')

        self._log('mount', 'failed',
                  client_ip=client_ip,
                  server=info.get('server_address', ''),
                  path=info.get('nfs_path', ''),
                  local=mpath,
                  duration=_duration,
                  msg=raw_error,
                  issues=issues,
                  hints=hints)
        return {'status': False, 'msg': '\n'.join(lines), 'issues': issues, 'hints': hints}

    def to_umount(self, get=None):
        """Execute umount -fl for an active NFS mount path.

        get may contain just {mount_name} (config is looked up) or a full
        mount config dict.  Returns {status, msg}.
        """
        d = self._to_dict(get)
        if not d:
            return {'status': False, 'msg': 'Invalid parameters'}
        mount_name = d.get('mount_name', '')
        if mount_name and not d.get('mount_path'):
            found = self.get_mount_find(mount_name)
            if not found:
                return {'status': False, 'msg': f'Mount not found: {mount_name}'}
            info = found[0] if isinstance(found, list) else found
        else:
            info = d
        mpath = info.get('mount_path', '')
        if not mpath:
            return {'status': False, 'msg': 'Mount path is empty'}
        if not self.is_exists_mount_path(mpath):
            return {'status': False, 'msg': f'Not mounted: {mpath}'}
        _t0 = time.time()
        ok, out = self.exec_shell(f"umount -fl {mpath} 2>/dev/null")
        _duration = int((time.time() - _t0) * 1000)
        self._log('umount', 'success' if ok else 'failed',
                  server=info.get('server_address', ''),
                  path=info.get('nfs_path', ''),
                  local=mpath,
                  duration=_duration,
                  msg='' if ok else out.strip())
        if ok:
            return {'status': True, 'msg': f'Unmounted successfully: {mpath}'}
        else:
            return {'status': False, 'msg': f'Umount failed: {out}'}

    def is_exists_mount_path(self, mount_path=None):
        """Return True if mount_path is an active mountpoint (via mountpoint -q)."""
        if not mount_path:
            return False
        ok, _ = self.exec_shell(f"mountpoint -q {mount_path}")
        return ok

    def auto_mount(self, get=None):
        """Mount all entries with auto_mount=1 that are not already mounted.

        Called at system boot by the nfs_free_service bootstrap.
        Returns {status, msg} with a success/failure count summary.
        """
        count = 0
        success = 0
        for m in self.get_mount_config():
            if m.get('auto_mount') and not self.is_exists_mount_path(m.get('mount_path', '')):
                res = self.to_mount(m)
                count += 1
                if res.get('status'):
                    success += 1
        self._log('auto_mount', 'success' if success == count else 'failed',
                  attempted=count, success=success, failed=count - success)
        return {'status': True, 'msg': f'Auto-mounted {success}/{count} shares'}

    def set_mount(self, get=None):
        """Alias for to_mount."""
        return self.to_mount(self._to_dict(get))

    def set_umount(self, get=None):
        """Alias for to_umount."""
        return self.to_umount(self._to_dict(get))

    def write_mount_conf(self, get=None):
        """No-op stub kept for API compatibility.

        Boot persistence is handled entirely by auto_mount(), which reads
        config/mount.json at startup — no separate conf file is required.
        """
        pass

    def _get_active_mounts(self):
        """Read /proc/mounts and return a dict of mount_path → mount_info for NFS mounts.
        mount_info includes filesystem, mount_path, fs_type, options, size, used_size.
        """
        active = {}
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4 and parts[2] in ('nfs', 'nfs4'):
                        mpath = parts[1]
                        info = {
                            'filesystem': parts[0],
                            'mount_path': mpath,
                            'fs_type': parts[2],
                            'options': parts[3],
                            'size': 0,
                            'used_size': 0,
                        }
                        try:
                            st = os.statvfs(mpath)
                            info['size'] = st.f_blocks * st.f_frsize
                            info['used_size'] = (st.f_blocks - st.f_bfree) * st.f_frsize
                            pct = int(round(info['used_size'] / info['size'] * 100)) if info['size'] else 0
                            info['used_pre'] = f'{pct}%'
                        except Exception:
                            info['used_pre'] = '0%'
                        active[mpath] = info
        except Exception:
            pass
        return active

    def _parse_nfsiostat(self):
        """Parse nfsiostat output into a dict keyed by mount_path.
        Each value: {ops, rpc_bklog, read_ops, read_kbs, read_kbop, read_retrans,
                     read_avg_rtt_ms, read_avg_exe_ms, write_ops, write_kbs,
                     write_kbop, write_retrans, write_avg_rtt_ms, write_avg_exe_ms}
        """
        ok, out = self.exec_shell("nfsiostat 2>/dev/null")
        if not ok or not out.strip():
            return {}
        result = {}
        current_mount = None
        lines = out.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            # Header: "server:/path mounted on /local/path:"
            m = re.match(r'^(\S+)\s+mounted on\s+(/[^\s:]+):?\s*$', line.strip())
            if m:
                current_mount = m.group(2)
                result[current_mount] = {
                    'ops': 0.0, 'rpc_bklog': 0.0,
                    'read_ops': 0.0, 'read_kbs': 0.0, 'read_kbop': 0.0,
                    'read_retrans': 0, 'read_avg_rtt_ms': 0.0, 'read_avg_exe_ms': 0.0,
                    'write_ops': 0.0, 'write_kbs': 0.0, 'write_kbop': 0.0,
                    'write_retrans': 0, 'write_avg_rtt_ms': 0.0, 'write_avg_exe_ms': 0.0,
                }
                i += 1
                continue
            if current_mount is None:
                i += 1
                continue
            # "ops/s  rpc bklog" header then values
            if 'ops/s' in line and 'rpc bklog' in line:
                i += 1
                nums = re.findall(r'[\d.]+', lines[i]) if i < len(lines) else []
                if len(nums) >= 2:
                    result[current_mount]['ops'] = float(nums[0])
                    result[current_mount]['rpc_bklog'] = float(nums[1])
                i += 1
                continue
            # "read:" or "write:" section
            rw = None
            if re.match(r'^\s*read:', line):
                rw = 'read'
            elif re.match(r'^\s*write:', line):
                rw = 'write'
            if rw:
                i += 1
                data_line = lines[i] if i < len(lines) else ''
                # Extract numbers (ignore "N (N.N%)" patterns — take just the leading N)
                nums = re.findall(r'([\d.]+)\s*(?:\([\d.]+%\))?', data_line)
                if len(nums) >= 6:
                    result[current_mount][f'{rw}_ops'] = float(nums[0])
                    result[current_mount][f'{rw}_kbs'] = float(nums[1])
                    result[current_mount][f'{rw}_kbop'] = float(nums[2])
                    result[current_mount][f'{rw}_retrans'] = int(float(nums[3]))
                    result[current_mount][f'{rw}_avg_rtt_ms'] = float(nums[4])
                    result[current_mount][f'{rw}_avg_exe_ms'] = float(nums[5])
                i += 1
                continue
            i += 1
        return result

    def _scan_connection_changes(self, active_mounts):
        """Compare current active NFS mounts against last known state and log changes.
        Detects mounts/unmounts that happened outside the plugin.
        Also snapshots incoming clients (showmount -a) and logs changes.
        State is persisted in a JSON sidecar file.
        """
        state_file = os.path.join(self._config_path, 'connection_state.json')
        try:
            prev = json.loads(open(state_file).read()) if os.path.exists(state_file) else {}
        except Exception:
            prev = {}

        prev_out = set(prev.get('outgoing', []))
        curr_out = set(active_mounts.keys())

        for mpath in curr_out - prev_out:
            info = active_mounts[mpath]
            self._log('connection', 'connected',
                      direction='outgoing', local=mpath,
                      filesystem=info.get('filesystem', ''),
                      fs_type=info.get('fs_type', ''))

        for mpath in prev_out - curr_out:
            self._log('connection', 'disconnected',
                      direction='outgoing', local=mpath,
                      filesystem=prev.get('out_info', {}).get(mpath, ''))

        # Incoming: clients connected to our local NFS server
        ok, raw = self.exec_shell("showmount -a 2>/dev/null")
        curr_in = set()
        if ok:
            for line in raw.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('All mount'):
                    curr_in.add(line)

        prev_in = set(prev.get('incoming', []))
        for client in curr_in - prev_in:
            parts = client.split(':')
            self._log('connection', 'connected',
                      direction='incoming',
                      client=parts[0] if parts else client,
                      path=parts[1] if len(parts) > 1 else '')
        for client in prev_in - curr_in:
            parts = client.split(':')
            self._log('connection', 'disconnected',
                      direction='incoming',
                      client=parts[0] if parts else client,
                      path=parts[1] if len(parts) > 1 else '')

        # Persist current state
        try:
            state = {
                'outgoing': list(curr_out),
                'out_info': {p: active_mounts[p].get('filesystem', '') for p in curr_out},
                'incoming': list(curr_in),
                'ts': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            with open(state_file, 'w') as f:
                json.dump(state, f)
        except Exception:
            pass

    def get_connections(self, get=None):
        """Return active outgoing mounts and incoming NFS clients.

        outgoing is read from /proc/mounts; incoming from showmount -a.
        Returns {outgoing: [...], incoming: [...]}.
        """
        active = self._get_active_mounts()
        outgoing = []
        for mpath, info in active.items():
            outgoing.append({
                'local': mpath,
                'filesystem': info.get('filesystem', ''),
                'fs_type': info.get('fs_type', ''),
                'options': info.get('options', ''),
                'size': info.get('size', 0),
                'used_size': info.get('used_size', 0),
            })

        incoming = []
        ok, raw = self.exec_shell("showmount -a 2>/dev/null")
        if ok:
            for line in raw.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('All mount'):
                    parts = line.split(':')
                    incoming.append({
                        'client': parts[0] if parts else line,
                        'path': parts[1] if len(parts) > 1 else '',
                    })
        return {'outgoing': outgoing, 'incoming': incoming}

    def get_disk_mounts(self, get=None):
        """List all NFS mounts currently active in the kernel.

        Reads /proc/mounts and returns entries where fs_type is nfs or nfs4.
        Each dict has keys: device, mount_point, fs_type, options.
        """
        result = []
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 4 and parts[2] in ('nfs', 'nfs4'):
                        result.append({
                            'device': parts[0],
                            'mount_point': parts[1],
                            'fs_type': parts[2],
                            'options': parts[3],
                        })
        except Exception:
            pass
        return result

    # ════════════════════════════════════════════════════════════
    # NFS SERVER MANAGEMENT
    # ════════════════════════════════════════════════════════════

    def get_overview(self, get=None):
        """Aggregate all data needed by the Dashboard in a single call.

        Returns a dict with keys:
          server     — {nfs-server: bool, rpcbind: bool}
          shares     — {total: int, list: [...up to 4...]}
          mounts     — {configured, mounted, untracked, avg_disk}
          io         — {ops, read_kbs, write_kbs} totals across all active mounts
          recent_log — last 8 activity log entries
        """
        # Server health
        server = {}
        for svc in ('nfs-server', 'rpcbind'):
            ok, out = self.exec_shell(f"systemctl is-active {svc} 2>/dev/null")
            server[svc] = (out.strip() == 'active')

        # Shares
        shares = self.get_share_config()

        # Mounts with live status
        active = self._get_active_mounts()
        iostat = self._parse_nfsiostat()
        mounts_cfg = self.get_mount_config()
        mounted_count = sum(1 for m in mounts_cfg if m.get('mount_path', '') in active)
        # Also count untracked
        configured_paths = {m.get('mount_path', '') for m in mounts_cfg}
        untracked = [p for p in active if p not in configured_paths]

        # Disk usage: average pct across all active NFS mounts
        pcts = []
        for info in active.values():
            pre = info.get('used_pre', '0%')
            try:
                pcts.append(int(pre.rstrip('%')))
            except Exception:
                pass
        avg_disk = int(sum(pcts) / len(pcts)) if pcts else 0

        # IO totals across all active mounts
        total_ops = total_read = total_write = 0.0
        for mpath, io in iostat.items():
            total_ops   += io.get('ops', 0)
            total_read  += io.get('read_kbs', 0)
            total_write += io.get('write_kbs', 0)

        # Recent log (last 8 entries)
        recent = []
        try:
            if os.path.exists(self._log_file):
                with open(self._log_file) as f:
                    logs = json.load(f)
                recent = logs[:8] if isinstance(logs, list) else []
        except Exception:
            pass

        return {
            'server': server,
            'shares': {
                'total': len(shares),
                'list': shares[:4],
            },
            'mounts': {
                'configured': len(mounts_cfg),
                'mounted': mounted_count,
                'untracked': len(untracked),
                'avg_disk': avg_disk,
            },
            'io': {
                'ops': round(total_ops, 2),
                'read_kbs': round(total_read, 3),
                'write_kbs': round(total_write, 3),
            },
            'recent_log': recent,
        }

    def get_server_status(self, get=None):
        """Return service health and registered RPC endpoints.

        Checks nfs-server and rpcbind via systemctl is-active, then parses
        rpcinfo -p into a service_list of {program, vers, proto, port, service}.
        """
        result = {}
        for svc in ('nfs-server', 'rpcbind'):
            ok, out = self.exec_shell(f"systemctl is-active {svc} 2>/dev/null")
            result[svc] = (out.strip() == 'active')

        service_list = []
        ok, out = self.exec_shell("rpcinfo -p 2>/dev/null")
        if ok and out:
            for line in out.split('\n'):
                parts = line.split()
                if len(parts) >= 4 and parts[0].isdigit():
                    service_list.append({
                        'program': parts[0],
                        'vers': parts[1],
                        'proto': parts[2],
                        'port': parts[3],
                        'service': parts[4] if len(parts) > 4 else '',
                    })
        result['service_list'] = service_list
        return result

    def server_admin(self, get):
        """Start, stop, restart or reload nfs-server and rpcbind.

        get must contain status_args with one of: start, stop, restart, reload.
        Returns {status, msg}.
        """
        d = self._to_dict(get)
        if not d:
            return {'status': False, 'msg': 'Invalid parameters'}
        act = str(d.get('status_args', '')).strip()
        if act not in ('start', 'stop', 'restart', 'reload'):
            return {'status': False, 'msg': f'Invalid action: {act}. Use start/stop/restart/reload'}

        for svc in ('nfs-server', 'rpcbind'):
            if act in ('start', 'restart', 'reload'):
                self.exec_shell(f"systemctl enable {svc} 2>/dev/null")
            self.exec_shell(f"systemctl {act} {svc} 2>/dev/null")
        self._log('server_admin', 'success', action=act, services='nfs-server, rpcbind')
        return {'status': True, 'msg': f'NFS and RPCBIND services {act}ed successfully'}

    def get_nfsstat(self, get=None):
        """Parse NFS protocol counters from /proc/net/rpc into structured dicts.

        Returns a dict that may contain any of:
          nfs_v3_server, nfs_v3_client — NFSv3 operation counts (proc3 lines)
          nfs_v4_server                — NFSv4 compound call counts (proc4 line)
          nfs_v4_servop, nfs_v4_client — per-operation counts (proc4ops lines)
        Missing source files are silently skipped; missing counters default to 0.
        """
        v3_names = [
            'null', 'getattr', 'setattr', 'lookup', 'access', 'readlink',
            'read', 'write', 'create', 'mkdir', 'symlink', 'mknod', 'remove',
            'rmdir', 'rename', 'link', 'readdir', 'readdirplus',
            'fsstat', 'fsinfo', 'pathconf', 'commit',
        ]
        v4op_names = [
            None, None, None,
            'access', 'close', 'commit', 'create', 'delegpurge', 'delegreturn',
            'getattr', 'getfh', 'link', 'lock', 'lockt', 'locku',
            'lookup', 'lookupp', 'nverify', 'open', 'openattr',
            'open_confirm', 'open_downgrade', 'putfh', 'putpubfh', 'putrootfh',
            'read', 'readdir', 'readlink', 'remove', 'rename', 'renew',
            'restorefh', 'savefh', 'secinfo', 'setattr', 'setclientid',
            'setclientid_confirm', 'verify', 'write', 'release_lockowner',
            'backchannel_ctl', 'bind_conn_to_session', 'exchange_id',
            'create_ses', 'destroy_ses', 'free_stateid',
            'get_dir_delegation', 'getdeviceinfo', 'getdevicelist',
            'layoutcommit', 'layoutget', 'layoutreturn', 'secinfononam',
            'sequence', 'set_ssv', 'test_stateid', 'want_delegation',
            'destroy_clid', 'reclaim_comp',
        ]
        client_remap = {
            'create_ses': 'create_session', 'destroy_ses': 'destroy_session',
            'destroy_clid': 'destroy_clientid', 'secinfononam': 'secinfo_no',
        }

        result = {}

        def _read(path):
            try:
                with open(path) as f:
                    return f.read()
            except Exception:
                return ''

        def _counts(parts):
            try:
                return [int(x) for x in parts[2:]]
            except ValueError:
                return []

        for path, role in (('/proc/net/rpc/nfsd', 'server'), ('/proc/net/rpc/nfs', 'client')):
            content = _read(path)
            if not content:
                continue
            for line in content.split('\n'):
                parts = line.split()
                if not parts:
                    continue
                tag = parts[0]
                if tag == 'proc3':
                    counts = _counts(parts)
                    data = {name: counts[i] if i < len(counts) else 0
                            for i, name in enumerate(v3_names)}
                    data['total'] = sum(counts)
                    data['other'] = 0
                    result[f'nfs_v3_{role}'] = data
                elif tag == 'proc4' and role == 'server':
                    counts = _counts(parts)
                    result['nfs_v4_server'] = {
                        'total': sum(counts),
                        'null': counts[0] if counts else 0,
                        'compound': counts[1] if len(counts) > 1 else 0,
                        'other': 0,
                    }
                elif tag == 'proc4ops':
                    counts = _counts(parts)
                    data = {'total': sum(counts), 'other': 0}
                    for i, name in enumerate(v4op_names):
                        if name and i < len(counts):
                            key = client_remap.get(name, name) if role == 'client' else name
                            data[key] = counts[i]
                    result['nfs_v4_client' if role == 'client' else 'nfs_v4_servop'] = data

        return result

    def get_nfsiostat(self, get=None):
        """Return raw nfsiostat output as a list of line strings for the frontend.

        This is the public API endpoint consumed by the Service status tab to
        render the raw nfsiostat text.  For structured per-mount metrics used
        internally by get_mount_list and get_overview, see _parse_nfsiostat().
        """
        ok, out = self.exec_shell("nfsiostat 2>/dev/null")
        if not ok:
            return []
        return [{'line': l.strip()} for l in out.split('\n') if l.strip()]

    # ════════════════════════════════════════════════════════════
    # PORT CONFIGURATION
    # ════════════════════════════════════════════════════════════

    def get_nfs_ports(self, get=None):
        """Return the fixed port numbers required on the server firewall.

        Keys: ports (string summary), mountd_port, rpcbind_port, nfs_port.
        """
        return {
            'ports': '111/2049/20048/32874-65535',
            'mountd_port': 20048,
            'rpcbind_port': 111,
            'nfs_port': 2049
        }

    def fix_mountd_port(self, get=None):
        """Pin mountd to port 20048 in /etc/nfs.conf and restart services.

        Also pins lockd (32874) and statd (32876) in the same write.  No-op
        if 20048 is already configured.  Returns {status, msg}.
        """
        import configparser
        nfs_conf = '/etc/nfs.conf'
        try:
            config = configparser.ConfigParser()
            if os.path.exists(nfs_conf):
                config.read(nfs_conf)
            if not config.has_section('mountd'):
                config.add_section('mountd')
            current = config.get('mountd', 'port', fallback='')
            if current == '20048':
                return {'status': True, 'msg': 'mountd port already set to 20048'}
            config.set('mountd', 'port', '20048')
            # Also lock down statd/lockd ports
            if not config.has_section('lockd'):
                config.add_section('lockd')
            config.set('lockd', 'port', '32874')
            config.set('lockd', 'udp-port', '32874')
            if not config.has_section('statd'):
                config.add_section('statd')
            config.set('statd', 'port', '32876')
            with open(nfs_conf, 'w') as f:
                config.write(f)
            self.exec_shell('systemctl restart nfs-server 2>/dev/null')
            self.exec_shell('systemctl restart rpcbind 2>/dev/null')
            return {'status': True, 'msg': 'mountd port fixed to 20048. Restart firewall plugin to allow ports.'}
        except Exception as e:
            return {'status': False, 'msg': f'Failed to configure mountd port: {e}'}

    # ════════════════════════════════════════════════════════════
    # INTERNAL HELPERS
    # ════════════════════════════════════════════════════════════

    def _reload_exports(self):
        """Reload NFS exports configuration (exportfs -ra)."""
        ok, _ = self.exec_shell("exportfs -ra 2>/dev/null")
        self._log('exports_reload', 'success' if ok else 'failed')

    # ════════════════════════════════════════════════════════════
    # ACTIVITY LOG
    # ════════════════════════════════════════════════════════════

    def _log(self, event, result, **data):
        """Append one structured entry to the activity log (thread-safe, max 1000).

        event is the operation key (mount, umount, share_create, …).
        result is 'success', 'failed', 'connected', or 'disconnected'.
        Extra keyword arguments are merged into the entry dict.
        Uses fcntl.LOCK_EX so concurrent panel requests do not corrupt the file.
        """
        entry = {
            'id':     uuid.uuid4().hex[:8],
            'ts':     datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event':  event,
            'result': result,
        }
        entry.update(data)
        try:
            os.makedirs(self._config_path, exist_ok=True)
            with open(self._log_file, 'a+') as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.seek(0)
                raw = f.read().strip()
                logs = json.loads(raw) if raw else []
                logs.insert(0, entry)
                if len(logs) > 1000:
                    logs = logs[:1000]
                f.seek(0)
                f.truncate()
                json.dump(logs, f, ensure_ascii=False, indent=None)
        except Exception:
            pass

    def get_log(self, get=None):
        """Return filtered activity log entries.

        Accepted filter keys in get: event, result, ip, limit (default 200, max 1000).
        ip is matched against client_ip and server fields.
        Returns {list: [...], total: int} where total is the count after filtering.
        """
        d = self._to_dict(get) or {}
        limit       = min(int(d.get('limit', 200)), 1000)
        ev_filter   = str(d.get('event',  '')).strip()
        res_filter  = str(d.get('result', '')).strip()
        ip_filter   = str(d.get('ip',     '')).strip()

        try:
            with open(self._log_file) as f:
                logs = json.load(f)
        except Exception:
            logs = []

        if ev_filter:
            logs = [l for l in logs if l.get('event') == ev_filter]
        if res_filter:
            logs = [l for l in logs if l.get('result') == res_filter]
        if ip_filter:
            logs = [l for l in logs if ip_filter in l.get('client_ip', '')
                                        or ip_filter in l.get('server', '')]

        return {'list': logs[:limit], 'total': len(logs)}

    def clear_log(self, get=None):
        """Truncate the activity log to an empty array.  Returns {status, msg}."""
        try:
            with open(self._log_file, 'w') as f:
                json.dump([], f)
            return {'status': True, 'msg': 'Activity log cleared'}
        except Exception as e:
            return {'status': False, 'msg': str(e)}

    # ════════════════════════════════════════════════════════════
    # MOUNT DIAGNOSTICS
    # ════════════════════════════════════════════════════════════

    def _check_port(self, host, port, timeout=3):
        """Return True if host:port accepts a TCP connection within timeout seconds.

        Uses bash /dev/tcp rather than Python sockets to reuse the existing
        shell execution path without additional imports.
        """
        ok, _ = self.exec_shell(
            f"timeout {timeout} bash -c 'echo >/dev/tcp/{host}/{port}' 2>/dev/null",
            timeout=timeout + 2
        )
        return ok

    def _get_client_ip_towards(self, server):
        """Return the local source IP that the kernel would use to reach server.

        Parses the 'src' field from 'ip route get <server>'.
        Returns an empty string if the route cannot be determined.
        """
        ok, out = self.exec_shell(
            f"ip route get {server} 2>/dev/null | grep -oE 'src [0-9.]+' | awk '{{print $2}}'"
        )
        return out.strip() if ok else ''

    def _parse_showmount_clients(self, showmount_output, target_path):
        """Extract allowed client specs for target_path from showmount -e output.

        Returns a list of spec strings (e.g. ['192.168.0.0/24', '10.0.0.1']),
        ['*'] if the export is open to everyone, or None if the path is not
        in the export list at all.
        """
        import re
        for line in showmount_output.strip().split('\n'):
            line = line.strip()
            if not line or line.lower().startswith('export list'):
                continue
            parts = line.split(None, 1)
            if not parts or parts[0] != target_path:
                continue
            if len(parts) < 2:
                return ['*']
            clients_str = parts[1].strip()
            if not clients_str or clients_str in ('(everyone)', '*', '(all machines)'):
                return ['*']
            specs = [s.strip() for s in re.split(r'[,\s]+', clients_str) if s.strip()]
            return specs if specs else ['*']
        return None

    def _ip_matches_export_spec(self, client_ip, spec):
        """Return True if client_ip is permitted by the given NFS export spec.

        Handles: '*' wildcard, exact IP, CIDR (192.168.0.0/24), and
        netmask notation (192.168.0.0/255.255.255.0).
        """
        import ipaddress
        if spec in ('*', '(everyone)', '(all machines)'):
            return True
        try:
            return ipaddress.ip_address(client_ip) in ipaddress.ip_network(spec, strict=False)
        except ValueError:
            return client_ip == spec

    def _diagnose_mount_failure(self, info, raw_error=''):
        """Run step-by-step diagnostics when an NFS mount fails.

        Uses showmount output and CIDR matching to identify exactly which
        client IP is rejected and what the server actually allows.
        info is the full mount configuration dict; raw_error is the stderr
        string from the failed mount command.
        Returns (issues, hints) — both are lists of human-readable strings.
        """
        server = info.get('server_address', '')
        remote_path = info.get('nfs_path', '')
        issues = []
        hints = []

        if not server:
            return ['No server address specified'], ['Set the NFS server IP/hostname']

        # ── Step 1: reachability ─────────────────────────────────
        ok, _ = self.exec_shell(f"ping -c 1 -W 2 {server} 2>/dev/null", timeout=5)
        if not ok:
            return (
                [f"Server {server} is unreachable (ping failed)"],
                ["Verify the server IP and network connectivity"]
            )

        # ── Step 2: detect client outgoing IP ────────────────────
        client_ip = self._get_client_ip_towards(server)

        # ── Step 3: check required NFS ports ────────────────────
        port_map = {111: 'rpcbind', 2049: 'NFS', 20048: 'mountd'}
        blocked = {p: n for p, n in port_map.items() if not self._check_port(server, p)}

        if 111 in blocked:
            issues.append(f"Port 111 (rpcbind) is blocked on server {server}")
            issues.append("Without rpcbind the server cannot receive mount requests")
            hints.append("Open port 111 (TCP/UDP) on the server firewall")
            return issues, hints

        if 2049 in blocked:
            issues.append(f"Port 2049 (NFS data) is blocked on server {server}")
            hints.append("Open port 2049 (TCP/UDP) on the server firewall")

        if 20048 in blocked:
            issues.append(f"Port 20048 (mountd) is blocked on server {server}")
            hints.append("Open port 20048 on the server firewall, then run 'Fix mountd port'")

        # ── Step 4: query exports via showmount ──────────────────
        ok, showmount_out = self.exec_shell(
            f"showmount -e {server} 2>/dev/null", timeout=10
        )
        if not ok or not showmount_out.strip():
            issues.append(
                f"showmount could not query exports from {server} "
                f"(mountd may be unreachable or not running)"
            )
            if 20048 in blocked:
                hints.append("Port 20048 (mountd) is blocked — open it on the server firewall")
            else:
                hints.append("On the server run: systemctl status nfs-server rpcbind")
            return issues, hints

        # ── Step 5: check if path is exported ───────────────────
        allowed_specs = self._parse_showmount_clients(showmount_out, remote_path)

        if allowed_specs is None:
            all_exported = []
            for line in showmount_out.strip().split('\n'):
                if line.strip() and not line.lower().startswith('export list'):
                    p = line.split()[0]
                    all_exported.append(p)
            issues.append(
                f"Path '{remote_path}' is NOT in server {server}'s export list"
            )
            if all_exported:
                hints.append(f"Server {server} currently exports: {', '.join(all_exported)}")
            hints.append("Add this path as a Share on the server, or select a different path")
            return issues, hints

        # ── Step 6: access control — the core of the diagnosis ──
        if allowed_specs == ['*']:
            # Everyone is allowed — something else caused the failure
            issues.append(
                f"Server {server} exports '{remote_path}' to all clients (*)"
            )
            if client_ip:
                issues.append(f"Client IP {client_ip} should be allowed but mount was still denied")
            if blocked:
                blocked_desc = ', '.join(f"{p} ({n})" for p, n in blocked.items())
                hints.append(f"Blocked ports may be causing the failure: {blocked_desc}")
            hints.append("On the server run 'exportfs -ra' to reload exports, then retry")
            hints.append("Check server logs: journalctl -u nfs-server -n 30")
        else:
            # Specific client specs — check if our IP matches
            allowed_str = ', '.join(allowed_specs)
            if client_ip:
                matched = any(
                    self._ip_matches_export_spec(client_ip, spec) for spec in allowed_specs
                )
                if matched:
                    # IP matches the rule but still denied — something subtler
                    issues.append(
                        f"Client IP {client_ip} matches server export rules "
                        f"[{allowed_str}] but mount was still denied"
                    )
                    if blocked:
                        hints.append(
                            f"Blocked ports may prevent data transfer: "
                            + ', '.join(f"{p} ({n})" for p, n in blocked.items())
                        )
                    hints.append(
                        "On the server run 'exportfs -ra' to ensure exports are active"
                    )
                    hints.append(
                        "Try changing NFS version (NFS-3 vs NFS-4) in mount settings"
                    )
                else:
                    # Clear IP mismatch — the core rejection reason
                    issues.append(
                        f"Server {server} rejected IP {client_ip}: "
                        f"export '{remote_path}' only allows [{allowed_str}]"
                    )
                    # Check if client is close to an allowed subnet
                    for spec in allowed_specs:
                        if '/' in spec:
                            hints.append(
                                f"Allowed subnet is {spec} — "
                                f"your IP {client_ip} is not within this range"
                            )
                    hints.append(
                        f"On the server, add '{client_ip}' to 'Allowed IPs' for "
                        f"share '{remote_path}', then click 'Save'"
                    )
            else:
                issues.append(
                    f"Server {server} only allows [{allowed_str}] for '{remote_path}' "
                    f"but could not determine client IP"
                )
                hints.append(
                    "On the server, verify 'Allowed IPs' includes this client's IP"
                )

        # ── Step 7: extra hints from raw error keywords ──────────
        err_lower = raw_error.lower()
        if 'version' in err_lower or 'nfsvers' in err_lower:
            hints.append("Try switching NFS version (NFS-3 vs NFS-4) in mount settings")
        if 'timed out' in err_lower or 'timeout' in err_lower:
            hints.append("Timeout — check firewall rules on both server and client")
        if 'no route' in err_lower:
            hints.append("No route to host — check network routing between client and server")
        if 'connection refused' in err_lower:
            hints.append("Connection refused — ensure nfs-server and rpcbind are running")

        return issues, hints

    def check_update(self):
        """Query GitHub Releases API and compare with the installed version.

        The result is cached in config/update_cache.json for 1 hour to stay
        within GitHub's unauthenticated rate limit (60 req/h per IP).

        Returns a dict with the following keys:
          status       — True if the API call succeeded, False on network error
          current      — installed version string (e.g. '1.1')
          latest       — latest published version from GitHub, or None on error
          has_update   — True when latest != current and latest is not empty
          release_url  — URL of the latest GitHub release page
          release_name — human-readable release title from GitHub
          msg          — error message (only present when status is False)
        """
        import urllib.request
        CURRENT    = '1.1'
        REPO_API   = 'https://api.github.com/repos/jalexiscv/aaPanel-nfs-free/releases/latest'
        RELEASES   = 'https://github.com/jalexiscv/aaPanel-nfs-free/releases'
        cache_file = os.path.join(self._config_path, 'update_cache.json')

        # Return cached data if it is less than 1 hour old
        if os.path.exists(cache_file):
            try:
                cached = json.loads(open(cache_file).read())
                if time.time() - cached.get('ts', 0) < 3600:
                    cached['current'] = CURRENT
                    return cached
            except Exception:
                pass

        try:
            req = urllib.request.Request(
                REPO_API,
                headers={'User-Agent': 'nfs_free-plugin/' + CURRENT, 'Accept': 'application/vnd.github+json'}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode())
            latest = data.get('tag_name', '').lstrip('v')
            result = {
                'status':       True,
                'current':      CURRENT,
                'latest':       latest,
                'has_update':   latest != CURRENT and latest != '',
                'release_url':  data.get('html_url', RELEASES),
                'release_name': data.get('name', latest),
                'ts':           time.time(),
            }
        except Exception as e:
            result = {
                'status':      False,
                'current':     CURRENT,
                'latest':      None,
                'has_update':  False,
                'release_url': RELEASES,
                'msg':         str(e),
                'ts':          time.time(),
            }

        try:
            with open(cache_file, 'w') as f:
                json.dump(result, f)
        except Exception:
            pass

        return result

    def __get_mod(self):
        """Return basic plugin identity metadata.

        Unused internally — kept as a named-mangled stub in case a future
        aaPanel version queries it via introspection.
        """
        return {'name': 'nfs_free', 'version': '1.1', 'author': 'Jose Alexis Correa Valencia'}
