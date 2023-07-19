#!/bin/bash
# =============================================================================
#  Network File System (NFS) — Free Edition
#  Repair Script
# =============================================================================
#  Description : Repairs the NFS plugin configuration by re-pinning the
#                mountd, statd, and lockd daemons to their fixed ports in
#                /etc/nfs.conf, then restarting the init service.
#
#                Run this script when:
#                  - NFS mounts fail after a system reboot.
#                  - showmount is unreachable from a remote host.
#                  - mountd is found listening on a random ephemeral port
#                    instead of the expected port 20048.
#
#  Usage       : bash repair.sh
#
#  Exit codes  : 0  success (always; errors are non-fatal)
#
#  Author      : Jose Alexis Correa Valencia (jalexiscv)
#  Email       : jalexiscv@gmail.com
#  GitHub      : https://github.com/jalexiscv
#  LinkedIn    : https://www.linkedin.com/in/jalexiscv/
#  Version     : 1.0
#  License     : MIT — Free Software
#  Date        : July 19, 2023
#  Copyright   : © 2023 Jose Alexis Correa Valencia
# =============================================================================

PLUGIN_PATH=/www/server/panel/plugin/nfs_free

# Source install.sh to reuse fix_mountd_port without re-running the installer.
# The function writes [mountd]/[statd]/[lockd] sections to /etc/nfs.conf and
# restarts nfs-server and rpcbind.
if [ -f "$PLUGIN_PATH/install.sh" ]; then
    source "$PLUGIN_PATH/install.sh" 2>/dev/null
    if declare -f fix_mountd_port >/dev/null 2>&1; then
        fix_mountd_port
    fi
fi

# Restart the auto-mount init service so any pending mounts are retried
/etc/init.d/nfs_free restart 2>/dev/null

echo "Successfully"
