import tkinter as tk  # Still need standard tkinter for Canvas
import customtkinter as ctk
from datetime import datetime
import time

# =============================================================================
# UI CONFIGURATION SECTION - Customize the user interface appearance and behavior
# =============================================================================

# ------------------------------------------------------------------------------
# WINDOW AND DISPLAY SETTINGS
# ------------------------------------------------------------------------------
WINDOW_SCALE = 0.65
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600
ENABLE_FULLSCREEN_STARTUP = True

# ------------------------------------------------------------------------------
# FONT SETTINGS
# ------------------------------------------------------------------------------
PRIMARY_FONT_FAMILY = "Helvetica"
BUTTON_FONT_FAMILY = "Helvetica"
MONOSPACE_FONT_FAMILY = "Courier"

FONT_SIZE_DIVISOR = 60  # Changed from 80 to make fonts larger
FONT_SIZE_BASE_MIN = 10  # Changed from 8
FONT_SIZE_BASE_MAX = 16  # Changed from 12

# ------------------------------------------------------------------------------
# COLOR THEME SETTINGS - DARK MODE (Inverted Colors)
# ------------------------------------------------------------------------------
BACKGROUND_COLOR = "#1a1a1a"  # Dark background (inverted from #f0f0f0)
FRAME_BACKGROUND_COLOR = "#2d2d2d"  # Dark frame background (inverted from #ffffff)
TEXT_COLOR = "#e0e0e0"  # Light text (inverted from #000000)
SECONDARY_TEXT_COLOR = "#999999"  # Light secondary text (inverted from #666666)

BUTTON_BACKGROUND_COLOR = "#3d3d3d"  # Dark button (inverted from #e0e0e0)
BUTTON_ACTIVE_COLOR = "#4d4d4d"  # Slightly lighter on press (inverted from #d0d0d0)
BUTTON_TEXT_COLOR = "#e0e0e0"  # Light button text (inverted from #000000)

STATUS_READY_COLOR = "#28a745"  # Keep green for ready
STATUS_WARNING_COLOR = "#ffc107"  # Keep yellow for warning
STATUS_ERROR_COLOR = "#dc3545"  # Keep red for error

GRADE_PERFECT_COLOR = "#32CD32"  # Bright green for perfect
GRADE_GOOD_COLOR = "#90EE90"  # Light green for good
GRADE_FAIR_COLOR = "#FFB347"  # Light orange for fair
GRADE_POOR_COLOR = "#FF6B6B"  # Light red for poor

DETECTION_BOX_COLOR = "#00FF00"  # Keep bright green
ROI_OVERLAY_COLOR = "#FFFF00"  # Keep yellow

# ------------------------------------------------------------------------------
# LAYOUT AND SPACING SETTINGS
# ------------------------------------------------------------------------------
MAIN_PADDING = 5
FRAME_PADDING = 2
CAMERA_FRAME_PADDING = 1
ELEMENT_PADDING_X = 2
ELEMENT_PADDING_Y = 2
LABEL_PADDING = 5

CAMERA_FEEDS_WEIGHT = 0
CONTROLS_WEIGHT = 0
STATS_WEIGHT = 1
CAMERA_FEED_HEIGHT_WEIGHT = 0

CAMERA_ASPECT_RATIO = "16:9"
CAMERA_DISPLAY_MARGIN = -35
CAMERA_FEED_MARGIN = 0

# ------------------------------------------------------------------------------
# UI BEHAVIOR SETTINGS
# ------------------------------------------------------------------------------
ENABLE_TOOLTIPS = True
ENABLE_ANIMATIONS = False
AUTO_SCROLL_LOGS = True
SCROLL_SENSITIVITY = 3

UI_UPDATE_SKIP = 3
STATS_UPDATE_SKIP = 15
LOG_UPDATE_SKIP = 10

# ------------------------------------------------------------------------------
# ADVANCED UI SETTINGS
# ------------------------------------------------------------------------------
STATS_TAB_HEIGHT = 200
LOG_SCROLLABLE_HEIGHT = 200

