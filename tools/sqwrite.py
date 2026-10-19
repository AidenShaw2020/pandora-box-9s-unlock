"""Writer for squashfs v4 (zlib) images, optionally in the Pandora-box vendor variant.

Vendor variant (vendor=True) differs from standard squashfs in two places, mirroring pandsq.py:
 - every directory entry carries an extra u16 after 'offset'
 - basic regular file inodes (type 2) carry an extra u32 before start_block
In the original images the dirent u16 equals the low 16 bits of the file inode's u32, so we keep that.

No fragments are written (every file tail gets its own block); identical files share data.
"""
import struct, zlib, hashlib

META = 8192
INVALID = 0xffffffffffffffff


class Node:
    def __init__(self, name, kind, mode=0o755, uid=0, gid=0, mtime=0, data=None, target=None, x=None, unk=None):
        self.name = name            # str
        self.kind = kind            # 'dir' | 'file' | 'symlink'
        self.mode = mode & 0o7777
        self.uid, self.gid, self.mtime = uid, gid, mtime
        self.data = data            # file: bytes or callable -> bytes
        self.target = target        # symlink target
        self.x, self.unk = x, unk   # vendor values to preserve (optional)
        self.children = []
        self.num = None
        self.ref = None

    def child(self, name):
        for c in self.children:
            if c.name == name:
                return c
        return None

    def get_bytes(self):
        return self.data() if callable(self.data) else (self.data or b'')


class MetaWriter:
    """Accumulates a metadata stream; refs are (compressed start of current block, offset in block)."""
    def __init__(self):
        self.out = bytearray()
        self.buf = bytearray()
        self.block_starts = []      # compressed offsets of written blocks

    def pos(self):
        return len(self.out), len(self.buf)

    def add(self, b):
        self.buf += b
        while len(self.buf) >= META:
            self._flush(bytes(self.buf[:META]))
            del self.buf[:META]

    def _flush(self, chunk):
        self.block_starts.append(len(self.out))
        c = zlib.compress(chunk, 9)
        if len(c) < len(chunk):
            self.out += struct.pack('<H', len(c)) + c
        else:
            self.out += struct.pack('<H', len(chunk) | 0x8000) + chunk

    def finish(self):
        if self.buf:
            self._flush(bytes(self.buf))
            self.buf = bytearray()
        return bytes(self.out)


def _sortkey(n):
    return n.name.encode('utf-8')


