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
        self.root.title("Airlock HIL Simulator")
        self.root.geometry("1800x1000")  # Made even wider to accommodate both panels
        self.root.configure(bg='#1a1a1a')
        
        # Serial connection
        self.ser = None
        self.connected = False
        
        # Airlock dimensions (scaled down for display)
        self.scale = 0.5  # Reduced scale to fit better with terminal
        self.airlock_width = 1376 * self.scale  # Updated total width: 408 + 560 + 408
        self.front_zone_width = 408 * self.scale
        self.middle_zone_width = 560 * self.scale
        self.back_zone_width = 408 * self.scale  # Changed to match front zone
        self.airlock_height = 175  # Reduced height by half to make room for sensor states
        
        # Rover properties
        self.rover_width = 638 * self.scale * 0.4  # Made much smaller for easier movement
        self.rover_height = 35  # Also smaller height
        self.rover_x = 50  # Start position - outside front zone
        self.rover_y = self.airlock_height // 2 + 50  # Adjust for canvas position
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
        self.gate_a_animation_time = 0  # Time elapsed during animation
        self.gate_b_animation_time = 0
        self.gate_animation_duration = 3.0  # Total animation duration in seconds
        self.gate_a_particles = []  # Particle effects for gate A
        self.gate_b_particles = []  # Particle effects for gate B
        
        # Gate movement direction tracking
        self.gate_a_target_state = False  # True = opening, False = closing
        self.gate_b_target_state = False  # True = opening, False = closing
        
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
        self.min_update_interval = 0.1  # Minimum 100ms between updates
        
        # Control flags
        self.needs_redraw = True
        
        self.setup_gui()
        self.start_reading_thread()
        self.start_animation_thread()
        self.start_sensor_update_thread()  # Add periodic sensor updates
        self.start_sensor_display_update_thread()  # Add periodic sensor display updates
        
    def setup_gui(self):
        # Main title
        title_label = tk.Label(self.root, text="Airlock HIL Simulator", 
                              font=('Arial', 24, 'bold'), 
                              fg='white', bg='#1a1a1a')
        title_label.pack(pady=10)
        
        # Connection frame
        conn_frame = tk.Frame(self.root, bg='#1a1a1a')
        conn_frame.pack(pady=5)
        
        tk.Label(conn_frame, text="COM Port:", 
                font=('Arial', 12), fg='white', bg='#1a1a1a').pack(side=tk.LEFT, padx=5)
        
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, 
                                      values=self.get_serial_ports(), width=15)
        self.port_combo.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", 
                                   command=self.toggle_connection,
                                   bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'))
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = tk.Button(conn_frame, text="Refresh Ports", 
                                   command=self.refresh_ports,
                                   bg='#2196F3', fg='white', font=('Arial', 10))
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(self.root, text="Disconnected", 
                                   font=('Arial', 12), fg='red', bg='#1a1a1a')
        self.status_label.pack(pady=5)
        
        # Create main content frame with two columns
        main_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Left column for airlock visualization
        left_frame = tk.Frame(main_frame, bg='#1a1a1a')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas for airlock visualization - reduced height to make room for sensor table
        self.canvas = tk.Canvas(left_frame, width=1000, height=250, 
                               bg='#2b2b2b', highlightthickness=0)
        self.canvas.pack(pady=5)
        
        # Make canvas focusable for keyboard events
        self.canvas.focus_set()
        
        # Sensor status frame - positioned right below canvas with normal padding
        sensor_frame = tk.LabelFrame(left_frame, text="Sensor States", 
                                   font=('Arial', 12, 'bold'), 
                                   fg='white', bg='#1a1a1a',
                                   labelanchor='n')
        sensor_frame.pack(pady=(5, 10), fill='x')  # Normal positive padding
        
        # Create horizontal sensor table
        self.sensor_labels = {}
        
        # Main container for horizontal layout
        table_container = tk.Frame(sensor_frame, bg='#1a1a1a')
        table_container.pack(fill='x', padx=10, pady=5)
        
        # First row sensors
        first_row_sensors = ['PRESENCE_FRONT', 'PRESENCE_MIDDLE', 'PRESENCE_BACK', 
                            'GATE_SAFETY_A', 'GATE_SAFETY_B']
        
        # First row container
        first_row = tk.Frame(table_container, bg='#1a1a1a')
        first_row.pack(fill='x', pady=(0, 3))
        
        # Create first row with equal distribution
        for i, sensor_name in enumerate(first_row_sensors):
            sensor_col = tk.Frame(first_row, bg='#1a1a1a')
            sensor_col.pack(side=tk.LEFT, fill='x', expand=True, padx=2)
            
            # Sensor name label (top)
            name_label = tk.Label(sensor_col, text=sensor_name, 
                                 font=('Arial', 9, 'bold'), 
                                 fg='white', bg='#333333',
                                 relief='raised', bd=1, pady=2)
            name_label.pack(fill='x')
            
            # State label (bottom)
            state_label = tk.Label(sensor_col, text="OFF", 
                                  font=('Arial', 10, 'bold'), 
                                  fg='white', bg='#4a4a4a',
                                  relief='raised', bd=1, pady=4)
            state_label.pack(fill='x')
            
            self.sensor_labels[sensor_name] = state_label
        
        # Second row sensors
        second_row_sensors = ['GATE_MOVING_A', 'GATE_MOVING_B', 'GATE_REQUEST_A', 'GATE_REQUEST_B']
        
        # Second row container
        second_row = tk.Frame(table_container, bg='#1a1a1a')
        second_row.pack(fill='x', pady=(3, 0))
        
        # Create second row with equal distribution
        for i, sensor_name in enumerate(second_row_sensors):
            sensor_col = tk.Frame(second_row, bg='#1a1a1a')
            sensor_col.pack(side=tk.LEFT, fill='x', expand=True, padx=2)
            
            # Sensor name label (top)
            name_label = tk.Label(sensor_col, text=sensor_name, 
                                 font=('Arial', 9, 'bold'), 
                                 fg='white', bg='#333333',
                                 relief='raised', bd=1, pady=2)
            name_label.pack(fill='x')
            
            # State label (bottom)
            state_label = tk.Label(sensor_col, text="OFF", 
                                  font=('Arial', 10, 'bold'), 
                                  fg='white', bg='#4a4a4a',
                                  relief='raised', bd=1, pady=4)
            state_label.pack(fill='x')
            
            self.sensor_labels[sensor_name] = state_label
        
        # Add empty columns to balance the second row (since it has 4 items vs 5 in first row)
        empty_col = tk.Frame(second_row, bg='#1a1a1a')
        empty_col.pack(side=tk.LEFT, fill='x', expand=True, padx=2)
        
        # Control instructions
        instructions = tk.Label(left_frame, 
                              text="Controls: Click and drag the rover or use arrow keys to move. Click canvas first for keyboard control.",
                              font=('Arial', 11), fg='white', bg='#1a1a1a')
        instructions.pack()
        
        # Right column for serial terminal
        right_frame = tk.Frame(main_frame, bg='#2a2a2a', width=450, relief='raised', bd=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)  # Maintain fixed width
        
        # Serial Terminal frame
        terminal_frame = tk.LabelFrame(right_frame, text="Serial Terminal", 
                                     font=('Arial', 14, 'bold'), 
                                     fg='white', bg='#2a2a2a',
                                     labelanchor='n')
        terminal_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=5)
        
        # Terminal output area
        self.terminal_output = scrolledtext.ScrolledText(terminal_frame, 
                                                        height=28, width=45,
                                                        bg='#000000', fg='#00ff00',
                                                        font=('Consolas', 9),
                                                        state=tk.DISABLED,
                                                        wrap=tk.WORD)
        self.terminal_output.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
        
        # Terminal input frame
        input_frame = tk.Frame(terminal_frame, bg='#2a2a2a')
        input_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Command entry
        tk.Label(input_frame, text="Command:", 
                font=('Arial', 10), fg='white', bg='#2a2a2a').pack(side=tk.LEFT)
        
        self.command_entry = tk.Entry(input_frame, font=('Consolas', 10),
                                     bg='#1a1a1a', fg='white', insertbackground='white')
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        self.command_entry.bind('<Return>', self.send_command)
        
        # Send button
        send_btn = tk.Button(input_frame, text="Send", 
                           command=self.send_command,
                           bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'))
        send_btn.pack(side=tk.RIGHT)
        
        # Terminal control buttons
        control_frame = tk.Frame(terminal_frame, bg='#2a2a2a')
        control_frame.pack(fill=tk.X, pady=(0, 5), padx=5)
        
        clear_btn = tk.Button(control_frame, text="Clear Terminal", 
                            command=self.clear_terminal,
                            bg='#ff6b35', fg='white', font=('Arial', 9))
        clear_btn.pack(side=tk.LEFT)
        
        auto_scroll_var = tk.BooleanVar(value=True)
        self.auto_scroll_check = tk.Checkbutton(control_frame, text="Auto Scroll",
                                               variable=auto_scroll_var,
                                               bg='#2a2a2a', fg='white',
                                               selectcolor='#4a4a4a')
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
        # Also bind to root for global key events
        self.root.bind("<KeyPress>", self.on_key_press)
        # Make sure canvas can receive focus
        self.canvas.bind("<Button-1>", self.on_canvas_focus, add='+')
        
        # Add welcome message to terminal
        self.add_terminal_message("=== Airlock HIL Simulator Terminal ===", "INFO")
        self.add_terminal_message("Type commands below to send to Arduino", "INFO")
        self.add_terminal_message("Commands are sent with < > delimiters automatically", "INFO")
        
        # Debug: Show initial gate states
        print(f"DEBUG: Initial gate states:")
        print(f"DEBUG: Gate A - Open: {self.gate_a_open}, Moving: {self.gate_a_moving}, Target: {self.gate_a_target_state}")
        print(f"DEBUG: Gate B - Open: {self.gate_b_open}, Moving: {self.gate_b_moving}, Target: {self.gate_b_target_state}")
        print(f"DEBUG: Gate requests: {self.gate_requests}")
        
    def add_terminal_message(self, message, msg_type="DATA"):
        """Add a message to the terminal with timestamp and formatting"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        self.terminal_output.config(state=tk.NORMAL)
        
        # Color coding based on message type
        if msg_type == "SENT":
            color_tag = "sent"
            prefix = ">> "
        elif msg_type == "RECEIVED":
            color_tag = "received"
            prefix = "<< "
        elif msg_type == "INFO":
            color_tag = "info"
            prefix = "-- "
        elif msg_type == "ERROR":
            color_tag = "error"
            prefix = "!! "
        else:
            color_tag = "default"
            prefix = "   "
        
        # Configure color tags
        self.terminal_output.tag_configure("sent", foreground="#ffff00")
        self.terminal_output.tag_configure("received", foreground="#00ff00")
        self.terminal_output.tag_configure("info", foreground="#00aaff")
        self.terminal_output.tag_configure("error", foreground="#ff0000")
        self.terminal_output.tag_configure("default", foreground="#ffffff")
        
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
        """Draw the static parts of the airlock that don't change"""
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw background grid pattern for tech look
        grid_size = 20
        for x in range(0, 1000, grid_size):
            self.canvas.create_line(x, 0, x, 250, fill='#333333', width=1, tags="static")
        for y in range(0, 250, grid_size):
            self.canvas.create_line(0, y, 1000, y, fill='#333333', width=1, tags="static")
        
        # Draw main airlock chamber with rounded corners and depth
        chamber_y_offset = 10
        chamber_height = self.airlock_height - 20
        
        # Draw outer shell with metallic look
        self.canvas.create_rectangle(self.start_x - 5, self.start_y - 5, 
                                   self.start_x + self.airlock_width + 5, 
                                   self.start_y + self.airlock_height + 5,
                                   fill='#2a2a2a', outline='#666666', width=4, tags="static")
        
        # Front zone with enhanced details
        front_x = self.start_x
        front_w = self.front_zone_width
        
        # Main chamber
        self.canvas.create_rectangle(front_x, self.start_y + chamber_y_offset, 
                                   front_x + front_w, 
                                   self.start_y + chamber_height,
                                   fill='#1a4a5c', outline='#4a9eff', width=3, tags="static")
        
        # Add rivets and detail lines
        for i in range(3):
            y_pos = self.start_y + 30 + i * 40
            self.canvas.create_oval(front_x + 10, y_pos, front_x + 15, y_pos + 5,
                                  fill='#666666', outline='#888888', tags="static")
            self.canvas.create_oval(front_x + front_w - 15, y_pos, front_x + front_w - 10, y_pos + 5,
                                  fill='#666666', outline='#888888', tags="static")
        
        # Horizontal detail lines
        for i in range(2):
            y_pos = self.start_y + 50 + i * 60
            self.canvas.create_line(front_x + 20, y_pos, front_x + front_w - 20, y_pos,
                                  fill='#4a9eff', width=2, tags="static")
        
        self.canvas.create_text(front_x + front_w/2, self.start_y + 25,
                              text="FRONT CHAMBER", fill='#4a9eff', 
                              font=('Arial', 12, 'bold'), tags="static")
        self.canvas.create_text(front_x + front_w/2, self.start_y + 40,
                              text="ENTRY ZONE", fill='#ffffff', 
                              font=('Arial', 9), tags="static")
        
        # Middle zone (pressurization chamber)
        middle_x = self.start_x + self.front_zone_width
        middle_w = self.middle_zone_width
        
        self.canvas.create_rectangle(middle_x, self.start_y + chamber_y_offset,
                                   middle_x + middle_w,
                                   self.start_y + chamber_height,
                                   fill='#4a2a1a', outline='#ff9a4a', width=3, tags="static")
        
        # Pressure indicator rings
        for i in range(4):
            ring_y = self.start_y + 40 + i * 25
            self.canvas.create_oval(middle_x + middle_w/2 - 15, ring_y,
                                  middle_x + middle_w/2 + 15, ring_y + 8,
                                  fill='', outline='#ff9a4a', width=2, tags="static")
        
        # Pressure lines
        for i in range(6):
            x_pos = middle_x + 30 + i * 80
            self.canvas.create_line(x_pos, self.start_y + 20, x_pos, self.start_y + chamber_height - 10,
                                  fill='#ff6a2a', width=1, dash=(5, 5), tags="static")
        
        self.canvas.create_text(middle_x + middle_w/2, self.start_y + 25,
                              text="TRANSITION CHAMBER", fill='#ff9a4a', 
                              font=('Arial', 12, 'bold'), tags="static")
        self.canvas.create_text(middle_x + middle_w/2, self.start_y + 40,
                              text="PRESSURIZATION ZONE", fill='#ffffff', 
                              font=('Arial', 9), tags="static")
        
        # Back zone
        back_x = self.start_x + self.front_zone_width + self.middle_zone_width
        back_w = self.back_zone_width
        
        self.canvas.create_rectangle(back_x, self.start_y + chamber_y_offset,
                                   back_x + back_w,
                                   self.start_y + chamber_height,
                                   fill='#1a5c1a', outline='#4aff4a', width=3, tags="static")
        
        # Add exit indicators
        for i in range(3):
            y_pos = self.start_y + 30 + i * 40
            self.canvas.create_oval(back_x + 10, y_pos, back_x + 15, y_pos + 5,
                                  fill='#666666', outline='#888888', tags="static")
            self.canvas.create_oval(back_x + back_w - 15, y_pos, back_x + back_w - 10, y_pos + 5,
                                  fill='#666666', outline='#888888', tags="static")
        
        # Exit arrows
        for i in range(2):
            arrow_x = back_x + 40 + i * 60
            self.canvas.create_polygon(arrow_x, self.start_y + 70,
                                     arrow_x + 15, self.start_y + 60,
                                     arrow_x + 15, self.start_y + 65,
                                     arrow_x + 25, self.start_y + 65,
                                     arrow_x + 25, self.start_y + 75,
                                     arrow_x + 15, self.start_y + 75,
                                     arrow_x + 15, self.start_y + 80,
                                     fill='#4aff4a', outline='#ffffff', tags="static")
        
        self.canvas.create_text(back_x + back_w/2, self.start_y + 25,
                              text="EXIT CHAMBER", fill='#4aff4a', 
                              font=('Arial', 12, 'bold'), tags="static")
        self.canvas.create_text(back_x + back_w/2, self.start_y + 40,
                              text="DECONTAMINATION ZONE", fill='#ffffff', 
                              font=('Arial', 9), tags="static")
    
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
        
        # Draw presence sensor lines
        # Front presence sensor line
        self.canvas.create_line(front_sensor_x, self.start_y + 20,
                              front_sensor_x, self.start_y + self.airlock_height - 20,
                              fill='#00ff00' if self.sensor_states['PRESENCE_FRONT'] else '#005500',
                              width=5, dash=(8, 4), tags="sensor_zones")
        self.canvas.create_text(front_sensor_x - 20, self.start_y + 10,
                              text="FRONT", fill='#00ff00' if self.sensor_states['PRESENCE_FRONT'] else '#005500',
                              font=('Arial', 9, 'bold'), tags="sensor_zones")
        
        # Middle presence sensor line
        self.canvas.create_line(middle_sensor_x, self.start_y + 20,
                              middle_sensor_x, self.start_y + self.airlock_height - 20,
                              fill='#00ff00' if self.sensor_states['PRESENCE_MIDDLE'] else '#005500',
                              width=5, dash=(8, 4), tags="sensor_zones")
        self.canvas.create_text(middle_sensor_x - 20, self.start_y + 10,
                              text="MIDDLE", fill='#00ff00' if self.sensor_states['PRESENCE_MIDDLE'] else '#005500',
                              font=('Arial', 9, 'bold'), tags="sensor_zones")
        
        # Back presence sensor line
        self.canvas.create_line(back_sensor_x, self.start_y + 20,
                              back_sensor_x, self.start_y + self.airlock_height - 20,
                              fill='#00ff00' if self.sensor_states['PRESENCE_BACK'] else '#005500',
                              width=5, dash=(8, 4), tags="sensor_zones")
        self.canvas.create_text(back_sensor_x - 20, self.start_y + 10,
                              text="BACK", fill='#00ff00' if self.sensor_states['PRESENCE_BACK'] else '#005500',
                              font=('Arial', 9, 'bold'), tags="sensor_zones")
        
        # Gate safety zones (keep these as areas)
        safety_zone_width = 60
        
        # Gate A safety zone
        self.canvas.create_rectangle(self.start_x + self.gate_a_x - safety_zone_width/2, self.start_y,
                                   self.start_x + self.gate_a_x + safety_zone_width/2,
                                   self.start_y + self.airlock_height,
                                   fill='', outline='#ff0000' if self.sensor_states['GATE_SAFETY_A'] else '#550000',
                                   width=3, dash=(3, 3), tags="sensor_zones")
        self.canvas.create_text(self.start_x + self.gate_a_x, self.start_y + self.airlock_height + 20,
                              text="Gate A Safety", fill='#ff0000' if self.sensor_states['GATE_SAFETY_A'] else '#550000',
                              font=('Arial', 10), tags="sensor_zones")
        
        # Gate B safety zone
        self.canvas.create_rectangle(self.start_x + self.gate_b_x - safety_zone_width/2, self.start_y,
                                   self.start_x + self.gate_b_x + safety_zone_width/2,
                                   self.start_y + self.airlock_height,
                                   fill='', outline='#ff0000' if self.sensor_states['GATE_SAFETY_B'] else '#550000',
                                   width=3, dash=(3, 3), tags="sensor_zones")
        self.canvas.create_text(self.start_x + self.gate_b_x, self.start_y + self.airlock_height + 20,
                              text="Gate B Safety", fill='#ff0000' if self.sensor_states['GATE_SAFETY_B'] else '#550000',
                              font=('Arial', 10), tags="sensor_zones")
    
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
        step = 15
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
            messagebox.showerror("Error", "Please select a COM port")
            return
        
        try:
            self.ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)  # Wait for Arduino to initialize
            self.connected = True
            self.connect_btn.config(text="Disconnect", bg='#f44336')
            self.status_label.config(text=f"Connected to {port}", fg='green')
            self.add_terminal_message(f"Connected to {port} at 115200 baud", "INFO")
            messagebox.showinfo("Success", f"Connected to {port}")
            # Send initial sensor states
            self.send_data()
        except serial.SerialException as e:
            error_msg = f"Failed to connect: {str(e)}"
            self.add_terminal_message(error_msg, "ERROR")
            messagebox.showerror("Error", error_msg)
    
    def disconnect_serial(self):
        if self.ser:
            self.ser.close()
            self.ser = None
        self.connected = False
        self.connect_btn.config(text="Connect", bg='#4CAF50')
        self.status_label.config(text="Disconnected", fg='red')
        self.add_terminal_message("Serial connection closed", "INFO")
    
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
        """Create particle effects for gate movement"""
        particles = []
        particle_count = 1  # Minimal particles - only 1 per creation
        
        for _ in range(particle_count):
            particle = {
                'x': self.start_x + gate_x + random.uniform(-3, 3),  # Very small spread
                'y': self.start_y + random.uniform(60, self.airlock_height - 60),
                'vx': random.uniform(-0.3, 0.3),  # Very slow movement
                'vy': random.uniform(-0.8, -0.2),  # Very slow movement
                'life': 1.0,
                'size': random.uniform(1, 1.5)  # Very small particles
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
        """Draw particle effects"""
        for particle in particles:
            alpha = max(0, min(255, int(particle['life'] * 255)))  # Clamp alpha value
            if alpha > 100:  # Only draw clearly visible particles
                # Create a simple glowing effect
                alpha_hex = f"{alpha:02x}"
                color = f"#{alpha_hex}{alpha_hex}00"  # Yellow particles
                size = max(1.0, particle['size'])  # Minimum size
                
                # Simple particle drawing
                x1 = particle['x'] - size
                y1 = particle['y'] - size 
                x2 = particle['x'] + size
                y2 = particle['y'] + size
                
                self.canvas.create_oval(
                    x1, y1, x2, y2,
                    fill=color, outline="", tags="particles"
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
        # Update and draw particles (but don't delete all particles every frame)
        self.gate_a_particles = self.update_particles(self.gate_a_particles)
        self.gate_b_particles = self.update_particles(self.gate_b_particles)
        
        # Only draw particles if there are particles to show
        if self.gate_a_particles or self.gate_b_particles:
            self.draw_particles(self.gate_a_particles)
            self.draw_particles(self.gate_b_particles)
        
        # Gate A with enhanced realistic design
        if self.gate_a_moving:
            eased_progress = self.ease_in_out_cubic(self.gate_animation_progress_a)
        else:
            eased_progress = self.gate_animation_progress_a
        
        # Calculate gate positions for sliding down effect
        gate_a_y = self.start_y + (self.airlock_height * eased_progress)
        gate_a_height = self.airlock_height * (1 - eased_progress)
        
        if gate_a_height < 5:
            gate_a_height = 5  # Minimum visible height
        
        # Enhanced gate colors and effects
        if self.gate_a_moving:
            pulse = abs(math.sin(time.time() * 4)) * 0.3 + 0.7
            gate_a_color = f"#{int(255*pulse):02x}{int(200*pulse):02x}00"
            
            # Add motion blur effect
            for offset in range(3):
                blur_alpha = int(60 - offset * 20)
                blur_color = f"#{blur_alpha:02x}{blur_alpha:02x}00"
                self.canvas.create_rectangle(
                    self.start_x + self.gate_a_x - self.gate_width/2 - offset, gate_a_y - offset,
                    self.start_x + self.gate_a_x + self.gate_width/2 + offset,
                    gate_a_y + gate_a_height + offset,
                    fill=blur_color, outline="", tags="gates"
                )
        else:
            gate_a_color = '#00cc00' if self.gate_a_open else '#cc0000'
        
        # Main gate body with metallic look
        gate_x_left = self.start_x + self.gate_a_x - self.gate_width/2
        gate_x_right = self.start_x + self.gate_a_x + self.gate_width/2
        
        # Draw gate segments for realistic look
        self.canvas.create_rectangle(
            gate_x_left, gate_a_y,
            gate_x_right, gate_a_y + gate_a_height,
            fill=gate_a_color, outline='#ffffff', width=2, tags="gates"
        )
        
        # Add realistic gate details
        if gate_a_height > 30:
            # Horizontal segments
            segment_count = max(2, int(gate_a_height / 25))
            for i in range(1, segment_count):
                y = gate_a_y + (gate_a_height / segment_count) * i
                self.canvas.create_line(gate_x_left + 1, y, gate_x_right - 1, y,
                                      fill='#333333', width=2, tags="gates")
            
            # Side rails
            self.canvas.create_rectangle(gate_x_left - 3, gate_a_y - 5,
                                       gate_x_left, gate_a_y + gate_a_height + 5,
                                       fill='#444444', outline='#666666', tags="gates")
            self.canvas.create_rectangle(gate_x_right, gate_a_y - 5,
                                       gate_x_right + 3, gate_a_y + gate_a_height + 5,
                                       fill='#444444', outline='#666666', tags="gates")
        
        # Gate status with enhanced styling
        status_text = "OPENING" if (self.gate_a_moving and self.gate_a_target_state) else \
                     "CLOSING" if (self.gate_a_moving and not self.gate_a_target_state) else \
                     "OPEN" if self.gate_a_open else "SEALED"
        
        status_color = '#ffff00' if self.gate_a_moving else ('#00ff00' if self.gate_a_open else '#ff0000')
        
        # Gate label background
        self.canvas.create_rectangle(
            self.start_x + self.gate_a_x - 35, self.start_y - 35,
            self.start_x + self.gate_a_x + 35, self.start_y - 5,
            fill='#1a1a1a', outline='#666666', width=1, tags="gates"
        )
        
        self.canvas.create_text(
            self.start_x + self.gate_a_x, self.start_y - 25,
            text="GATE A", fill='#4a9eff', font=('Arial', 11, 'bold'), tags="gates"
        )
        self.canvas.create_text(
            self.start_x + self.gate_a_x, self.start_y - 12,
            text=status_text, fill=status_color, font=('Arial', 8, 'bold'), tags="gates"
        )
        
        # Gate B with same enhanced design
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
            gate_b_color = f"#{int(255*pulse):02x}{int(200*pulse):02x}00"
            
            for offset in range(3):
                blur_alpha = int(60 - offset * 20)
                blur_color = f"#{blur_alpha:02x}{blur_alpha:02x}00"
                self.canvas.create_rectangle(
                    self.start_x + self.gate_b_x - self.gate_width/2 - offset, gate_b_y - offset,
                    self.start_x + self.gate_b_x + self.gate_width/2 + offset,
                    gate_b_y + gate_b_height + offset,
                    fill=blur_color, outline="", tags="gates"
                )
        else:
            gate_b_color = '#00cc00' if self.gate_b_open else '#cc0000'
        
        gate_x_left = self.start_x + self.gate_b_x - self.gate_width/2
        gate_x_right = self.start_x + self.gate_b_x + self.gate_width/2
        
        self.canvas.create_rectangle(
            gate_x_left, gate_b_y,
            gate_x_right, gate_b_y + gate_b_height,
            fill=gate_b_color, outline='#ffffff', width=2, tags="gates"
        )
        
        if gate_b_height > 30:
            segment_count = max(2, int(gate_b_height / 25))
            for i in range(1, segment_count):
                y = gate_b_y + (gate_b_height / segment_count) * i
                self.canvas.create_line(gate_x_left + 1, y, gate_x_right - 1, y,
                                      fill='#333333', width=2, tags="gates")
            
            self.canvas.create_rectangle(gate_x_left - 3, gate_b_y - 5,
                                       gate_x_left, gate_b_y + gate_b_height + 5,
                                       fill='#444444', outline='#666666', tags="gates")
            self.canvas.create_rectangle(gate_x_right, gate_b_y - 5,
                                       gate_x_right + 3, gate_b_y + gate_b_height + 5,
                                       fill='#444444', outline='#666666', tags="gates")
        
        status_text = "OPENING" if (self.gate_b_moving and self.gate_b_target_state) else \
                     "CLOSING" if (self.gate_b_moving and not self.gate_b_target_state) else \
                     "OPEN" if self.gate_b_open else "SEALED"
        
        status_color = '#ffff00' if self.gate_b_moving else ('#00ff00' if self.gate_b_open else '#ff0000')
        
        self.canvas.create_rectangle(
            self.start_x + self.gate_b_x - 35, self.start_y - 35,
            self.start_x + self.gate_b_x + 35, self.start_y - 5,
            fill='#1a1a1a', outline='#666666', width=1, tags="gates"
        )
        
        self.canvas.create_text(
            self.start_x + self.gate_b_x, self.start_y - 25,
            text="GATE B", fill='#ff9a4a', font=('Arial', 11, 'bold'), tags="gates"
        )
        self.canvas.create_text(
            self.start_x + self.gate_b_x, self.start_y - 12,
            text=status_text, fill=status_color, font=('Arial', 8, 'bold'), tags="gates"
        )
    
    def draw_rover(self):
        # Enhanced rover design to look more realistic
        rover_body_color = '#2a5a8a'
        rover_detail_color = '#4a8eff'
        
        # Main rover body (chassis)
        body_width = self.rover_width * 0.8
        body_height = self.rover_height * 0.6
        
        # Main chassis
        self.canvas.create_rectangle(
            self.rover_x - body_width/2, self.rover_y - body_height/2,
            self.rover_x + body_width/2, self.rover_y + body_height/2,
            fill=rover_body_color, outline='#ffffff', width=2, tags="rover"
        )
        
        # Command module (smaller rectangle on top)
        module_width = body_width * 0.6
        module_height = body_height * 0.4
        module_y = self.rover_y - body_height/2 - module_height/2
        
        self.canvas.create_rectangle(
            self.rover_x - module_width/2, module_y - module_height/2,
            self.rover_x + module_width/2, module_y + module_height/2,
            fill='#1a4a6a', outline='#ffffff', width=1, tags="rover"
        )
        
        # Draw wheels/tracks
        wheel_radius = 8
        wheel_color = '#333333'
        
        # Left wheels
        for i in range(3):
            wheel_x = self.rover_x - body_width/2 + 20 + i * 30
            wheel_y = self.rover_y + body_height/2 + wheel_radius - 3
            
            # Wheel
            self.canvas.create_oval(
                wheel_x - wheel_radius, wheel_y - wheel_radius,
                wheel_x + wheel_radius, wheel_y + wheel_radius,
                fill=wheel_color, outline='#666666', width=2, tags="rover"
            )
            
            # Wheel center
            self.canvas.create_oval(
                wheel_x - 3, wheel_y - 3,
                wheel_x + 3, wheel_y + 3,
                fill='#666666', outline='#888888', tags="rover"
            )
        
        # Right wheels
        for i in range(3):
            wheel_x = self.rover_x - body_width/2 + 20 + i * 30
            wheel_y = self.rover_y - body_height/2 - wheel_radius + 3
            
            # Wheel
            self.canvas.create_oval(
                wheel_x - wheel_radius, wheel_y - wheel_radius,
                wheel_x + wheel_radius, wheel_y + wheel_radius,
                fill=wheel_color, outline='#666666', width=2, tags="rover"
            )
            
            # Wheel center
            self.canvas.create_oval(
                wheel_x - 3, wheel_y - 3,
                wheel_x + 3, wheel_y + 3,
                fill='#666666', outline='#888888', tags="rover"
            )
        
        # Solar panels
        panel_width = body_width * 0.9
        panel_height = 6
        panel_y = self.rover_y - body_height/2 - 8
        
        self.canvas.create_rectangle(
            self.rover_x - panel_width/2, panel_y - panel_height/2,
            self.rover_x + panel_width/2, panel_y + panel_height/2,
            fill='#1a1a4a', outline='#4a4aff', width=1, tags="rover"
        )
        
        # Solar panel grid
        for i in range(8):
            x = self.rover_x - panel_width/2 + 10 + i * 15
            self.canvas.create_line(x, panel_y - panel_height/2 + 1,
                                  x, panel_y + panel_height/2 - 1,
                                  fill='#6a6aff', width=1, tags="rover")
        
        # Antenna
        antenna_x = self.rover_x + body_width/2 - 10
        antenna_base_y = module_y - module_height/2
        antenna_tip_y = antenna_base_y - 15
        
        self.canvas.create_line(antenna_x, antenna_base_y, antenna_x, antenna_tip_y,
                              fill='#ffffff', width=3, tags="rover")
        self.canvas.create_oval(antenna_x - 3, antenna_tip_y - 3,
                              antenna_x + 3, antenna_tip_y + 3,
                              fill='#ff0000', outline='#ffffff', tags="rover")
        
        # Front sensor array
        sensor_x = self.rover_x + body_width/2 - 5
        for i in range(3):
            sensor_y = self.rover_y - 8 + i * 8
            self.canvas.create_oval(sensor_x - 2, sensor_y - 2,
                                  sensor_x + 2, sensor_y + 2,
                                  fill='#00ff00', outline='#ffffff', tags="rover")
        
        # Direction indicator (enhanced arrow)
        arrow_x = self.rover_x + body_width/2 + 8
        arrow_points = [
            arrow_x, self.rover_y,
            arrow_x + 15, self.rover_y - 8,
            arrow_x + 10, self.rover_y,
            arrow_x + 15, self.rover_y + 8
        ]
        
        self.canvas.create_polygon(arrow_points, fill='#ffff00', outline='#ffffff', width=2, tags="rover")
        
        # Rover identification label
        self.canvas.create_text(self.rover_x, self.rover_y + 2,
                              text="MARS ROVER", fill='#ffffff', 
                              font=('Arial', 8, 'bold'), tags="rover")
        
        # Status indicator
        status_x = self.rover_x - body_width/2 - 20
        self.canvas.create_oval(status_x - 4, self.rover_y - 4,
                              status_x + 4, self.rover_y + 4,
                              fill='#00ff00', outline='#ffffff', width=1, tags="rover")
        self.canvas.create_text(status_x, self.rover_y - 15,
                              text="ACTIVE", fill='#00ff00', 
                              font=('Arial', 7), tags="rover")

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
        
        # Update sensor labels
        for name, state in self.sensor_states.items():
            if name in self.sensor_labels:
                label = self.sensor_labels[name]
                if state:
                    label.config(text="ON", bg='#00ff00', fg='black')
                else:
                    label.config(text="OFF", bg='#4a4a4a', fg='white')
        
        # Update gate moving states in labels
        self.sensor_labels['GATE_MOVING_A'].config(
            text="ON" if self.gate_a_moving else "OFF",
            bg='#00ff00' if self.gate_a_moving else '#4a4a4a',
            fg='black' if self.gate_a_moving else 'white'
        )
        self.sensor_labels['GATE_MOVING_B'].config(
            text="ON" if self.gate_b_moving else "OFF",
            bg='#00ff00' if self.gate_b_moving else '#4a4a4a',
            fg='black' if self.gate_b_moving else 'white'
        )
        
        # Update gate request states in labels
        self.sensor_labels['GATE_REQUEST_A'].config(
            text="ON" if self.gate_requests['GATE_REQUEST_A'] else "OFF",
            bg='#00ff00' if self.gate_requests['GATE_REQUEST_A'] else '#4a4a4a',
            fg='black' if self.gate_requests['GATE_REQUEST_A'] else 'white'
        )
        self.sensor_labels['GATE_REQUEST_B'].config(
            text="ON" if self.gate_requests['GATE_REQUEST_B'] else "OFF",
            bg='#00ff00' if self.gate_requests['GATE_REQUEST_B'] else '#4a4a4a',
            fg='black' if self.gate_requests['GATE_REQUEST_B'] else 'white'
        )
        
        # Request throttled update instead of immediate update
        self.request_update()

if __name__ == "__main__":
    root = tk.Tk()
    app = AirlockGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop() 