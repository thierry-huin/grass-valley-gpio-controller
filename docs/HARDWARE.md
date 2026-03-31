# Hardware - Control de Audio Grass Valley XCU via Arduino + W5500 + MCP4728

## Descripción General

Sistema de control de ganancia de audio para 32 cámaras Grass Valley.
La Raspberry Pi ejecuta la GUI y se comunica via TCP/Ethernet con 2 Arduino Nano Every,
cada uno controlando 8 MCP4728 DAC (16 cámaras x 2 micrófonos).

## Componentes Necesarios

- 2x Arduino Nano Every (ATmega4809)
- 2x Módulo W5500 Ethernet
- 16x MCP4728 (módulo breakout DAC I2C, 4 canales, 12 bits)
- 1x Raspberry Pi 5 con Raspberry Pi OS
- 1x Switch Ethernet (5 puertos mínimo)
- 32x Conectores SubD-15 hembra (uno por XCU)
- Cables Ethernet Cat5e/6

## Esquema General

```
Raspberry Pi 5 (GUI Tkinter)
│ eth0 (192.168.10.1)
│
└── Switch Ethernet dedicado (192.168.10.x)
        │
        ├── Arduino Nano Every A + W5500 (192.168.10.11:5000)
        │       │ SPI (D10,D11,D12,D13)
        │       │ I2C (A4=SDA, A5=SCL)
        │       ├── MCP4728 0x60 → CAM 1-2
        │       ├── MCP4728 0x61 → CAM 3-4
        │       ├── MCP4728 0x62 → CAM 5-6
        │       ├── MCP4728 0x63 → CAM 7-8
        │       ├── MCP4728 0x64 → CAM 9-10
        │       ├── MCP4728 0x65 → CAM 11-12
        │       ├── MCP4728 0x66 → CAM 13-14
        │       └── MCP4728 0x67 → CAM 15-16
        │
        └── Arduino Nano Every B + W5500 (192.168.10.12:5000)
                │ (misma configuración I2C/SPI)
                ├── MCP4728 0x60 → CAM 17-18
                ├── ... 
                └── MCP4728 0x67 → CAM 31-32
```

## Conexión por Cámara (SubD-15 Signalling Connector)

```
     Salida DAC                          XCU Grass Valley
     Canal A o C                         SubD-15 hembra
    ┌──────────┐                        ┌─────────────────┐
    │  VOUT A  ├────────────────────────┤ Pin 6  Audio 1  │
    │  (Mic 1) │                        │        level    │
    └──────────┘                        │                 │
                                        │                 │
     Salida DAC                         │                 │
     Canal B o D                        │                 │
    ┌──────────┐                        │                 │
    │  VOUT B  ├────────────────────────┤ Pin 14 Audio 2  │
    │  (Mic 2) │                        │        level    │
    └──────────┘                        │                 │
                                        │                 │
     GND común                          │                 │
    ┌──────────┐                        │                 │
    │   GND    ├────────────────────────┤ Pin 15 GND      │
    │          │                        │                 │
    └──────────┘                        │                 │
                                        │  Pin 7  5V (OCP)│ ← NO CONECTAR al DAC
                                        │                 │
                                        └─────────────────┘

    NOTA: Pin 7 (5V) es una SALIDA de la XCU para el panel OCP.
          NO conectar al DAC. El DAC se alimenta desde la Raspberry Pi.
```

## Pines Arduino Nano Every

### SPI (W5500 Ethernet)
- D10 = CS
- D11 = MOSI
- D12 = MISO
- D13 = SCK

### I2C (MCP4728 DAC)
- A4 = SDA
- A5 = SCL

SPI e I2C coexisten sin conflicto.

## Configuración de Red

- Red Ethernet dedicada (no usar la LAN del estudio)
- Raspberry Pi: 192.168.10.1
- Arduino A: 192.168.10.11 (MAC: DE:AD:BE:EF:00:01)
- Arduino B: 192.168.10.12 (MAC: DE:AD:BE:EF:00:02)
- Puerto TCP: 5000
- Switch: cualquier switch Ethernet no gestionado

⚠️ IMPORTANTE: VDD del MCP4728 debe ser 5V para alcanzar salida de 4.3V.
Alimentar los MCP4728 con 5V desde el Arduino (pin 5V).

## Tabla de Niveles de Ganancia

| Nivel dBu | Sensibilidad | Voltaje | Valor DAC (12-bit) |
|------------|-------------|---------|---------------------|
| -22 dBu (+12 dBu) | Máxima | 4.3V | 3522 |
| -28 dBu (+4 dBu) | | 3.7V | 3031 |
| -34 dBu (-2 dBu) | | 3.1V | 2539 |
| -40 dBu (-8 dBu) | Media | 2.5V | 2048 |
| -46 dBu (-14 dBu) | | 1.9V | 1556 |
| -52 dBu (-20 dBu) | | 1.3V | 1065 |
| -58 dBu (-26 dBu) | | 0.7V | 573 |
| -64 dBu (-32 dBu) | Mínima | 0.0V | 0 |

Fórmula: `valor_DAC = voltaje / 5.0 × 4096`

## Configuración de Direcciones I2C del MCP4728

El MCP4728 tiene una dirección base de 0x60. La dirección se puede modificar
mediante un comando I2C especial (General Call Address Write).

| Chip | Dirección | Cámaras |
|------|-----------|---------|
| 0 | 0x60 | CAM 1-2 |
| 1 | 0x61 | CAM 3-4 |
| 2 | 0x62 | CAM 5-6 |
| 3 | 0x63 | CAM 7-8 |
| 4 | 0x64 | CAM 9-10 |
| 5 | 0x65 | CAM 11-12 |
| 6 | 0x66 | CAM 13-14 |
| 7 | 0x67 | CAM 15-16 |

⚠️ **NOTA**: Todos los MCP4728 vienen de fábrica con dirección 0x60.
Hay que reprogramar la dirección de cada chip individualmente antes de
conectarlos todos al mismo bus. Esto se hace con el comando especial
"General Call Address Write" del MCP4728.

## Notas de Seguridad

1. **NO conectar Pin 7 (5V OCP) de la XCU** al circuito DAC
2. **Alimentar MCP4728 con 5V** (no 3.3V) para alcanzar el rango completo 0-4.3V
3. **GND común** entre Raspberry Pi, todos los MCP4728 y todas las XCU (Pin 15)
4. **Probar con una sola XCU** antes de conectar todas
5. Las XCU deben estar **encendidas** durante las pruebas (necesitan recibir la tensión)
6. **Verificar con multímetro** que la salida DAC genera el voltaje correcto antes de conectar a la XCU
