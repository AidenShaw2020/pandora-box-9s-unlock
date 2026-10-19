#!/bin/sh
# Public template. The profile-specific shared library stays on the user's P3.
P3=/mnt/udisk
MARK=pandora-9s-unlock-v1
EXPECTED=$(cat "$P3/unlock.sectors" 2>/dev/null)
case "$EXPECTED" in ''|*[!0-9]*) exit 0 ;; esac
[ "$(cat /sys/block/mmcblk0/size 2>/dev/null)" = "$EXPECTED" ] || exit 0
[ "$(cat "$P3/unlock.marker" 2>/dev/null)" = "$MARK" ] || exit 0
[ -f "$P3/cardspoof_kernel.so" ] || exit 0
[ -f /usr/lib/cardspoof.so ] || exit 0
unset LD_PRELOAD
mkdir -p "$P3/log" || exit 0
if mount -o bind "$P3/cardspoof_kernel.so" /usr/lib/cardspoof.so; then
    echo 'BIND_OK; continue normal vendor menu/game loop' > "$P3/log/UNLOCK_STATUS.txt"
else
    echo 'BIND_FAILED; system file was not replaced' > "$P3/log/UNLOCK_STATUS.txt"
fi
sync
exit 0
