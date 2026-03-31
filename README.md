# Grass Valley XCU - Control de Audio por DAC

Control de ganancia de audio para 16 cámaras Grass Valley mediante DAC I2C (MCP4728) y Raspberry Pi.

## Descripción

Este sistema controla remotamente el nivel de ganancia de audio (sensibilidad de micrófono) de las XCU Grass Valley a través del conector SubD-15 (Signalling Connector). Utiliza Arduino Nano Every + W5500 Ethernet + chips DAC MCP4728 para generar voltajes analógicos precisos (0-5V) controlados desde una Raspberry Pi via TCP.

## Características

- ✅ Control de 32 cámaras × 2 micrófonos = 64 canales de audio
- ✅ Arquitectura escalable: agregar nodos Arduino via Ethernet
- ✅ 8 niveles de ganancia: -22 a -64 dBu
- ✅ Interfaz gráfica fullscreen (Tkinter) con grid 8×4
- ✅ Nombres de cámara personalizables (doble-clic)
- ✅ Persistencia de estados entre sesiones (JSON)
- ✅ Indicador de conexión por nodo Arduino (verde/rojo)
- ✅ Modo demo para desarrollo sin hardware
- ✅ Interfaz en español

## Hardware

### Componentes
- Raspberry Pi 5
- 2× Arduino Nano Every (ATmega4809)
- 2× Módulo W5500 Ethernet
- 16× MCP4728 (DAC I2C, 4 canales, 12 bits)
- 1× Switch Ethernet
- 32× Conectores SubD-15 hembra

### Conexión por XCU (SubD-15)
- **Pin 6** → Audio 1 level ← Salida DAC (Mic 1)
- **Pin 14** → Audio 2 level ← Salida DAC (Mic 2)
- **Pin 15** → GND
- **Pin 7** → 5V (OCP) — **NO CONECTAR al DAC**

Ver [docs/HARDWARE.md](docs/HARDWARE.md) para esquemas detallados.

## Instalación

### Raspberry Pi (GUI)
```bash
git clone https://github.com/thierry-huin/grass-valley-gpio-controller.git
cd grass-valley-gpio-controller
bash install.sh
```

Crea un acceso directo "GV Audio Control" en Sound & Video y en el escritorio.

### Arduino Nano Every (firmware)
1. Abrir `arduino/gv_dac_firmware/gv_dac_firmware.ino` en Arduino IDE
2. Cambiar IP y MAC según el nodo (ver comentarios en el sketch)
3. Subir al Arduino Nano Every
4. Repetir para cada nodo

### Configuración de Red
Configurar IP estática en la Pi (192.168.10.1) en la interfaz Ethernet dedicada.
Los nodos Arduino se configuran en `config/nodes.json`.

### Modo demo (sin hardware)
```bash
python3 src/gv_dac_controller.py
```

## Niveles de Ganancia

| Nivel | Voltaje | Sensibilidad |
|-------|---------|-------------|
| -22 dBu | 4.3V | Máxima |
| -28 dBu | 3.7V | |
| -34 dBu | 3.1V | |
| -40 dBu | 2.5V | Media (default) |
| -46 dBu | 1.9V | |
| -52 dBu | 1.3V | |
| -58 dBu | 0.7V | |
| -64 dBu | 0.0V | Mínima |

## Estructura del Proyecto

```
grass-valley-gpio-controller/
├── src/
│   └── gv_dac_controller.py    # Aplicación principal (GUI + DAC)
├── docs/
│   ├── HARDWARE.md              # Documentación hardware y esquemas
│   └── PIN_MAPPING.md           # Mapeo DAC → cámaras
├── tests/                       # Directorio para pruebas
├── requirements.txt             # Dependencias Python
├── AGENTS.md                    # Guía para Warp AI
├── .gitignore
└── README.md                    # Este archivo
```

## Documentación Adicional

- [Esquemas de hardware](docs/HARDWARE.md)
- [Mapeo de pines DAC](docs/PIN_MAPPING.md)

## Autor

Creado con ayuda de Warp AI Agent.
