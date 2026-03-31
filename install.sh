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

# 2. Create launcher script
echo "[2/4] Creando script de lanzamiento..."
cat > "$SCRIPT_DIR/run.sh" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/src/gv_dac_controller.py"
EOF
chmod +x "$SCRIPT_DIR/run.sh"
echo "  ✓ run.sh creado"

# 3. Create desktop shortcut
echo "[3/4] Creando acceso directo en el escritorio..."
mkdir -p "$(dirname "$DESKTOP_FILE")"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=GV Audio Control
Comment=Control de Audio DAC - 32 Cámaras Grass Valley XCU
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

# 4. Configure network (optional)
echo "[4/4] Configuración de red..."
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
echo "  - Doble-clic en 'GV Audio Control' en el escritorio"
echo "  - O desde terminal: $SCRIPT_DIR/run.sh"
echo ""
echo "Configuración Arduino:"
echo "  - Subir arduino/gv_dac_firmware/gv_dac_firmware.ino"
echo "  - Cambiar IP/MAC por nodo (ver comentarios en el sketch)"
echo ""
