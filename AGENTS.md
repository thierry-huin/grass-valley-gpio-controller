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

### Single-File Application

The entire application lives in `src/gv_dac_controller.py`. It follows a single-class architecture pattern.

**Main Class: `DACControllerApp`**
- Controls 8× MCP4728 DAC chips via I2C (addresses 0x60-0x67)
- Each chip has 4 channels (A, B, C, D) controlling 2 cameras (2 mics each)
- Total: 32 analog output channels for 16 cameras × 2 microphones
- Output voltage range: 0-5V mapped to 8 gain levels (-22 to -64 dBu)

### Key Design Patterns

**Graceful Degradation:**
```python
try:
    import adafruit_mcp4728
    import board
    import busio
    I2C_AVAILABLE = True
except (ImportError, RuntimeError, NotImplementedError):
    I2C_AVAILABLE = False
```

All DAC operations are wrapped in `if I2C_AVAILABLE:` checks.

**Hardware Abstraction:**
- `_set_dac_output(chip_index, channel, dac_value)` - Low-level DAC write
- `_apply_gain_hardware(camera_name, mike_name, level)` - Maps camera/mic to DAC chip/channel
- `set_microphone_gain()` - High-level: hardware + state + UI update

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
- MCP4728 chips come with default address 0x60; must be reprogrammed individually

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
Created with assistance from Warp AI Agent.
