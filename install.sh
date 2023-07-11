#!/bin/bash
# =============================================================================
#  Network File System (NFS) — Free Edition
#  Install / Uninstall Script
# =============================================================================
#  Description : Installs or removes the nfs_free aaPanel plugin.
#                Handles OS package installation, fixed-port configuration
#                for mountd/statd/lockd, firewall rules, SysV init service
#                registration, and systemd service activation.
#
#  Usage       : bash install.sh {install|uninstall}
#
#  Exit codes  : 0  success
#                1  invalid argument
#
#  Author      : Jose Alexis Correa Valencia (jalexiscv)
#  Email       : jalexiscv@gmail.com
#  GitHub      : https://github.com/jalexiscv
#  LinkedIn    : https://www.linkedin.com/in/jalexiscv/
#  Version     : 1.0
#  License     : MIT — Free Software
#  Date        : July 11, 2023
#  Copyright   : © 2023 Jose Alexis Correa Valencia
# =============================================================================

PATH=/www/server/panel/pyenv/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

PLUGIN_PATH=/www/server/panel/plugin/nfs_free
INIT_SCRIPT=/etc/init.d/nfs_free
SERVICE_NAME=nfs_free

# -----------------------------------------------------------------------------
# install_nfs_packages
#
# Installs the NFS server and client packages required by the plugin.
# Detects the package manager (apt / yum / dnf) and installs the appropriate
# package set. Prints a warning if nfsstat is not found after installation,
# indicating that the packages may not have been installed correctly.
#
# Supported distributions:
#   - Debian / Ubuntu  : nfs-kernel-server, nfs-common
#   - RHEL / CentOS    : nfs-utils  (via yum)
#   - Fedora / Rocky   : nfs-utils  (via dnf)
#
# @return  void
# -----------------------------------------------------------------------------
install_nfs_packages() {
    echo "Installing NFS server packages..."
    if [ -f /usr/bin/apt ]; then
        apt update -qq && apt install -y nfs-kernel-server nfs-common 2>/dev/null
    elif [ -f /usr/bin/yum ]; then
        yum install -y nfs-utils 2>/dev/null
    elif [ -f /usr/bin/dnf ]; then
        dnf install -y nfs-utils 2>/dev/null
    fi

    if [ ! -f /usr/sbin/nfsstat ] && [ ! -f /usr/bin/nfsstat ]; then
        echo "Warning: NFS server packages may not have installed correctly."
        echo "Please install nfs-kernel-server (Debian/Ubuntu) or nfs-utils (RHEL/CentOS) manually."
    fi
}

# -----------------------------------------------------------------------------
# fix_mountd_port
#
# Pins the NFS auxiliary daemons to fixed, well-known ports in /etc/nfs.conf
# so that firewall rules between plugin instances remain stable across reboots.
#
# Ports configured:
#   mountd  → 20048 (TCP/UDP)   — handles mount requests
#   statd   → 32876 (TCP/UDP)   — NSM state recovery
#   lockd   → 32874 (TCP/UDP)   — NLM file locking
#
# Without this configuration mountd uses a random ephemeral port assigned by
# rpcbind at startup, making it impossible to write static firewall rules.
#
# Also opens the required firewall ports in ufw if the service is active.
#
# @return  void
# -----------------------------------------------------------------------------
fix_mountd_port() {
    echo "Configuring NFS mountd on fixed port 20048..."
    NFS_CONF=/etc/nfs.conf
    if [ ! -f "$NFS_CONF" ]; then
        touch "$NFS_CONF"
    fi

    # Add [mountd] section if absent, then set or update port
    if ! grep -q '^\[mountd\]' "$NFS_CONF"; then
        echo "[mountd]" >> "$NFS_CONF"
    fi
    if grep -q '^port=' "$NFS_CONF"; then
        sed -i 's/^port=.*/port=20048/' "$NFS_CONF"
    else
        sed -i '/^\[mountd\]/a port=20048' "$NFS_CONF"
    fi

    # Pin statd port
    if ! grep -q '^\[statd\]' "$NFS_CONF"; then
        echo "[statd]" >> "$NFS_CONF"
        echo "port=32876" >> "$NFS_CONF"
    fi

    # Pin lockd port (TCP and UDP)
    if ! grep -q '^\[lockd\]' "$NFS_CONF"; then
        echo "[lockd]" >> "$NFS_CONF"
        echo "port=32874" >> "$NFS_CONF"
        echo "udp-port=32874" >> "$NFS_CONF"
    fi

    # Open firewall ports when ufw is active
    if command -v ufw >/dev/null 2>&1 && ufw status | grep -q 'active'; then
        for port in 111 2049 20048 32874 32876; do
            ufw allow $port/tcp 2>/dev/null
        done
        echo "Firewall ports opened: 111, 2049, 20048, 32874, 32876"
    fi

    systemctl restart nfs-server 2>/dev/null
    systemctl restart rpcbind 2>/dev/null
    echo "mountd fixed to port 20048"
}

