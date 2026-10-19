# ESP32 physical SD-card identity reader

Open [`read_card_identity/read_card_identity.ino`](read_card_identity/read_card_identity.ino) in Arduino IDE. This is the project's earlier ESP32 reader adapted for current SdFat APIs and English output, with SCR reading added. It reads **CID, CSD, OCR, and SCR**, and prints the manufacturer, OEM/product fields, and physical serial number.

It initializes the card over SPI without mounting a filesystem. It does not open files, format the card, erase blocks, or write card data. Consequently it can inspect registers even if the card uses a filesystem the Arduino cannot mount.

## Hardware and wiring

Use a classic ESP32 development board and a microSD socket/breakout compatible with **3.3 V power and logic**. A bare microSD card must not be connected to 5 V. Check your breakout's regulator/level-shifter requirements rather than assuming every module has the same VCC input.

| SD socket signal | Classic ESP32 default | Earlier LilyGO VGA32 experiment |
|---|---:|---:|
| CS / DAT3 | GPIO 5 | GPIO 13 |
| SCK / CLK | GPIO 18 | GPIO 14 |
| MISO / DAT0 | GPIO 19 | GPIO 2 |
| MOSI / CMD | GPIO 23 | GPIO 12 |
| GND | GND | GND |
| Bare card supply | 3.3 V | 3.3 V |

The VGA32 column records the pin mapping used in the earlier MicroPython investigation. It is not the default Arduino mapping and has not been retested with this revised sketch. Change the four macros near the top of the sketch if using it. Pins and boot-strapping behavior vary by board; the default mapping does not apply unchanged to ESP32-C3/S3 boards.

## Arduino IDE

1. Install **esp32 by Espressif Systems** through Boards Manager and select the appropriate board (the compile check used **ESP32 Dev Module**).
2. Install **SdFat by Bill Greiman**, version **2.3.1**, through Library Manager. Select the upstream library, rather than accidentally compiling against a similarly named fork.
3. Wire the unpowered reader, insert the card, and connect the ESP32 by USB.
4. Compile/upload this sketch to the ESP32. Open Serial Monitor at **115200 baud**, then press Reset to read again if needed.
5. Save the output privately. Power off before moving the card back to the console.

The default SPI clock is 4 MHz. If initialization fails, first verify power and all four signals; try `SD_CLOCK_MHZ 1` and short wires. A failed CID read does not print uninitialized manufacturer or serial fields.

## Optional CLI compile

With Arduino CLI, the ESP32 core and SdFat installed:

```sh
arduino-cli compile --fqbn esp32:esp32:esp32 arduino/read_card_identity
```

The published sketch was compile-checked with **Arduino CLI 1.5.1, ESP32 core 3.3.11, and upstream SdFat 2.3.1**. This revision has not been uploaded to a connected board or retested against the owner's original card; compilation is not a new hardware confirmation. No actual card output is included in the public repository.

## Output format

The output labels are `CID`, `CSD`, `SCR`, `OCR`, `MID`, `OID`, `PNM`, `PSN`, and `SERIAL`. Hex output retains leading zeroes: CID/CSD contain 32 hexadecimal digits, SCR 16, OCR/PSN eight, and SERIAL is `0x` followed by eight digits. No real card values are embedded in the sketch.

## Physical values are not automatically an unlock profile

This reader reports the physical card's SPI registers. In the tested Pandora firmware, the vendor kernel presented different **application-visible** identity values. Feeding physical SPI values directly to the preload shim did not unlock the clone.

Use the Arduino output as private identification and diagnostic evidence. Compare it with values observed through the working vendor environment; do not silently substitute it for `identity/application-visible.json`. OCR is a separate register and is not a replacement for SCR. See [the unlock investigation](../docs/unlock.md#2-distinguish-physical-identity-from-application-identity).

Dependency: [Bill Greiman's SdFat](https://github.com/greiman/SdFat), which retains its own MIT license and is installed separately.
