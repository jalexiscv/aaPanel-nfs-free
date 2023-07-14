#!/bin/bash
# =============================================================================
#  Network File System (NFS) — Free Edition
#  SysV Init Script — Auto-mount service
# =============================================================================
#  Description : SysV-compatible init script installed at /etc/init.d/nfs_free.
#                Runs at system boot (runlevels 2–5) to auto-mount all NFS
#                shares that have auto_mount=1 in the plugin configuration.
#                Uses the aaPanel Python environment when available, falling
#                back to the system Python 3 interpreter.
#
#  Usage       : /etc/init.d/nfs_free {start|stop|restart|reload|status}
#
#  Runlevels   : start on 2 3 4 5  (priority 55)
#                stop  on 0 1 6    (priority 25)
#
#  Author      : Jose Alexis Correa Valencia (jalexiscv)
#  Email       : jalexiscv@gmail.com
#  GitHub      : https://github.com/jalexiscv
#  LinkedIn    : https://www.linkedin.com/in/jalexiscv/
#  Version     : 1.0
#  License     : MIT — Free Software
#  Date        : July 14, 2023
#  Copyright   : © 2023 Jose Alexis Correa Valencia
# =============================================================================

# chkconfig: 2345 55 25

### BEGIN INIT INFO
# Provides:          nfs_free
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: NFS Free — Auto-mount service
# Description:       Auto-mounts NFS shares configured in nfs_free plugin
### END INIT INFO

PANEL_PATH=/www/server/panel
PLUGIN_PATH=$PANEL_PATH/plugin/nfs_free
SERVICE_SCRIPT=$PLUGIN_PATH/nfs_free_service
cd $PANEL_PATH

# Prefer the panel's virtualenv; fall back to system Python 3
if [ -f $PANEL_PATH/pyenv/bin/activate ]; then
    source $PANEL_PATH/pyenv/bin/activate 2>/dev/null
    PYTHON_BIN=$PANEL_PATH/pyenv/bin/python
else
    PYTHON_BIN=/usr/bin/python3
fi

# -----------------------------------------------------------------------------
# start_service
#
# Launches nfs_free_service in the background via nohup. The service script
# calls nfs_free_main.auto_mount(), which iterates over mount.json and mounts
# every entry with auto_mount=1 that is not already mounted.
# Output is discarded because this runs unattended at boot time.
#
# @return  void
# -----------------------------------------------------------------------------
start_service() {
    echo -n "Starting NFS Free auto-mount service... "
    nohup $PYTHON_BIN $SERVICE_SCRIPT > /dev/null 2>&1 &
    echo "done"
}

# -----------------------------------------------------------------------------
# Entry point — SysV action dispatch
# -----------------------------------------------------------------------------
case "$1" in
    start)
        start_service
        ;;
    stop)
        # Auto-mount is a one-shot operation at boot; nothing to stop
        echo "NFS Free service stop requested (auto-mount only runs at boot)"
        ;;
    restart|reload)
        start_service
        ;;
    status)
        echo "NFS Free auto-mount service"
        ;;
    *)
        echo "Usage: /etc/init.d/nfs_free {start|restart|reload|stop|status}"
        exit 1
        ;;
esac