STATUS_BAR_HEIGHT = 25
STATUS_UPDATE_INTERVAL = 100

DETECTION_DETAILS_HEIGHT = 150
MAX_DETECTION_ENTRIES = 50

# =============================================================================
# END OF UI CONFIGURATION SECTION
# =============================================================================


class GUIOnlyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Set appearance mode and color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        self.title("Wood Sorting Application - Modern UI (CustomTkinter)")

        # Get screen dimensions for dynamic sizing
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate window size
        if ENABLE_FULLSCREEN_STARTUP:
            self.attributes("-fullscreen", True)
            self.is_fullscreen = True
            window_width = screen_width
            window_height = screen_height
        else:
            window_width = int(screen_width * WINDOW_SCALE)
            window_height = int(screen_height * WINDOW_SCALE)
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2
            self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.resizable(True, True)
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # Fullscreen keybindings
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)

        # Calculate responsive font sizes
        base_font_size = max(FONT_SIZE_BASE_MIN, min(FONT_SIZE_BASE_MAX, int(screen_height / FONT_SIZE_DIVISOR)))
        self.font_small = (PRIMARY_FONT_FAMILY, base_font_size - 1)
        self.font_normal = (PRIMARY_FONT_FAMILY, base_font_size)
        self.font_large = (PRIMARY_FONT_FAMILY, base_font_size + 2, "bold")
        self.font_button = (BUTTON_FONT_FAMILY, base_font_size, "bold")

        # Initialize variables
        self.total_pieces_processed = 0
        self.session_start_time = time.time()
        self.grade_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        self.live_stats = {"grade1": 0, "grade2": 0, "grade3": 0, "grade4": 0, "grade5": 0}
        self.current_mode = "IDLE"
        
        # Camera display dimensions - match GUIonly.py exactly
        self.canvas_width = screen_width // 2 - 25
        self.canvas_height = 360

        self.create_gui()
        
        # Set close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_gui(self):
        """Create all GUI components with CustomTkinter"""
        
        # Wood specification notice at top
        notice_label = ctk.CTkLabel(
            self, 
            text="⚠ ACCEPTS ONLY 21\" × 5\" PALOCHINA WOOD ⚠",
            font=("Arial", 14, "bold"),
            fg_color="#8B0000",
            text_color="#FFE4E1",
            corner_radius=6,
            height=28
        )
        notice_label.place(relx=0.5, y=3, anchor="n")
        
        # Camera feed canvases - exact positioning and sizing with proper margins
        # Left camera with margin on left
        self.top_canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, 
                                   bg='black', highlightbackground="#555555", highlightthickness=1)
        self.top_canvas.place(x=10, y=35, width=self.canvas_width, height=self.canvas_height)

        # Right camera with proper spacing and right margin
        self.bottom_canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, 
                                      bg='black', highlightbackground="#555555", highlightthickness=1)
        self.bottom_canvas.place(x=self.canvas_width + 40, y=35, width=self.canvas_width, height=self.canvas_height)

        # Calculate available width for control panels to align with cameras
        screen_width = self.winfo_screenwidth()
        
        # Status panel - aligned under left camera with same width
        status_frame = ctk.CTkFrame(self, width=self.canvas_width, height=125, corner_radius=8)
        status_frame.place(x=10, y=415)  # Same x as top camera
        status_frame.pack_propagate(False)

        ctk.CTkLabel(status_frame, text="System Status", font=("Arial", 14, "bold")).pack(pady=(8, 2))

        self.status_label = tk.Text(status_frame, font=("Arial", 12), wrap=tk.WORD,
                                   height=3, width=int(self.canvas_width/10), state=tk.DISABLED, relief="flat",
                                   background=FRAME_BACKGROUND_COLOR, foreground=TEXT_COLOR,
                                   insertbackground=TEXT_COLOR, borderwidth=0)
        self.status_label.pack(pady=(2, 5), padx=8, fill="both", expand=True)
        self.update_status_text("Status: GUI Design Mode (CustomTkinter)")

        # Calculate positions for panels under right camera
        # Total width under right camera
        right_camera_x = self.canvas_width + 20
        available_width_right = self.canvas_width
        
        # ROI panel - smaller width
        roi_width = 250
        roi_frame = ctk.CTkFrame(self, width=roi_width, height=125, corner_radius=8)
        roi_frame.place(x=right_camera_x, y=415)
        roi_frame.pack_propagate(False)

        ctk.CTkLabel(roi_frame, text="ROI", font=("Arial", 14, "bold")).pack(pady=(8, 5))

        self.roi_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(roi_frame, text="Top ROI", variable=self.roi_var, 
                     font=("Arial", 12)).pack(anchor="w", padx=15, pady=3)

        self.bottom_roi_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(roi_frame, text="Bottom ROI", variable=self.bottom_roi_var,
                     font=("Arial", 12)).pack(anchor="w", padx=15, pady=3)

        self.lane_roi_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(roi_frame, text="Lane ROI", variable=self.lane_roi_var,
                     font=("Arial", 12)).pack(anchor="w", padx=15, pady=3)

        # Conveyor Control - positioned after ROI
        control_x = right_camera_x + roi_width + 10
        control_width = int((available_width_right - roi_width - 10) * 0.60)
        control_frame = ctk.CTkFrame(self, width=control_width, height=125, corner_radius=8)
        control_frame.place(x=control_x, y=415)
        control_frame.pack_propagate(False)

        ctk.CTkLabel(control_frame, text="Conveyor Control", 
                    font=("Arial", 14, "bold")).place(x=int(control_width/2 - 70), y=8)

        button_width = int((control_width - 20) / 2)
        ctk.CTkButton(
            control_frame, text="ON", command=lambda: self.set_mode("SCAN_PHASE"),
            fg_color="#28a745", hover_color="#218838", corner_radius=6,
            font=("Arial", 16, "bold"), width=button_width, height=45
        ).place(x=5, y=30)
        
        ctk.CTkButton(
            control_frame, text="OFF", command=lambda: self.set_mode("IDLE"),
            fg_color="#6c757d", hover_color="#5a6268", corner_radius=6,
            font=("Arial", 16, "bold"), width=button_width, height=45
        ).place(x=button_width + 10, y=30)
        
        # CLOSE button - exact width to match ON + OFF buttons combined
        close_button_width = (button_width * 2) + 5  # Both buttons + gap between them
        ctk.CTkButton(
            control_frame, text="CLOSE", command=self.on_closing,
            fg_color="#8B0000", hover_color="#660000", corner_radius=6,
            font=("Arial", 16, "bold"), width=close_button_width, height=45
        ).place(x=5, y=78)  # Aligned to left edge

        # Reports panel - fills remaining space to align with right edge of camera
        reports_x = control_x + control_width + 10
        reports_width = (right_camera_x + self.canvas_width) - reports_x
        reports_frame = ctk.CTkFrame(self, width=reports_width, height=180, corner_radius=8)
        reports_frame.place(x=reports_x, y=415)
        reports_frame.pack_propagate(False)

        ctk.CTkLabel(reports_frame, text="Reports", font=("Arial", 14, "bold")).pack(pady=(5, 2))

        # Create scrollable frame for reports content
        reports_scrollable = ctk.CTkScrollableFrame(reports_frame, 
                                                   width=reports_width - 20, 
                                                   height=80,
                                                   fg_color="transparent")
        reports_scrollable.pack(fill="both", expand=True, padx=8, pady=(0, 5))

        self.log_status_label = ctk.CTkLabel(
            reports_scrollable, text="Log: Ready",
            text_color=STATUS_READY_COLOR, font=("Arial", 11)
        )
        self.log_status_label.pack(pady=(2, 3))

        ctk.CTkButton(
            reports_scrollable, text="Generate Report",
            command=self.generate_report_placeholder,
            fg_color=BUTTON_BACKGROUND_COLOR, hover_color=BUTTON_ACTIVE_COLOR,
            corner_radius=6, height=30, font=("Arial", 12)
        ).pack(pady=2, padx=10, fill="x")

        ctk.CTkButton(
            reports_scrollable, text="View Session Folder",
            command=self.view_folder_placeholder,
            fg_color="#1E3A8A", hover_color="#1E40AF",
            corner_radius=6, height=30, font=("Arial", 12)
        ).pack(pady=2, padx=10, fill="x")

        ctk.CTkButton(
            reports_scrollable, text="Test Real Notifications",
            command=self.test_toast_notifications,
            fg_color="#6f42c1", hover_color="#5a2d91",
            corner_radius=6, height=30, font=("Arial", 12)
        ).pack(pady=2, padx=10, fill="x")

        ctk.CTkButton(
            reports_scrollable, text="Test Simple Notifications",
            command=self.test_simple_notifications,
            fg_color="#17a2b8", hover_color="#138496",
            corner_radius=6, height=30, font=("Arial", 12)
        ).pack(pady=2, padx=10, fill="x")

        self.show_report_notification = tk.BooleanVar(value=True)
        ctk.CTkSwitch(reports_scrollable, text="Notifications",
                     variable=self.show_report_notification,
                     font=("Arial", 11)).pack(pady=3)

        self.last_report_label = ctk.CTkLabel(reports_scrollable, text="Last: None",
                                              font=("Arial", 10), 
                                              wraplength=reports_width - 40,
                                              text_color=SECONDARY_TEXT_COLOR)
        self.last_report_label.pack(pady=(2, 5))

        # Statistics section
        self.create_statistics_section()

    def create_statistics_section(self):
        """Create the statistics section with CustomTkinter tabs"""
        # Main statistics frame at bottom - use screen width calculation
        screen_width = self.winfo_screenwidth()
        stats_width = screen_width - 20
        
        stats_outer_frame = ctk.CTkFrame(self, width=stats_width, height=480, corner_radius=8)
        stats_outer_frame.place(x=10, rely=1.0, anchor="sw")
        stats_outer_frame.pack_propagate(False)

        # Create tabview for statistics
        self.stats_tabview = ctk.CTkTabview(stats_outer_frame, height=455,
                                           segmented_button_fg_color="#2b2b2b",
                                           segmented_button_selected_color="#1f538d",
                                           segmented_button_selected_hover_color="#14375e")
        self.stats_tabview.pack(fill="both", expand=True, padx=8, pady=8)

        # Add tabs
        self.stats_tabview.add("SS-EN 1611-1 Summary")
        self.stats_tabview.add("Grading Standards")
        self.stats_tabview.add("System Performance")

        # Tab 1: Grade Summary
        self.create_grade_summary_tab()

        # Tab 2: Grading Standards
        self.create_grading_standards_tab()

        # Tab 3: Performance
        self.create_performance_tab()

    def create_grade_summary_tab(self):
        """Create grade summary tab with CTk widgets"""
        tab = self.stats_tabview.tab("SS-EN 1611-1 Summary")

        # Main container
        main_container = ctk.CTkFrame(tab, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # Title
        ctk.CTkLabel(main_container, text="SS-EN 1611-1 Live Grading Results", 
                    font=("Arial", 16, "bold")).pack(pady=(5, 10))  # Changed from 15

        # Camera grades row - more compact
        grades_row = ctk.CTkFrame(main_container, fg_color="transparent", height=75)  # Changed from 70
        grades_row.pack(fill="x", padx=5, pady=(0, 8))
        grades_row.pack_propagate(False)

        # Top Camera
        top_container = ctk.CTkFrame(grades_row, corner_radius=6)
        top_container.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(top_container, text="Top Camera:", 
                    font=("Arial", 12, "bold")).pack(pady=(10, 0))  # Changed from 11 and pady
        self.top_grade_label = ctk.CTkLabel(top_container, text="No Wood Graded", 
                                           text_color="gray", font=("Arial", 11))  # Changed from 10
        self.top_grade_label.pack(pady=(0, 10))  # Changed from 8

        # Bottom Camera
        bottom_container = ctk.CTkFrame(grades_row, corner_radius=6)
        bottom_container.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(bottom_container, text="Bottom Camera:", 
                    font=("Arial", 12, "bold")).pack(pady=(10, 0))  # Changed from 11 and pady
        self.bottom_grade_label = ctk.CTkLabel(bottom_container, text="No Wood Graded",
                                              text_color="gray", font=("Arial", 11))  # Changed from 10
        self.bottom_grade_label.pack(pady=(0, 10))  # Changed from 8

        # Final Grade
        final_container = ctk.CTkFrame(grades_row, corner_radius=6, 
                                      fg_color="#2d5016", border_width=1, 
                                      border_color="#4a7c2a")
        final_container.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(final_container, text="Final Grade:", 
                    font=("Arial", 13, "bold")).pack(pady=(10, 0))  # Changed from 12 and pady
        self.combined_grade_label = ctk.CTkLabel(final_container, text="No Wood Graded",
                                                font=("Arial", 12, "bold"),   # Changed from 11
                                                text_color="gray")
        self.combined_grade_label.pack(pady=(0, 10))  # Changed from 8

        # Grade counters container
        counters_container = ctk.CTkFrame(main_container, fg_color="transparent")
        counters_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.live_stats_labels = {}
        grade_info = [
            ("grade1", "G2-0\n(Good) → Bin 1", GRADE_PERFECT_COLOR),
            ("grade2", "G2-1\n(Good) → Bin 2", GRADE_GOOD_COLOR),
            ("grade3", "G2-2\n(Fair) → Bin 2", GRADE_FAIR_COLOR),
            ("grade4", "G2-3\n(Poor) → Bin 3", GRADE_FAIR_COLOR),
            ("grade5", "G2-4\n(Poor) → Bin 3", GRADE_POOR_COLOR)
        ]

        for grade_key, label_text, color in grade_info:
            grade_box = ctk.CTkFrame(counters_container, corner_radius=8, 
                                    border_width=2, border_color="#3a3a3a")
            grade_box.pack(side="left", fill="both", expand=True, padx=3)

            # Create inner frame to help with centering
            inner_box = ctk.CTkFrame(grade_box, fg_color="transparent")
            inner_box.pack(fill="both", expand=True)

            ctk.CTkLabel(inner_box, text=label_text, font=("Arial", 14, "bold"),  # Changed from 13
                        justify="center").pack(pady=(15, 5))  # Changed padding

            self.live_stats_labels[grade_key] = ctk.CTkLabel(
                inner_box, text="0", font=("Arial", 42, "bold"), text_color=color,  # Changed from 36
                anchor="center", justify="center"  # Added anchor and justify
            )
            self.live_stats_labels[grade_key].pack(pady=(5, 15), expand=True)  # Added expand=True

    def create_grading_standards_tab(self):
        """Create grading standards tab"""
        tab = self.stats_tabview.tab("Grading Standards")

        scrollable = ctk.CTkScrollableFrame(tab, corner_radius=8, 
                                           fg_color="#2b2b2b")
        scrollable.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(scrollable, text="SS-EN 1611-1 Pine Timber Grading Reference",
                    font=("Arial", 16, "bold")).pack(pady=(15, 10))  # Changed from 15

        content_text = """SS-EN 1611-1 Pine Timber Grading Standard

This is a placeholder for grading standards.

In the full application, this displays detailed grading criteria including:

• Knot size limits per grade
• Knot frequency limits
• Wood width-based adjustments
• Grading logic and decision rules
• Quality classification parameters
• Measurement methodologies"""

        text_label = ctk.CTkLabel(scrollable, text=content_text, 
                                 font=("Arial", 14), justify="left", anchor="w")  # Changed from 13
        text_label.pack(fill="both", padx=25, pady=10)

    def create_performance_tab(self):
        """Create performance tab"""
        tab = self.stats_tabview.tab("System Performance")

        scrollable = ctk.CTkScrollableFrame(tab, corner_radius=8,
                                           fg_color="#2b2b2b")
        scrollable.pack(fill="both", expand=True, padx=8, pady=8)

        ctk.CTkLabel(scrollable, text="System Configuration",
                    font=("Arial", 16, "bold")).pack(pady=(15, 10))  # Changed from 15

        content_text = """System Performance Metrics

This is a placeholder for performance data.

In the full application, this displays real-time metrics including:

• Processing speed and throughput
• Camera calibration settings
• Detection accuracy statistics
• System resource usage
• Hardware performance monitoring
• Network connectivity status"""

        text_label = ctk.CTkLabel(scrollable, text=content_text,
                                 font=("Arial", 14), justify="left", anchor="w")  # Changed from 13
        text_label.pack(fill="both", padx=25, pady=10)

    def update_status_text(self, text, color=None):
        """Update status text widget"""
        self.status_label.config(state=tk.NORMAL)
        self.status_label.delete(1.0, tk.END)
        self.status_label.insert(1.0, text)
        if color:
            self.status_label.config(foreground=color)
        self.status_label.config(state=tk.DISABLED)

    def set_mode(self, mode):
        """Set system mode (GUI only - no actual functionality)"""
        self.current_mode = mode
        self.update_status_text(f"Status: {mode}", STATUS_READY_COLOR)
        print(f"Mode set to: {mode}")

    def generate_report_placeholder(self):
        """Placeholder for report generation"""
        self.log_status_label.configure(text="Log: Report generated", text_color="#28a745")
        print("Generate Report clicked")

    def view_folder_placeholder(self):
        """Placeholder for view folder"""
        print("View Session Folder clicked")

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode"""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode"""
        self.is_fullscreen = False
        self.attributes("-fullscreen", False)
        return "break"

    def show_toast_notification(self, title, message, duration=5000, type="info"):
        """
        Show a non-blocking toast notification overlay
        
        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds (default 5000 = 5 seconds)
            type: Notification type - "success", "warning", "error", "info"
        """
        try:
            # Get current timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Color scheme based on notification type
            colors = {
                "success": {"bg": "#28a745", "fg": "#ffffff"},
                "warning": {"bg": "#ffc107", "fg": "#000000"},
                "error": {"bg": "#dc3545", "fg": "#ffffff"},
                "info": {"bg": "#17a2b8", "fg": "#ffffff"}
            }
            
            color_scheme = colors.get(type, colors["info"])
            
            # Define fixed toast dimensions (larger for kiosk)
            toast_width = 450
            toast_height = 120  # Increased from 100 to accommodate timestamp
            
            # Create toast frame (overlay on main window) with fixed size
            toast = ctk.CTkFrame(
                self,
                fg_color=color_scheme["bg"],
                corner_radius=10,
                border_width=2,
                border_color="#ffffff",
                width=toast_width,
                height=toast_height
            )
            toast.pack_propagate(False)  # Prevent content from resizing the frame
            
            # Timestamp label (small, subtle)
            timestamp_label = ctk.CTkLabel(
                toast,
                text=f"🕐 {timestamp}",
                font=("Arial", 12),
                text_color=color_scheme["fg"]
            )
            timestamp_label.pack(padx=20, pady=(8, 0))
            
            # Title label (larger font for kiosk)
            title_label = ctk.CTkLabel(
                toast,
                text=title,
                font=("Arial", 16, "bold"),  # Increased from 14 to 16
                text_color=color_scheme["fg"]
            )
            title_label.pack(padx=20, pady=(2, 2))
            
            # Message label (larger font for kiosk)
            message_label = ctk.CTkLabel(
                toast,
                text=message,
                font=("Arial", 14),  # Increased from 12 to 14
                text_color=color_scheme["fg"],
                wraplength=400
            )
            message_label.pack(padx=20, pady=(2, 12))
            
            # Position toast in the center of the margin between the two camera canvases
            toast.update_idletasks()  # Force geometry update
            
            # Calculate position - center of margin between cameras
            # Left camera ends at: 10 + canvas_width
            # Right camera starts at: canvas_width + 40
            # Margin between cameras is 30px (from x=canvas_width+10 to x=canvas_width+40)
            margin_center = self.canvas_width + 25  # Middle of the 30px margin
            x_position = margin_center - (toast_width // 2)  # Center toast on margin
            y_position = 35  # Below the wood specification notice
            
            # Place the toast (width already set in constructor)
            toast.place(x=x_position, y=y_position)
            
            # Lift toast to front
            toast.lift()
            
            # Auto-dismiss after duration
            def dismiss_toast():
                try:
                    toast.destroy()
                except:
                    pass
            
            # Schedule dismissal
            self.after(duration, dismiss_toast)
            
            # Optional: Click to dismiss
            def click_dismiss(event):
                dismiss_toast()
            
            toast.bind("<Button-1>", click_dismiss)
            timestamp_label.bind("<Button-1>", click_dismiss)
            title_label.bind("<Button-1>", click_dismiss)
            message_label.bind("<Button-1>", click_dismiss)
            
            print(f"Toast notification shown: [{timestamp}] {title}")
            
        except Exception as e:
            print(f"Error showing toast notification: {e}")
            # Fallback to console output
            print(f"TOAST: {title} - {message}")

    def test_toast_notifications(self):
        """Test all toast notification types with realistic examples"""
        # Camera reconnection success (from actual app)
        self.after(500, lambda: self.show_toast_notification(
            "Camera Reconnected",
            "Top camera successfully reconnected and ready",
            duration=5000,
            type="success"
        ))
        
        # Low confidence detection warning (from actual app)
        self.after(2500, lambda: self.show_toast_notification(
            "Low Confidence Detection",
            "Sound Knot detected with 45% confidence - below 50% threshold",
            duration=6000,
            type="warning"
        ))
        
        # Wood alignment warning (from actual app)
        self.after(5000, lambda: self.show_toast_notification(
            "Wood Misalignment Detected",
            "Wood touching top lane boundary - check conveyor alignment",
            duration=6000,
            type="warning"
        ))
        
        # Arduino reconnection (from actual app)
        self.after(7500, lambda: self.show_toast_notification(
            "Arduino Reconnected",
            "Controller reconnected on COM3 after 2 attempts",
            duration=5000,
            type="success"
        ))
        
        # Report generation success (from actual app)
        self.after(10000, lambda: self.show_toast_notification(
            "Report Generated",
            "PDF report saved: Wood_Session_2024-11-02_143022.pdf",
            duration=5000,
            type="info"
        ))
        
        # Camera disconnection error (from actual app)
        self.after(12500, lambda: self.show_toast_notification(
            "Camera Disconnected",
            "Bottom camera connection lost - attempting reconnection...",
            duration=8000,
            type="error"
        ))

    def test_simple_notifications(self):
        """Test simple notification types (original demo)"""
        # Success toast
        self.after(500, lambda: self.show_toast_notification(
            "Success",
            "This is a success notification example!",
            duration=5000,
            type="success"
        ))
        
        # Info toast
        self.after(2000, lambda: self.show_toast_notification(
            "Information",
            "This is an informational notification example.",
            duration=5000,
            type="info"
        ))
        
        # Warning toast
        self.after(3500, lambda: self.show_toast_notification(
            "Warning",
            "This is a warning notification example.",
            duration=5000,
            type="warning"
        ))
        
        # Error toast
        self.after(5000, lambda: self.show_toast_notification(
            "Error",
            "This is an error notification example.",
            duration=5000,
            type="error"
        ))

    def on_closing(self):
        """Handle window closing"""
        print("Closing GUI design application...")
        self.destroy()


if __name__ == "__main__":
    app = GUIOnlyApp()
    
    # Test realistic toast notifications after a short delay
    app.after(1000, app.test_toast_notifications)
    
    app.mainloop()
