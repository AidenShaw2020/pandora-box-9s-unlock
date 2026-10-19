"""Groups the real DB entries (games_clean.db) into families of one original game + its hacks/clones/variants.
usage: python families.py <clean db> <sdcard dir> <out families.csv>

Arcade (zip sets): family = parent set from the FBNeo / MAME 2003 DATs (cloneof). Sets unknown to the DATs
(Chinese hacks such as dino2020, wofzl) belong to the longest known set name they start with; 'p4' four-player
variants belong to their base set.
Consoles (NES, MD, SNES, GB*, GG): ROMs are cut into 256-byte blocks; two ROMs sharing >= 50 % of their distinct
non-uniform blocks (Jaccard) are the same game (a hack keeps most of the original's data). ROMs are also matched
against No-Intro (CRC32 without header) to find the original and its real name.
Representative per family: original (DAT parent / No-Intro match) on a standard core, else the lowest id.
"""
import csv, os, re, sqlite3, sys, zlib, hashlib, collections
import xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__))
DB, SD, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

EMU_DIR = {'9': 'roms', '10': 'romsmgba', '12': 'romsgbc', '13': 'romsgg', '14': 'romsmd', '17': 'romsmd', '15': 'romssfc',
           '16': 'romsp', '21': 'romsmame2000', '24': 'romsfba2012driver', '51': 'roms_3h', '52': 'roms_3h',
           '61': 'roms2022', '62': 'roms2022', '63': 'roms2022', '64': 'roms2022/romsp', '80': 'romsfba2012v2',
           '81': 'romsfba2012v3', '82': 'romsfba2012v4', '83': 'romsfbneo', '7': 'romsp'}
SYSTEM = {'9': 'nes', '10': 'gba', '12': 'gbc', '13': 'gg', '14': 'md', '17': 'md', '62': 'md', '15': 'snes',
          '16': 'ps', '64': 'ps', '7': 'ps'}
STANDARD_EMU = {'11', '18', '19', '20', '22', '23', '83', '9', '10', '12', '13', '14', '15', '16', '17'}
NOINTRO = {'nes': 'Nintendo_-_Nintendo_Entertainment_System.dat', 'md': 'Sega_-_Mega_Drive_-_Genesis.dat',
           'snes': 'Nintendo_-_Super_Nintendo_Entertainment_System.dat', 'gba': 'Nintendo_-_Game_Boy_Advance.dat',
           'gbc': 'Nintendo_-_Game_Boy_Color.dat', 'gg': 'Sega_-_Game_Gear.dat'}

c = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
rows = c.execute("""select g.id, g.game, g.suffix, g.emu_type, g.game_type, e.name, cn.name
                    from tbl_game g join tbl_en e on e.id=g.id left join tbl_cn cn on cn.id=g.id""").fetchall()

# ---- ROM files -------------------------------------------------------------------------------
alldirs = [d for d in os.listdir(SD) if d.startswith('roms')] + ['roms2022/romsp']
files = {d: {f.lower(): f for f in os.listdir(os.path.join(SD, d))} for d in alldirs if os.path.isdir(os.path.join(SD, d))}
def rom_path(game, suffix, emu):
    fn = (game + suffix).lower()
    order = [EMU_DIR.get(emu, 'roms')] + [d for d in alldirs if d != EMU_DIR.get(emu, 'roms')]
    for d in order:
        if d in files and fn in files[d]:
            return os.path.join(SD, d, files[d][fn])
    return None

# ---- arcade DATs -------------------------------------------------------------------------------
clone, desc = {}, {}
for f in ['fbneo.dat', 'mame2003.xml']:
    for g in ET.parse(os.path.join(HERE, 'dats', f)).getroot().iter('game'):
        n = g.get('name')
        if n not in clone:
            clone[n] = g.get('cloneof') or n
            d = g.find('description'); desc[n] = d.text if d is not None else ''
known = set(clone)
db_stems = {r[1].lower() for r in rows}

ALIAS = {'kof01': 'kof2001', 'kof02': 'kof2002'}          # vendor names of the original sets
def arcade_family(s):
    s = s.lower()
    if s in ALIAS:
        return clone.get(ALIAS[s], ALIAS[s]), True
    if s not in known and s.endswith('p4') and len(s) > 4:
        s = s[:-2]
    if s in known:
        return clone[s], s == clone[s]
    for L in range(len(s) - 1, 2, -1):               # unknown hack: longest known set name it starts with
        p = s[:L]
        if p in known:
            return clone[p], False
        if p in db_stems and p != s:
            return arcade_family(p)[0], False
    return s, True

# ---- consoles ------------------------------------------------------------------------------
def load_nointro(sysname):
    crc = {}
    txt = open(os.path.join(HERE, 'dats', NOINTRO[sysname]), encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'game \(\s*name "([^"]+)".*?rom \( name "[^"]*" size \d+ crc ([0-9A-Fa-f]{8})', txt, re.S):
        crc.setdefault(m.group(2).upper(), m.group(1))
    return crc
nointro = {s: load_nointro(s) for s in NOINTRO}

def rom_bytes(path, sysname):
    d = open(path, 'rb').read()
    if sysname == 'nes' and d[:4] == b'NES\x1a':
        d = d[16 + (512 if d[6] & 4 else 0):]
    return d

def blocks(d):
    out = set()
    for i in range(0, len(d) - 255, 256):
        b = d[i:i + 256]
        if b.count(b[0]) < 200:                      # skip padding / uniform blocks
            out.add(hashlib.blake2b(b, digest_size=8).digest())
    return out

