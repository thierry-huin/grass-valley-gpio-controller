#!/usr/bin/env python3
"""
Grass Valley XCU - DAC Audio Controller (32 Cameras)
Controls audio gain via Arduino Nano Every + W5500 + MCP4728 DAC over TCP Ethernet.

Architecture:
  Raspberry Pi (GUI) → TCP → Arduino Nano A (W5500) → I2C → 8x MCP4728 → CAM 1-16
                     → TCP → Arduino Nano B (W5500) → I2C → 8x MCP4728 → CAM 17-32
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import socket
import json
import os
import sys
import threading


# ============================================================
# Arduino TCP Node
# ============================================================

class ArduinoNode:
    """Manages TCP connection to an Arduino Nano Every + W5500 node"""

    def __init__(self, node_id, ip, port, camera_start, camera_end):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.camera_start = camera_start
        self.camera_end = camera_end
        self.connected = False
        self.detected_chips = []
        self._lock = threading.Lock()

    def send_command(self, cmd, timeout=2.0):
        """Send a command to the Arduino and return the response"""
        with self._lock:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((self.ip, self.port))
                sock.sendall((cmd + '\n').encode())

                response = b''
                while True:
                    chunk = sock.recv(256)
                    if not chunk:
                        break
                    response += chunk
                    if b'\n' in response:
                        break

                sock.close()
                return response.decode().strip()
            except (socket.error, socket.timeout, OSError):
                self.connected = False
                return None

    def ping(self):
        """Test connection to Arduino"""
        result = self.send_command('PING', timeout=1.0)
        self.connected = (result == 'PONG')
        return self.connected

    def scan(self):
        """Scan for MCP4728 chips on this Arduino"""
        result = self.send_command('SCAN')
        if result and result.startswith('CHIPS '):
            chips_str = result[6:]
            if chips_str == 'none':
                self.detected_chips = []
            else:
                self.detected_chips = chips_str.split(',')
            self.connected = True
        else:
            self.detected_chips = []
        return self.detected_chips

    def set_dac(self, chip, channel, value):
        """Set DAC output value"""
        result = self.send_command(f'SET {chip} {channel} {value}')
        return result == 'OK'

    def get_id(self):
        """Get firmware identification"""
        return self.send_command('ID')


# ============================================================
# Main Application
# ============================================================

class DACControllerApp:
    """Main application: 32 camera audio gain control via Arduino nodes"""

    # Gain level presets: dBu label → DAC voltage → 12-bit DAC value
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

    GAIN_LEVELS = ['-22 dBu', '-28 dBu', '-34 dBu', '-40 dBu',
                   '-46 dBu', '-52 dBu', '-58 dBu', '-64 dBu']

    def __init__(self, root):
        self.root = root
        self.root.title("Control de Audio DAC - 32 Cámaras Grass Valley")

        # Fullscreen
        self.root.attributes('-fullscreen', True)
        self.root.bind('<F11>', lambda e: self.root.attributes('-fullscreen', False))
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))

        # Config paths
        self.app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = os.path.join(self.app_dir, 'config')
        self.nodes_file = os.path.join(self.config_dir, 'nodes.json')
        self.names_file = os.path.expanduser("~/camera_names_gv_config.json")
        self.states_file = os.path.expanduser("~/camera_states_gv_config.json")

        # Load Arduino nodes
        self.nodes = self._load_nodes()

        # Build camera mapping
        self.CAMERAS = {}
        self._build_camera_mapping()

        # Camera names
        self.camera_names = list(self.CAMERAS.keys())
        self.num_cameras = len(self.camera_names)
        self.camera_custom_names = self._load_camera_names()

        # Microphone states
        saved_states = self._load_microphone_states()
        self.mike_states = {}
        for cam_name, mikes in self.CAMERAS.items():
            for mike_name in mikes.keys():
                key = (cam_name, mike_name)
                self.mike_states[key] = saved_states.get(key, '-40 dBu')

        # UI storage
        self.mike_ui = {}
        self.node_status_labels = {}

        # Track loaded states
        self.states_loaded_from_file = len(saved_states) > 0

        # Connect to Arduino nodes and restore states
        self._connect_all_nodes()
        self._restore_all_saved_states()

        # Build GUI
        self.create_widgets()

        # Periodic connection check
        self._schedule_connection_check()

    # ========================================================
    # Node Management
    # ========================================================

    def _load_nodes(self):
        """Load Arduino node configuration from JSON"""
        nodes = []
        try:
            if os.path.exists(self.nodes_file):
                with open(self.nodes_file, 'r') as f:
                    config = json.load(f)
                for n in config.get('nodes', []):
                    node = ArduinoNode(
                        node_id=n['id'],
                        ip=n['ip'],
                        port=n.get('port', 5000),
                        camera_start=n['camera_start'],
                        camera_end=n['camera_end']
                    )
                    nodes.append(node)
        except Exception as e:
            print(f"Error loading nodes config: {e}")

        if not nodes:
            # Default: 2 nodes
            nodes = [
                ArduinoNode('A', '192.168.10.11', 5000, 1, 16),
                ArduinoNode('B', '192.168.10.12', 5000, 17, 32),
            ]
        return nodes

    def _connect_all_nodes(self):
        """Try to connect to all Arduino nodes"""
        for node in self.nodes:
            try:
                node.ping()
                if node.connected:
                    node.scan()
                    fw = node.get_id()
                    print(f"✓ Node {node.node_id} ({node.ip}): {fw} - Chips: {node.detected_chips}")
                else:
                    print(f"✗ Node {node.node_id} ({node.ip}): not reachable")
            except Exception as e:
                print(f"✗ Node {node.node_id} ({node.ip}): {e}")

    def _schedule_connection_check(self):
        """Periodically check Arduino connections"""
        def check():
            for node in self.nodes:
                was_connected = node.connected
                node.ping()
                if node.connected != was_connected:
                    self._update_node_status_ui()
            self.root.after(5000, check)
        self.root.after(5000, check)

    # ========================================================
    # Camera Mapping
    # ========================================================

    def _build_camera_mapping(self):
        """Build camera → (node, chip_index, channel) mapping"""
        for node in self.nodes:
            for cam_num in range(node.camera_start, node.camera_end + 1):
                cam_name = f'CAM {cam_num}'
                self.CAMERAS[cam_name] = {}

                # Local camera index within this node (0-15)
                local_idx = cam_num - node.camera_start

                # Chip index within this node (0-7)
                chip_index = local_idx // 2

                # First or second camera on the chip
                is_second = local_idx % 2 == 1

                if is_second:
                    self.CAMERAS[cam_name]['Mic 1'] = (node, chip_index, 2)  # Channel C
                    self.CAMERAS[cam_name]['Mic 2'] = (node, chip_index, 3)  # Channel D
                else:
                    self.CAMERAS[cam_name]['Mic 1'] = (node, chip_index, 0)  # Channel A
                    self.CAMERAS[cam_name]['Mic 2'] = (node, chip_index, 1)  # Channel B

    # ========================================================
    # Persistence
    # ========================================================

    def _load_camera_names(self):
        """Load custom camera names"""
        try:
            if os.path.exists(self.names_file):
                with open(self.names_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading camera names: {e}")
        return {f'CAM {i}': f'CAM {i}' for i in range(1, self.num_cameras + 1)}

    def _save_camera_names(self):
        """Save custom camera names"""
        try:
            with open(self.names_file, 'w', encoding='utf-8') as f:
                json.dump(self.camera_custom_names, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar nombres: {e}")
            return False

    def _load_microphone_states(self):
        """Load microphone gain states"""
        try:
            if os.path.exists(self.states_file):
                with open(self.states_file, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    return {tuple(k.split('|')): v for k, v in saved.items()}
        except Exception as e:
            print(f"Error loading states: {e}")
        return {}

    def _save_microphone_states(self):
        """Save microphone gain states"""
        try:
            data = {f"{cam}|{mike}": level for (cam, mike), level in self.mike_states.items()}
            with open(self.states_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving states: {e}")
            return False

    # ========================================================
    # Hardware Control
    # ========================================================

    def _apply_gain_hardware(self, camera_name, mike_name, level):
        """Send DAC value to Arduino node"""
        if level not in self.GAIN_PRESETS:
            return False

        node, chip_index, channel = self.CAMERAS[camera_name][mike_name]
        dac_value = self.GAIN_PRESETS[level]['dac_value']

        if not node.connected:
            return False

        return node.set_dac(chip_index, channel, dac_value)

    def _restore_all_saved_states(self):
        """Restore all saved states to hardware"""
        for cam_name in self.camera_names:
            for mike_name in ['Mic 1', 'Mic 2']:
                level = self.mike_states.get((cam_name, mike_name), '-40 dBu')
                try:
                    self._apply_gain_hardware(cam_name, mike_name, level)
                except Exception:
                    pass

    # ========================================================
    # GUI
    # ========================================================

    def get_camera_display_name(self, camera_key):
        return self.camera_custom_names.get(camera_key, camera_key)

    def edit_camera_name_dialog(self, camera_key):
        current_name = self.get_camera_display_name(camera_key)
        new_name = simpledialog.askstring(
            "Editar Nombre de Cámara",
            f"Ingrese el nuevo nombre para {camera_key}:",
            initialvalue=current_name,
            parent=self.root
        )
        if new_name and new_name.strip():
            self.camera_custom_names[camera_key] = new_name.strip()
            if self._save_camera_names():
                self.display_all_cameras_grid()

    def create_widgets(self):
        """Create GUI - 32 cameras in 8x4 grid"""
        self.root.configure(bg='#808080')

        # Bottom bar
        button_frame = tk.Frame(self.root, bg='#808080')
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)

        # Left: version + node status
        left_container = tk.Frame(button_frame, bg='#808080')
        left_container.pack(side=tk.LEFT, padx=5)

        tk.Label(
            left_container,
            text="v2026.03.31 - Grass Valley XCU - Arduino W5500 + MCP4728",
            font=("Arial", 8), bg='#808080', fg='#00FF00'
        ).pack(anchor='w')

        # Node status indicators
        status_frame = tk.Frame(left_container, bg='#808080')
        status_frame.pack(anchor='w')
        for node in self.nodes:
            color = "#00FF00" if node.connected else "#FF4444"
            chips = len(node.detected_chips) if node.connected else 0
            text = f"Node {node.node_id} ({node.ip}): {'OK' if node.connected else 'OFF'} - {chips} DACs"
            lbl = tk.Label(
                status_frame, text=text,
                font=("Arial", 9), bg='#808080', fg=color
            )
            lbl.pack(side=tk.LEFT, padx=10)
            self.node_status_labels[node.node_id] = lbl

        # Right: buttons
        # Quit
        quit_frame = tk.Frame(button_frame, relief=tk.RAISED, bd=3, bg='light grey')
        quit_frame.pack(side=tk.RIGHT, padx=5)
        quit_btn = tk.Label(
            quit_frame, text="Salir", font=("Arial", 11, "bold"),
            bg='light grey', fg='black', cursor='hand2', padx=15, pady=5
        )
        quit_btn.pack()
        quit_btn.bind('<Button-1>', lambda e: self.quit_application())
        quit_frame.bind('<Button-1>', lambda e: self.quit_application())
        quit_frame.config(cursor='hand2')

        # All-level buttons
        all_levels_to_show = ['-22 dBu', '-34 dBu', '-40 dBu', '-52 dBu', '-64 dBu']
        for level in reversed(all_levels_to_show):
            f = tk.Frame(button_frame, relief=tk.RAISED, bd=3, bg='light grey')
            f.pack(side=tk.RIGHT, padx=2)
            display_text = level.replace(' dBu', '')
            btn = tk.Label(
                f, text=f"All {display_text}", font=("Arial", 10, "bold"),
                bg='light grey', fg='black', cursor='hand2', padx=10, pady=5
            )
            btn.pack()

            def make_all_handler(lvl=level):
                def handler(e):
                    self.set_all_to_level(lvl)
                    return "break"
                return handler

            btn.bind('<Button-1>', make_all_handler())
            f.bind('<Button-1>', make_all_handler())
            f.config(cursor='hand2')

        # Save button
        save_frame = tk.Frame(button_frame, relief=tk.RAISED, bd=3, bg='light grey')
        save_frame.pack(side=tk.RIGHT, padx=5)
        save_btn = tk.Label(
            save_frame, text="Guardar Estados", font=("Arial", 11, "bold"),
            bg='light grey', fg='black', cursor='hand2', padx=15, pady=5
        )
        save_btn.pack()
        save_btn.bind('<Button-1>', lambda e: self.manual_save_states())
        save_frame.bind('<Button-1>', lambda e: self.manual_save_states())
        save_frame.config(cursor='hand2')

        # Main content
        self.content_frame = tk.Frame(self.root, bg='#808080')
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.display_all_cameras_grid()

        # Notification for loaded states
        if self.states_loaded_from_file:
            num_restored = sum(1 for v in self.mike_states.values() if v != '-40 dBu')
            self.root.after(500, lambda: messagebox.showinfo(
                "Estados Recuperados",
                f"Se han cargado los estados guardados.\n\nMicrófonos con estado personalizado: {num_restored}"
            ))

    def display_all_cameras_grid(self):
        """Display all cameras in grid: 8 columns x 4 rows"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.mike_ui.clear()

        cols = 8
        rows = (self.num_cameras + cols - 1) // cols

        for i in range(rows):
            self.content_frame.grid_rowconfigure(i, weight=1)
        for j in range(cols):
            self.content_frame.grid_columnconfigure(j, weight=1)

        for idx, camera_name in enumerate(self.camera_names):
            row_idx = idx // cols
            col_idx = idx % cols

            cam_container = tk.Frame(self.content_frame, bg='#505050', relief=tk.RIDGE, bd=2)
            cam_container.grid(row=row_idx, column=col_idx, sticky='nsew', padx=2, pady=2)

            cam_container.grid_rowconfigure(0, weight=0)
            cam_container.grid_rowconfigure(1, weight=1)
            cam_container.grid_rowconfigure(2, weight=1)
            cam_container.grid_columnconfigure(0, weight=1)

            # Camera name
            display_name = self.get_camera_display_name(camera_name)
            name_label = tk.Label(
                cam_container, text=display_name,
                font=("Arial", 11, "bold"), bg='#505050', fg='white', cursor='hand2'
            )
            name_label.grid(row=0, column=0, sticky='ew', pady=(3, 5))
            name_label.bind('<Double-Button-1>',
                           lambda e, cam=camera_name: self.edit_camera_name_dialog(cam))

            # Node indicator (small colored dot)
            node, _, _ = self.CAMERAS[camera_name]['Mic 1']
            node_color = "#00FF00" if node.connected else "#FF4444"
            node_indicator = tk.Label(
                cam_container, text=f"●{node.node_id}",
                font=("Arial", 7), bg='#505050', fg=node_color
            )
            node_indicator.place(relx=1.0, x=-5, y=2, anchor='ne')

            # Microphones
            for mike_idx, mike_name in enumerate(['Mic 1', 'Mic 2']):
                mike_frame = tk.Frame(cam_container, bg='#404040', relief=tk.GROOVE, bd=1)
                mike_frame.grid(row=mike_idx + 1, column=0, sticky='nsew', padx=3, pady=2)

                mike_frame.grid_columnconfigure(0, weight=0)
                mike_frame.grid_columnconfigure(1, weight=1)
                mike_frame.grid_rowconfigure(0, weight=1)

                label = tk.Label(
                    mike_frame, text=mike_name[-1],
                    font=("Arial", 10, "bold"), bg='#404040', fg='#CCCCCC', width=2
                )
                label.grid(row=0, column=0, sticky='ns', padx=(3, 2))

                btn_container = tk.Frame(mike_frame, bg='#404040')
                btn_container.grid(row=0, column=1, sticky='nsew', padx=2, pady=3)

                for i in range(8):
                    btn_container.grid_columnconfigure(i, weight=1)
                btn_container.grid_rowconfigure(0, weight=1)

                buttons = {}
                for btn_idx, level in enumerate(self.GAIN_LEVELS):
                    current_level = self.mike_states[(camera_name, mike_name)]
                    is_active = (level == current_level)

                    btn_frame = tk.Frame(
                        btn_container, relief=tk.RAISED, bd=2,
                        bg='blue' if is_active else 'light grey'
                    )
                    btn_frame.grid(row=0, column=btn_idx, sticky='nsew', padx=1)
                    btn_frame.grid_rowconfigure(0, weight=1)
                    btn_frame.grid_columnconfigure(0, weight=1)

                    display_text = level.replace(' dBu', '')
                    btn = tk.Label(
                        btn_frame, text=display_text,
                        font=("Arial", 9, "bold"),
                        bg='blue' if is_active else 'light grey',
                        fg='white' if is_active else 'black',
                        cursor='hand2'
                    )
                    btn.grid(row=0, column=0, sticky='nsew', padx=2, pady=4)

                    def make_click_handler(cam=camera_name, mike=mike_name, lvl=level):
                        def handler(e):
                            self.set_microphone_gain(cam, mike, lvl)
                            return "break"
                        return handler

                    btn.bind('<Button-1>', make_click_handler())
                    btn_frame.bind('<Button-1>', make_click_handler())
                    btn_frame.config(cursor='hand2')

                    buttons[level] = {'label': btn, 'frame': btn_frame}

                self.mike_ui[(camera_name, mike_name)] = {'buttons': buttons}

    def _update_node_status_ui(self):
        """Update node connection indicators"""
        for node in self.nodes:
            if node.node_id in self.node_status_labels:
                lbl = self.node_status_labels[node.node_id]
                color = "#00FF00" if node.connected else "#FF4444"
                chips = len(node.detected_chips) if node.connected else 0
                text = f"Node {node.node_id} ({node.ip}): {'OK' if node.connected else 'OFF'} - {chips} DACs"
                lbl.config(text=text, fg=color)

    # ========================================================
    # Actions
    # ========================================================

    def set_microphone_gain(self, camera_name, mike_name, level, update_ui=True):
        """Set gain level for a microphone"""
        if level not in self.GAIN_PRESETS:
            return

        # Apply to hardware
        node, _, _ = self.CAMERAS[camera_name][mike_name]
        if node.connected:
            try:
                self._apply_gain_hardware(camera_name, mike_name, level)
            except Exception as e:
                messagebox.showerror("Error", f"Error DAC {camera_name} {mike_name}: {e}")
                return

        # Update state
        self.mike_states[(camera_name, mike_name)] = level
        self._save_microphone_states()

        # Update UI
        if update_ui and (camera_name, mike_name) in self.mike_ui:
            self.update_microphone_ui(camera_name, mike_name)
            self.root.update_idletasks()

    def update_microphone_ui(self, camera_name, mike_name):
        """Update button colors for a microphone"""
        key = (camera_name, mike_name)
        if key not in self.mike_ui:
            return

        current_level = self.mike_states[key]
        ui = self.mike_ui[key]

        for level, btn_dict in ui['buttons'].items():
            label = btn_dict['label']
            frame = btn_dict['frame']

            if level == current_level:
                label.config(bg='blue', fg='white')
                frame.config(bg='blue', relief=tk.SUNKEN)
            else:
                label.config(bg='light grey', fg='black')
                frame.config(bg='light grey', relief=tk.RAISED)

    def set_all_to_level(self, level):
        """Set all microphones to the specified level"""
        for camera_name in self.camera_names:
            for mike_name in ['Mic 1', 'Mic 2']:
                self.set_microphone_gain(camera_name, mike_name, level, update_ui=False)

        for camera_name in self.camera_names:
            for mike_name in ['Mic 1', 'Mic 2']:
                if (camera_name, mike_name) in self.mike_ui:
                    self.update_microphone_ui(camera_name, mike_name)

        self.root.update_idletasks()
        display_level = level.replace(' dBu', '')
        messagebox.showinfo("Aplicado", f"Todas las cámaras configuradas a {display_level} dBu")

    def manual_save_states(self, event=None):
        """Manually save states"""
        if self._save_microphone_states():
            messagebox.showinfo(
                "Éxito",
                f"Estados guardados correctamente.\n\nArchivo: {self.states_file}"
            )
        else:
            messagebox.showerror("Error", "No se pudieron guardar los estados.")
        return "break"

    def quit_application(self):
        """Save and quit"""
        if messagebox.askokcancel("Salir", "¿Está seguro que desea salir?"):
            self._save_microphone_states()
            self.root.destroy()


# ============================================================
# Main
# ============================================================

def main():
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print("\n" + "=" * 60)
        print("ERROR: No se puede iniciar la interfaz gráfica")
        print("=" * 60)
        print(f"\nDetalle: {e}\n")
        print("Ejecute desde el escritorio de la Raspberry Pi")
        print("o use Screen Sharing en Raspberry Pi Connect.")
        print("=" * 60 + "\n")
        sys.exit(1)

    app = DACControllerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.quit_application)
    root.mainloop()


if __name__ == "__main__":
    main()
