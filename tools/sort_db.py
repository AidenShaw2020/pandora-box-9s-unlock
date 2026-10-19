"""Reorder Pandora DB by English display title; preserve all stored field values and IDs."""
import collections,hashlib,json,pathlib,re,shutil,sqlite3,sys,unicodedata
TABLES=('tbl_game','tbl_en','tbl_cn','tbl_tw','tbl_ko','tbl_sp')
def title_key(name):
 s=''.join(c for c in unicodedata.normalize('NFKD',name).casefold() if not unicodedata.combining(c))
 s=''.join(c for c in s if c.isalnum() or c.isspace())
 return ' '.join(s.split())
def content(c):
 return {t:collections.Counter(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in c.execute('select * from '+t)) for (t,) in c.execute("select name from sqlite_master where type='table'").fetchall()}
def schema(c):return c.execute('select type,name,tbl_name,sql from sqlite_master order by type,name').fetchall()
if __name__=='__main__':
 src=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2]);query=pathlib.Path(sys.argv[3]).read_text(encoding='utf8')
 dest.mkdir(parents=True,exist_ok=False)
 backup=dest/'games_before_alphabetical.db';out=dest/'games_alphabetical.db'
 shutil.copyfile(src,backup);shutil.copyfile(backup,out)
 c=sqlite3.connect(out);before=content(c);oldschema=schema(c)
 english=c.execute('select id,name from tbl_en').fetchall();names=dict(english)
 assert len(names)==len(english) and all(n and n.strip() for n in names.values())
 ids=sorted(names,key=lambda id_:(title_key(names[id_]),names[id_].casefold(),int(id_)))
 assert len(ids)==c.execute('select count(*) from tbl_game').fetchone()[0]
 order={id_:n for n,id_ in enumerate(ids)}
 c.execute('begin immediate')
 for table in TABLES:
  cols=[r[1] for r in c.execute('pragma table_info('+table+')')];idx=cols.index('id');rows=c.execute('select * from '+table).fetchall()
  assert len(rows)==len(ids) and {r[idx] for r in rows}==set(ids)
  rows.sort(key=lambda r:order[r[idx]])
  c.execute('delete from '+table)
  c.executemany('insert into '+table+' ('+','.join('"'+col+'"' for col in cols)+') values ('+','.join('?' for _ in cols)+')',rows)
 c.commit();c.execute('vacuum')
 assert schema(c)==oldschema and content(c)==before,'Unexpected stored field or schema changes'
 assert c.execute('pragma integrity_check').fetchone()==('ok',)
 assert not c.execute('pragma foreign_key_check').fetchall()
 games={r[0]:r[1] for r in c.execute('select id,game from tbl_game')}
 actual=[(r[0],r[1]) for r in c.execute(query)];expected=[(names[i],games[i]) for i in ids]
 assert actual==expected,'Menu query order differs from alphabetical order'
 perclass={}
 for cat,count in c.execute('select game_type,count(*) from tbl_game group by game_type').fetchall():
  selected={r[0] for r in c.execute('select id from tbl_game where game_type=?',(cat,))}
  got=[(r[0],r[1]) for r in c.execute(query+' and tbl_game.game_type=?',(cat,))]
  assert got==[(names[i],games[i]) for i in ids if i in selected]
  perclass[cat]=count
 report={'games':len(ids),'unchanged_all_fields_and_ids':True,'integrity':'ok','categories':perclass,'first_30':[n for n,g in actual[:30]],'last_10':[n for n,g in actual[-10:]],'sorting':'English display title, case/diacritic/punctuation insensitive; numbers first; The under T; no series priority','backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'sorted_sha256':hashlib.sha256(out.read_bytes()).hexdigest()}
 (dest/'verification.json').write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
 shutil.copyfile(__file__,dest/'sort_db.py');c.close()
 print(json.dumps(report,ensure_ascii=False,indent=2))
