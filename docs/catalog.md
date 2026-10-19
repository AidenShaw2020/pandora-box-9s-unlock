# Catalog cleanup, sorting, and Recent

The active catalog is a normal SQLite database. The vendor program's unusual/encrypted loading mechanism was a separate issue; a second encrypted game catalog was not established.

On the modified system, `P3/games.db` is bind-mounted over `/usr/lib/game`. Always edit a copy and retain the previous database. The tools below never require ROMs to be redistributed.

## Historical cleanup on this unit

| Stage | Entries |
|---|---:|
| Original catalog | 32,000 |
| After removing misleading renamed variants and one missing-ROM entry | 4,693 |
| After selecting one representative per family | 3,318 |

`clean_db.py` uses the observed absence of `tbl_en.idx` as a cleanup rule and removes the known missing entry `shuangjielongquanbossban`. This is a firmware-specific heuristic, not a universal definition of a fake game. Inspect those rows in your own database first.

```sh
python tools/clean_db.py local/games-original.db build/games-clean.db
```

`families.py` groups arcade clones using FBNeo/MAME metadata and compares console ROMs using shared 256-byte blocks. No-Intro CRCs help choose representative originals. These are heuristics: regional pairs and incorrect vendor titles can remain. It expects these separately obtained files in `tools/dats/`:

```text
fbneo.dat
mame2003.xml
Nintendo_-_Nintendo_Entertainment_System.dat
Nintendo_-_Super_Nintendo_Entertainment_System.dat
Nintendo_-_Game_Boy_Advance.dat
Nintendo_-_Game_Boy_Color.dat
Sega_-_Mega_Drive_-_Genesis.dat
Sega_-_Game_Gear.dat
```

The metadata itself is not bundled. Use compatible metadata from the relevant [FBNeo](https://github.com/finalburnneo/FBNeo), [MAME 2003](https://github.com/libretro/mame2003-libretro), and [No-Intro](https://no-intro.org/) projects. Review the generated CSV, especially the `keep` choices, before applying it:

```sh
python tools/families.py build/games-clean.db local/sdcard build/families.csv
python tools/unique_db.py build/games-clean.db build/families.csv build/games-unique.db
```

The original research cleanup scripts expect new output paths. They can overwrite an existing output file; never point an output at your source or mounted card. They preserve kept IDs but intentionally remove rows from game and language tables.

## Alphabetical order

The observed vendor menu query has **no `ORDER BY`**. Changing display names or an apparent sort-key column alone does not make this menu enumerate alphabetically. The working approach rewrites the physical row order in `tbl_game` and all five locale tables in the same title order.

```sh
python tools/sort_db.py build/games-unique.db build/alphabetical tools/menu_games_query.sql
```

The destination directory must not exist. It contains the previous database, a sorted database, and `verification.json`. The sorter checks:

- Every stored field value, ID, row count, and schema definition is unchanged.
- SQLite `integrity_check` and `foreign_key_check` pass.
- The actual menu query yields the expected complete order.
- Every game category retains its members in that same order.

Titles are compared in English, ignoring case, diacritics, and punctuation. Number-prefixed titles come first; “The” stays under T. There is no priority for King of Fighters or any other series. This reflects the owner's requested order.

Back up P3's current `games.db`, copy in the generated `games_alphabetical.db` as `games.db`, then reset history before boot. The owner confirmed the resulting order on the real console.

## Why P1+P2 restarted the menu

The category screen initially opened **Recent**. The text file `rcp_roms` still held entries from a much larger catalog: 24 numbers, including 11 above the new 3,318-entry range. In a controlled test, retaining that file crashed the menu after the same P1+P2 input. Clearing only the recent list let the entire category screen render.

Preserving database IDs was therefore insufficient. The history mechanism has list-dependent references; their exact interpretation was not fully mapped. It is unsafe to treat all saved numbers as stable database IDs or to remap a mixed old/new list speculatively.

Inspect, then archive and clear the list:

```sh
python tools/reset_history.py /path/to/mounted/PANDORA
python tools/reset_history.py /path/to/mounted/PANDORA --apply
```

On Windows the mounted path can be `H:/`, after independently verifying that it is the intended data partition. The script makes a timestamped, byte-verified backup next to `rcp_roms` and leaves the active file empty. It does not modify games, saves, or the database. History should rebuild as games are played; test launching one game and returning to Recent.

Do not restore the obsolete recent list just to repopulate the screen. Keep its backup for analysis. Other index-dependent settings should be investigated if symptoms appear; this fix did not reset all configuration or saved games.

## Preview videos

The observed menu uses `movies/<game>.avi`. Some original NES previews contained only one frame. When those clips failed to display, the previous game's video stayed visible, making the next entry appear to have the wrong preview.

The project regenerated previews using local emulation. The working export format was AVI/MPEG-4 (`FMP4`) without B-frames. Preview videos and emulator cores are not distributed in this repository; use your own content. Catalog sorting does not rename ROMs or preview files.