# ---- build entries -----------------------------------------------------------------------------
E = []
for id_, game, suf, emu, gtype, en, cn in rows:
    path = rom_path(game, suf, emu)
    sysname = SYSTEM.get(emu, 'arcade')
    e = dict(id=id_, game=game, suffix=suf, emu=emu, type=gtype, en=en or '', cn=cn or '', path=path, sys=sysname,
             original=False, real_name='')
    if sysname == 'arcade':
        fam, orig = arcade_family(game)
        e.update(family='arc:' + fam, original=orig, real_name=desc.get(game.lower(), desc.get(fam, '')))
    elif path and sysname in nointro:
        data = rom_bytes(path, sysname)
        nm = nointro[sysname].get('%08X' % (zlib.crc32(data) & 0xffffffff))
        e.update(blocks=blocks(data), original=bool(nm and '(Hack)' not in nm and 'Pirate' not in nm), real_name=nm or '')
    E.append(e)

# union-find over consoles, plus identical ROM file (same family regardless)
parent = list(range(len(E)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
def union(i, j):
    a, b = find(i), find(j)
    if a != b: parent[b] = a
by_key = collections.defaultdict(list)
for i, e in enumerate(E):
    by_key[e.get('family') or ('file:' + (e['path'] or e['game'] + e['suffix']).lower())].append(i)
for v in by_key.values():
    for j in v[1:]: union(v[0], j)
sims = []
for sysname in NOINTRO:
    idx = [i for i, e in enumerate(E) if e['sys'] == sysname and e.get('blocks')]
    inv = collections.defaultdict(list)                # block -> entries, to only compare ROMs sharing blocks
    for i in idx:
        for b in E[i]['blocks']: inv[b].append(i)
    shared = collections.Counter()
    for b, lst in inv.items():
        if len(lst) < 40:                              # very common blocks (engines, fonts) say nothing
            for x in range(len(lst)):
                for y in range(x + 1, len(lst)):
                    shared[(lst[x], lst[y])] += 1
    for (i, j), n in shared.items():
        a, b = len(E[i]['blocks']), len(E[j]['blocks'])
        jac = n / len(E[i]['blocks'] | E[j]['blocks'])
        if jac >= 0.5 and min(a, b) / max(a, b) >= 0.6:  # similar size: a compilation does not merge its games
            union(i, j); sims.append((E[i]['game'], E[j]['game'], round(jac, 2)))

# arcade sets unknown to the DATs: same title as a known set once hack words are removed -> same family
HACKWORDS = r'(x\d+|ps|ch|boss|plus|ult|ultimate|ultim|remix|rev\d|v\d+|enhanced|enh|edition|version|ver|super|special|the|returns?|retur|strengthened|strengt|blue|g|fking|evolution|evo|combo)'
def title_key(n):
    n = re.sub(r'(\d)([a-z])', r' ', re.sub(r'([a-z])(\d)', r' ', n.lower()))
    return re.sub(r'[^a-z0-9]', '', re.sub(HACKWORDS, ' ', n))
known_titles = {}
for i, e in enumerate(E):
    if e['sys'] == 'arcade' and (e['game'].lower() in known or e['game'].lower() in ALIAS):
        known_titles.setdefault(title_key(e['en']), i)
numbered = sorted((k for k in known_titles if k and k[-1].isdigit() and len(k) >= 6), key=len, reverse=True)
for i, e in enumerate(E):
    if (e['sys'] == 'arcade' and e['game'].lower() not in known and e['game'].lower() not in ALIAS
            and e['family'] == 'arc:' + e['game'].lower()):   # only sets the name prefix did not place already
        key = title_key(e['en'])
        j = known_titles.get(key)
        if j is None:                                  # e.g. 'kingoffighters2001' + leftover hack letters
            j = next((known_titles[k] for k in numbered if key.startswith(k) and not key[len(k):len(k) + 1].isdigit()), None)
        if j is not None and title_key(e['en']):
            union(j, i)
            e['original'] = False

fam = collections.defaultdict(list)
for i, e in enumerate(E):
    fam[find(i)].append(e)

words = lambda n: set(re.findall(r'[a-z0-9]{2,}', n.lower())) - {'the', 'of', 'version', 'edition', 'ver'}
def rank(e):
    stem = e['game'].lower()
    is_parent = e['sys'] == 'arcade' and (e.get('family') == 'arc:' + stem or stem in ALIAS)
    official = stem in known if e['sys'] == 'arcade' else bool(e['real_name'])
    overlap = len(words(e['en']) & words(e['real_name'])) if e['sys'] == 'arcade' else 0
    extra = len(words(e['en']) - words(e['real_name'])) if e['sys'] == 'arcade' else 0
    return (not is_parent, -overlap, extra, not e['original'], not official, e['path'] is None, e['emu'] not in STANDARD_EMU,
            bool(re.search(r' x\d+$', e['en'])), int(e['id']))
with open(OUT, 'w', newline='', encoding='utf-8') as fo:
    w = csv.writer(fo)
    w.writerow(['family', 'keep', 'id', 'game', 'suffix', 'emu', 'sys', 'type', 'en', 'cn', 'original', 'real_name', 'rom'])
    for k, members in sorted(fam.items(), key=lambda kv: min(int(e['id']) for e in kv[1])):
        members.sort(key=rank)
        famname = members[0]['game']
        for n, e in enumerate(members):
            w.writerow([famname, int(n == 0), e['id'], e['game'], e['suffix'], e['emu'], e['sys'], e['type'], e['en'], e['cn'],
                        int(e['original']), e['real_name'], 'yes' if e['path'] else 'no'])
print('entries', len(E), 'families', len(fam), 'removed', len(E) - len(fam))
print('per system', collections.Counter(E[find(i)]['sys'] for i in range(len(E)) if find(i) == i))
print('similarity links', len(sims))