class SquashWriter:
    def __init__(self, path, root, vendor=True, block_size=131072, mkfs_time=0, level=6, log=None):
        self.path, self.root, self.vendor = path, root, vendor
        self.bs, self.mkfs_time, self.level = block_size, mkfs_time, level
        self.log = log or (lambda *a: None)

    # --- helpers -------------------------------------------------------
    def _number(self):
        n = 1
        def rec(d):
            nonlocal n
            d.children.sort(key=_sortkey)
            for c in d.children:
                c.num = n; n += 1
            for c in d.children:
                if c.kind == 'dir':
                    rec(c)
        rec(self.root)
        self.root.num = n
        self.count = n

    def _id(self, v):
        if v not in self.idmap:
            self.idmap[v] = len(self.ids); self.ids.append(v)
        return self.idmap[v]

    def _vendor_vals(self, n):
        if n.unk is None:
            n.unk = (0x02000000 + 0x40 * n.num) & 0xffffffff
        if n.x is None:
            n.x = n.unk & 0xffff

    def _hdr(self, t, n):
        return struct.pack('<HHHHII', t, n.mode, self._id(n.uid), self._id(n.gid), n.mtime, n.num)

    # --- data ----------------------------------------------------------
    def _write_data(self, f):
        dedup = {}
        files = []
        def rec(d):
            for c in d.children:
                if c.kind == 'file':
                    files.append(c)
                elif c.kind == 'dir':
                    rec(c)
        rec(self.root)
        total = 0
        for i, n in enumerate(files):
            data = n.get_bytes()
            key = (len(data), hashlib.md5(data).digest())
            if key in dedup:
                n.start, n.blocks = dedup[key]
            else:
                n.start = f.tell(); n.blocks = []
                for off in range(0, len(data), self.bs):
                    chunk = data[off:off + self.bs]
                    c = zlib.compress(chunk, self.level)
                    if len(c) < len(chunk):
                        f.write(c); n.blocks.append(len(c))
                    else:
                        f.write(chunk); n.blocks.append(len(chunk) | 0x1000000)
                dedup[key] = (n.start, n.blocks)
            n.size = len(data)
            total += len(data)
            if i % 1000 == 0:
                self.log('data %d/%d files, %.1f MB' % (i, len(files), total / 1e6))

    # --- metadata ------------------------------------------------------
    def _write_inode(self, n, dirpos=None, dirlen=None, parent=None):
        iw = self.iw
        n.ref = iw.pos()
        if n.kind == 'file':
            if self.vendor:
                self._vendor_vals(n)
            if n.start < 2**32 and n.size < 2**32:
                b = self._hdr(2, n)
                if self.vendor:
                    b += struct.pack('<I', n.unk)
                b += struct.pack('<IIII', n.start, 0xffffffff, 0, n.size)
            else:
                b = self._hdr(9, n) + struct.pack('<QQQIIII', n.start, n.size, 0, 1, 0xffffffff, 0, 0xffffffff)
            b += struct.pack('<%dI' % len(n.blocks), *n.blocks)
        elif n.kind == 'symlink':
            if self.vendor and n.x is None:
                n.x = (0x40 * n.num) & 0xffff
            t = n.target.encode('utf-8')
            b = self._hdr(3, n) + struct.pack('<II', 1, len(t)) + t
        else:
            if self.vendor and n.x is None:
                n.x = (0x40 * n.num) & 0xffff
            nlink = 2 + sum(1 for c in n.children if c.kind == 'dir')
            blk, off = dirpos
            if dirlen + 3 <= 0xffff:
                b = self._hdr(1, n) + struct.pack('<IIHHI', blk, nlink, dirlen + 3, off, parent)
            else:
                b = self._hdr(8, n) + struct.pack('<IIIIHHI', nlink, dirlen + 3, blk, parent, 0, off, 0xffffffff)
        iw.add(b)

    def _listing(self, d):
        out = bytearray()
        kids = d.children
        i = 0
        while i < len(kids):
            blk = kids[i].ref[0]; base = kids[i].num
            group = []
            while i < len(kids) and len(group) < 256 and kids[i].ref[0] == blk and abs(kids[i].num - base) <= 32767:
                group.append(kids[i]); i += 1
            out += struct.pack('<IIi', len(group) - 1, blk, base)
            for c in group:
                name = c.name.encode('utf-8')
                t = {'dir': 1, 'file': 2, 'symlink': 3}[c.kind]
                if self.vendor:
                    out += struct.pack('<HHhHH', c.ref[1], c.x & 0xffff, c.num - base, t, len(name) - 1)
                else:
                    out += struct.pack('<HhHH', c.ref[1], c.num - base, t, len(name) - 1)
                out += name
        return bytes(out)

    def _write_dir(self, d, parent):
        for c in d.children:
            if c.kind == 'dir':
                self._write_dir(c, d.num)
            else:
                self._write_inode(c)
        listing = self._listing(d)
        pos = self.dw.pos()
        self.dw.add(listing)
        self._write_inode(d, pos, len(listing), parent)

    def _table(self, f, entries_bytes):
        """Write a lookup-style table (metadata blocks + u64 index); return index position."""
        mw = MetaWriter()
        mw.add(entries_bytes)
        blob = mw.finish()
        start = f.tell()
        f.write(blob)
        idx = f.tell()
        f.write(b''.join(struct.pack('<Q', start + s) for s in mw.block_starts))
        return idx

    def write(self):
        self._number()
        self.ids, self.idmap = [], {}
        self.iw, self.dw = MetaWriter(), MetaWriter()
        with open(self.path, 'wb') as f:
            f.write(b'\0' * 96)
            self._write_data(f)
            self._write_dir(self.root, self.count + 1)
            inode_start = f.tell(); f.write(self.iw.finish())
            dir_start = f.tell(); f.write(self.dw.finish())
            frag_start = f.tell()
            # export table: inode refs by inode number
            refs = [None] * self.count
            def rec(d):
                refs[d.num - 1] = d.ref
                for c in d.children:
                    if c.kind == 'dir':
                        rec(c)
                    else:
                        refs[c.num - 1] = c.ref
            rec(self.root)
            exp_start = self._table(f, b''.join(struct.pack('<Q', (r[0] << 16) | r[1]) for r in refs))
            id_start = self._table(f, b''.join(struct.pack('<I', v) for v in self.ids))
            bytes_used = f.tell()
            pad = (-bytes_used) % 4096
            f.write(b'\0' * pad)
            root_ref = (self.root.ref[0] << 16) | self.root.ref[1]
            flags = 0x10 | 0x40 | 0x80     # no fragments, duplicates, exportable
            sb = struct.pack('<IIIIIHHHHHHQQQQQQQQ', 0x73717368, self.count, self.mkfs_time, self.bs, 0, 1,
                             self.bs.bit_length() - 1, flags, len(self.ids), 4, 0, root_ref, bytes_used,
                             id_start, INVALID, inode_start, dir_start, frag_start, exp_start)
            f.seek(0); f.write(sb)
        return bytes_used


def tree_from_image(sq):
    """Build a Node tree mirroring a PandSq image (file data read lazily)."""
    ids = sq.ids()
    rino = sq.inode(sq.root >> 16, sq.root & 0xffff)
    root = Node('', 'dir', rino['mode'], ids[rino['uid']], ids[rino['gid']], rino['mtime'])
    def rec(dnode, dino):
        for name, b, o, x in sq.listdir(dino):
            ino = sq.inode(b, o)
            kw = dict(mode=ino['mode'], uid=ids[ino['uid']], gid=ids[ino['gid']], mtime=ino['mtime'], x=x)
            t = ino['type']
            if t in (1, 8):
                n = Node(name, 'dir', **kw); rec(n, ino)
            elif t in (2, 9):
                n = Node(name, 'file', data=(lambda ino=ino: sq.read(ino)), unk=ino.get('crc'), **kw)
            elif t in (3, 10):
                n = Node(name, 'symlink', target=ino['target'], **kw)
            else:
                raise ValueError('unsupported inode type %d at %s' % (t, name))
            dnode.children.append(n)
    rec(root, rino)
    return root


def find(root, path, create_dirs=False, mtime=0):
    node = root
    parts = [p for p in path.split('/') if p]
    for i, p in enumerate(parts):
        c = node.child(p)
        if c is None:
            if not create_dirs:
                return None
            c = Node(p, 'dir', 0o755, 0, 0, mtime); node.children.append(c)
        node = c
    return node


def put_file(root, path, data, mode=0o644, mtime=0):
    """Add or replace a file. Replacing keeps the original metadata except data (and drops vendor unk)."""
    d, _, name = path.rstrip('/').rpartition('/')
    parent = find(root, d, create_dirs=True, mtime=mtime)
    old = parent.child(name)
    if old is not None and old.kind == 'file':
        old.data = data
        old.unk = None; old.x = None
        return old
    if old is not None:
        parent.children.remove(old)
    n = Node(name, 'file', mode, 0, 0, mtime, data=data)
    parent.children.append(n)
    return n
