"""Generate a private C header from application-visible SD identity values."""
import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding='utf-8-sig'))
    patterns = {'cid': r'[0-9a-fA-F]{32}', 'csd': r'[0-9a-fA-F]{32}',
                'serial': r'0x[0-9a-fA-F]{8}', 'scr': r'[0-9a-fA-F]{16}'}
    for key, pattern in patterns.items():
        if not isinstance(profile.get(key), str) or not re.fullmatch(pattern, profile[key]):
            parser.error(f'{key}: expected exact hexadecimal application-visible value')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='ascii', newline='\n') as stream:
        stream.write('/* PRIVATE: generated card identity; do not publish. */\n')
        for key in patterns:
            stream.write(f'#define PANDORA_{key.upper()} "{profile[key]}"\n')
    print('Private header created; identity values were not printed.')


if __name__ == '__main__':
    main()
