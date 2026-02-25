# Hardware - Control de Audio Grass Valley XCU via DAC MCP4728

## Descripción General

Sistema de control de ganancia de audio para 16 cámaras Grass Valley mediante DAC I2C.
Cada XCU acepta una tensión analógica de 0 a 5V en su conector SubD-15 (Signalling Connector)
para controlar el nivel de audio de cada micrófono.

## Componentes Necesarios

| Cantidad | Componente | Especificación |
|----------|------------|----------------|
| 8 | MCP4728 (módulo breakout) | DAC I2C, 4 canales, 12 bits, salida 0-5V |
| 1 | Raspberry Pi 4 | Con Raspberry Pi OS |
| 16 | Conectores SubD-15 hembra | Uno por XCU |
| - | Cable I2C | SDA + SCL + VCC + GND |
| - | Cable multipar | Para conexión DAC → SubD-15 |

## Esquema General

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RASPBERRY PI 4                               │
│                                                                     │
│    GPIO 2 (SDA) ───────┬──── Bus I2C SDA                          │
│    GPIO 3 (SCL) ───────┼──── Bus I2C SCL                          │
│    3.3V         ───────┼──── VCC (alimentación lógica I2C)        │
│    GND          ───────┼──── GND común                            │
│                        │                                           │
└────────────────────────┼───────────────────────────────────────────┘
                         │
          Bus I2C (SDA + SCL + VCC + GND)
                         │
     ┌───────────────────┼───────────────────────────────┐
     │                   │                               │
     │    ┌──────────────┴──────────────┐                │
     │    │  Todos los MCP4728 comparten │                │
     │    │  el mismo bus I2C            │                │
     │    └──────────────┬──────────────┘                │
     │                   │                               │
┌────▼────┐  ┌──────────▼──────┐           ┌────────────▼───────┐
│MCP4728  │  │MCP4728          │    ...     │MCP4728             │
│Chip 0   │  │Chip 1           │           │Chip 7              │
│0x60     │  │0x61             │           │0x67                │
│         │  │                 │           │                    │
│ A → CAM1│  │ A → CAM3 Mic1  │           │ A → CAM15 Mic1    │
│   Mic1  │  │ B → CAM3 Mic2  │           │ B → CAM15 Mic2    │
│ B → CAM1│  │ C → CAM4 Mic1  │           │ C → CAM16 Mic1    │
│   Mic2  │  │ D → CAM4 Mic2  │           │ D → CAM16 Mic2    │
│ C → CAM2│  │                 │           │                    │
│   Mic1  │  └────────┬────────┘           └─────────┬──────────┘
│ D → CAM2│           │                              │
│   Mic2  │           │                              │
└────┬────┘           │                              │
     │                │                              │
     │    Salidas analógicas 0-5V                    │
     │                │                              │
     ▼                ▼                              ▼
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

## Detalle del Bus I2C

```
Raspberry Pi                MCP4728 ×8 (en paralelo)
                    ┌──────────────────────────────────────────────┐
  GPIO 2 (SDA) ────┤── SDA Chip0 ── SDA Chip1 ── ... ── SDA Chip7│
  GPIO 3 (SCL) ────┤── SCL Chip0 ── SCL Chip1 ── ... ── SCL Chip7│
  3.3V / 5V    ────┤── VDD Chip0 ── VDD Chip1 ── ... ── VDD Chip7│
  GND          ────┤── GND Chip0 ── GND Chip1 ── ... ── GND Chip7│
                    └──────────────────────────────────────────────┘

  ⚠️ IMPORTANTE: VDD del MCP4728 determina el voltaje máximo de salida.
     Si VDD = 5V → salida máxima = 5V (necesario para alcanzar 4.3V)
     Si VDD = 3.3V → salida máxima = 3.3V (INSUFICIENTE)

     Alimentar los MCP4728 con 5V desde la Raspberry Pi (pin 2 o 4).
     El bus I2C funciona a 3.3V pero los MCP4728 son compatibles.
```

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
