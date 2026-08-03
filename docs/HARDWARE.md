# Hardware - Control de Audio Grass Valley XCU via Arduino + W5500 + MCP4728

## Descripción General

Sistema de control de ganancia de audio para 32 cámaras Grass Valley.
La Raspberry Pi ejecuta la GUI y se comunica via TCP/Ethernet con 2 Arduino Nano Every,
cada uno controlando 8 MCP4728 DAC (16 cámaras x 2 micrófonos).

## Componentes Necesarios

- 2x Arduino Nano Every (ATmega4809)
- 2x Módulo W5500 Ethernet
- 2x TCA9548A (multiplexor I2C de 8 canales, uno por nodo Arduino)
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
        │       │ I2C (A4=SDA, A5=SCL) → TCA9548A (0x70)
        │       │       ├── Canal 0 → MCP4728 (0x60) → CAM 1-2
        │       │       ├── Canal 1 → MCP4728 (0x60) → CAM 3-4
        │       │       ├── Canal 2 → MCP4728 (0x60) → CAM 5-6
        │       │       ├── Canal 3 → MCP4728 (0x60) → CAM 7-8
        │       │       ├── Canal 4 → MCP4728 (0x60) → CAM 9-10
        │       │       ├── Canal 5 → MCP4728 (0x60) → CAM 11-12
        │       │       ├── Canal 6 → MCP4728 (0x60) → CAM 13-14
        │       │       └── Canal 7 → MCP4728 (0x60) → CAM 15-16
        │
        └── Arduino Nano Every B + W5500 (192.168.10.12:5000)
                │ (misma configuración I2C/SPI) → TCA9548A (0x70)
                ├── Canal 0-6 → MCP4728 (0x60) → CAM 17-30
                └── Canal 7 → MCP4728 (0x60) → CAM 31-32
