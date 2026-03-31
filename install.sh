#!/bin/bash
# Grass Valley DAC Controller - Raspberry Pi Installation Script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
DESKTOP_FILE="$HOME/.local/share/applications/gv-dac-controller.desktop"

echo "============================================"
echo "  Grass Valley DAC Controller - Instalación"
echo "============================================"
echo ""

# 1. System dependencies
echo "[1/5] Instalando dependencias del sistema..."
sudo apt update
sudo apt install -y python3-pip python3-tk python3-venv python3-lgpio i2c-tools git

# 2. Enable I2C
echo "[2/5] Habilitando I2C..."
sudo raspi-config nonint do_i2c 0
echo "  ✓ I2C habilitado"

# 3. Python virtual environment
echo "[3/5] Creando entorno virtual Python..."
if [ -d "$VENV_DIR" ]; then
    echo "  Eliminando venv existente..."
    rm -rf "$VENV_DIR"
fi
python3 -m venv --system-site-packages "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -r "$SCRIPT_DIR/requirements.txt"
echo "  ✓ Dependencias Python instaladas"

# 4. Create launcher script
echo "[4/5] Creando script de lanzamiento..."
cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
python3 "$SCRIPT_DIR/src/gv_dac_controller.py"
EOF
chmod +x "$SCRIPT_DIR/run.sh"
echo "  ✓ run.sh creado"

# 5. Create desktop shortcut
echo "[5/5] Creando acceso directo en el escritorio..."
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=GV Audio Control
Comment=Control de Audio DAC - Grass Valley XCU
Exec=$SCRIPT_DIR/run.sh
Icon=camera-video
Terminal=false
Type=Application
Categories=AudioVideo;
StartupNotify=true
EOF

# Also copy to Desktop if it exists
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/gv-dac-controller.desktop"
    chmod +x "$HOME/Desktop/gv-dac-controller.desktop"
    echo "  ✓ Acceso directo copiado al escritorio"
fi

echo ""
echo "============================================"
echo "  ✓ Instalación completada"
echo "============================================"
echo ""
echo "Para ejecutar:"
echo "  - Doble-clic en 'GV Audio Control' en el escritorio"
echo "  - O desde terminal: $SCRIPT_DIR/run.sh"
echo ""
echo "Verificar hardware I2C:"
echo "  sudo i2cdetect -y 1"
echo ""
