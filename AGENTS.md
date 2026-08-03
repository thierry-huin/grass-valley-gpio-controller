# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a Python-based Raspberry Pi DAC controller with a Tkinter GUI for controlling audio gain levels on Grass Valley camera XCUs. It uses MCP4728 I2C DAC chips to generate precise analog voltages (0-5V) that control microphone sensitivity on the XCU's SubD-15 Signalling Connector.

The application runs in two modes:
- **Production mode**: On a Raspberry Pi with I2C/DAC hardware
- **Demo mode**: On any system without DAC hardware (for development/testing)

The interface is in Spanish.

## Essential Commands

### Running the Application

**On Raspberry Pi (production):**
```bash
python3 src/gv_dac_controller.py
```

**Development/Demo mode (any system):**
```bash
python3 src/gv_dac_controller.py
```

### Installation

```bash
pip3 install -r requirements.txt
```

### Testing

There are currently no automated tests. The `tests/` directory exists but is empty. When adding tests, consider:
- Mocking MCP4728/I2C for testing on non-Raspberry Pi systems
- Testing both I2C_AVAILABLE=True and I2C_AVAILABLE=False code paths
- Testing UI state management without requiring X11/display

## Architecture

### Two Runtime Modes (two separate scripts)

**`src/gv_dac_controller.py` — main/production app (32 cameras)**
- Raspberry Pi (Tkinter GUI) talks TCP to 2× Arduino Nano Every + W5500 nodes (`ArduinoNode` class, `config/nodes.json`)
- Each Arduino node runs `arduino/gv_dac_firmware/gv_dac_firmware.ino`, which owns the I2C bus locally
- On each node's I2C bus: 1× **TCA9548A** mux (address `0x70`, fixed via A0-A2 tied low) fans out to 8× MCP4728, **all left at the factory default address `0x60`** and isolated per TCA9548A channel (0-7)
- The Pi never talks I2C directly — it only sends `SET <chip> <channel> <value>` over TCP, where `chip` is the **TCA9548A channel index (0-7)**, not an I2C address
- Total: 2 nodes × 8 chips × 4 channels = 64 analog outputs for 32 cameras × 2 microphones
- See `docs/HARDWARE.md` for the full TCA9548A pinout

**`src/gv_dac_controller_i2c.py` — legacy direct-I2C app (16 cameras)**
- Runs directly on a Raspberry Pi's own I2C bus (no Arduino, no TCP), using `adafruit_mcp4728` via `board`/`busio`
- Still assumes 8× MCP4728 reprogrammed to unique addresses `0x60`-`0x67` on the same bus (`DAC_ADDRESSES` list) — it does **not** use a TCA9548A mux
- Kept for reference/smaller deployments; if the same addressing problem applies, it should get the same TCA9548A treatment as the Arduino firmware before relying on reprogrammed addresses
- Total: 8 chips × 4 channels = 32 analog outputs for 16 cameras × 2 microphones

Both scripts follow a single-class architecture pattern (`DACControllerApp`) with 0-5V output mapped to 8 gain levels (-22 to -64 dBu).

### Key Design Patterns

**Graceful Degradation (`gv_dac_controller_i2c.py` only):**
```python
try:
    import adafruit_mcp4728
    import board
    import busio
    I2C_AVAILABLE = True
except (ImportError, RuntimeError, NotImplementedError):
    I2C_AVAILABLE = False
```

All DAC operations in that script are wrapped in `if I2C_AVAILABLE:` checks. `gv_dac_controller.py` instead checks `node.connected` before sending TCP commands to each Arduino node.

**Hardware Abstraction:**
- `gv_dac_controller.py`: `_apply_gain_hardware(camera_name, mike_name, level)` looks up `(node, chip_index, channel)` and calls `node.set_dac(chip_index, channel, dac_value)`, which sends the TCP `SET` command
- `gv_dac_controller_i2c.py`: `_apply_gain_hardware(camera_name, mike_name, level)` writes directly to the `adafruit_mcp4728` object at the mapped chip/channel

**State Management:**
- `mike_states` dict is the source of truth: `{(camera_name, mike_name): gain_level}`
- States saved to `~/camera_states_gv_config.json`
- Camera names saved to `~/camera_names_gv_config.json`
- States are restored from file on startup

**Gain Presets (8 levels):**
```python
GAIN_PRESETS = {
    '-22 dBu': {'voltage': 4.3, 'dac_value': 3522},
    '-28 dBu': {'voltage': 3.7, 'dac_value': 3031},
    '-34 dBu': {'voltage': 3.1, 'dac_value': 2539},
    '-40 dBu': {'voltage': 2.5, 'dac_value': 2048},
    '-46 dBu': {'voltage': 1.9, 'dac_value': 1556},
    '-52 dBu': {'voltage': 1.3, 'dac_value': 1065},
    '-58 dBu': {'voltage': 0.7, 'dac_value': 573},
    '-64 dBu': {'voltage': 0.0, 'dac_value': 0},
}
```

### Dependencies

**Python Standard Library:**
- `tkinter`: GUI framework
- `sys`, `json`, `os`, `time`

**External Dependencies:**
- `adafruit-circuitpython-mcp4728`: MCP4728 DAC control
- `adafruit-blinka`: CircuitPython compatibility on Raspberry Pi

## Important Constraints

### Hardware
- MCP4728 must be powered with **5V** (not 3.3V) to output up to 4.3V
- SubD-15 Pin 7 (5V from XCU) must **NOT** be connected to DAC circuit
- All GND must be common (Raspberry Pi + DACs + XCUs)
- MCP4728 chips are unreliable to reprogram to unique addresses (requires a
  precisely-timed LDAC sequence); instead all chips stay at default address
  0x60 and are isolated per-channel behind a TCA9548A I2C mux (address 0x70)
  on each Arduino node's I2C bus

### Code Considerations

**When modifying DAC operations:**
- Always maintain the `if I2C_AVAILABLE:` guard pattern
- Wrap DAC calls in try/except blocks
- DAC library expects 16-bit values; shift 12-bit values: `value << 4`

**When modifying the UI:**
- Interface text must remain in Spanish
- Active button color must be blue
- Maintain 4×4 grid layout for 16 cameras
- 8 buttons per microphone (one per gain level)
- Double-click camera name to edit

**Differences from Sony project (raspberry-pi-gpio-controller):**
- Uses DAC (MCP4728) instead of relay modules + MCP23017
- 8 gain levels instead of 5 attenuation levels
- No Fourth_Relay or hover logic (each mic has dedicated DAC channel)
- Gain expressed in dBu instead of dB
- Config files use `_gv_` suffix to avoid conflicts

## Development Notes

### No Build System

Run directly as Python script. No build system beyond `requirements.txt`.

### Project History

Based on the Sony HDCU-3500 relay controller project (`raspberry-pi-gpio-controller`).
Adapted for Grass Valley XCU with analog voltage control instead of digital relay control.
Created by Thierry Huin with assistance from Warp AI Agent.
