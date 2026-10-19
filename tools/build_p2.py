"""Rebuild a local vendor rootfs image with the supplied init and private shim."""
import argparse
from pathlib import Path
from pandsq import PandSq
from sqwrite import SquashWriter, tree_from_image, put_file, find


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('myinit', type=Path)
    parser.add_argument('shim', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve() == args.original.resolve():
        parser.error('output must be a new regular image file')
    if not args.shim.read_bytes().startswith(b'\x7fELF'):
        parser.error('shim must be a compiled ARM ELF shared library')
    sq = PandSq(args.original)
    root = tree_from_image(sq)
    init = find(root, '/usr/retrogame/myinit')
    if init is None:
        parser.error('unexpected rootfs: vendor myinit not found')
    mode = init.mode
    put_file(root, '/usr/retrogame/myinit', args.myinit.read_bytes().replace(b'\r\n', b'\n'))
    find(root, '/usr/retrogame/myinit').mode = mode
    put_file(root, '/usr/lib/cardspoof.so', args.shim.read_bytes(), mode=0o644, mtime=sq.mkfs_time)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    length = SquashWriter(str(args.output), root, vendor=True, mkfs_time=sq.mkfs_time, level=9).write()
    if length > 512 * 1024 * 1024:
        raise RuntimeError('rootfs exceeds the documented 512 MiB P2 slot; do not flash')
    print(f'Created {length} bytes. This tool did not write any physical disk.')


if __name__ == '__main__':
    main()
