"""Archive and clear the recent-game list after changing the game catalog."""
import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('p3', type=Path, help='Mounted data partition, never a raw disk')
    parser.add_argument('--apply', action='store_true', help='Back up and reset; default is inspect only')
    args = parser.parse_args()
    history = args.p3 / 'rcp_roms'
    data = history.read_bytes()
    lines = data.decode('ascii').splitlines()
    print(f'{len(lines)} history entries; {len(data)} bytes; SHA256 {hashlib.sha256(data).hexdigest()}')
    if not args.apply:
        print('Inspect only. Use --apply to archive and clear this list.')
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup = history.with_name(f'rcp_roms.before-reset-{stamp}.txt')
    with backup.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if backup.read_bytes() != data or history.read_bytes() != data:
        raise RuntimeError('Backup verification failed or history changed; reset aborted')
    with history.open('wb') as stream:
        stream.flush()
        os.fsync(stream.fileno())
    print(f'History cleared. Verified backup: {backup.name}')


if __name__ == '__main__':
    main()
