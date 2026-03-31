#!/usr/bin/env python3
"""
Raspberry Pi DAC Controller - 16 Camera Audio Gain Control (Grass Valley XCU)
Controls audio gain levels via 8x MCP4728 I2C DAC chips for Grass Valley camera XCUs
Architecture: 8 MCP4728 (4-channel DAC each), 1 chip per 2 cameras, voltage output 0-5V
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import json
import os
import time

# Try to import MCP4728 DAC library
try:
    import adafruit_mcp4728
    import board
    import busio
    I2C_AVAILABLE = True
except (ImportError, RuntimeError, NotImplementedError) as e:
    I2C_AVAILABLE = False
    print(f"Warning: MCP4728/I2C not available. Running in demo mode. Error: {e}")


class DACControllerApp:
    """Main application class for DAC controller with 16 camera/microphone gain presets (Grass Valley XCU)"""
    
    # I2C Configuration: 8x MCP4728 DAC chips
    # Each MCP4728 has 4 analog output channels (A, B, C, D)
    # Total: 8 chips × 4 channels = 32 outputs (32 used: 16 cameras × 2 mics)
    
    # Hardware Architecture:
    # - 16 cameras with 2 microphones each = 32 audio channels
    # - Each MCP4728 controls 2 cameras (4 channels: Mic1A, Mic2A, Mic1B, Mic2B)
    # - Output voltage 0-5V controls audio gain level on XCU SubD-15 connector
    # - Pin 6: Audio 1 level, Pin 14: Audio 2 level, Pin 15: GND
    
    # MCP4728 I2C addresses (default 0x60, configurable)
    DAC_ADDRESSES = [
        0x60,  # Chip 0: CAM 1-2
        0x61,  # Chip 1: CAM 3-4
        0x62,  # Chip 2: CAM 5-6
        0x63,  # Chip 3: CAM 7-8
        0x64,  # Chip 4: CAM 9-10
        0x65,  # Chip 5: CAM 11-12
        0x66,  # Chip 6: CAM 13-14
        0x67,  # Chip 7: CAM 15-16
    ]
    
    # Gain level presets: dBu label → DAC voltage → 12-bit DAC value
    # MCP4728 with VDD=5V reference: value = voltage / 5.0 * 4096
    # Grass Valley XCU SubD-15 connector: 0-5V analog input on pins 6 and 14
    # Resistor ladder: 8x 1kΩ from 5V (pin 7) to GND (pin 15)
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
    
    # Ordered list of gain levels (highest to lowest sensitivity)
    GAIN_LEVELS = ['-22 dBu', '-28 dBu', '-34 dBu', '-40 dBu', '-46 dBu', '-52 dBu', '-58 dBu', '-64 dBu']
    
    # Camera configuration: maps camera name → {mic_name: (chip_index, channel)}
    # Channel: 'a'=channel A, 'b'=channel B, 'c'=channel C, 'd'=channel D
    CAMERAS = {}
    
    def __init__(self, root):
        global I2C_AVAILABLE
        
        self.root = root
        self.root.title("Control de Audio DAC - 16 Cámaras Grass Valley (8 MCP4728)")
        
        # Fullscreen (works on Raspberry Pi OS/Linux)
        self.root.attributes('-fullscreen', True)
        
        # Allow exit with F11 or ESC
        self.root.bind('<F11>', lambda e: self.root.attributes('-fullscreen', False))
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        
        # Configuration file paths
        self.config_file = os.path.expanduser("~/camera_names_gv_config.json")
        self.states_file = os.path.expanduser("~/camera_states_gv_config.json")
        
        # Build camera/DAC channel mapping
        self._build_camera_mapping()
        
        # Load custom camera names
        self.camera_custom_names = self._load_camera_names()
        
        # Initialize DAC chips
        self.dac_chips = []
        self.detected_addresses = []
        if I2C_AVAILABLE:
            try:
                # Initialize I2C bus
                self.i2c = busio.I2C(board.SCL, board.SDA)
                
                # Scan for available DAC chips
                while not self.i2c.try_lock():
                    pass
                devices = self.i2c.scan()
                self.i2c.unlock()
                
                print(f"I2C devices found: {[hex(d) for d in devices]}")
                
                # Initialize each detected MCP4728 chip
                for addr in self.DAC_ADDRESSES:
                    if addr in devices:
                        try:
                            dac = adafruit_mcp4728.MCP4728(self.i2c, address=addr)
                            self.dac_chips.append(dac)
                            self.detected_addresses.append(addr)
                            print(f"✓ Initialized MCP4728 at address 0x{addr:02X}")
                        except Exception as e:
                            print(f"✗ Failed to initialize MCP4728 at 0x{addr:02X}: {e}")
                            self.dac_chips.append(None)
                    else:
                        self.dac_chips.append(None)  # Keep index aligned
                        print(f"- No MCP4728 at address 0x{addr:02X}")
                
                if not self.detected_addresses:
                    print("No MCP4728 chips detected. Running in demo mode.")
                    I2C_AVAILABLE = False
                else:
                    print(f"Successfully initialized {len(self.detected_addresses)} MCP4728 chip(s)")
                    
            except Exception as e:
                print(f"Error initializing I2C: {e}")
                I2C_AVAILABLE = False
        
        # Store microphone states: {(camera_name, mike_name): current_gain_level}
        # Load saved states or initialize with default -40 dBu (mid-range)
        saved_states = self._load_microphone_states()
        self.mike_states = {}
        for cam_name, mikes in self.CAMERAS.items():
            for mike_name in mikes.keys():
                key = (cam_name, mike_name)
                self.mike_states[key] = saved_states.get(key, '-40 dBu')
        
        # Store UI elements: {(camera_name, mike_name): {'buttons': {level: Button}}}
        self.mike_ui = {}
        
        # Camera names list
        self.camera_names = list(self.CAMERAS.keys())
        
        # Track if states were loaded from file
        self.states_loaded_from_file = len(saved_states) > 0
        
        # Apply saved states to hardware
        if I2C_AVAILABLE and self.dac_chips:
            self._restore_all_saved_states()
        
        self.create_widgets()
    
    def _build_camera_mapping(self):
        """Build the camera to DAC channel mapping dynamically
        
        Architecture:
        - Each MCP4728 has 4 channels (A, B, C, D)
        - Channel A: Camera N, Mic 1
        - Channel B: Camera N, Mic 2
        - Channel C: Camera N+1, Mic 1
        - Channel D: Camera N+1, Mic 2
        - 2 cameras per MCP4728 chip
        """
        for cam_num in range(1, 17):  # 16 cameras
            cam_name = f'CAM {cam_num}'
            self.CAMERAS[cam_name] = {}
            
            # Determine which chip for this camera
            # Camera 1,2 → Chip 0; Camera 3,4 → Chip 1; etc.
            chip_index = (cam_num - 1) // 2
            
            # Determine if this is the first or second camera on the chip
            is_second_camera = (cam_num - 1) % 2 == 1
            
            if is_second_camera:
                self.CAMERAS[cam_name]['Mic 1'] = (chip_index, 'c')
                self.CAMERAS[cam_name]['Mic 2'] = (chip_index, 'd')
            else:
                self.CAMERAS[cam_name]['Mic 1'] = (chip_index, 'a')
                self.CAMERAS[cam_name]['Mic 2'] = (chip_index, 'b')
    
    def _load_camera_names(self):
        """Load custom camera names from configuration file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {f'CAM {i}': f'CAM {i}' for i in range(1, 17)}
        except Exception as e:
            print(f"Error loading camera names: {e}")
            return {f'CAM {i}': f'CAM {i}' for i in range(1, 17)}
    
    def _save_camera_names(self):
        """Save custom camera names to configuration file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.camera_custom_names, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar nombres: {e}")
            return False
    
    def _load_microphone_states(self):
        """Load microphone gain states from configuration file"""
        try:
            if os.path.exists(self.states_file):
                with open(self.states_file, 'r', encoding='utf-8') as f:
                    saved_states = json.load(f)
                    return {tuple(key.split('|')): value for key, value in saved_states.items()}
            else:
                return {}
        except Exception as e:
            print(f"Error loading microphone states: {e}")
            return {}
    
    def _save_microphone_states(self):
        """Save microphone gain states to configuration file"""
        try:
            states_to_save = {f"{cam}|{mike}": level for (cam, mike), level in self.mike_states.items()}
            with open(self.states_file, 'w', encoding='utf-8') as f:
                json.dump(states_to_save, f, indent=2, ensure_ascii=False)
            print(f"✓ States saved to {self.states_file}")
            return True
        except Exception as e:
            print(f"✗ Error saving microphone states: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_camera_display_name(self, camera_key):
        """Get the display name for a camera (custom or default)"""
        return self.camera_custom_names.get(camera_key, camera_key)
    
    def edit_camera_name_dialog(self, camera_key):
        """Open dialog to edit camera name"""
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
                messagebox.showinfo("Éxito", f"Nombre actualizado: {new_name.strip()}")
    
    def _set_dac_output(self, chip_index, channel, dac_value):
        """Set a specific DAC channel output value
        
        Args:
            chip_index: Index of the MCP4728 chip (0-7)
            channel: Channel letter ('a', 'b', 'c', 'd')
            dac_value: 12-bit DAC value (0-4095)
        """
        if not I2C_AVAILABLE or chip_index >= len(self.dac_chips):
            return False
        
        dac = self.dac_chips[chip_index]
        if dac is None:
            return False
        
        try:
            # MCP4728 channels are accessed as attributes
            ch = getattr(dac, f'channel_{channel}')
            ch.value = dac_value << 4  # MCP4728 library expects 16-bit value, shift 12-bit to upper
            return True
        except Exception as e:
            print(f"✗ Error setting DAC chip {chip_index} channel {channel} to {dac_value}: {e}")
            return False
    
    def _restore_all_saved_states(self):
        """Restore saved states for all microphones by setting DAC outputs"""
        if not I2C_AVAILABLE:
            return
        
        for cam_name in self.camera_names:
            for mike_name in ['Mic 1', 'Mic 2']:
                level = self.mike_states.get((cam_name, mike_name), '-40 dBu')
                try:
                    self._apply_gain_hardware(cam_name, mike_name, level)
                    print(f"{cam_name}: {mike_name}={level}")
                except Exception as e:
                    print(f"Error restoring {mike_name} for {cam_name}: {e}")
        
        print("Saved states restored for all microphones")
    
    def _apply_gain_hardware(self, camera_name, mike_name, level):
        """Apply gain level to hardware DAC output"""
        if level not in self.GAIN_PRESETS:
            print(f"Unknown level: {level}")
            return False
        
        chip_index, channel = self.CAMERAS[camera_name][mike_name]
        dac_value = self.GAIN_PRESETS[level]['dac_value']
        
        return self._set_dac_output(chip_index, channel, dac_value)
    
    def create_widgets(self):
        """Create the GUI widgets - all 16 cameras in 4x4 grid, fullscreen"""
        
        # Configure root background
        self.root.configure(bg='#808080')
        
        # Bottom control buttons (pack first so they stay at bottom)
        button_frame = tk.Frame(self.root, bg='#808080')
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        # Left side container for version and status
        left_status_container = tk.Frame(button_frame, bg='#808080')
        left_status_container.pack(side=tk.LEFT, padx=5)
        
        # Version date label
        version_label = tk.Label(
            left_status_container,
            text="v2026.02.25 - Grass Valley XCU - 8 MCP4728 DAC",
            font=("Arial", 8),
            bg='#808080',
            fg='#00FF00'
        )
        version_label.pack(anchor='w')
        
        # Status indicator
        chip_count = len(self.detected_addresses) if I2C_AVAILABLE else 0
        if I2C_AVAILABLE:
            addr_list = ", ".join([f"0x{a:02X}" for a in self.detected_addresses])
            status_text = f"I2C OK - {chip_count} DAC(s) [{addr_list}] - {chip_count * 4} canales"
            status_color = "#00FF00" if chip_count > 0 else "#FFA500"
        else:
            status_text = "Modo DEMO - Sin hardware I2C"
            status_color = "#FFA500"
        
        status_label = tk.Label(
            left_status_container,
            text=status_text,
            font=("Arial", 10),
            bg='#808080',
            fg=status_color
        )
        status_label.pack(anchor='w')
        
        # Control buttons on the right
        quit_frame = tk.Frame(button_frame, relief=tk.RAISED, bd=3, bg='light grey')
        quit_frame.pack(side=tk.RIGHT, padx=5)
        quit_btn = tk.Label(
            quit_frame,
            text="Salir",
            font=("Arial", 11, "bold"),
            bg='light grey',
            fg='black',
            cursor='hand2',
            padx=15,
            pady=5
        )
        quit_btn.pack()
        quit_btn.bind('<Button-1>', lambda e: self.quit_application())
        quit_frame.bind('<Button-1>', lambda e: self.quit_application())
        quit_frame.config(cursor='hand2')
        
        # All buttons for applying levels to all cameras (show a subset to fit)
        all_levels_to_show = ['-22 dBu', '-34 dBu', '-40 dBu', '-52 dBu', '-64 dBu']
        for level in reversed(all_levels_to_show):
            all_frame = tk.Frame(button_frame, relief=tk.RAISED, bd=3, bg='light grey')
            all_frame.pack(side=tk.RIGHT, padx=2)
            
            display_text = level.replace(' dBu', '')
            all_btn = tk.Label(
                all_frame,
                text=f"All {display_text}",
                font=("Arial", 10, "bold"),
                bg='light grey',
                fg='black',
                cursor='hand2',
                padx=10,
                pady=5
            )
            all_btn.pack()
            
            def make_all_handler(lvl=level):
                def handler(e):
                    self.set_all_to_level(lvl)
                    return "break"
                return handler
            
            all_btn.bind('<Button-1>', make_all_handler())
            all_frame.bind('<Button-1>', make_all_handler())
            all_frame.config(cursor='hand2')
        
        # Save states button
        save_frame = tk.Frame(button_frame, relief=tk.RAISED, bd=3, bg='light grey')
        save_frame.pack(side=tk.RIGHT, padx=5)
        save_btn = tk.Label(
            save_frame,
            text="Guardar Estados",
            font=("Arial", 11, "bold"),
            bg='light grey',
            fg='black',
            cursor='hand2',
            padx=15,
            pady=5
        )
        save_btn.pack()
        save_btn.bind('<Button-1>', lambda e: self.manual_save_states())
        save_frame.bind('<Button-1>', lambda e: self.manual_save_states())
        save_frame.config(cursor='hand2')
        
        # Main content frame
        self.content_frame = tk.Frame(self.root, bg='#808080')
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Display all cameras in grid
        self.display_all_cameras_grid()
        
        # Show notification if states were loaded
        if self.states_loaded_from_file:
            num_restored = sum(1 for key in self.mike_states.keys() if self.mike_states[key] != '-40 dBu')
            self.root.after(500, lambda: messagebox.showinfo(
                "Estados Recuperados",
                f"Se han cargado los estados guardados de la sesión anterior.\n\nNúmero de micrófonos con estado personalizado: {num_restored}"
            ))
    
    def display_all_cameras_grid(self):
        """Display all 16 cameras in 4x4 grid, fullscreen for 1920x1080"""
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Clear all UI references
        self.mike_ui.clear()
        
        # Configure grid weights for expansion
        for i in range(4):
            self.content_frame.grid_rowconfigure(i, weight=1)
            self.content_frame.grid_columnconfigure(i, weight=1)
        
        # Create 4 rows x 4 columns grid
        for row_idx in range(4):
            for col_idx in range(4):
                cam_idx = row_idx * 4 + col_idx
                camera_name = self.camera_names[cam_idx]
                
                # Camera container
                cam_container = tk.Frame(self.content_frame, bg='#505050', relief=tk.RIDGE, bd=2)
                cam_container.grid(row=row_idx, column=col_idx, sticky='nsew', padx=3, pady=3)
                
                # Configure internal expansion
                cam_container.grid_rowconfigure(0, weight=0)  # Name label
                cam_container.grid_rowconfigure(1, weight=1)  # Mic 1
                cam_container.grid_rowconfigure(2, weight=1)  # Mic 2
                cam_container.grid_columnconfigure(0, weight=1)
                
                # Camera name (double-click to edit)
                display_name = self.get_camera_display_name(camera_name)
                name_label = tk.Label(
                    cam_container,
                    text=display_name,
                    font=("Arial", 14, "bold"),
                    bg='#505050',
                    fg='white',
                    cursor='hand2'
                )
                name_label.grid(row=0, column=0, sticky='ew', pady=(5, 8))
                name_label.bind('<Double-Button-1>', lambda e, cam=camera_name: self.edit_camera_name_dialog(cam))
                
                # Microphones
                for mike_idx, mike_name in enumerate(['Mic 1', 'Mic 2']):
                    # Microphone row frame
                    mike_frame = tk.Frame(cam_container, bg='#404040', relief=tk.GROOVE, bd=2)
                    mike_frame.grid(row=mike_idx+1, column=0, sticky='nsew', padx=5, pady=3)
                    
                    # Configure internal expansion
                    mike_frame.grid_columnconfigure(0, weight=0)  # Label
                    mike_frame.grid_columnconfigure(1, weight=1)  # Buttons
                    mike_frame.grid_rowconfigure(0, weight=1)
                    
                    # Microphone label
                    label = tk.Label(
                        mike_frame,
                        text=mike_name[-1],  # Just "1" or "2"
                        font=("Arial", 12, "bold"),
                        bg='#404040',
                        fg='#CCCCCC',
                        width=2
                    )
                    label.grid(row=0, column=0, sticky='ns', padx=(5, 3))
                    
                    # Buttons container
                    button_container = tk.Frame(mike_frame, bg='#404040')
                    button_container.grid(row=0, column=1, sticky='nsew', padx=3, pady=5)
                    
                    # Configure button expansion - 8 buttons
                    for i in range(8):
                        button_container.grid_columnconfigure(i, weight=1)
                    button_container.grid_rowconfigure(0, weight=1)
                    
                    # Create gain level buttons
                    buttons = {}
                    
                    for btn_idx, level in enumerate(self.GAIN_LEVELS):
                        current_level = self.mike_states[(camera_name, mike_name)]
                        is_active = (level == current_level)
                        
                        btn_frame = tk.Frame(
                            button_container,
                            relief=tk.RAISED,
                            bd=2,
                            bg='blue' if is_active else 'light grey'
                        )
                        btn_frame.grid(row=0, column=btn_idx, sticky='nsew', padx=1)
                        btn_frame.grid_rowconfigure(0, weight=1)
                        btn_frame.grid_columnconfigure(0, weight=1)
                        
                        # Display label: just the number without "dBu"
                        display_text = level.replace(' dBu', '')
                        
                        btn = tk.Label(
                            btn_frame,
                            text=display_text,
                            font=("Arial", 11, "bold"),
                            bg='blue' if is_active else 'light grey',
                            fg='white' if is_active else 'black',
                            cursor='hand2'
                        )
                        btn.grid(row=0, column=0, sticky='nsew', padx=3, pady=6)
                        
                        def make_click_handler(cam=camera_name, mike=mike_name, lvl=level):
                            def handler(e):
                                self.set_microphone_gain(cam, mike, lvl)
                                return "break"
                            return handler
                        
                        btn.bind('<Button-1>', make_click_handler())
                        btn_frame.bind('<Button-1>', make_click_handler())
                        btn_frame.config(cursor='hand2')
                        
                        buttons[level] = {'label': btn, 'frame': btn_frame}
                    
                    # Store UI references
                    self.mike_ui[(camera_name, mike_name)] = {
                        'buttons': buttons
                    }
    
    def set_microphone_gain(self, camera_name, mike_name, level, update_ui=True):
        """Set the gain level for a microphone by setting DAC output voltage"""
        if level not in self.GAIN_PRESETS:
            return
        
        # Apply to hardware
        if I2C_AVAILABLE and self.dac_chips:
            try:
                success = self._apply_gain_hardware(camera_name, mike_name, level)
                if not success:
                    chip_idx, channel = self.CAMERAS[camera_name][mike_name]
                    if chip_idx < len(self.dac_chips) and self.dac_chips[chip_idx] is None:
                        pass  # Chip not available, continue in demo mode
                    else:
                        messagebox.showerror("Error", f"Error al controlar DAC de {camera_name} {mike_name}")
                        return
            except Exception as e:
                messagebox.showerror("Error", f"Error al controlar DAC de {camera_name} {mike_name}: {e}")
                return
        
        # Update state
        self.mike_states[(camera_name, mike_name)] = level
        
        # Save states to file
        self._save_microphone_states()
        
        # Update UI
        if update_ui and (camera_name, mike_name) in self.mike_ui:
            self.update_microphone_ui(camera_name, mike_name)
            self.root.update_idletasks()
            self.root.update()
    
    def update_microphone_ui(self, camera_name, mike_name):
        """Update the UI elements for a microphone based on its current gain level"""
        key = (camera_name, mike_name)
        if key not in self.mike_ui:
            return
        
        current_level = self.mike_states[key]
        ui = self.mike_ui[key]
        
        # Update button colors - highlight the active level with blue
        for level, btn_dict in ui['buttons'].items():
            label = btn_dict['label']
            frame = btn_dict['frame']
            
            if level == current_level:
                label.config(bg='blue', fg='white')
                frame.config(bg='blue', relief=tk.SUNKEN)
            else:
                label.config(bg='light grey', fg='black')
                frame.config(bg='light grey', relief=tk.RAISED)
        
        # Force redraw
        for btn_dict in ui['buttons'].values():
            btn_dict['label'].update()
            btn_dict['frame'].update()
    
    def set_all_to_level(self, level):
        """Set all microphones to the specified gain level"""
        for camera_name in self.camera_names:
            for mike_name in ['Mic 1', 'Mic 2']:
                self.set_microphone_gain(camera_name, mike_name, level, update_ui=False)
        
        # Now update UI for all visible microphones
        for camera_name in self.camera_names:
            for mike_name in ['Mic 1', 'Mic 2']:
                if (camera_name, mike_name) in self.mike_ui:
                    self.update_microphone_ui(camera_name, mike_name)
        
        # Force GUI update
        self.root.update_idletasks()
        self.root.update()
        
        display_level = level.replace(' dBu', '')
        messagebox.showinfo("Aplicado", f"Todas las cámaras han sido configuradas a {display_level} dBu")
    
    def manual_save_states(self, event=None):
        """Manually save current microphone states"""
        print(f"manual_save_states called - saving {len(self.mike_states)} states")
        
        success = self._save_microphone_states()
        print(f"Save result: {success}")
        
        if success:
            messagebox.showinfo(
                "Éxito",
                f"Estados guardados correctamente.\n\nArchivo: {self.states_file}\n\nLos estados se cargarán automáticamente al reiniciar la aplicación."
            )
        else:
            messagebox.showerror(
                "Error",
                "No se pudieron guardar los estados."
            )
        return "break"
    
    def quit_application(self):
        """Clean up and quit the application"""
        if messagebox.askokcancel("Salir", "¿Está seguro que desea salir?"):
            # Save states before exiting
            print("Saving states before exit...")
            if self._save_microphone_states():
                print("✓ States saved successfully before exit")
            else:
                print("✗ Failed to save states before exit")
            
            self.cleanup()
            self.root.destroy()
    
    def cleanup(self):
        """Clean up DAC resources - set all outputs to 0V"""
        if I2C_AVAILABLE and self.dac_chips:
            try:
                for chip_idx, dac in enumerate(self.dac_chips):
                    if dac is not None:
                        for ch_name in ['a', 'b', 'c', 'd']:
                            try:
                                ch = getattr(dac, f'channel_{ch_name}')
                                ch.value = 0
                            except Exception:
                                pass
                print("DAC controller cleanup completed - all 32 channels set to 0V")
            except Exception as e:
                print(f"Error during DAC cleanup: {e}")


def main():
    """Main entry point"""
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print("\n" + "="*60)
        print("ERROR: No se puede iniciar la interfaz gráfica")
        print("="*60)
        print(f"\nDetalle: {e}\n")
        print("Este error ocurre porque no hay un servidor de display (X11) disponible.")
        print("\nSoluciones posibles:\n")
        print("1. Si está conectado por SSH:")
        print("   - Reconecte usando: ssh -X usuario@raspberry")
        print("   - O instale VNC para acceso gráfico remoto\n")
        print("2. Si está en la Raspberry Pi directamente:")
        print("   - Asegúrese de estar en el entorno gráfico (escritorio)")
        print("   - Ejecute 'startx' si está en consola de texto\n")
        print("3. Para ejecutar sin interfaz gráfica:")
        print("   - Este programa requiere GUI y no puede ejecutarse en modo headless")
        print("="*60 + "\n")
        sys.exit(1)
    
    app = DACControllerApp(root)
    
    # Handle window close event
    root.protocol("WM_DELETE_WINDOW", app.quit_application)
    
    # Start the GUI event loop
    root.mainloop()


if __name__ == "__main__":
    main()
