"""Patch the observed vendor init for a FAT32 data partition and identity preload."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    text = args.original.read_text(encoding='utf-8').replace('\r\n', '\n')
    mount = 'mount /dev/mmcblk0p3  $P3_MOUNT_POINT\nmount $P3_MOUNT_POINT/roms $MEDIADIR'
    anchor = 'cd /tmp\n\ninit_res'
    if text.count(mount) != 1 or text.count(anchor) != 1:
        parser.error('unexpected or already patched init; no output written')
    replacement = '''# FAT32 data partition; retain support for an image named roms.
mount -o flush /dev/mmcblk0p3 $P3_MOUNT_POINT || mount /dev/mmcblk0p3 $P3_MOUNT_POINT
if [ -f $P3_MOUNT_POINT/roms ]; then
        mount $P3_MOUNT_POINT/roms $MEDIADIR
else
        mount -o bind $P3_MOUNT_POINT/sdcard $MEDIADIR
fi
[ -f $P3_MOUNT_POINT/games.db ] && mount -o bind $P3_MOUNT_POINT/games.db /usr/lib/game
[ -f $P3_MOUNT_POINT/autorun.sh ] && sh $P3_MOUNT_POINT/autorun.sh'''
    text = text.replace(mount, replacement)
    text = text.replace(anchor, 'cd /tmp\n\n[ -f /usr/lib/cardspoof.so ] && export LD_PRELOAD=/usr/lib/cardspoof.so\n\ninit_res')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as output:
        output.write(text)
    print('Patched init written; normal menu/game launch loop retained.')


if __name__ == '__main__':
    main()
