"""Copy a byte range from a local backup into a new regular file; never flash."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('offset', type=lambda s: int(s, 0))
    parser.add_argument('size', type=lambda s: int(s, 0))
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.offset < 0 or args.size <= 0 or args.offset + args.size > args.image.stat().st_size:
        parser.error('range is outside the backup')
    with args.image.open('rb') as source, args.output.open('xb') as output:
        source.seek(args.offset)
        left = args.size
        while left:
            block = source.read(min(left, 1024*1024))
            if not block:
                raise EOFError('unexpected end of backup')
            output.write(block)
            left -= len(block)
    print(f'Extracted {args.size} bytes; source backup was read only.')


if __name__ == '__main__':
    main()
