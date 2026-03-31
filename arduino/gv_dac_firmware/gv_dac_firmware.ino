/*
 * Grass Valley XCU - DAC Controller Firmware
 * Arduino Nano Every + W5500 Ethernet + 8x MCP4728 I2C DAC
 *
 * Controls audio gain levels via MCP4728 DAC chips for Grass Valley camera XCUs.
 * Receives commands from Raspberry Pi via TCP socket.
 *
 * Hardware:
 *   - Arduino Nano Every (ATmega4809)
 *   - W5500 Ethernet module (SPI: D10=CS, D11=MOSI, D12=MISO, D13=SCK)
 *   - 8x MCP4728 DAC (I2C: A4=SDA, A5=SCL, addresses 0x60-0x67)
 *
 * Protocol (TCP port 5000):
 *   SET <chip> <channel> <value>  - Set DAC output (chip:0-7, ch:0-3, value:0-4095)
 *   SCAN                          - List detected I2C DAC chips
 *   PING                          - Connection test
 *   ID                            - Firmware identification
 *
 * Configuration:
 *   Change IP_ADDR and MAC below for each Arduino node.
 *   Node A: 192.168.10.11, Node B: 192.168.10.12, etc.
 */

#include <SPI.h>
#include <Ethernet.h>
#include <Wire.h>

// ============================================================
// CONFIGURATION - Change these for each Arduino node
// ============================================================

// MAC address (must be unique per node)
byte mac[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x01 };  // Node A: 0x01, Node B: 0x02

// Static IP address
IPAddress ip(192, 168, 10, 11);  // Node A: .11, Node B: .12

// TCP server port
const uint16_t TCP_PORT = 5000;

// ============================================================
// MCP4728 Configuration
// ============================================================

// MCP4728 base I2C address
const uint8_t MCP4728_BASE_ADDR = 0x60;
const uint8_t NUM_DAC_CHIPS = 8;

// MCP4728 Multi-Write command for single channel
// Command: 0x40 | (channel << 1)
// Data: [VREF:1][PD1:0][PD0:0][Gx:0][D11:D8] [D7:D0]
const uint8_t MCP4728_CMD_WRITE = 0x40;

// Track which chips are detected
bool dacDetected[NUM_DAC_CHIPS];

// ============================================================
// TCP Server
// ============================================================

EthernetServer server(TCP_PORT);
const uint8_t CMD_BUF_SIZE = 64;

// ============================================================
// MCP4728 Functions (direct Wire.h, no external library)
// ============================================================

void mcp4728_write_channel(uint8_t chipIndex, uint8_t channel, uint16_t value) {
  if (chipIndex >= NUM_DAC_CHIPS || !dacDetected[chipIndex]) return;
  if (channel > 3) return;
  if (value > 4095) value = 4095;

  uint8_t addr = MCP4728_BASE_ADDR + chipIndex;

  // Multi-Write command: write single channel
  // Byte 1: 0x40 | (channel << 1) | UDAC(0)
  // Byte 2: VREF(0) | PD1(0) | PD0(0) | Gx(0) | D11-D8
  // Byte 3: D7-D0
  uint8_t cmd = MCP4728_CMD_WRITE | (channel << 1);
  uint8_t msb = (value >> 8) & 0x0F;  // Upper 4 bits + VREF=0, PD=00, Gx=0
  uint8_t lsb = value & 0xFF;          // Lower 8 bits

  Wire.beginTransmission(addr);
  Wire.write(cmd);
  Wire.write(msb);
  Wire.write(lsb);
  Wire.endTransmission();
}

void scanI2CDevices() {
  for (uint8_t i = 0; i < NUM_DAC_CHIPS; i++) {
    uint8_t addr = MCP4728_BASE_ADDR + i;
    Wire.beginTransmission(addr);
    dacDetected[i] = (Wire.endTransmission() == 0);
  }
}

// ============================================================
// Command Processing
// ============================================================

void processCommand(EthernetClient &client, char *cmd) {
  // PING
  if (strcmp(cmd, "PING") == 0) {
    client.println(F("PONG"));
    return;
  }

  // ID
  if (strcmp(cmd, "ID") == 0) {
    client.println(F("GV-DAC-CTRL v1.0"));
    return;
  }

  // SCAN
  if (strcmp(cmd, "SCAN") == 0) {
    scanI2CDevices();
    client.print(F("CHIPS "));
    bool first = true;
    for (uint8_t i = 0; i < NUM_DAC_CHIPS; i++) {
      if (dacDetected[i]) {
        if (!first) client.print(F(","));
        client.print(F("0x"));
        if (MCP4728_BASE_ADDR + i < 0x10) client.print(F("0"));
        client.print(MCP4728_BASE_ADDR + i, HEX);
        first = false;
      }
    }
    if (first) client.print(F("none"));
    client.println();
    return;
  }

  // SET <chip> <channel> <value>
  if (strncmp(cmd, "SET ", 4) == 0) {
    int chip, channel, value;
    if (sscanf(cmd + 4, "%d %d %d", &chip, &channel, &value) == 3) {
      if (chip < 0 || chip >= NUM_DAC_CHIPS) {
        client.println(F("ERR chip 0-7"));
        return;
      }
      if (channel < 0 || channel > 3) {
        client.println(F("ERR channel 0-3"));
        return;
      }
      if (value < 0 || value > 4095) {
        client.println(F("ERR value 0-4095"));
        return;
      }
      if (!dacDetected[chip]) {
        client.println(F("ERR chip not found"));
        return;
      }

      mcp4728_write_channel(chip, channel, value);
      client.println(F("OK"));
    } else {
      client.println(F("ERR SET chip ch val"));
    }
    return;
  }

  client.println(F("ERR unknown cmd"));
}

// ============================================================
// Setup & Loop
// ============================================================

void setup() {
  // Initialize I2C
  Wire.begin();

  // Scan for MCP4728 chips
  scanI2CDevices();

  // Initialize Ethernet with static IP
  Ethernet.begin(mac, ip);

  // Check for Ethernet hardware
  if (Ethernet.hardwareStatus() == EthernetNoHardware) {
    // Blink LED to indicate error (pin 13)
    pinMode(LED_BUILTIN, OUTPUT);
    while (true) {
      digitalWrite(LED_BUILTIN, HIGH);
      delay(200);
      digitalWrite(LED_BUILTIN, LOW);
      delay(200);
    }
  }

  // Start TCP server
  server.begin();

  // LED on = ready
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
}

void loop() {
  EthernetClient client = server.available();

  if (client) {
    char cmdBuf[CMD_BUF_SIZE];
    uint8_t cmdPos = 0;

    while (client.connected()) {
      if (client.available()) {
        char c = client.read();

        if (c == '\n' || c == '\r') {
          if (cmdPos > 0) {
            cmdBuf[cmdPos] = '\0';
            processCommand(client, cmdBuf);
            cmdPos = 0;
          }
        } else if (cmdPos < CMD_BUF_SIZE - 1) {
          cmdBuf[cmdPos++] = c;
        }
      }
    }
    client.stop();
  }
}
