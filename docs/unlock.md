# Unlock and larger-card workflow

This guide describes the successful route for the tested H3 unit. It assumes you own the original console and card and have a full backup. It does not supply someone else's card identity or vendor software.

## 1. Keep a complete original backup

Create a full raw image of the original card, including the MBR, bootloader, reserved sectors, and all partitions. Record a checksum and retain the original card. Work on a replacement card and copies of the image.

Identify partitions from the image's MBR. For the layout in [hardware.md](hardware.md), P2 starts at 24,576 × 512 bytes. Extract it into a new local file:

```sh
python tools/extract_region.py local/sd.img 12582912 209715200 local/p2-original.squashfs
python tools/pandsq.py local/p2-original.squashfs ls /usr/retrogame
python tools/pandsq.py local/p2-original.squashfs extract local/rootfs /usr/retrogame/myinit
```

The 200 MiB size above applies to the original image in this project. Read your own MBR first. `extract_region.py` refuses to overwrite its output. The reader's `extract` command extracts regular files only; it is not a complete rootfs exporter with symlink restoration.

## 2. Distinguish physical identity from application identity

The protection reads MMC attributes such as `cid`, `csd`, `serial`, and `scr`, plus reserved blocks from the original medium. The successful profile used the exact ASCII values visible to the application under the vendor kernel, with **no trailing newline**.

Reading a physical SD CID over SPI can help identify a card, but it did not produce the complete profile expected by this menu. In this case the vendor kernel transformed what the application saw. A shim populated with only the physical registers still crashed.

`src/cardprobe.c` prints lengths and hexadecimal bytes of attributes read through `fopen`. Compile it for the target ABI, then run it under the same environment as the menu on a working original system:

```sh
./cardprobe /sys/class/mmc_host/mmc0/mmc0:0001
```

The actual device suffix can differ. Also inspect the preload environment: running the probe through an old shim can simply report that shim's incorrect values. Store results privately. This probe reads attributes; it does not derive an expected identity from an arbitrary clone or recover a profile from the retail model name.

If the expected identity is still unknown, the historical investigation used a process core and the unmodified vendor check under emulation. That analysis was specific to the captured firmware; no universal profile-extraction tool is included.

## 3. Build a profile-specific shim

Make `local/card.json` from `profiles/card.example.json` and fill it with your own verified application-visible values. `local/` and `build/` are ignored by Git.

```sh
python tools/make_identity.py local/card.json build/card_identity.h
docker build --platform linux/arm/v7 -t pandora-arm-tools:local toolchain
docker run --rm --platform linux/arm/v7 --network none -v "$PWD:/work" -w /work pandora-arm-tools:local gcc -Wall -Wextra -Werror -shared -fPIC -O2 -Ibuild -o build/cardspoof_kernel.so src/cardspoof.c -ldl
docker run --rm --platform linux/arm/v7 --network none -v "$PWD:/work" -w /work pandora-arm-tools:local gcc -Wall -Wextra -Werror -O2 -o build/cardprobe src/cardprobe.c
```

These shell examples use POSIX quoting; in PowerShell, use `-v "${PWD}:/work"`. The Docker image is an old compatibility toolchain for the observed firmware. The resulting shared library embeds the identity and must remain private. Do not substitute a modern ARM compiler without checking its glibc requirements against the target.

The shim intercepts read-only `fopen`/`fopen64` calls for the four MMC attributes. All other file accesses use the original C-library functions. It logs to `/mnt/udisk/log/cardspoof_kernel.txt`; those logs contain card-specific values.

## 4. Patch the init flow and rebuild P2 locally

```sh
python tools/patch_init.py local/rootfs/usr/retrogame/myinit build/myinit
python tools/build_p2.py local/p2-original.squashfs build/myinit build/cardspoof_kernel.so build/p2-unlock.squashfs
```

The patch adds FAT32 mounting, optional `sdcard/` and database bind mounts, a P3 `autorun.sh` hook, and `LD_PRELOAD=/usr/lib/cardspoof.so`. It retains the vendor's menu → game → return-to-menu loop. The builder installs the supplied shim into the rootfs; it does not silently pick up an obsolete library from an earlier experiment.

The SquashFS tools handle the vendor's extra directory-entry and basic-file-inode fields. A stock `mksquashfs` invocation is not a drop-in replacement for this format. The builder writes a new local file only.

## 5. Prepare the replacement layout and populate P3

Use the [documented layout](hardware.md) when assembling a replacement image. Preserve the first 12 MiB of the original image, including P1 and reserved authentication data; update only the MBR entries that locate the enlarged P2 slot and P3. Place the rebuilt P2 at sector 24,576 and create the FAT32 partition at sector 1,073,152. Its final sector must be inside the actual replacement card.

The historical build used 512-byte sectors, 32 KiB FAT32 clusters, two FATs, and a data region aligned to 4 MiB. This repository deliberately does not choose a Windows disk number or flash a physical device. Use an image/partitioning tool you can verify against your actual target.

P3 needs the original resources and settings from your own backup:

```text
PANDORA/
  autorun.sh
  cardspoof_kernel.so
  unlock.marker
  unlock.sectors
  games.db
  config.bin, configknl.bin, configknl.def.bin, ...
  lang
  rcp_roms
  dx.en.1280x720/                 (and the other original language skins)
  saves/
  sdcard/                        (contents of the original roms filesystem)
    movies/
    nvram/
    roms.../
```

Copy `runtime/autorun.sh` to P3. Put the literal line `pandora-9s-unlock-v1` in `unlock.marker`, and your replacement card's exact count of 512-byte sectors in `unlock.sectors`. Copy the compiled library as `cardspoof_kernel.so`.

At boot the public autorun checks that capacity and marker, then temporarily bind-mounts the P3 library over `/usr/lib/cardspoof.so`. It writes `log/UNLOCK_STATUS.txt`. The bind disappears at power-off and is reapplied at the next boot. No boot/system partition is rewritten by this autorun.

The original deployed recovery package uses its earlier marker and diagnostic autorun instead. Do not mix the public marker names with that exact private package; its own README describes the matching files.

## 6. Verify, then change the catalog

Boot the replacement, check that the menu remains running, launch a game, and return to the menu. Only then apply [catalog cleanup and sorting](catalog.md). Back up and reset recent-game history whenever list membership or order changes. Otherwise the initial Recent category can dereference obsolete entries and restart the menu.

If boot still fails, read [validation and troubleshooting](validation.md). An apparently correct identity file alone does not prove the shim was loaded, the reserved data matches, or the expected kernel-visible values are correct.
