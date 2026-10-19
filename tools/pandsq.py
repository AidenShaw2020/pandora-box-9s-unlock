"""Reader for the Pandora-box modified squashfs (zlib) image.
Differences vs. standard squashfs v4:
 - directory entries have an extra u16 after 'offset' (value varies)
 - basic regular file inode (type 2) has an extra u32 BEFORE start_block (value varies)
Extended file inodes (type 9), directories and symlinks are standard.
"""
import struct, zlib, math

class PandSq:
    def __init__(self, path):
        self.f = open(path, 'rb')
        sb = self.f.read(96)
        (self.magic, self.inodes, self.mkfs_time, self.bs, self.nfrags, comp, _, self.flags, self.n_ids, _, _, self.root, self.bytes_used,
         self.idt, _, self.inot, self.dirt, self.fragt, self.expt) = struct.unpack('<IIIIIHHHHHHQQQQQQQQ', sb)
        self.I, self.imap = self._table(self.inot, self.dirt)
        self.D, self.dmap = self._table(self.dirt, self.fragt)
        # fragment table
        n_idx = math.ceil(self.nfrags * 16 / 8192)
        self.f.seek(self.fragt)
        ptrs = struct.unpack('<%dQ' % n_idx, self.f.read(8 * n_idx))
        raw = b''
        for p in ptrs:
            raw += self._meta(p)[0]
        self.frags = [struct.unpack_from('<QII', raw, i * 16)[:2] for i in range(self.nfrags)]
        self._fcache = {}

    def _meta(self, pos):
        self.f.seek(pos)
        h = struct.unpack('<H', self.f.read(2))[0]
        l = h & 0x7fff
        d = self.f.read(l)
        if not h & 0x8000:
            d = zlib.decompress(d)
        return d, 2 + l

    def _table(self, start, end):
        data = bytearray(); m = {}; pos = start
        while pos < end:
            d, n = self._meta(pos)
            m[pos - start] = len(data); data += d; pos += n
        return bytes(data), m

    def ids(self):
        n_idx = math.ceil(self.n_ids * 4 / 8192)
        self.f.seek(self.idt)
        raw = b''
        for ptr in struct.unpack('<%dQ' % n_idx, self.f.read(8 * n_idx)):
            raw += self._meta(ptr)[0]
        return list(struct.unpack_from('<%dI' % self.n_ids, raw))

    def inode(self, ref_blk, ref_off):
        d = self._inode(ref_blk, ref_off)
        t, mode, uid, gid, mtime, num = struct.unpack_from('<HHHHII', self.I, self.imap[ref_blk] + ref_off)
        d.update(mode=mode, uid=uid, gid=gid, mtime=mtime, num=num)
        return d

    def _inode(self, ref_blk, ref_off):
        p = self.imap[ref_blk] + ref_off
        t = struct.unpack_from('<H', self.I, p)[0]
        p += 16
        if t == 2:
            crc, start, frag, foff, size = struct.unpack_from('<IIIII', self.I, p); p += 20  # first u32: unknown vendor field
            nb = size // self.bs if frag != 0xffffffff else math.ceil(size / self.bs)
            blocks = struct.unpack_from('<%dI' % nb, self.I, p)
            return dict(type=t, start=start, crc=crc, frag=frag, foff=foff, size=size, blocks=blocks)
        if t == 9:
            start, size, _, _, frag, foff, _ = struct.unpack_from('<QQQIIII', self.I, p); p += 40
            nb = size // self.bs if frag != 0xffffffff else math.ceil(size / self.bs)
            blocks = struct.unpack_from('<%dI' % nb, self.I, p)
            return dict(type=t, start=start, crc=None, frag=frag, foff=foff, size=size, blocks=blocks)
        if t == 1:
            start, _, fsz, doff, _ = struct.unpack_from('<IIHHI', self.I, p)
            return dict(type=t, dstart=start, dsize=fsz - 3, doff=doff)
        if t == 8:
            _, fsz, start, _, _, doff, _ = struct.unpack_from('<IIIIHHI', self.I, p)
            return dict(type=t, dstart=start, dsize=fsz - 3, doff=doff)
        if t in (3, 10):
            _, tsz = struct.unpack_from('<II', self.I, p)
            return dict(type=t, target=self.I[p + 8:p + 8 + tsz].decode('utf-8', 'replace'))
        return dict(type=t)

    def listdir(self, ino):
        pos = self.dmap[ino['dstart']] + ino['doff']; end = pos + ino['dsize']; out = []
        while pos < end:
            cnt, sblk, _ = struct.unpack_from('<IIi', self.D, pos); pos += 12
            for _ in range(cnt + 1):
                o, x, _, typ, nsz = struct.unpack_from('<HHhHH', self.D, pos); pos += 10
                out.append((self.D[pos:pos + nsz + 1].decode('utf-8', 'replace'), sblk, o, x)); pos += nsz + 1
        return out

    def walk(self, ino=None, path=''):
        if ino is None:
            ino = self.inode(self.root >> 16, self.root & 0xffff)
        for name, b, o, x in self.listdir(ino):
            c = self.inode(b, o); c['dirent_x'] = x; full = path + '/' + name
            yield full, c
            if c['type'] in (1, 8):
                yield from self.walk(c, full)

    def read(self, ino, limit=None):
        out = bytearray(); pos = ino['start']
        for bsz in ino['blocks']:
            l = bsz & 0xffffff
            self.f.seek(pos); d = self.f.read(l); pos += l
            if l == 0:
                d = b'\0' * self.bs
            elif not bsz & 0x1000000:
                d = zlib.decompress(d)
            out += d
            if limit and len(out) >= limit:
                return bytes(out[:limit])
        if ino['frag'] != 0xffffffff:
            fs, fsz = self.frags[ino['frag']]
            if ino['frag'] not in self._fcache:
                self.f.seek(fs); d = self.f.read(fsz & 0xffffff)
                if not fsz & 0x1000000:
                    d = zlib.decompress(d)
                self._fcache = {ino['frag']: d}
            d = self._fcache[ino['frag']]
            out += d[ino['foff']:ino['foff'] + ino['size'] - len(out)]
        return bytes(out[:ino['size']])


if __name__ == '__main__':
    # usage: python pandsq.py <image> ls [prefix]
    #        python pandsq.py <image> extract <outdir> <path-prefix>...
    import sys, os
    sq = PandSq(sys.argv[1]); cmd = sys.argv[2]
    if cmd == 'ls':
        pre = sys.argv[3] if len(sys.argv) > 3 else ''
        for p, ino in sq.walk():
            if p.startswith(pre):
                if ino['type'] in (1, 8):
                    print(p + '/')
                elif 'size' in ino:
                    print('%s\t%d' % (p, ino['size']))
                else:
                    print('%s\t-> %s' % (p, ino.get('target', 'type %d' % ino['type'])))
    elif cmd == 'extract':
        outd, pres = sys.argv[3], sys.argv[4:]
        for p, ino in sq.walk():
            if ino['type'] in (2, 9) and any(p.startswith(x) for x in pres):
                dst = os.path.join(outd, *p.strip('/').split('/'))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, 'wb') as fo:
                    fo.write(sq.read(ino))
                print(p)