```

Todos los MCP4728 permanecen en su dirección de fábrica `0x60`; el
TCA9548A los aísla en "sub-buses" independientes seleccionando un
canal a la vez antes de cada transacción I2C.

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

### I2C (TCA9548A → MCP4728 DAC)
- A4 = SDA
- A5 = SCL

El bus I2C del Arduino conecta únicamente al TCA9548A (SD/SC "upstream").
Cada uno de los 8 MCP4728 se conecta a un canal distinto del TCA9548A
(SD0/SC0 … SD7/SC7 "downstream"), todos a la dirección `0x60`.

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

⚠️ IMPORTANTE: El TCA9548A usado (400kHz, 1.8V) debe alimentarse según su
VCC lógico. Si el Arduino trabaja a 5V y el mux es de 1.8V, hay que
confirmar que la breakout board incluya traductores de nivel en las
líneas SDA/SCL (la mayoría de las boards TCA9548A sí los incluyen);
si no, usar una versión de mux compatible con 5V o añadir level shifters.

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

## Direccionamiento I2C: TCA9548A + MCP4728

Reprogramar la dirección de cada MCP4728 requiere una secuencia especial
("General Call Address Write") con timing preciso sobre el pin LDAC, que
no suele estar accesible en las breakout boards. Para evitar ese problema,
todos los MCP4728 se dejan en su dirección de fábrica `0x60` y se aíslan
en canales separados de un multiplexor **TCA9548A** (dirección `0x70`).

| Chip (canal TCA9548A) | Dirección MCP4728 | Cámaras |
|------|-----------|---------|
| 0 | 0x60 | CAM 1-2 |
| 1 | 0x60 | CAM 3-4 |
| 2 | 0x60 | CAM 5-6 |
| 3 | 0x60 | CAM 7-8 |
| 4 | 0x60 | CAM 9-10 |
| 5 | 0x60 | CAM 11-12 |
| 6 | 0x60 | CAM 13-14 |
| 7 | 0x60 | CAM 15-16 |

Antes de cada transacción I2C con un MCP4728, el firmware escribe un byte
de selección de canal al TCA9548A (`1 << canal`), de forma que solo ese
MCP4728 queda "visible" en el bus durante la transacción.

## Pineado Completo TCA9548A (por nodo Arduino)

Cada nodo (Arduino A y Arduino B) lleva su propio TCA9548A. El pineado es
idéntico en ambos nodos.

### TCA9548A ↔ Arduino Nano Every (lado "upstream")

| Pin TCA9548A | Conexión | Notas |
|---|---|---|
| VCC | Arduino 5V | Ver nota de compatibilidad de voltaje abajo |
| GND | GND común | Compartido con Arduino, MCP4728 y XCUs |
| SDA | Arduino A4 | Bus I2C "upstream" |
| SCL | Arduino A5 | Bus I2C "upstream" |
| A0 | GND | Fija bit 0 de dirección → dirección final `0x70` |
| A1 | GND | Fija bit 1 de dirección |
| A2 | GND | Fija bit 2 de dirección |
| RESET | VCC (o pull-up) | Activo en bajo; dejar en alto en operación normal |

### TCA9548A ↔ MCP4728 (lado "downstream", 1 canal por chip)

| Canal TCA9548A | Pines TCA9548A | Conecta a | Cámaras |
|---|---|---|---|
| 0 | SD0 / SC0 | MCP4728 #0 SDA/SCL | CAM 1-2 (A/B) |
| 1 | SD1 / SC1 | MCP4728 #1 SDA/SCL | CAM 3-4 (A/B) |
| 2 | SD2 / SC2 | MCP4728 #2 SDA/SCL | CAM 5-6 (A/B) |
| 3 | SD3 / SC3 | MCP4728 #3 SDA/SCL | CAM 7-8 (A/B) |
| 4 | SD4 / SC4 | MCP4728 #4 SDA/SCL | CAM 9-10 (A/B) |
| 5 | SD5 / SC5 | MCP4728 #5 SDA/SCL | CAM 11-12 (A/B) |
| 6 | SD6 / SC6 | MCP4728 #6 SDA/SCL | CAM 13-14 (A/B) |
| 7 | SD7 / SC7 | MCP4728 #7 SDA/SCL | CAM 15-16 (A/B) |

(Nodo B repite la misma tabla para sus 8 chips, cubriendo CAM 17-32.)

### Cada MCP4728 individual

| Pin MCP4728 | Conexión |
|---|---|
| VDD | 5V (mismo riel que alimenta el TCA9548A y el Arduino) |
| GND | GND común |
| SDA | SDx correspondiente del TCA9548A (ver tabla de canales) |
| SCL | SCx correspondiente del TCA9548A (ver tabla de canales) |
| LDAC | GND (atado a bajo permanentemente, para que cada `Multi-Write` se aplique de inmediato) |
| VOUT A/B/C/D | Ver `docs/PIN_MAPPING.md` para el mapeo a Mic 1/Mic 2 de cada cámara |

⚠️ **Compatibilidad de voltaje**: el Arduino Nano Every trabaja a lógica de
5V. Si tu breakout del TCA9548A es de 400kHz/1.8V, confirma en su datasheet
el rango de VCC soportado (la mayoría de los TCA9548A aceptan VCC de
1.65V a 5.5V, por lo que alimentarlo a 5V suele ser válido). Si tu board en
particular limita VCC a 1.8V, necesitarás traductores de nivel adicionales
entre el Arduino (5V) y el mux, o alimentar todo el tramo I2C a 3.3V si el
Arduino y los MCP4728 lo soportan.

## Notas de Seguridad

1. **NO conectar Pin 7 (5V OCP) de la XCU** al circuito DAC
2. **Alimentar MCP4728 con 5V** (no 3.3V) para alcanzar el rango completo 0-4.3V
3. **GND común** entre Raspberry Pi, todos los MCP4728 y todas las XCU (Pin 15)
4. **Probar con una sola XCU** antes de conectar todas
5. Las XCU deben estar **encendidas** durante las pruebas (necesitan recibir la tensión)
6. **Verificar con multímetro** que la salida DAC genera el voltaje correcto antes de conectar a la XCU
