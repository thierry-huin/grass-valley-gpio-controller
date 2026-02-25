# Grass Valley XCU - Control de Audio por DAC

Control de ganancia de audio para 16 cámaras Grass Valley mediante DAC I2C (MCP4728) y Raspberry Pi.

## Descripción

Este sistema controla remotamente el nivel de ganancia de audio (sensibilidad de micrófono) de las XCU Grass Valley a través del conector SubD-15 (Signalling Connector). Utiliza chips DAC MCP4728 para generar voltajes analógicos precisos (0-5V) que la XCU interpreta como niveles de ganancia.

## Características

- ✅ Control de 16 cámaras × 2 micrófonos = 32 canales de audio
- ✅ 8 niveles de ganancia: -22 a -64 dBu
- ✅ Interfaz gráfica fullscreen (Tkinter) con grid 4×4
- ✅ Nombres de cámara personalizables (doble-clic)
- ✅ Persistencia de estados entre sesiones (JSON)
- ✅ Modo demo para desarrollo sin hardware I2C
- ✅ Interfaz en español

## Hardware

### Componentes
- Raspberry Pi 4
- 8× MCP4728 (DAC I2C, 4 canales, 12 bits)
- 16× Conectores SubD-15 hembra

### Conexión por XCU (SubD-15)
- **Pin 6** → Audio 1 level ← Salida DAC (Mic 1)
- **Pin 14** → Audio 2 level ← Salida DAC (Mic 2)
- **Pin 15** → GND
- **Pin 7** → 5V (OCP) — **NO CONECTAR al DAC**

Ver [docs/HARDWARE.md](docs/HARDWARE.md) para esquemas detallados.

## Instalación

### 1. Clonar el repositorio
```bash
git clone <repository-url>
cd grass-valley-gpio-controller
```

### 2. Instalar dependencias
```bash
pip3 install -r requirements.txt
```

### 3. Ejecutar

**En Raspberry Pi (producción):**
```bash
python3 src/gv_dac_controller.py
```

**En cualquier sistema (modo demo):**
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
