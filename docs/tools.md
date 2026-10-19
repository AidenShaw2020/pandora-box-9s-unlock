# Tool reference

Most Python tools use the standard library (Python 3.10+ recommended). The C sources target ARMv7 Linux; the tested firmware uses glibc 2.25. Docker with ARM/QEMU support provides the compatibility compiler. No account tokens or cloud services are needed to run the tools.

| Tool | Inputs | Output / scope |
|---|---|---|
| `extract_region.py` | Image, byte offset, byte size, new output path | Copies a range read-only from the source image |
| `pandsq.py` | Vendor SquashFS image, `ls` or `extract` | Lists files or extracts selected regular files |
| `sqwrite.py` | Imported Python API | Vendor-compatible writer, including modified inode/directory fields |
| `patch_init.py` | Original init, new output | Targeted init changes; refuses an unexpected/already patched input |
| `build_p2.py` | Original P2, patched init, compiled shim, new output | New local P2 image; no raw-disk writes |
| `make_identity.py` | Private JSON, new header path | Validates exact ASCII hex lengths; does not print values |
| `cardspoof.c` | Generated private `card_identity.h` | A card-specific shared library; keep the result private |
| `cardprobe.c` | Optional sysfs base path | Reads and prints attribute lengths and exact bytes; output is private |
| `clean_db.py` | Original DB, new DB | Applies the observed catalog cleanup heuristic |
| `families.py` | Clean DB, local ROM directories, CSV path | Family candidates; requires external DAT metadata |
| `unique_db.py` | Clean DB, reviewed family CSV, new DB | Keeps selected representatives |
| `sort_db.py` | DB, new directory, `menu_games_query.sql` | Backup, sorted DB, and verification report |
| `reset_history.py` | Mounted P3 path, optional `--apply` | Inspect only by default; verified backup before clearing history |

The original `clean_db.py`, `families.py`, and `unique_db.py` are preserved research scripts, with their assumptions documented in [catalog.md](catalog.md). Use new output filenames, review their decisions, and avoid treating their heuristics as universal firmware rules.

## Original findings

The modified SquashFS uses an extra `u16` in directory entries and an extra `u32` before the basic file inode's `start_block`. Extended inodes, directories, and symlinks follow the normal structures used by these tools. The writer does not emit fragments; identical data can share blocks.

The native menu's query is kept in `tools/menu_games_query.sql` for order verification. Its join structure matters: the sorter verifies both the complete result and category-filtered results rather than assuming insertion order alone is enough.

## Provenance and licensing

This repository packages project-specific tools and findings developed while repairing and customizing the owner's console. Earlier investigation and filesystem/catalog work used Claude Code; the final application-visible identity fix, alphabetical-order verification, history diagnosis, and publication preparation used Codex with owner testing on hardware.

No external ROM collection, firmware executable, or extracted vendor filesystem is included. Docker base images and external DAT metadata retain their own licenses. The console photographs are attributed separately in [images/README.md](images/README.md) and are excluded from the project's MIT license.
