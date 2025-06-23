import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import threading
import time
import math
import datetime
import random

class AirlockGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ERC Airlock HIL Simulator - Mars Mission Control")
        self.root.geometry("1800x1000")
        
        # ERC Mars Theme Colors (from STYLE.MD)
        self.colors = {
            'mars_orange': '#FF6B35',
            'deep_mars': '#E55100', 
            'martian_sunset': '#FF8F65',
            'space_black': '#1A1A1A',
            'rover_dark': '#2D2D2D',
            'shadow_brown': '#3E2723',
            'mission_yellow': '#FFB300',
            'system_green': '#4CAF50',
            'alert_red': '#F44336',
            'tech_blue': '#2196F3',
            'primary_text': '#FFFFFF',
            'secondary_text': '#CCCCCC'
        }
        
        self.root.configure(bg=self.colors['space_black'])
        
        # Serial connection
        self.ser = None
        self.connected = False
        
        # Airlock dimensions (scaled down for display)
        self.scale = 0.5
        self.airlock_width = 1376 * self.scale
        self.front_zone_width = 408 * self.scale
        self.middle_zone_width = 560 * self.scale
        self.back_zone_width = 408 * self.scale
        self.airlock_height = 175
        
        # Rover properties - enhanced for ERC theme
        self.rover_width = 638 * self.scale * 0.4
        self.rover_height = 35
        self.rover_x = 50
        self.rover_y = self.airlock_height // 2 + 50
        self.rover_dragging = False
        
        # Gate properties
        self.gate_width = 10
        self.gate_a_x = self.front_zone_width
        self.gate_b_x = self.front_zone_width + self.middle_zone_width
        self.gate_a_open = False
        self.gate_b_open = False
        self.gate_a_moving = False
        self.gate_b_moving = False
        self.gate_animation_progress_a = 0
        self.gate_animation_progress_b = 0
        
        # Enhanced animation properties
        self.gate_a_animation_time = 0
        self.gate_b_animation_time = 0
        self.gate_animation_duration = 3.0
        self.gate_a_particles = []
        self.gate_b_particles = []
        
        # Gate movement direction tracking
        self.gate_a_target_state = False
        self.gate_b_target_state = False
        
        # Drawing positions
        self.start_x = 100
        self.start_y = 50
        
        # Sensor states
        self.sensor_states = {
            'PRESENCE_FRONT': False,
            'PRESENCE_MIDDLE': False,
            'PRESENCE_BACK': False,
            'GATE_SAFETY_A': False,
            'GATE_SAFETY_B': False,
            'GATE_MOVING_A': False,
            'GATE_MOVING_B': False
        }
        
        # Gate requests from Arduino
        self.gate_requests = {
            'GATE_REQUEST_A': False,
            'GATE_REQUEST_B': False
        }
        
        # Anti-flicker system
        self.update_pending = False
        self.last_update_time = 0
        self.min_update_interval = 0.1
        
        # Control flags
        self.needs_redraw = True
        
        self.setup_gui()
        self.start_reading_thread()
        self.start_animation_thread()
        self.start_sensor_update_thread()
        self.start_sensor_display_update_thread()
        
    def setup_gui(self):
        # Main title with ERC styling
        title_frame = tk.Frame(self.root, bg=self.colors['space_black'])
        title_frame.pack(pady=15)
        
        # ERC mission header
        title_label = tk.Label(title_frame, text="EUROPEAN ROVER CHALLENGE", 
                              font=('Arial', 28, 'bold'), 
                              fg=self.colors['mars_orange'], bg=self.colors['space_black'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Mars Airlock HIL Simulator", 
                                 font=('Arial', 16), 
                                 fg=self.colors['secondary_text'], bg=self.colors['space_black'])
        subtitle_label.pack()
        
        # Connection frame with Mars theme
        conn_frame = tk.Frame(self.root, bg=self.colors['rover_dark'], relief='raised', bd=2)
        conn_frame.pack(pady=10, padx=20, fill='x')
        
        # Internal padding frame
        conn_inner = tk.Frame(conn_frame, bg=self.colors['rover_dark'])
        conn_inner.pack(pady=8, padx=15, fill='x')
        
        tk.Label(conn_inner, text="Mission Control Link:", 
                font=('Arial', 12, 'bold'), fg=self.colors['primary_text'], bg=self.colors['rover_dark']).pack(side=tk.LEFT, padx=5)
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_inner, textvariable=self.port_var, 
                                      values=self.get_serial_ports(), width=15)
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        # Styled buttons with ERC theme
        self.connect_btn = tk.Button(conn_inner, text="ESTABLISH LINK", 
                                   command=self.toggle_connection,
                                   bg=self.colors['system_green'], fg=self.colors['primary_text'], 
                                   font=('Arial', 10, 'bold'), relief='raised', bd=3)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = tk.Button(conn_inner, text="SCAN PORTS", 
                                   command=self.refresh_ports,
                                   bg=self.colors['tech_blue'], fg=self.colors['primary_text'], 
                                   font=('Arial', 10, 'bold'), relief='raised', bd=3)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label with enhanced styling
        self.status_label = tk.Label(self.root, text="◯ COMMUNICATION OFFLINE", 
                                   font=('Arial', 14, 'bold'), fg=self.colors['alert_red'], 
                                   bg=self.colors['space_black'])
        self.status_label.pack(pady=5)
        
        # Create main content frame with Mars theme
        main_frame = tk.Frame(self.root, bg=self.colors['space_black'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15)
        
        # Left column for airlock visualization
        left_frame = tk.Frame(main_frame, bg=self.colors['space_black'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Mission control header
        mission_header = tk.Label(left_frame, text="🚀 MARS SURFACE OPERATIONS", 
                                 font=('Arial', 16, 'bold'), 
                                 fg=self.colors['mars_orange'], bg=self.colors['space_black'])
        mission_header.pack(pady=(0, 10))
        
        # Canvas with Mars atmosphere background
        self.canvas = tk.Canvas(left_frame, width=1000, height=250, 
                               bg=self.colors['deep_mars'], highlightthickness=0, relief='sunken', bd=3)
        self.canvas.pack(pady=5)
        
        # Make canvas focusable for keyboard events
        self.canvas.focus_set()
        
        # Sensor status frame with enhanced ERC styling
        sensor_frame = tk.LabelFrame(left_frame, text="📡 SENSOR TELEMETRY", 
                                   font=('Arial', 14, 'bold'), 
                                   fg=self.colors['primary_text'], bg=self.colors['rover_dark'],
                                   relief='raised', bd=3, labelanchor='n')
        sensor_frame.pack(pady=(10, 10), fill='x')
        
        # Create horizontal sensor table with Mars theme
        self.sensor_labels = {}
        
        # Main container for horizontal layout
        table_container = tk.Frame(sensor_frame, bg=self.colors['rover_dark'])
        table_container.pack(fill='x', padx=15, pady=10)
        
        # First row sensors
        first_row_sensors = ['PRESENCE_FRONT', 'PRESENCE_MIDDLE', 'PRESENCE_BACK', 
                            'GATE_SAFETY_A', 'GATE_SAFETY_B']
        
        # First row container
        first_row = tk.Frame(table_container, bg=self.colors['rover_dark'])
        first_row.pack(fill='x', pady=(0, 5))
        
        # Create first row with equal distribution
        for i, sensor_name in enumerate(first_row_sensors):
            sensor_col = tk.Frame(first_row, bg=self.colors['rover_dark'])
            sensor_col.pack(side=tk.LEFT, fill='x', expand=True, padx=3)
            
            # Sensor name label with Mars styling
            name_label = tk.Label(sensor_col, text=sensor_name, 
                                 font=('Arial', 9, 'bold'), 
                                 fg=self.colors['primary_text'], bg=self.colors['shadow_brown'],
                                 relief='raised', bd=2, pady=3)
            name_label.pack(fill='x')
            
            # State label with enhanced styling
            state_label = tk.Label(sensor_col, text="OFFLINE", 
                                  font=('Arial', 10, 'bold'), 
                                  fg=self.colors['secondary_text'], bg=self.colors['space_black'],
                                  relief='sunken', bd=2, pady=4)
            state_label.pack(fill='x')
            
            self.sensor_labels[sensor_name] = state_label
        
        # Second row sensors
        second_row_sensors = ['GATE_MOVING_A', 'GATE_MOVING_B', 'GATE_REQUEST_A', 'GATE_REQUEST_B']
        
        # Second row container
        second_row = tk.Frame(table_container, bg=self.colors['rover_dark'])
        second_row.pack(fill='x', pady=(5, 0))
        
        # Create second row with equal distribution
        for i, sensor_name in enumerate(second_row_sensors):
            sensor_col = tk.Frame(second_row, bg=self.colors['rover_dark'])
            sensor_col.pack(side=tk.LEFT, fill='x', expand=True, padx=3)
            
            # Sensor name label
            name_label = tk.Label(sensor_col, text=sensor_name, 
                                 font=('Arial', 9, 'bold'), 
                                 fg=self.colors['primary_text'], bg=self.colors['shadow_brown'],
                                 relief='raised', bd=2, pady=3)
            name_label.pack(fill='x')
            
            # State label
            state_label = tk.Label(sensor_col, text="OFFLINE", 
                                  font=('Arial', 10, 'bold'), 
                                  fg=self.colors['secondary_text'], bg=self.colors['space_black'],
                                  relief='sunken', bd=2, pady=4)
            state_label.pack(fill='x')
            
            self.sensor_labels[sensor_name] = state_label
        
        # Add empty column to balance the second row
        empty_col = tk.Frame(second_row, bg=self.colors['rover_dark'])
        empty_col.pack(side=tk.LEFT, fill='x', expand=True, padx=3)
        
        # Control instructions with Mars theme
        instructions = tk.Label(left_frame, 
                              text="🎮 ROVER CONTROL: Drag rover or use arrow keys • Click canvas for keyboard control",
                              font=('Arial', 11, 'bold'), fg=self.colors['mission_yellow'], 
                              bg=self.colors['space_black'])
        instructions.pack(pady=10)
        
        # Right column for mission terminal with enhanced styling
        right_frame = tk.Frame(main_frame, bg=self.colors['shadow_brown'], width=450, relief='raised', bd=3)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(15, 0))
        right_frame.pack_propagate(False)
        
        # Mission Terminal frame
        terminal_frame = tk.LabelFrame(right_frame, text="🖥️ MISSION CONTROL TERMINAL", 
                                     font=('Arial', 14, 'bold'), 
                                     fg=self.colors['primary_text'], bg=self.colors['shadow_brown'],
                                     relief='raised', bd=3, labelanchor='n')
        terminal_frame.pack(fill=tk.BOTH, expand=True, pady=12, padx=8)
        
        # Terminal output area with Mars theme
        self.terminal_output = scrolledtext.ScrolledText(terminal_frame, 
                                                        height=28, width=45,
                                                        bg=self.colors['space_black'], fg=self.colors['system_green'],
                                                        font=('Consolas', 9),
                                                        state=tk.DISABLED,
                                                        wrap=tk.WORD, relief='sunken', bd=2)
        self.terminal_output.pack(pady=8, padx=8, fill=tk.BOTH, expand=True)
        
        # Terminal input frame
        input_frame = tk.Frame(terminal_frame, bg=self.colors['shadow_brown'])
        input_frame.pack(fill=tk.X, pady=8, padx=8)
        
        # Command entry with styling
        tk.Label(input_frame, text="CMD:", 
                font=('Arial', 10, 'bold'), fg=self.colors['primary_text'], bg=self.colors['shadow_brown']).pack(side=tk.LEFT)
        
        self.command_entry = tk.Entry(input_frame, font=('Consolas', 10),
                                     bg=self.colors['rover_dark'], fg=self.colors['primary_text'], 
                                     insertbackground=self.colors['mars_orange'], relief='sunken', bd=2)
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        self.command_entry.bind('<Return>', self.send_command)
        
        # Send button with Mars styling
        send_btn = tk.Button(input_frame, text="TRANSMIT", 
                           command=self.send_command,
                           bg=self.colors['mars_orange'], fg=self.colors['primary_text'], 
                           font=('Arial', 9, 'bold'), relief='raised', bd=2)
        send_btn.pack(side=tk.RIGHT)
        
        # Terminal control buttons with enhanced styling
        control_frame = tk.Frame(terminal_frame, bg=self.colors['shadow_brown'])
        control_frame.pack(fill=tk.X, pady=(0, 8), padx=8)
        
        clear_btn = tk.Button(control_frame, text="CLEAR LOG", 
                            command=self.clear_terminal,
                            bg=self.colors['alert_red'], fg=self.colors['primary_text'], 
                            font=('Arial', 9, 'bold'), relief='raised', bd=2)
        clear_btn.pack(side=tk.LEFT)
        
        auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_check = tk.Checkbutton(control_frame, text="Auto Scroll",
                                               variable=auto_scroll_var,
                                               bg=self.colors['shadow_brown'], fg=self.colors['primary_text'],
                                               selectcolor=self.colors['rover_dark'], font=('Arial', 9))
        self.auto_scroll_check.pack(side=tk.RIGHT)
        self.auto_scroll = auto_scroll_var
        
        # Draw initial airlock
        self.draw_airlock_static()
        self.update_display()
        
        # Bind controls
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyPress>", self.on_key_press)
        self.canvas.bind("<Button-1>", self.on_canvas_focus, add='+')
        
        # Add welcome message to terminal with ERC theme
        self.add_terminal_message("=== ERC MARS MISSION CONTROL ACTIVATED ===", "INFO")
        self.add_terminal_message("🚀 European Rover Challenge Airlock System Online", "INFO")
        self.add_terminal_message("📡 Awaiting ground control commands...", "INFO")
        
        # Debug: Show initial gate states
        print(f"DEBUG: Initial gate states:")
        print(f"DEBUG: Gate A - Open: {self.gate_a_open}, Moving: {self.gate_a_moving}, Target: {self.gate_a_target_state}")
        print(f"DEBUG: Gate B - Open: {self.gate_b_open}, Moving: {self.gate_b_moving}, Target: {self.gate_b_target_state}")
        print(f"DEBUG: Gate requests: {self.gate_requests}")
    
    def add_terminal_message(self, message, msg_type="DATA"):
        """Add a message to the terminal with timestamp and ERC styling"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        self.terminal_output.config(state=tk.NORMAL)
        
        # Enhanced color coding for ERC theme
        if msg_type == "SENT":
            color_tag = "sent"
            prefix = "🔼 TX: "
        elif msg_type == "RECEIVED":
            color_tag = "received"
            prefix = "🔽 RX: "
        elif msg_type == "INFO":
            color_tag = "info"
            prefix = "ℹ️  SYS: "
        elif msg_type == "ERROR":
            color_tag = "error"
            prefix = "⚠️  ERR: "
        else:
            color_tag = "default"
            prefix = "📊 DAT: "
        
        # Configure ERC theme color tags
        self.terminal_output.tag_configure("sent", foreground=self.colors['mission_yellow'])
        self.terminal_output.tag_configure("received", foreground=self.colors['system_green'])
        self.terminal_output.tag_configure("info", foreground=self.colors['tech_blue'])
        self.terminal_output.tag_configure("error", foreground=self.colors['alert_red'])
        self.terminal_output.tag_configure("default", foreground=self.colors['mars_orange'])
        
        formatted_message = f"[{timestamp}] {prefix}{message}\n"
        self.terminal_output.insert(tk.END, formatted_message, color_tag)
        
        # Auto scroll if enabled
        if self.auto_scroll.get():
            self.terminal_output.see(tk.END)
        
        self.terminal_output.config(state=tk.DISABLED)
    
    def send_command(self, event=None):
        """Send a custom command through the terminal"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        if not self.connected:
            self.add_terminal_message("Not connected to serial port!", "ERROR")
            return
        
        # Add delimiters if not present
        if not command.startswith('<'):
            command = '<' + command
        if not command.endswith('>'):
            command = command + '>'
        
        try:
            self.ser.write(command.encode())
            self.add_terminal_message(command, "SENT")
            self.command_entry.delete(0, tk.END)
        except serial.SerialException as e:
            self.add_terminal_message(f"Failed to send command: {str(e)}", "ERROR")
    
    def clear_terminal(self):
        """Clear the terminal output"""
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.delete(1.0, tk.END)
        self.terminal_output.config(state=tk.DISABLED)
        self.add_terminal_message("Terminal cleared", "INFO")
    
    def draw_airlock_static(self):
        """Draw the static parts of the airlock with ERC Mars theme"""
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw Martian landscape background
        canvas_width = 1000
        canvas_height = 250
        
        # Create layered Martian mountains in background
        mountain_layers = [
            # Far mountains (lighter, more distant)
            {'points': [0, 180, 200, 160, 400, 170, 600, 150, 800, 165, 1000, 175, 1000, 250, 0, 250], 'color': '#B8724C'},
            # Mid mountains
            {'points': [0, 200, 150, 190, 350, 195, 550, 180, 750, 190, 950, 185, 1000, 190, 1000, 250, 0, 250], 'color': '#A8624C'},
            # Near mountains (darker)
            {'points': [0, 220, 100, 210, 300, 215, 500, 205, 700, 210, 900, 205, 1000, 210, 1000, 250, 0, 250], 'color': '#8B4A2C'}
        ]
        
        for layer in mountain_layers:
            self.canvas.create_polygon(layer['points'], fill=layer['color'], outline="", tags="static")
        
        # Add distant atmospheric haze effect
        for i in range(5):
            alpha_val = 30 - i * 5
            haze_color = f"#{alpha_val:02x}{alpha_val//2:02x}00"
            y_pos = 50 + i * 30
            self.canvas.create_rectangle(0, y_pos, canvas_width, y_pos + 20, 
                                       fill=haze_color, outline="", stipple='gray25', tags="static")
        
        # Draw Martian surface with rocky texture
        surface_y = 220
        # Base surface
        self.canvas.create_rectangle(0, surface_y, canvas_width, canvas_height, 
                                   fill=self.colors['shadow_brown'], outline="", tags="static")
        
        # Add rocky surface details
        for i in range(30):
            rock_x = random.randint(0, canvas_width)
            rock_y = random.randint(surface_y, canvas_height - 10)
            rock_size = random.randint(2, 6)
            rock_shade = random.choice([self.colors['rover_dark'], '#4A3426', '#5A3426'])
            self.canvas.create_oval(rock_x, rock_y, rock_x + rock_size, rock_y + rock_size,
                                  fill=rock_shade, outline="", tags="static")
        
        # Draw main airlock structure with enhanced Mars base design
        chamber_y_offset = 15
        chamber_height = self.airlock_height - 30
        
        # Airlock foundation platform
        platform_y = self.start_y + self.airlock_height
        self.canvas.create_rectangle(self.start_x - 10, platform_y, 
                                   self.start_x + self.airlock_width + 10, platform_y + 15,
                                   fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=2, tags="static")
        
        # Main airlock structure with reinforced Mars base look
        self.canvas.create_rectangle(self.start_x - 8, self.start_y - 8, 
                                   self.start_x + self.airlock_width + 8, 
                                   self.start_y + self.airlock_height + 8,
                                   fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=4, tags="static")
        
        # Front zone (Mars Environment) - Red theme for Martian surface
        front_x = self.start_x
        front_w = self.front_zone_width
        
        self.canvas.create_rectangle(front_x, self.start_y + chamber_y_offset, 
                                   front_x + front_w, 
                                   self.start_y + chamber_height,
                                   fill='#3a1a1a', outline=self.colors['alert_red'], width=3, tags="static")
        
        # Mars environment details for front chamber
        for i in range(4):
            y_pos = self.start_y + 35 + i * 30
            # Left side environmental sensors
            self.canvas.create_oval(front_x + 8, y_pos, front_x + 18, y_pos + 10,
                                  fill=self.colors['alert_red'], outline=self.colors['primary_text'], tags="static")
            # Right side environmental sensors
            self.canvas.create_oval(front_x + front_w - 18, y_pos, front_x + front_w - 8, y_pos + 10,
                                  fill=self.colors['alert_red'], outline=self.colors['primary_text'], tags="static")
        
        # Chamber identification
        self.canvas.create_text(front_x + front_w/2, self.start_y + 25,
                              text="MARS SURFACE", fill=self.colors['alert_red'], 
                              font=('Arial', 14, 'bold'), tags="static")
        self.canvas.create_text(front_x + front_w/2, self.start_y + 40,
                              text="Martian Environment", fill=self.colors['secondary_text'], 
                              font=('Arial', 10), tags="static")
        
        # Middle zone (Transition Chamber) - Orange theme for Mars adaptation
        middle_x = self.start_x + self.front_zone_width
        middle_w = self.middle_zone_width
        
        self.canvas.create_rectangle(middle_x, self.start_y + chamber_y_offset,
                                   middle_x + middle_w,
                                   self.start_y + chamber_height,
                                   fill='#4a2a1a', outline=self.colors['mars_orange'], width=3, tags="static")
        
        # Transition zone details - pressure adaptation systems
        for i in range(6):
            ring_x = middle_x + 30 + i * 80
            ring_y = self.start_y + chamber_height//2
            # Pressure rings
            for j in range(3):
                radius = 8 + j * 4
                self.canvas.create_oval(ring_x - radius, ring_y - radius//2,
                                      ring_x + radius, ring_y + radius//2,
                                      fill='', outline=self.colors['mars_orange'], width=1, tags="static")
        
        # Atmospheric processing indicators
        for i in range(4):
            x_pos = middle_x + 40 + i * 120
            self.canvas.create_line(x_pos, self.start_y + 25, x_pos, self.start_y + chamber_height - 15,
                                  fill=self.colors['mission_yellow'], width=2, dash=(8, 4), tags="static")
        
        self.canvas.create_text(middle_x + middle_w/2, self.start_y + 25,
                              text="TRANSITION CHAMBER", fill=self.colors['mars_orange'], 
                              font=('Arial', 14, 'bold'), tags="static")
        self.canvas.create_text(middle_x + middle_w/2, self.start_y + 40,
                              text="Atmosphere Processing", fill=self.colors['secondary_text'], 
                              font=('Arial', 10), tags="static")
        
        # Back zone (Earth Habitat) - Blue theme for pressurized habitat
        back_x = self.start_x + self.front_zone_width + self.middle_zone_width
        back_w = self.back_zone_width
        
        self.canvas.create_rectangle(back_x, self.start_y + chamber_y_offset,
                                   back_x + back_w,
                                   self.start_y + chamber_height,
                                   fill='#1a3a5c', outline=self.colors['tech_blue'], width=3, tags="static")
        
        # Habitat environment indicators
        for i in range(3):
            y_pos = self.start_y + 35 + i * 35
            # Life support systems
            self.canvas.create_rectangle(back_x + 15, y_pos, back_x + 25, y_pos + 20,
                                       fill=self.colors['tech_blue'], outline=self.colors['primary_text'], tags="static")
            self.canvas.create_rectangle(back_x + back_w - 25, y_pos, back_x + back_w - 15, y_pos + 20,
                                       fill=self.colors['tech_blue'], outline=self.colors['primary_text'], tags="static")
        
        # Habitat entry indicators
        for i in range(2):
            arrow_x = back_x + 50 + i * 80
            # Habitat entry arrows
            self.canvas.create_polygon(arrow_x, self.start_y + 80,
                                     arrow_x + 20, self.start_y + 70,
                                     arrow_x + 15, self.start_y + 75,
                                     arrow_x + 30, self.start_y + 75,
                                     arrow_x + 30, self.start_y + 85,
                                     arrow_x + 15, self.start_y + 85,
                                     arrow_x + 20, self.start_y + 90,
                                     fill=self.colors['tech_blue'], outline=self.colors['primary_text'], tags="static")
        
        self.canvas.create_text(back_x + back_w/2, self.start_y + 25,
                              text="HABITAT ENTRY", fill=self.colors['tech_blue'], 
                              font=('Arial', 14, 'bold'), tags="static")
        self.canvas.create_text(back_x + back_w/2, self.start_y + 40,
                              text="Earth-like Environment", fill=self.colors['secondary_text'], 
                              font=('Arial', 10), tags="static")
        
        # Add ERC mission patch/logo area
        logo_x = 20
        logo_y = 20
        self.canvas.create_oval(logo_x, logo_y, logo_x + 60, logo_y + 60,
                              fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=3, tags="static")
        self.canvas.create_text(logo_x + 30, logo_y + 20, text="ERC", 
                              font=('Arial', 12, 'bold'), fill=self.colors['mars_orange'], tags="static")
        self.canvas.create_text(logo_x + 30, logo_y + 40, text="2024", 
                              font=('Arial', 10), fill=self.colors['secondary_text'], tags="static")
    
    def update_display(self):
        """Update only the dynamic parts of the display - now throttled"""
        self.request_update()
    
    def update_gates_only(self):
        """Update only the gates and particles - now throttled"""  
        self.request_update()
    
    def draw_sensor_zones(self):
        # Calculate sensor line positions at center of each zone
        front_sensor_x = self.start_x + self.front_zone_width / 2
        middle_sensor_x = self.start_x + self.front_zone_width + self.middle_zone_width / 2
        back_sensor_x = self.start_x + self.front_zone_width + self.middle_zone_width + self.back_zone_width / 2
        
        # HIGH CONTRAST sensor lines - much more visible when triggered
        # Front presence sensor line
        if self.sensor_states['PRESENCE_FRONT']:
            # ACTIVE - bright pulsing green with thick line
            pulse = abs(math.sin(time.time() * 6)) * 0.4 + 0.6
            line_color = f"#00{int(255*pulse):02x}00"
            text_color = f"#00{int(255*pulse):02x}00"
            line_width = 8
        else:
            # INACTIVE - very dim and thin
            line_color = '#1a1a1a'
            text_color = '#333333'
            line_width = 2
            
        self.canvas.create_line(front_sensor_x, self.start_y + 20,
                              front_sensor_x, self.start_y + self.airlock_height - 20,
                              fill=line_color, width=line_width, dash=(8, 4), tags="sensor_zones")
        self.canvas.create_text(front_sensor_x - 25, self.start_y + 10,
                              text="FRONT", fill=text_color,
                              font=('Arial', 10, 'bold'), tags="sensor_zones")
        
        # Middle presence sensor line
        if self.sensor_states['PRESENCE_MIDDLE']:
            # ACTIVE - bright pulsing green
            pulse = abs(math.sin(time.time() * 6)) * 0.4 + 0.6
            line_color = f"#00{int(255*pulse):02x}00"
            text_color = f"#00{int(255*pulse):02x}00"
            line_width = 8
        else:
            # INACTIVE - very dim
            line_color = '#1a1a1a'
            text_color = '#333333'
            line_width = 2
            
        self.canvas.create_line(middle_sensor_x, self.start_y + 20,
                              middle_sensor_x, self.start_y + self.airlock_height - 20,
                              fill=line_color, width=line_width, dash=(8, 4), tags="sensor_zones")
        self.canvas.create_text(middle_sensor_x - 25, self.start_y + 10,
                              text="MIDDLE", fill=text_color,
                              font=('Arial', 10, 'bold'), tags="sensor_zones")
        
        # Back presence sensor line
        if self.sensor_states['PRESENCE_BACK']:
            # ACTIVE - bright pulsing green
            pulse = abs(math.sin(time.time() * 6)) * 0.4 + 0.6
            line_color = f"#00{int(255*pulse):02x}00"
            text_color = f"#00{int(255*pulse):02x}00"
            line_width = 8
        else:
            # INACTIVE - very dim
            line_color = '#1a1a1a'
            text_color = '#333333'
            line_width = 2
            
        self.canvas.create_line(back_sensor_x, self.start_y + 20,
                              back_sensor_x, self.start_y + self.airlock_height - 20,
                              fill=line_color, width=line_width, dash=(8, 4), tags="sensor_zones")
        self.canvas.create_text(back_sensor_x - 25, self.start_y + 10,
                              text="BACK", fill=text_color,
                              font=('Arial', 10, 'bold'), tags="sensor_zones")
        
        # HIGH CONTRAST Gate safety zones 
        safety_zone_width = 60
        
        # Gate A safety zone
        if self.sensor_states['GATE_SAFETY_A']:
            # ACTIVE - bright pulsing red
            pulse = abs(math.sin(time.time() * 8)) * 0.3 + 0.7
            zone_color = f"#{int(255*pulse):02x}0000"
            text_color = f"#{int(255*pulse):02x}0000"
            zone_width = 5
        else:
            # INACTIVE - very dim
            zone_color = '#2a1a1a'
            text_color = '#444444'
            zone_width = 2
            
        self.canvas.create_rectangle(self.start_x + self.gate_a_x - safety_zone_width/2, self.start_y,
                                   self.start_x + self.gate_a_x + safety_zone_width/2,
                                   self.start_y + self.airlock_height,
                                   fill='', outline=zone_color, width=zone_width, dash=(3, 3), tags="sensor_zones")
        self.canvas.create_text(self.start_x + self.gate_a_x, self.start_y + self.airlock_height + 20,
                              text="Gate A Safety", fill=text_color,
                              font=('Arial', 10, 'bold'), tags="sensor_zones")
        
        # Gate B safety zone
        if self.sensor_states['GATE_SAFETY_B']:
            # ACTIVE - bright pulsing red
            pulse = abs(math.sin(time.time() * 8)) * 0.3 + 0.7
            zone_color = f"#{int(255*pulse):02x}0000"
            text_color = f"#{int(255*pulse):02x}0000"
            zone_width = 5
        else:
            # INACTIVE - very dim
            zone_color = '#2a1a1a'
            text_color = '#444444'
            zone_width = 2
            
        self.canvas.create_rectangle(self.start_x + self.gate_b_x - safety_zone_width/2, self.start_y,
                                   self.start_x + self.gate_b_x + safety_zone_width/2,
                                   self.start_y + self.airlock_height,
                                   fill='', outline=zone_color, width=zone_width, dash=(3, 3), tags="sensor_zones")
        self.canvas.create_text(self.start_x + self.gate_b_x, self.start_y + self.airlock_height + 20,
                              text="Gate B Safety", fill=text_color,
                              font=('Arial', 10, 'bold'), tags="sensor_zones")
    
    def check_collision(self, new_x):
        # No collision detection - allow free movement for testing
        return False
    
    def on_canvas_click(self, event):
        # Set focus to canvas for keyboard events
        self.canvas.focus_set()
        
        # Check if click is on rover
        rover_left = self.rover_x - self.rover_width/2
        rover_right = self.rover_x + self.rover_width/2
        rover_top = self.rover_y - self.rover_height/2
        rover_bottom = self.rover_y + self.rover_height/2
        
        if rover_left <= event.x <= rover_right and rover_top <= event.y <= rover_bottom:
            self.rover_dragging = True
            self.drag_start_x = event.x - self.rover_x
            print("Rover grabbed for dragging")
        else:
            print(f"Clicked at ({event.x}, {event.y}), rover at ({self.rover_x}, {self.rover_y})")
    
    def on_canvas_drag(self, event):
        if self.rover_dragging:
            new_x = event.x - self.drag_start_x
            self.rover_x = new_x
            self.update_sensors()
            print(f"Rover moved to x={self.rover_x}")
    
    def on_canvas_release(self, event):
        if self.rover_dragging:
            print("Rover released")
        self.rover_dragging = False
    
    def on_key_press(self, event):
        step = 1  # Reduced from 15 to 5 pixels for more precise control
        new_x = self.rover_x
        
        if event.keysym == 'Left':
            new_x = self.rover_x - step
            print("Left arrow pressed")
        elif event.keysym == 'Right':
            new_x = self.rover_x + step
            print("Right arrow pressed")
        else:
            return
        
        self.rover_x = new_x
        self.update_sensors()
        print(f"Rover moved to x={self.rover_x}")
    
    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def refresh_ports(self):
        self.port_combo['values'] = self.get_serial_ports()
    
    def toggle_connection(self):
        if not self.connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Mission Control Error", "Please select a communication port")
            return
        
        try:
            self.ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
            self.connected = True
            self.connect_btn.config(text="TERMINATE LINK", bg=self.colors['alert_red'])
            self.status_label.config(text=f"🛰️ MISSION CONTROL LINK ACTIVE - {port}", fg=self.colors['system_green'])
            self.add_terminal_message(f"🚀 Mission Control Link Established on {port} at 115200 baud", "INFO")
            messagebox.showinfo("ERC Mission Control", f"Communication link established with {port}")
            # Send initial sensor states
            self.send_data()
        except serial.SerialException as e:
            error_msg = f"Failed to establish communication link: {str(e)}"
            self.add_terminal_message(error_msg, "ERROR")
            messagebox.showerror("Mission Control Error", error_msg)
    
    def disconnect_serial(self):
        if self.ser:
            self.ser.close()
            self.ser = None
        self.connected = False
        self.connect_btn.config(text="ESTABLISH LINK", bg=self.colors['system_green'])
        self.status_label.config(text="◯ COMMUNICATION OFFLINE", fg=self.colors['alert_red'])
        self.add_terminal_message("🔌 Mission Control Link Terminated", "INFO")
    
    def send_data(self):
        if not self.connected or not self.ser:
            return
        
        # Format data as expected by Arduino
        data_parts = []
        for name, state in self.sensor_states.items():
            if name not in ['GATE_MOVING_A', 'GATE_MOVING_B']:  # Don't send internal states
                value = "1" if state else "0"
                data_parts.append(f"{name}:{value}")
        
        # Add gate moving states
        data_parts.append(f"GATE_MOVING_A:{'1' if self.gate_a_moving else '0'}")
        data_parts.append(f"GATE_MOVING_B:{'1' if self.gate_b_moving else '0'}")
        
        message = "<" + ",".join(data_parts) + ">"
        
        try:
            self.ser.write(message.encode())
            self.add_terminal_message(message, "SENT")
        except serial.SerialException as e:
            error_msg = f"Failed to send data: {str(e)}"
            self.add_terminal_message(error_msg, "ERROR")
            messagebox.showerror("Error", error_msg)
    
    def read_arduino_data(self):
        if not self.connected or not self.ser:
            return
        
        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode().strip()
                print("LINE "+line)
                print(line.startswith('<'))
                
                print(line[-1])
                if line.startswith('<') and line.endswith('>'):
                    # Parse the received data
                    data = line[1:-1]  # Remove < and >
                    pairs = data.split(',')
                    for pair in pairs:
                        if ':' in pair:
                            name, value = pair.split(':')
                            if name in self.gate_requests:
                                old_value = self.gate_requests[name]
                                self.gate_requests[name] = value == '1'
                                print(f"DEBUG: {name} changed from {old_value} to {self.gate_requests[name]}")
                    
                    self.add_terminal_message(line, "RECEIVED")
                    print(f"Received: {line}")
                    print(f"DEBUG: Current gate requests: {self.gate_requests}")
                    self.process_gate_requests()
                elif line:  # Any other non-empty message
                    self.add_terminal_message(line, "RECEIVED")
        except serial.SerialException:
            pass
    
    def process_gate_requests(self):
        print(f"DEBUG: Processing gate requests...")
        print(f"DEBUG: Gate A - Request: {self.gate_requests['GATE_REQUEST_A']}, Open: {self.gate_a_open}, Moving: {self.gate_a_moving}, Target: {self.gate_a_target_state}")
        print(f"DEBUG: Gate B - Request: {self.gate_requests['GATE_REQUEST_B']}, Open: {self.gate_b_open}, Moving: {self.gate_b_moving}, Target: {self.gate_b_target_state}")
        
        # Process gate A request - allow direction changes during movement
        if self.gate_requests['GATE_REQUEST_A']:  # Request = 1: OPEN
            if not self.gate_a_moving:
                # Start opening if not moving and not fully open
                if not self.gate_a_open:
                    self.gate_a_target_state = True  # Opening
                    self.gate_a_moving = True
                    self.gate_a_animation_time = self.gate_animation_progress_a * self.gate_animation_duration
                    self.sensor_states['GATE_MOVING_A'] = True
                    print("Gate A: Starting to open (request = 1) with enhanced animation")
                    
                    # Create minimal initial particle (just 1)
                    initial_particles = self.create_gate_particles(self.gate_a_x, 'opening')[:1]  # Only 1 particle
                    self.gate_a_particles.extend(initial_particles)
                else:
                    print("DEBUG: Gate A already fully open - no movement needed")
            else:
                # Gate is moving - check if we need to change direction
                if not self.gate_a_target_state:  # Currently closing, switch to opening
                    self.gate_a_target_state = True  # Switch to opening
                    # Calculate new animation time to continue from current position
                    self.gate_a_animation_time = self.gate_animation_progress_a * self.gate_animation_duration
                    print(f"Gate A: Switching to opening mid-movement from progress {self.gate_animation_progress_a}")
                    
                    # Create particles for direction change
                    initial_particles = self.create_gate_particles(self.gate_a_x, 'opening')[:1]
                    self.gate_a_particles.extend(initial_particles)
                # If already opening, continue opening (no change needed)
        else:  # Request = 0: CLOSE
            if not self.gate_a_moving:
                # Start closing if not moving and not fully closed
                if self.gate_a_open:
                    self.gate_a_target_state = False  # Closing
                    self.gate_a_moving = True
                    self.gate_a_animation_time = (1.0 - self.gate_animation_progress_a) * self.gate_animation_duration
                    self.sensor_states['GATE_MOVING_A'] = True
                    print("Gate A: Starting to close (request = 0) with enhanced animation")
                    
                    # Create minimal initial particle (just 1)
                    initial_particles = self.create_gate_particles(self.gate_a_x, 'closing')[:1]  # Only 1 particle
                    self.gate_a_particles.extend(initial_particles)
                else:
                    print("DEBUG: Gate A already fully closed - no movement needed")
            else:
                # Gate is moving - check if we need to change direction
                if self.gate_a_target_state:  # Currently opening, switch to closing
                    self.gate_a_target_state = False  # Switch to closing
                    # Calculate new animation time to continue from current position
                    self.gate_a_animation_time = (1.0 - self.gate_animation_progress_a) * self.gate_animation_duration
                    print(f"Gate A: Switching to closing mid-movement from progress {self.gate_animation_progress_a}")
                    
                    # Create particles for direction change
                    initial_particles = self.create_gate_particles(self.gate_a_x, 'closing')[:1]
                    self.gate_a_particles.extend(initial_particles)
                # If already closing, continue closing (no change needed)
        
        # Process gate B request - allow direction changes during movement
        if self.gate_requests['GATE_REQUEST_B']:  # Request = 1: OPEN
            if not self.gate_b_moving:
                # Start opening if not moving and not fully open
                if not self.gate_b_open:
                    self.gate_b_target_state = True  # Opening
                    self.gate_b_moving = True
                    self.gate_b_animation_time = self.gate_animation_progress_b * self.gate_animation_duration
                    self.sensor_states['GATE_MOVING_B'] = True
                    print("Gate B: Starting to open (request = 1) with enhanced animation")
                    
                    # Create minimal initial particle (just 1)
                    initial_particles = self.create_gate_particles(self.gate_b_x, 'opening')[:1]  # Only 1 particle
                    self.gate_b_particles.extend(initial_particles)
                else:
                    print("DEBUG: Gate B already fully open - no movement needed")
            else:
                # Gate is moving - check if we need to change direction
                if not self.gate_b_target_state:  # Currently closing, switch to opening
                    self.gate_b_target_state = True  # Switch to opening
                    # Calculate new animation time to continue from current position
                    self.gate_b_animation_time = self.gate_animation_progress_b * self.gate_animation_duration
                    print(f"Gate B: Switching to opening mid-movement from progress {self.gate_animation_progress_b}")
                    
                    # Create particles for direction change
                    initial_particles = self.create_gate_particles(self.gate_b_x, 'opening')[:1]
                    self.gate_b_particles.extend(initial_particles)
                # If already opening, continue opening (no change needed)
        else:  # Request = 0: CLOSE
            if not self.gate_b_moving:
                # Start closing if not moving and not fully closed
                if self.gate_b_open:
                    self.gate_b_target_state = False  # Closing
                    self.gate_b_moving = True
                    self.gate_b_animation_time = (1.0 - self.gate_animation_progress_b) * self.gate_animation_duration
                    self.sensor_states['GATE_MOVING_B'] = True
                    print("Gate B: Starting to close (request = 0) with enhanced animation")
                    
                    # Create minimal initial particle (just 1)
                    initial_particles = self.create_gate_particles(self.gate_b_x, 'closing')[:1]  # Only 1 particle
                    self.gate_b_particles.extend(initial_particles)
                else:
                    print("DEBUG: Gate B already fully closed - no movement needed")
            else:
                # Gate is moving - check if we need to change direction
                if self.gate_b_target_state:  # Currently opening, switch to closing
                    self.gate_b_target_state = False  # Switch to closing
                    # Calculate new animation time to continue from current position
                    self.gate_b_animation_time = (1.0 - self.gate_animation_progress_b) * self.gate_animation_duration
                    print(f"Gate B: Switching to closing mid-movement from progress {self.gate_animation_progress_b}")
                    
                    # Create particles for direction change
                    initial_particles = self.create_gate_particles(self.gate_b_x, 'closing')[:1]
                    self.gate_b_particles.extend(initial_particles)
                # If already closing, continue closing (no change needed)
    
    def animate_gates(self):
        dt = 0.1  # Increased delta time to 100ms for smoother, less frequent updates
        gates_moving = False
        animation_changed = False  # Track if animation state actually changed
        
        # Animate gate A
        if self.gate_a_moving:
            gates_moving = True
            
            # Check safety during movement
            #safety_triggered = self.sensor_states['GATE_SAFETY_A']
            safety_triggered=False
            if self.gate_a_target_state:  # Opening
                # Always allow opening, even if safety is triggered
                old_progress = self.gate_animation_progress_a
                self.gate_a_animation_time += dt
                progress = min(self.gate_a_animation_time / self.gate_animation_duration, 1.0)
                self.gate_animation_progress_a = progress
                
                # Only mark as changed if progress actually changed significantly
                if abs(progress - old_progress) > 0.02:  # Increased threshold to 2%
                    animation_changed = True
                
                # Create particles during opening (further reduced frequency)
               
                
                if progress >= 1.0:
                    self.gate_animation_progress_a = 1.0
                    self.gate_a_open = True
                    self.gate_a_moving = False
                    self.gate_a_animation_time = 0
                    self.sensor_states['GATE_MOVING_A'] = False
                    animation_changed = True
                    print("Gate A: Fully opened with enhanced animation")
                    
                    # Create burst of particles when fully opened (minimal burst)
                    burst_particles = self.create_gate_particles(self.gate_a_x, 'opened')[:1]  # Only 1 particle
                    self.gate_a_particles.extend(burst_particles)
                    
            else:  # Closing
                # Stop closing if safety is triggered, but allow to continue when clear
                if not safety_triggered:
                    old_progress = self.gate_animation_progress_a
                    self.gate_a_animation_time += dt
                    progress = min(self.gate_a_animation_time / self.gate_animation_duration, 1.0)
                    self.gate_animation_progress_a = 1.0 - progress  # Reverse for closing
                    
                    # Only mark as changed if progress actually changed significantly
                    if abs((1.0 - progress) - old_progress) > 0.02:  # Increased threshold to 2%
                        animation_changed = True
                    
                    # Create particles during closing (minimal frequency)
                    if random.random() < 0.01:  # Reduced to 1% chance each frame
                        new_particles = self.create_gate_particles(self.gate_a_x, 'closing')
                        self.gate_a_particles.extend(new_particles)
                        animation_changed = True
                    
                    if progress >= 1.0:
                        self.gate_animation_progress_a = 0.0
                        self.gate_a_open = False
                        self.gate_a_moving = False
                        self.gate_a_animation_time = 0
                        self.sensor_states['GATE_MOVING_A'] = False
                        animation_changed = True
                        print("Gate A: Fully closed with enhanced animation")
                else:
                    print("Gate A: Closing paused - safety triggered")
        
        # Animate gate B (similar to gate A)
        if self.gate_b_moving:
            gates_moving = True
            
            # Check safety during movement
            #safety_triggered = self.sensor_states['GATE_SAFETY_B']
            safety_triggered=False
            if self.gate_b_target_state:  # Opening
                # Always allow opening, even if safety is triggered
                old_progress = self.gate_animation_progress_b
                self.gate_b_animation_time += dt
                progress = min(self.gate_b_animation_time / self.gate_animation_duration, 1.0)
                self.gate_animation_progress_b = progress
                
                # Only mark as changed if progress actually changed significantly
                if abs(progress - old_progress) > 0.02:  # Increased threshold to 2%
                    animation_changed = True
                
                # Create particles during opening (further reduced frequency)
                if random.random() < 0.02:  # Reduced to 2% chance each frame
                    new_particles = self.create_gate_particles(self.gate_b_x, 'opening')
                    self.gate_b_particles.extend(new_particles)
                    animation_changed = True
                
                if progress >= 1.0:
                    self.gate_animation_progress_b = 1.0
                    self.gate_b_open = True
                    self.gate_b_moving = False
                    self.gate_b_animation_time = 0
                    self.sensor_states['GATE_MOVING_B'] = False
                    animation_changed = True
                    print("Gate B: Fully opened with enhanced animation")
                    
                    # Create burst of particles when fully opened (minimal burst)
                    burst_particles = self.create_gate_particles(self.gate_b_x, 'opened')[:1]  # Only 1 particle
                    self.gate_b_particles.extend(burst_particles)
                    
            else:  # Closing
                # Stop closing if safety is triggered, but allow to continue when clear
                if not safety_triggered:
                    old_progress = self.gate_animation_progress_b
                    self.gate_b_animation_time += dt
                    progress = min(self.gate_b_animation_time / self.gate_animation_duration, 1.0)
                    self.gate_animation_progress_b = 1.0 - progress  # Reverse for closing
                    
                    # Only mark as changed if progress actually changed significantly
                    if abs((1.0 - progress) - old_progress) > 0.02:  # Increased threshold to 2%
                        animation_changed = True
                    
                    # Create particles during closing (minimal frequency)
                    if random.random() < 0.01:  # Reduced to 1% chance each frame
                        new_particles = self.create_gate_particles(self.gate_b_x, 'closing')
                        self.gate_b_particles.extend(new_particles)
                        animation_changed = True
                    
                    if progress >= 1.0:
                        self.gate_animation_progress_b = 0.0
                        self.gate_b_open = False
                        self.gate_b_moving = False
                        self.gate_b_animation_time = 0
                        self.sensor_states['GATE_MOVING_B'] = False
                        animation_changed = True
                        print("Gate B: Fully closed with enhanced animation")
                else:
                    print("Gate B: Closing paused - safety triggered")
        
        # Update particles and check if any exist
        if self.gate_a_particles or self.gate_b_particles:
            self.gate_a_particles = self.update_particles(self.gate_a_particles)
            self.gate_b_particles = self.update_particles(self.gate_b_particles)
            animation_changed = True
        
        # Only request update if something meaningful changed
        if animation_changed:
            self.request_update()
    
    def start_reading_thread(self):
        def read_loop():
            while True:
                self.read_arduino_data()
                time.sleep(0.05)  # Read every 50ms
        
        thread = threading.Thread(target=read_loop, daemon=True)
        thread.start()
    
    def start_animation_thread(self):
        def animation_loop():
            while True:
                self.animate_gates()
                time.sleep(0.1)  # Increased to 100ms for smoother, less frequent updates
        
        thread = threading.Thread(target=animation_loop, daemon=True)
        thread.start()
    
    def start_sensor_update_thread(self):
        def sensor_update_loop():
            while True:
                if self.connected:
                    self.send_data()
                time.sleep(0.1)  # Send sensor data every 100ms
        
        thread = threading.Thread(target=sensor_update_loop, daemon=True)
        thread.start()
    
    def start_sensor_display_update_thread(self):
        def sensor_display_update_loop():
            while True:
                if self.connected:
                    self.update_display()
                time.sleep(0.1)  # Send sensor display data every 100ms
        
        thread = threading.Thread(target=sensor_display_update_loop, daemon=True)
        thread.start()
    
    def on_closing(self):
        self.disconnect_serial()
        self.root.destroy()

    def on_canvas_focus(self, event):
        self.canvas.focus_set()

    def ease_in_out_cubic(self, t):
        """Smooth easing function for natural movement"""
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2
    
    def create_gate_particles(self, gate_x, gate_type):
        """Create enhanced particle effects for gate movement with ERC Mars theme"""
        particles = []
        particle_count = 1  # Minimal particles for better performance
        
        for _ in range(particle_count):
            # Enhanced particle colors for Mars theme
            if gate_type in ['opening', 'opened']:
                color_base = self.colors['system_green']
            elif gate_type in ['closing']:
                color_base = self.colors['mars_orange']
            else:
                color_base = self.colors['mission_yellow']
            
            particle = {
                'x': self.start_x + gate_x + random.uniform(-5, 5),
                'y': self.start_y + random.uniform(60, self.airlock_height - 60),
                'vx': random.uniform(-0.5, 0.5),
                'vy': random.uniform(-1.0, -0.3),
                'life': 1.0,
                'size': random.uniform(1.5, 2.5),
                'color': color_base
            }
            particles.append(particle)
        return particles
    
    def update_particles(self, particles):
        """Update particle positions and remove dead particles"""
        alive_particles = []
        for particle in particles:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 0.015  # Very slow fade out
            particle['size'] *= 0.998  # Very slow size reduction
            
            if particle['life'] > 0 and particle['size'] > 0.9:  # Live longer
                alive_particles.append(particle)
        
        return alive_particles
    
    def draw_particles(self, particles):
        """Draw enhanced particle effects for ERC theme"""
        for particle in particles:
            alpha = max(0, min(255, int(particle['life'] * 255)))
            if alpha > 120:  # Only draw clearly visible particles
                size = max(1.0, particle['size'])
                
                # Enhanced particle rendering with glow effect
                x1 = particle['x'] - size
                y1 = particle['y'] - size 
                x2 = particle['x'] + size
                y2 = particle['y'] + size
                
                # Main particle
                self.canvas.create_oval(
                    x1, y1, x2, y2,
                    fill=particle['color'], outline="", tags="particles"
                )
                
                # Subtle glow effect for Mars atmosphere
                if size > 1.5:
                    glow_size = size * 1.3
                    self.canvas.create_oval(
                        particle['x'] - glow_size, particle['y'] - glow_size,
                        particle['x'] + glow_size, particle['y'] + glow_size,
                        fill="", outline=particle['color'], width=1, tags="particles"
                    )

    def request_update(self, force=False):
        """Throttled update system to prevent flickering"""
        current_time = time.time()
        
        if force or (current_time - self.last_update_time) >= self.min_update_interval:
            if not self.update_pending:
                self.update_pending = True
                # Schedule update on next GUI cycle
                self.root.after(10, self._perform_update)
    
    def _perform_update(self):
        """Actually perform the update - called from GUI thread"""
        if self.update_pending:
            self.update_pending = False
            self.last_update_time = time.time()
            
            # Single unified update that minimizes canvas operations
            self._unified_update()
    
    def _unified_update(self):
        """Single method that handles all visual updates efficiently"""
        # Remove only dynamic elements in one operation
        self.canvas.delete("sensor_zones", "gates", "rover", "particles")
        
        # Redraw everything in the correct order
        self.draw_sensor_zones()
        self.draw_gates()
        self.draw_rover()

    def draw_gates(self):
        # Update and draw particles
        self.gate_a_particles = self.update_particles(self.gate_a_particles)
        self.gate_b_particles = self.update_particles(self.gate_b_particles)
        
        # Draw particles with enhanced ERC theme
        if self.gate_a_particles or self.gate_b_particles:
            self.draw_particles(self.gate_a_particles)
            self.draw_particles(self.gate_b_particles)
        
        # Enhanced Gate A with ERC Mars theme
        if self.gate_a_moving:
            eased_progress = self.ease_in_out_cubic(self.gate_animation_progress_a)
        else:
            eased_progress = self.gate_animation_progress_a
        
        # Calculate gate positions for sliding down effect
        gate_a_y = self.start_y + (self.airlock_height * eased_progress)
        gate_a_height = self.airlock_height * (1 - eased_progress)
        
        if gate_a_height < 5:
            gate_a_height = 5
        
        # Enhanced gate colors with ERC theme
        if self.gate_a_moving:
            pulse = abs(math.sin(time.time() * 4)) * 0.3 + 0.7
            # Use mission colors for moving gates
            red_val = int(255 * pulse) if self.gate_a_target_state else int(200 * pulse)
            green_val = int(200 * pulse) if self.gate_a_target_state else int(100 * pulse)
            gate_a_color = f"#{red_val:02x}{green_val:02x}00"
            
            # Enhanced motion blur effect
            for offset in range(3):
                blur_alpha = int(80 - offset * 25)
                blur_color = f"#{blur_alpha:02x}{blur_alpha//2:02x}00"
                self.canvas.create_rectangle(
                    self.start_x + self.gate_a_x - self.gate_width/2 - offset, gate_a_y - offset,
                    self.start_x + self.gate_a_x + self.gate_width/2 + offset,
                    gate_a_y + gate_a_height + offset,
                    fill=blur_color, outline="", tags="gates"
                )
        else:
            gate_a_color = self.colors['system_green'] if self.gate_a_open else self.colors['alert_red']
        
        # Main gate body with enhanced Mars tech look
        gate_x_left = self.start_x + self.gate_a_x - self.gate_width/2
        gate_x_right = self.start_x + self.gate_a_x + self.gate_width/2
        
        # Main gate structure
        self.canvas.create_rectangle(
            gate_x_left, gate_a_y,
            gate_x_right, gate_a_y + gate_a_height,
            fill=gate_a_color, outline=self.colors['primary_text'], width=3, tags="gates"
        )
        
        # Enhanced gate details for Mars base aesthetics
        if gate_a_height > 30:
            # Horizontal segments with ERC styling
            segment_count = max(2, int(gate_a_height / 25))
            for i in range(1, segment_count):
                y = gate_a_y + (gate_a_height / segment_count) * i
                self.canvas.create_line(gate_x_left + 2, y, gate_x_right - 2, y,
                                      fill=self.colors['rover_dark'], width=2, tags="gates")
            
            # Enhanced side rails with Mars tech look
            self.canvas.create_rectangle(gate_x_left - 4, gate_a_y - 8,
                                       gate_x_left, gate_a_y + gate_a_height + 8,
                                       fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=2, tags="gates")
            self.canvas.create_rectangle(gate_x_right, gate_a_y - 8,
                                       gate_x_right + 4, gate_a_y + gate_a_height + 8,
                                       fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=2, tags="gates")
        
        # Enhanced gate status with ERC mission styling
        status_text = "OPENING" if (self.gate_a_moving and self.gate_a_target_state) else \
                     "CLOSING" if (self.gate_a_moving and not self.gate_a_target_state) else \
                     "OPEN" if self.gate_a_open else "SEALED"
        
        status_color = self.colors['mission_yellow'] if self.gate_a_moving else \
                      (self.colors['system_green'] if self.gate_a_open else self.colors['alert_red'])
        
        # Enhanced gate label background
        self.canvas.create_rectangle(
            self.start_x + self.gate_a_x - 40, self.start_y - 40,
            self.start_x + self.gate_a_x + 40, self.start_y - 5,
            fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=2, tags="gates"
        )
        
        self.canvas.create_text(
            self.start_x + self.gate_a_x, self.start_y - 28,
            text="GATE A", fill=self.colors['tech_blue'], font=('Arial', 11, 'bold'), tags="gates"
        )
        self.canvas.create_text(
            self.start_x + self.gate_a_x, self.start_y - 15,
            text=status_text, fill=status_color, font=('Arial', 9, 'bold'), tags="gates"
        )
        
        # Enhanced Gate B with same styling
        if self.gate_b_moving:
            eased_progress = self.ease_in_out_cubic(self.gate_animation_progress_b)
        else:
            eased_progress = self.gate_animation_progress_b
        
        gate_b_y = self.start_y + (self.airlock_height * eased_progress)
        gate_b_height = self.airlock_height * (1 - eased_progress)
        
        if gate_b_height < 5:
            gate_b_height = 5
        
        if self.gate_b_moving:
            pulse = abs(math.sin(time.time() * 4)) * 0.3 + 0.7
            red_val = int(255 * pulse) if self.gate_b_target_state else int(200 * pulse)
            green_val = int(200 * pulse) if self.gate_b_target_state else int(100 * pulse)
            gate_b_color = f"#{red_val:02x}{green_val:02x}00"
            
            for offset in range(3):
                blur_alpha = int(80 - offset * 25)
                blur_color = f"#{blur_alpha:02x}{blur_alpha//2:02x}00"
                self.canvas.create_rectangle(
                    self.start_x + self.gate_b_x - self.gate_width/2 - offset, gate_b_y - offset,
                    self.start_x + self.gate_b_x + self.gate_width/2 + offset,
                    gate_b_y + gate_b_height + offset,
                    fill=blur_color, outline="", tags="gates"
                )
        else:
            gate_b_color = self.colors['system_green'] if self.gate_b_open else self.colors['alert_red']
        
        gate_x_left = self.start_x + self.gate_b_x - self.gate_width/2
        gate_x_right = self.start_x + self.gate_b_x + self.gate_width/2
        
        self.canvas.create_rectangle(
            gate_x_left, gate_b_y,
            gate_x_right, gate_b_y + gate_b_height,
            fill=gate_b_color, outline=self.colors['primary_text'], width=3, tags="gates"
        )
        
        if gate_b_height > 30:
            segment_count = max(2, int(gate_b_height / 25))
            for i in range(1, segment_count):
                y = gate_b_y + (gate_b_height / segment_count) * i
                self.canvas.create_line(gate_x_left + 2, y, gate_x_right - 2, y,
                                      fill=self.colors['rover_dark'], width=2, tags="gates")
            
            self.canvas.create_rectangle(gate_x_left - 4, gate_b_y - 8,
                                       gate_x_left, gate_b_y + gate_b_height + 8,
                                       fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=2, tags="gates")
            self.canvas.create_rectangle(gate_x_right, gate_b_y - 8,
                                       gate_x_right + 4, gate_b_y + gate_b_height + 8,
                                       fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=2, tags="gates")
        
        status_text = "OPENING" if (self.gate_b_moving and self.gate_b_target_state) else \
                     "CLOSING" if (self.gate_b_moving and not self.gate_b_target_state) else \
                     "OPEN" if self.gate_b_open else "SEALED"
        
        status_color = self.colors['mission_yellow'] if self.gate_b_moving else \
                      (self.colors['system_green'] if self.gate_b_open else self.colors['alert_red'])
        
        self.canvas.create_rectangle(
            self.start_x + self.gate_b_x - 40, self.start_y - 40,
            self.start_x + self.gate_b_x + 40, self.start_y - 5,
            fill=self.colors['rover_dark'], outline=self.colors['mars_orange'], width=2, tags="gates"
        )
        
        self.canvas.create_text(
            self.start_x + self.gate_b_x, self.start_y - 28,
            text="GATE B", fill=self.colors['mars_orange'], font=('Arial', 11, 'bold'), tags="gates"
        )
        self.canvas.create_text(
            self.start_x + self.gate_b_x, self.start_y - 15,
            text=status_text, fill=status_color, font=('Arial', 9, 'bold'), tags="gates"
        )
    
    def draw_rover(self):
        """Enhanced Mars rover design for ERC theme"""
        # ERC Mars Rover color scheme
        rover_body_color = self.colors['rover_dark']
        rover_accent_color = self.colors['mars_orange']
        rover_tech_color = self.colors['tech_blue']
        
        # Main rover body (enhanced dimensions for Mars rover)
        body_width = self.rover_width * 0.85
        body_height = self.rover_height * 0.7
        
        # Main chassis with Mars mission styling
        self.canvas.create_rectangle(
            self.rover_x - body_width/2, self.rover_y - body_height/2,
            self.rover_x + body_width/2, self.rover_y + body_height/2,
            fill=rover_body_color, outline=rover_accent_color, width=3, tags="rover"
        )
        
        # Central command module (Mars mission control)
        module_width = body_width * 0.7
        module_height = body_height * 0.5
        module_y = self.rover_y - body_height/2 - module_height/2 - 2
        
        self.canvas.create_rectangle(
            self.rover_x - module_width/2, module_y - module_height/2,
            self.rover_x + module_width/2, module_y + module_height/2,
            fill=self.colors['shadow_brown'], outline=rover_accent_color, width=2, tags="rover"
        )
        
        # Mars mission equipment pods (left and right)
        pod_width = 15
        pod_height = 20
        
        # Left equipment pod
        self.canvas.create_rectangle(
            self.rover_x - body_width/2 - 5, self.rover_y - pod_height/2,
            self.rover_x - body_width/2 + pod_width - 5, self.rover_y + pod_height/2,
            fill=rover_tech_color, outline=self.colors['primary_text'], width=1, tags="rover"
        )
        
        # Right equipment pod
        self.canvas.create_rectangle(
            self.rover_x + body_width/2 - pod_width + 5, self.rover_y - pod_height/2,
            self.rover_x + body_width/2 + 5, self.rover_y + pod_height/2,
            fill=rover_tech_color, outline=self.colors['primary_text'], width=1, tags="rover"
        )
        
        # Enhanced wheel system - 6 wheels for Mars terrain
        wheel_radius = 10
        wheel_color = self.colors['space_black']
        wheel_rim_color = rover_accent_color
        
        # Calculate wheel positions (3 on each side)
        wheel_positions = []
        for i in range(3):
            wheel_x = self.rover_x - body_width/2 + 25 + i * (body_width - 50) / 2
            wheel_positions.append(wheel_x)
        
        # Draw all 6 wheels (top and bottom)
        for wheel_x in wheel_positions:
            # Top wheels
            wheel_y = self.rover_y - body_height/2 - wheel_radius + 2
            self.canvas.create_oval(
                wheel_x - wheel_radius, wheel_y - wheel_radius,
                wheel_x + wheel_radius, wheel_y + wheel_radius,
                fill=wheel_color, outline=wheel_rim_color, width=2, tags="rover"
            )
            # Wheel spokes
            for spoke in range(4):
                angle = spoke * math.pi / 2
                spoke_x = wheel_x + wheel_radius * 0.6 * math.cos(angle)
                spoke_y = wheel_y + wheel_radius * 0.6 * math.sin(angle)
                self.canvas.create_line(wheel_x, wheel_y, spoke_x, spoke_y,
                                      fill=wheel_rim_color, width=1, tags="rover")
            
            # Bottom wheels
            wheel_y = self.rover_y + body_height/2 + wheel_radius - 2
            self.canvas.create_oval(
                wheel_x - wheel_radius, wheel_y - wheel_radius,
                wheel_x + wheel_radius, wheel_y + wheel_radius,
                fill=wheel_color, outline=wheel_rim_color, width=2, tags="rover"
            )
            # Wheel spokes
            for spoke in range(4):
                angle = spoke * math.pi / 2
                spoke_x = wheel_x + wheel_radius * 0.6 * math.cos(angle)
                spoke_y = wheel_y + wheel_radius * 0.6 * math.sin(angle)
                self.canvas.create_line(wheel_x, wheel_y, spoke_x, spoke_y,
                                      fill=wheel_rim_color, width=1, tags="rover")
        
        # Enhanced solar panel array
        panel_width = body_width * 1.1
        panel_height = 8
        panel_y = self.rover_y - body_height/2 - 12
        
        self.canvas.create_rectangle(
            self.rover_x - panel_width/2, panel_y - panel_height/2,
            self.rover_x + panel_width/2, panel_y + panel_height/2,
            fill=self.colors['space_black'], outline=rover_tech_color, width=2, tags="rover"
        )
        
        # Solar panel grid pattern
        for i in range(10):
            x = self.rover_x - panel_width/2 + 8 + i * (panel_width - 16) / 9
            self.canvas.create_line(x, panel_y - panel_height/2 + 2,
                                  x, panel_y + panel_height/2 - 2,
                                  fill=rover_tech_color, width=1, tags="rover")
        
        # Communication array (mast with dish)
        mast_x = self.rover_x + body_width/2 - 20
        mast_base_y = module_y - module_height/2
        mast_tip_y = mast_base_y - 20
        
        # Mast
        self.canvas.create_line(mast_x, mast_base_y, mast_x, mast_tip_y,
                              fill=self.colors['primary_text'], width=4, tags="rover")
        
        # Communication dish
        self.canvas.create_oval(mast_x - 8, mast_tip_y - 6,
                              mast_x + 8, mast_tip_y + 2,
                              fill=rover_accent_color, outline=self.colors['primary_text'], width=2, tags="rover")
        
        # Central communication beacon
        self.canvas.create_oval(mast_x - 2, mast_tip_y - 8,
                              mast_x + 2, mast_tip_y - 4,
                              fill=self.colors['alert_red'], outline=self.colors['primary_text'], tags="rover")
        
        # Front sensor array (Mars exploration sensors)
        sensor_x = self.rover_x + body_width/2 - 8
        sensor_colors = [self.colors['system_green'], self.colors['mission_yellow'], self.colors['alert_red']]
        
        for i in range(3):
            sensor_y = self.rover_y - 12 + i * 12
            self.canvas.create_oval(sensor_x - 3, sensor_y - 3,
                                  sensor_x + 3, sensor_y + 3,
                                  fill=sensor_colors[i], outline=self.colors['primary_text'], tags="rover")
        
        # Robotic arm attachment point
        arm_base_x = self.rover_x - body_width/2 + 15
        arm_base_y = self.rover_y
        self.canvas.create_oval(arm_base_x - 4, arm_base_y - 4,
                              arm_base_x + 4, arm_base_y + 4,
                              fill=self.colors['shadow_brown'], outline=rover_accent_color, width=2, tags="rover")
        
        # Direction indicator (enhanced Mars rover style)
        arrow_x = self.rover_x + body_width/2 + 12
        arrow_points = [
            arrow_x, self.rover_y,
            arrow_x + 18, self.rover_y - 10,
            arrow_x + 12, self.rover_y,
            arrow_x + 18, self.rover_y + 10
        ]
        
        self.canvas.create_polygon(arrow_points, fill=self.colors['mission_yellow'], 
                                 outline=self.colors['primary_text'], width=2, tags="rover")
        
        # Rover identification and mission status
        self.canvas.create_text(self.rover_x, self.rover_y + 5,
                              text="ERC MARS ROVER", fill=self.colors['primary_text'], 
                              font=('Arial', 8, 'bold'), tags="rover")
        
        # Mission status indicator
        status_x = self.rover_x - body_width/2 - 25
        self.canvas.create_oval(status_x - 5, self.rover_y - 5,
                              status_x + 5, self.rover_y + 5,
                              fill=self.colors['system_green'], outline=self.colors['primary_text'], width=2, tags="rover")
        self.canvas.create_text(status_x, self.rover_y - 18,
                              text="MISSION", fill=self.colors['system_green'], 
                              font=('Arial', 7, 'bold'), tags="rover")
        self.canvas.create_text(status_x, self.rover_y - 28,
                              text="ACTIVE", fill=self.colors['system_green'], 
                              font=('Arial', 7, 'bold'), tags="rover")

    def update_sensors(self):
        # Calculate rover edges
        rover_left = self.rover_x - self.rover_width/2
        rover_right = self.rover_x + self.rover_width/2
        
        # Reset all sensors
        old_states = self.sensor_states.copy()
        
        # Calculate sensor line positions at center of each zone
        front_sensor_x = self.start_x + self.front_zone_width / 2
        middle_sensor_x = self.start_x + self.front_zone_width + self.middle_zone_width / 2
        back_sensor_x = self.start_x + self.front_zone_width + self.middle_zone_width + self.back_zone_width / 2
        
        # Check presence sensors (trigger if any part of rover crosses sensor line)
        self.sensor_states['PRESENCE_FRONT'] = rover_left <= front_sensor_x <= rover_right
        self.sensor_states['PRESENCE_MIDDLE'] = rover_left <= middle_sensor_x <= rover_right
        self.sensor_states['PRESENCE_BACK'] = rover_left <= back_sensor_x <= rover_right
        
        # Check gate safety sensors (based on rover edges, keep existing logic)
        safety_zone_width = 60
        
        # Gate A safety
        gate_a_pos = self.start_x + self.gate_a_x
        if (rover_right > gate_a_pos - safety_zone_width/2 and 
            rover_left < gate_a_pos + safety_zone_width/2):
            self.sensor_states['GATE_SAFETY_A'] = True
        else:
            self.sensor_states['GATE_SAFETY_A'] = False
        
        # Gate B safety
        gate_b_pos = self.start_x + self.gate_b_x
        if (rover_right > gate_b_pos - safety_zone_width/2 and 
            rover_left < gate_b_pos + safety_zone_width/2):
            self.sensor_states['GATE_SAFETY_B'] = True
        else:
            self.sensor_states['GATE_SAFETY_B'] = False
        
        # Update sensor labels with HIGH CONTRAST ERC theme colors
        for name, state in self.sensor_states.items():
            if name in self.sensor_labels:
                label = self.sensor_labels[name]
                if state:
                    # ACTIVE - bright green background with black text for maximum visibility
                    label.config(text="🟢 ACTIVE", bg='#00FF00', fg='#000000', font=('Arial', 10, 'bold'))
                else:
                    # INACTIVE - dark background with dim text
                    label.config(text="⚫ OFFLINE", bg='#1a1a1a', fg='#666666', font=('Arial', 10, 'normal'))
        
        # Update gate moving states with HIGH CONTRAST
        if self.gate_a_moving:
            self.sensor_labels['GATE_MOVING_A'].config(
                text="🟡 MOVING", bg='#FFFF00', fg='#000000', font=('Arial', 10, 'bold')
            )
        else:
            self.sensor_labels['GATE_MOVING_A'].config(
                text="⚫ STATIC", bg='#1a1a1a', fg='#666666', font=('Arial', 10, 'normal')
            )
            
        if self.gate_b_moving:
            self.sensor_labels['GATE_MOVING_B'].config(
                text="🟡 MOVING", bg='#FFFF00', fg='#000000', font=('Arial', 10, 'bold')
            )
        else:
            self.sensor_labels['GATE_MOVING_B'].config(
                text="⚫ STATIC", bg='#1a1a1a', fg='#666666', font=('Arial', 10, 'normal')
            )
        
        # Update gate request states with HIGH CONTRAST
        if self.gate_requests['GATE_REQUEST_A']:
            self.sensor_labels['GATE_REQUEST_A'].config(
                text="🔶 REQUESTED", bg='#FF6B35', fg='#FFFFFF', font=('Arial', 10, 'bold')
            )
        else:
            self.sensor_labels['GATE_REQUEST_A'].config(
                text="⚫ IDLE", bg='#1a1a1a', fg='#666666', font=('Arial', 10, 'normal')
            )
            
        if self.gate_requests['GATE_REQUEST_B']:
            self.sensor_labels['GATE_REQUEST_B'].config(
                text="🔶 REQUESTED", bg='#FF6B35', fg='#FFFFFF', font=('Arial', 10, 'bold')
            )
        else:
            self.sensor_labels['GATE_REQUEST_B'].config(
                text="⚫ IDLE", bg='#1a1a1a', fg='#666666', font=('Arial', 10, 'normal')
            )
        
        # Request throttled update instead of immediate update
        self.request_update()

if __name__ == "__main__":
    root = tk.Tk()
    app = AirlockGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop() 