# -----------------------------------------------------------------------------
# install_service
#
# Registers and starts the nfs_free SysV init service that performs
# auto-mounting of configured NFS shares at system boot.
#
# Steps performed:
#   1. Copies init.sh to /etc/init.d/nfs_free and makes it executable.
#   2. Registers the service with update-rc.d (Debian/Ubuntu) or
#      chkconfig (RHEL/CentOS).
#   3. Enables and starts nfs-server and rpcbind via systemd.
#   4. Calls fix_mountd_port to ensure stable port configuration.
#   5. Starts the auto-mount service immediately.
#
# @return  void
# -----------------------------------------------------------------------------
install_service() {
    echo "Setting up auto-mount service..."

    cp -f $PLUGIN_PATH/init.sh $INIT_SCRIPT
    chmod +x $INIT_SCRIPT

    if [ -f /usr/bin/apt-get ]; then
        update-rc.d $SERVICE_NAME defaults 2>/dev/null
    else
        chkconfig --add $SERVICE_NAME 2>/dev/null
        chkconfig --level 2345 $SERVICE_NAME on 2>/dev/null
    fi

    systemctl enable nfs-server 2>/dev/null
    systemctl start nfs-server 2>/dev/null
    systemctl enable rpcbind 2>/dev/null
    systemctl start rpcbind 2>/dev/null

    # Fixed port required for cross-firewall showmount between plugin instances
    fix_mountd_port

    $INIT_SCRIPT start 2>/dev/null
}

# -----------------------------------------------------------------------------
# install_plugin
#
# Full installation entry point. Orchestrates package installation, service
# setup, directory permissions, and panel reload signal.
#
# @return  void
# -----------------------------------------------------------------------------
install_plugin() {
    echo "Installing Network File System (NFS) Free Edition v1.0..."
    echo "Author: Jose Alexis Correa Valencia (jalexiscv)"
    echo ""

    mkdir -p $PLUGIN_PATH/config
    install_nfs_packages
    install_service

    chmod -R 755 $PLUGIN_PATH
    chmod 600 $PLUGIN_PATH/config/*.json 2>/dev/null

    # Signal aaPanel to reload the plugin list
    if [ -f /www/server/panel/data/reload.pl ]; then
        echo > /www/server/panel/data/reload.pl
    fi

    echo ""
    echo "============================================"
    echo " Network File System (NFS) v1.0"
    echo " Installed successfully!"
    echo "============================================"
    echo " Author : Jose Alexis Correa Valencia"
    echo " GitHub : https://github.com/jalexiscv"
    echo " License: MIT — Free Software"
    echo " Date   : July 11, 2023"
    echo "============================================"
    echo ""
}

# -----------------------------------------------------------------------------
# uninstall_plugin
#
# Removes the plugin from the system. Stops and deregisters the init service,
# deletes the plugin directory, and signals the panel to reload.
#
# Note: NFS system packages (nfs-kernel-server / nfs-utils) are intentionally
# preserved so that any manually configured exports continue to work.
# /etc/exports is also left untouched.
#
# @return  void
# -----------------------------------------------------------------------------
uninstall_plugin() {
    echo "Uninstalling Network File System (NFS) Free Edition..."

    if [ -f $INIT_SCRIPT ]; then
        $INIT_SCRIPT stop 2>/dev/null
    fi

    if [ -f /usr/bin/apt-get ]; then
        update-rc.d $SERVICE_NAME remove 2>/dev/null
    else
        chkconfig --del $SERVICE_NAME 2>/dev/null
    fi

    rm -f $INIT_SCRIPT
    rm -rf $PLUGIN_PATH

    if [ -f /www/server/panel/data/reload.pl ]; then
        echo > /www/server/panel/data/reload.pl
    fi

    echo "Network File System (NFS) uninstalled."
    echo "Note: NFS packages (nfs-kernel-server/nfs-utils) were NOT removed."
    echo "Note: /etc/exports was NOT modified."
}

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
case "$1" in
    install)
        install_plugin
        ;;
    uninstall)
        uninstall_plugin
        ;;
    *)
        echo "Usage: $0 {install|uninstall}"
        exit 1
        ;;
esac
