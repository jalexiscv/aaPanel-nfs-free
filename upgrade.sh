#!/bin/bash
# =============================================================================
#  Network File System (NFS) — Free Edition
#  Upgrade Script
# =============================================================================
#  Description : Upgrades the NFS system packages to the latest available
#                version from the OS package manager, re-pins the NFS daemon
#                ports via fix_mountd_port, and restarts the init service.
#
#                Run this script when:
#                  - Applying OS security patches that include NFS packages.
#                  - Resolving compatibility issues after a kernel upgrade.
#                  - The panel triggers a plugin upgrade through its interface.
#
#  Usage       : bash upgrade.sh
#
#  Packages upgraded:
#    Debian / Ubuntu  : nfs-kernel-server
#    RHEL / CentOS    : nfs-utils
#
#  Exit codes  : 0  success (always; package manager errors are non-fatal)
#
#  Author      : Jose Alexis Correa Valencia (jalexiscv)
#  Email       : jalexiscv@gmail.com
#  GitHub      : https://github.com/jalexiscv
#  LinkedIn    : https://www.linkedin.com/in/jalexiscv/
#  Version     : 1.0
#  License     : MIT — Free Software
#  Date        : July 23, 2023
#  Copyright   : © 2023 Jose Alexis Correa Valencia
# =============================================================================

PLUGIN_PATH=/www/server/panel/plugin/nfs_free

# Upgrade the NFS package for the detected distribution
if [ -f /usr/bin/apt ]; then
    apt install -y nfs-kernel-server 2>/dev/null
else
    yum install -y nfs-utils 2>/dev/null
fi

# Re-apply fixed port configuration after the package upgrade, since the
# package manager may overwrite /etc/nfs.conf with default values.
if [ -f "$PLUGIN_PATH/install.sh" ]; then
    source "$PLUGIN_PATH/install.sh" 2>/dev/null
    if declare -f fix_mountd_port >/dev/null 2>&1; then
        fix_mountd_port
    fi
fi

# Restart the auto-mount service to pick up any changes
/etc/init.d/nfs_free restart 2>/dev/null

echo "Successfully"
