#!/bin/bash
# Grass Valley DAC Controller - Raspberry Pi Installation Script
# Architecture: RPi (GUI) → TCP/Ethernet → Arduino Nano Every + W5500 → MCP4728 DAC
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/gv-dac-controller.desktop"

echo "============================================"
echo "  Grass Valley DAC Controller - Instalación"
echo "============================================"
echo ""

# 1. System dependencies
echo "[1/4] Instalando dependencias del sistema..."
sudo apt update
sudo apt install -y python3-tk git

# 2. Install I2C dependencies (for direct mode)
echo "[2/5] Instalando dependencias I2C (modo directo)..."
sudo apt install -y python3-lgpio i2c-tools || true
if [ -d "$SCRIPT_DIR/venv" ]; then rm -rf "$SCRIPT_DIR/venv"; fi
python3 -m venv --system-site-packages "$SCRIPT_DIR/venv"
source "$SCRIPT_DIR/venv/bin/activate"
pip install adafruit-circuitpython-mcp4728 adafruit-blinka
deactivate
echo "  ✓ Dependencias I2C instaladas"

# 3. Create launcher scripts
echo "[3/5] Creando scripts de lanzamiento..."

# Arduino Ethernet version (32 cameras)
cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/src/gv_dac_controller.py"
EOF
chmod +x "$SCRIPT_DIR/run.sh"

# I2C direct version (16 cameras)
cat > "$SCRIPT_DIR/run_i2c.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
python3 "$SCRIPT_DIR/src/gv_dac_controller_i2c.py"
EOF
chmod +x "$SCRIPT_DIR/run_i2c.sh"
echo "  ✓ run.sh y run_i2c.sh creados"

# 4. Create desktop shortcuts
echo "[4/5] Creando accesos directos..."
mkdir -p "$(dirname "$DESKTOP_FILE")"

# Arduino version shortcut
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=GV Audio Control (32 Cam - Arduino)
Comment=Control de Audio DAC - 32 Cámaras via Arduino + W5500
Exec=$SCRIPT_DIR/run.sh
Icon=camera-video
Terminal=false
Type=Application
Categories=AudioVideo;
StartupNotify=true
EOF

# I2C direct version shortcut
DESKTOP_FILE_I2C="$HOME/.local/share/applications/gv-dac-controller-i2c.desktop"
cat > "$DESKTOP_FILE_I2C" << EOF
[Desktop Entry]
Name=GV Audio Control (16 Cam - I2C)
Comment=Control de Audio DAC - 16 Cámaras via I2C directo
Exec=$SCRIPT_DIR/run_i2c.sh
Icon=camera-video
Terminal=false
Type=Application
Categories=AudioVideo;
StartupNotify=true
EOF

# Copy to Desktop if it exists
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/gv-dac-controller.desktop"
    cp "$DESKTOP_FILE_I2C" "$HOME/Desktop/gv-dac-controller-i2c.desktop"
    chmod +x "$HOME/Desktop/gv-dac-controller.desktop"
    chmod +x "$HOME/Desktop/gv-dac-controller-i2c.desktop"
    echo "  ✓ Accesos directos copiados al escritorio"
fi

# 5. Configure network (optional)
echo "[5/5] Configuración de red..."
echo "  ⚠ Asegúrese de configurar la interfaz Ethernet de la Pi"
echo "    con IP estática 192.168.10.1 en la red dedicada."
echo "    Los Arduinos deben estar en 192.168.10.11 y .12"
echo "    (ver config/nodes.json)"

echo ""
echo "============================================"
echo "  ✓ Instalación completada"
echo "============================================"
echo ""
echo "Para ejecutar:"
echo "  32 cam (Arduino): doble-clic 'GV Audio Control (32 Cam)' o ./run.sh"
echo "  16 cam (I2C):     doble-clic 'GV Audio Control (16 Cam)' o ./run_i2c.sh"
echo ""
echo "Configuración Arduino:"
echo "  - Subir arduino/gv_dac_firmware/gv_dac_firmware.ino"
echo "  - Cambiar IP/MAC por nodo (ver comentarios en el sketch)"
echo ""
