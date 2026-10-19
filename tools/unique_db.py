"""Builds the unique-games DB: keeps one entry per family from families.csv (keep=1), drops hacks/clones/variants.
Trailing ' xN' markers are stripped from the kept names (and their sort keys). Ids stay unchanged.
usage: python unique_db.py <clean db> <families.csv> <out db>"""
import csv, re, shutil, sqlite3, sys, collections
SRC, FAM, OUT = sys.argv[1:4]
LANGS = ['tbl_en', 'tbl_cn', 'tbl_tw', 'tbl_ko', 'tbl_sp']
rows = list(csv.DictReader(open(FAM, encoding='utf-8')))
keep = {r['id'] for r in rows if r['keep'] == '1'}
shutil.copyfile(SRC, OUT)
c = sqlite3.connect(OUT)
allids = {i for (i,) in c.execute('select id from tbl_game')}
assert keep <= allids and len(rows) == len(allids)
c.execute('create temp table keep_ids(id text primary key)')
c.executemany('insert into keep_ids values (?)', [(i,) for i in keep])
for t in ['tbl_game'] + LANGS:
    c.execute('delete from %s where id not in (select id from keep_ids)' % t)
renamed = 0
for t in LANGS:
    entries = c.execute('select id, name, idx from %s' % t).fetchall()
    taken = collections.Counter((n or '').strip().lower() for _, n, _ in entries)
    for id_, name, idx in entries:
        m = re.search(r'\s*x\d+$', name or '')
        if m and taken[name[:m.start()].strip().lower()] == 0:   # strip only if the plain name stays unique
            new = name[:m.start()].rstrip(); taken[new.lower()] += 1
            nidx = re.sub(r'X\d+$', '', idx) if idx else idx
            c.execute('update %s set name=?, idx=? where id=?' % t, (new, nidx, id_)); renamed += 1
c.commit(); c.execute('vacuum')
print('kept', c.execute('select count(*) from tbl_game').fetchone()[0], 'renamed names', renamed)
print('per class', dict(collections.Counter(r for (r,) in c.execute('select game_type from tbl_game'))))
print('per emu', dict(collections.Counter(r for (r,) in c.execute('select emu_type from tbl_game'))))
print('integrity', c.execute('pragma integrity_check').fetchone()[0])
