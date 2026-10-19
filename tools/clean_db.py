"""Builds a clean game DB: drops the vendor's fake renamed variants (rows without tbl_en.idx, ~27 300 of 32 000)
and games whose ROM is known to be missing. Ids of kept rows stay unchanged.
usage: python clean_db.py <source db> <output db>"""
import shutil, sqlite3, sys, collections
SRC, OUT = sys.argv[1], sys.argv[2]
DROP_GAMES = ['shuangjielongquanbossban']          # NES, no ROM anywhere on the card
LANGS = ['tbl_en', 'tbl_cn', 'tbl_tw', 'tbl_ko', 'tbl_sp']
shutil.copyfile(SRC, OUT)
c = sqlite3.connect(OUT)
before = c.execute('select count(*) from tbl_game').fetchone()[0]
fake = {i for (i,) in c.execute("select g.id from tbl_game g join tbl_en e on e.id=g.id where e.idx is null")}
fake |= {i for (i,) in c.execute('select id from tbl_game where game in (%s)' % ','.join('?' * len(DROP_GAMES)), DROP_GAMES)}
orphans = {i for (i,) in c.execute('select id from tbl_game where id not in (select id from tbl_en)')}
assert not orphans, orphans
c.execute('create temp table drop_ids(id text primary key)')
c.executemany('insert into drop_ids values (?)', [(i,) for i in fake])
for t in ['tbl_game'] + LANGS:
    c.execute('delete from %s where id in (select id from drop_ids)' % t)
c.commit()
c.execute('vacuum')
after = c.execute('select count(*) from tbl_game').fetchone()[0]
print('rows %d -> %d (dropped %d)' % (before, after, len(fake)))
for t in LANGS:
    print(t, c.execute('select count(*) from %s' % t).fetchone()[0])
print('per class', dict(collections.Counter(r for (r,) in c.execute('select game_type from tbl_game'))))
print('distinct games', c.execute('select count(distinct game||suffix||emu_type) from tbl_game').fetchone()[0])
print('integrity', c.execute('pragma integrity_check').fetchone()[0], 'journal', c.execute('pragma journal_mode').fetchone()[0])
