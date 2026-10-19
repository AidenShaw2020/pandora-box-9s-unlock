# Validation and troubleshooting

## Confirmed on the console

The owner confirmed these separate results on 19 October 2026:

1. The replacement card booted the normal menu after the identity fix.
2. The full library appeared alphabetically.
3. After clearing stale recent-game entries, P1+P2 opened the category menu again.

The number of individual games tested was not recorded. These confirmations do not establish compatibility with every title, every emulator, or other 9S hardware revisions.

## Local evidence behind the fixes

The identity diagnosis compared several shim candidates against the same original vendor check. Wrong candidates reached the same failing store in `libh3mini.so+0x1c4aa`, after identity validation failed. Correct application-visible attributes let the unmodified `ck()` routine return successfully, both in emulation and in an independent ARM execution with the production shim.

The original reserved blocks read by that check matched the clone. No speculative replacement of those blocks was needed. Raw SPI registers and vendor-kernel-visible values had been confused in the earlier attempts.

For the category issue, a local ARM/QEMU environment ran the captured, loaded vendor menu using original libraries and skin, copies of the configuration/database, software rendering, and mocked device input. The original backup was mounted read only. The same four synthetic key events (1 down, 2 down, 1 up, 2 up) were used in each comparison:

| Recent list | Result |
|---|---|
| Existing mixed old/new list | `SIGSEGV`, PC `0x20cdc`, LR `0x2ae9c`, fault address `0x9a` |
| Empty list | Category screen rendered, Recent selected, survived the 30-second test |
| Two valid current entries | Category screen rendered, survived the 30-second test |

The crash log and successful rendering are the meaningful evidence. A timeout exit status alone is insufficient because signal handling/thread shutdown in the mock environment could itself stall. This environment reproduces a software path, not the complete HDMI/audio/input hardware.

The public parameterized shim was additionally compiled with `-Wall -Wextra -Werror` and checked using the original glibc 2.25 loader and a private test profile. Its inputs and generated binaries remain outside the public Git history. See `docs/checks.json` for the checks performed before initial publication.

## Symptoms and next checks

| Symptom | Useful check |
|---|---|
| “No signal” | Check boot/display setup and power before diagnosing a running application. |
| Black screen with signal present | Look for a repeated `pbfe` crash; this project's cause was the identity check. |
| P1+P2 flashes and reloads the menu | Back up `rcp_roms`; reproduce with an empty recent list before changing skins or the database again. |
| Alphabetical rewrite appears ignored | Confirm the mounted database path and actual query; this firmware opens `/usr/lib/game`. |
| The previous game's preview stays on screen | Probe the current AVI for a single-frame or unsupported clip. |
| USB/SD readers stop seeing multiple cards | Diagnose the host/card reader separately. In this session Windows needed a reboot; that was not evidence of an encrypted catalog. |

The deployed private package writes `log/CODEX7_STATUS.txt`, `log/codex7_runN/`, and `log/cardspoof_kernel.txt`. Its snapshots cover only the early boot period, so later crashes may be absent from the snapshot of system messages. Public `runtime/autorun.sh` is a smaller template and writes `log/UNLOCK_STATUS.txt` instead.

Logs and core dumps can expose the full card identity and copies of memory. Keep them with private recovery material.

## Recovery boundaries

The deployed final boot fix changed files on the replacement card's P3 and installed a temporary bind mount at boot. It did not rewrite the original card, the full backup, or P1/P2 during that final fix. The replacement system's P2 had already been rebuilt earlier to support loose files, the external DB, and preload.

Do not confuse those stages: a stock clone without the earlier init changes cannot use this P3 autorun automatically. Likewise, rebuilding P2 with an obsolete identity shim does not become correct merely because the filesystem image builds successfully.

A backed-up pre-fix autorun may be a diagnostic script that intentionally stops the normal menu loop. It is not necessarily a usable rollback. Use the exact matching private package or restore your own complete known-good backup.
