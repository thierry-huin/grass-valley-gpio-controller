# Pin Mapping - 8 MCP4728 DAC Architecture

## Overview
- **16 cámaras** Grass Valley con XCU
- **8 MCP4728** DAC chips I2C (4 canales cada uno)
- **32 canales** de salida analógica (16 cámaras × 2 micrófonos)
- **Conector**: SubD-15 (Signalling Connector) por XCU

## Mapeo Completo: DAC → Cámara

| Cámara | Mic 1 | Mic 2 | Chip MCP4728 | Dirección I2C |
|--------|-------|-------|--------------|---------------|
| CAM 1  | Ch A  | Ch B  | 0            | 0x60          |
| CAM 2  | Ch C  | Ch D  | 0            | 0x60          |
| CAM 3  | Ch A  | Ch B  | 1            | 0x61          |
| CAM 4  | Ch C  | Ch D  | 1            | 0x61          |
| CAM 5  | Ch A  | Ch B  | 2            | 0x62          |
| CAM 6  | Ch C  | Ch D  | 2            | 0x62          |
| CAM 7  | Ch A  | Ch B  | 3            | 0x63          |
| CAM 8  | Ch C  | Ch D  | 3            | 0x63          |
| CAM 9  | Ch A  | Ch B  | 4            | 0x64          |
| CAM 10 | Ch C  | Ch D  | 4            | 0x64          |
| CAM 11 | Ch A  | Ch B  | 5            | 0x65          |
| CAM 12 | Ch C  | Ch D  | 5            | 0x65          |
| CAM 13 | Ch A  | Ch B  | 6            | 0x66          |
| CAM 14 | Ch C  | Ch D  | 6            | 0x66          |
| CAM 15 | Ch A  | Ch B  | 7            | 0x67          |
| CAM 16 | Ch C  | Ch D  | 7            | 0x67          |

## Conexión SubD-15 por XCU

| Pin SubD-15 | Función | Conexión DAC |
|-------------|---------|-------------|
| 6  | Audio 1 level (0-5V) | VOUT canal A o C (Mic 1) |
| 14 | Audio 2 level (0-5V) | VOUT canal B o D (Mic 2) |
| 15 | GND | GND común |
| 7  | 5V (OCP) | **NO CONECTAR** |
| 1  | Preview output ext. | No usado |
| 2  | Call output ext. | No usado |
| 3  | ISO input ext. | No usado |
| 4  | On Air input ext. | No usado |
| 5  | Call input ext. | No usado |
| 8  | Housing | No usado |
| 9  | Preview output ext. return | No usado |
| 10 | Call output ext. return | No usado |
| 11 | ISO input ext. return | No usado |
| 12 | On Air input ext. return | No usado |
| 13 | Call input ext. return | No usado |

## Valores DAC por Nivel de Ganancia

| Nivel | Voltaje | Valor DAC 12-bit | Valor DAC 16-bit (librería) |
|-------|---------|------------------|-----------------------------|
| -22 dBu | 4.3V | 3522 | 56352 |
| -28 dBu | 3.7V | 3031 | 48496 |
| -34 dBu | 3.1V | 2539 | 40624 |
| -40 dBu | 2.5V | 2048 | 32768 |
| -46 dBu | 1.9V | 1556 | 24896 |
| -52 dBu | 1.3V | 1065 | 17040 |
| -58 dBu | 0.7V | 573  | 9168  |
| -64 dBu | 0.0V | 0    | 0     |

**Nota**: La librería `adafruit-circuitpython-mcp4728` espera valores de 16 bits.
El valor de 12 bits se desplaza 4 posiciones a la izquierda: `valor_16bit = valor_12bit << 4`
