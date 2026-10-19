/*
 * Read physical SD CID/CSD/OCR/SCR registers using an ESP32 and SdFat 2.3.1.
 * No filesystem is mounted and no card data is written or erased.
 * The output belongs to your private recovery material, not a public issue.
 * See ../README.md for wiring and the physical-vs-application identity caveat.
 */
#include <SPI.h>
#include <SdFat.h>

// Classic ESP32 VSPI defaults. Override at build time or edit for your board.
#ifndef SD_CS
#define SD_CS 5
#endif
#ifndef SD_SCK
#define SD_SCK 18
#endif
#ifndef SD_MISO
#define SD_MISO 19
#endif
#ifndef SD_MOSI
#define SD_MOSI 23
#endif
#ifndef SD_CLOCK_MHZ
#define SD_CLOCK_MHZ 4
#endif

SdSpiCard card;

static void printHex(const uint8_t* bytes, size_t length) {
  for (size_t i = 0; i < length; ++i) {
    if (bytes[i] < 0x10) Serial.print('0');
    Serial.print(bytes[i], HEX);
  }
}

static void printRegister(const char* label, const void* bytes, size_t length) {
  Serial.print(label);
  Serial.print(' ');
  printHex(static_cast<const uint8_t*>(bytes), length);
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println();
  Serial.println("=== Physical SD card identity (read only) ===");
  SPI.begin(SD_SCK, SD_MISO, SD_MOSI, SD_CS);
  if (!card.begin(SdSpiConfig(SD_CS, SHARED_SPI, SD_SCK_MHZ(SD_CLOCK_MHZ), &SPI))) {
    Serial.println("SD init FAILED: check power, wiring and pins; try a lower SPI clock.");
    return;
  }

  cid_t cid = {};
  csd_t csd = {};
  scr_t scr = {};
  uint32_t ocr = 0;
  static_assert(sizeof(cid) == 16, "Unexpected CID structure size");
  static_assert(sizeof(csd) == 16, "Unexpected CSD structure size");
  static_assert(sizeof(scr) == 8, "Unexpected SCR structure size");

  if (card.readCID(&cid)) {
    printRegister("CID", &cid, sizeof(cid));
    const uint8_t* raw = reinterpret_cast<const uint8_t*>(&cid);
    printRegister("MID", raw, 1);
    Serial.print("OID ");
    Serial.write(raw + 1, 2);
    Serial.println();
    Serial.print("PNM ");
    Serial.write(raw + 3, 5);
    Serial.println();
    printRegister("PSN", raw + 9, 4);
    Serial.print("SERIAL 0x");
    printHex(raw + 9, 4);
    Serial.println();
  } else {
    Serial.println("CID read failed; decoded CID fields skipped.");
  }

  if (card.readCSD(&csd)) printRegister("CSD", &csd, sizeof(csd));
  else Serial.println("CSD read failed.");

  if (card.readOCR(&ocr)) {
    const uint8_t bytes[] = {
      static_cast<uint8_t>(ocr >> 24), static_cast<uint8_t>(ocr >> 16),
      static_cast<uint8_t>(ocr >> 8), static_cast<uint8_t>(ocr)
    };
    printRegister("OCR", bytes, sizeof(bytes));
  } else {
    Serial.println("OCR read failed.");
  }

  if (card.readSCR(&scr)) printRegister("SCR", &scr, sizeof(scr));
  else Serial.println("SCR read failed.");

  Serial.println("=== Done. Keep this output private; reset to read again. ===");
}

void loop() {}
