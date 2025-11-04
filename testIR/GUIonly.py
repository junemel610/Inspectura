import tkinter as tk
from tkinter import ttk
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

FONT_SIZE_DIVISOR = 80
FONT_SIZE_BASE_MIN = 8
FONT_SIZE_BASE_MAX = 12

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


class GUIOnlyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wood Sorting Application - GUI Design (Dark Mode)")
        
        # Set dark background for main window
        self.configure(bg=BACKGROUND_COLOR)

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

        # Configure styles for dark mode
        style = ttk.Style()
        
        # Configure dark theme for ttk widgets
        style.theme_use('clam')  # Use clam theme as base for better dark mode support
        
        # Configure general ttk styles
        style.configure(".", background=BACKGROUND_COLOR, foreground=TEXT_COLOR,
                       fieldbackground=FRAME_BACKGROUND_COLOR)
        
        # LabelFrame style
        style.configure("TLabelFrame", background=BACKGROUND_COLOR, foreground=TEXT_COLOR,
                       bordercolor="#555555", relief="solid")
        style.configure("TLabelFrame.Label", background=BACKGROUND_COLOR, foreground=TEXT_COLOR)
        
        # Frame style
        style.configure("TFrame", background=BACKGROUND_COLOR)
        
        # Label style
        style.configure("TLabel", background=BACKGROUND_COLOR, foreground=TEXT_COLOR)
        
        # Checkbutton style
        style.configure("TCheckbutton", background=BACKGROUND_COLOR, foreground=TEXT_COLOR)
        style.map("TCheckbutton", background=[("active", BACKGROUND_COLOR)])
        
        # Notebook (tabs) style
        style.configure("TNotebook", background=BACKGROUND_COLOR, borderwidth=0)
        style.configure("TNotebook.Tab", background=BUTTON_BACKGROUND_COLOR, 
                       foreground=TEXT_COLOR, padding=[10, 2])
        style.map("TNotebook.Tab", background=[("selected", FRAME_BACKGROUND_COLOR)],
                 foreground=[("selected", TEXT_COLOR)])
        
        # Button style
        style.configure("Custom.TButton",
                       background=BUTTON_BACKGROUND_COLOR,
                       foreground=BUTTON_TEXT_COLOR,
                       font=self.font_button,
                       borderwidth=1,
                       relief="raised")
        style.map("Custom.TButton",
                 background=[("active", BUTTON_ACTIVE_COLOR),
                           ("pressed", BUTTON_ACTIVE_COLOR)])

        # Initialize variables
        self.total_pieces_processed = 0
        self.session_start_time = time.time()
        self.grade_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        self.live_stats = {"grade1": 0, "grade2": 0, "grade3": 0, "grade4": 0, "grade5": 0}
        self.current_mode = "IDLE"
        
        # Camera display dimensions
        self.canvas_width = screen_width // 2 - 25
        self.canvas_height = 360

        self.create_gui()
        
        # Set close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_gui(self):
        """Create all GUI components"""
        
        # Wood specification notice at top - adjusted for dark mode
        notice_label = tk.Label(self, 
                               text="⚠ ACCEPTS ONLY 21\" × 5\" PALOCHINA WOOD ⚠",
                               font=("Arial", 10, "bold"),
                               bg="#8B0000",  # Dark red background
                               fg="#FFE4E1",  # Light pink text
                               relief=tk.RAISED,
                               borderwidth=2,
                               padx=12,
                               pady=2)
        notice_label.place(relx=0.5, y=3, anchor="n")
        
        # Camera feed canvases - keep black for camera feeds
        self.top_canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, 
                                   bg='black', highlightbackground="#555555", highlightthickness=1)
        self.top_canvas.place(x=25, y=28, width=self.canvas_width, height=self.canvas_height)

        self.bottom_canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, 
                                      bg='black', highlightbackground="#555555", highlightthickness=1)
        self.bottom_canvas.place(x=self.canvas_width + 50, y=28, width=self.canvas_width, height=self.canvas_height)

        # Status panel under top camera
        status_frame = ttk.LabelFrame(self, text="System Status", padding=FRAME_PADDING)
        status_frame.place(x=25, y=415, width=640, height=125)

        self.status_label = tk.Text(status_frame, font=self.font_normal, wrap=tk.WORD,
                                   height=3, width=25, state=tk.DISABLED, relief="flat",
                                   background=FRAME_BACKGROUND_COLOR, foreground=TEXT_COLOR,
                                   insertbackground=TEXT_COLOR)
        self.status_label.pack(pady=LABEL_PADDING, fill="x", expand=False)
        self.update_status_text("Status: GUI Design Mode (Dark Mode)")

        # ROI panel under bottom camera
        roi_frame = ttk.LabelFrame(self, text="ROI", padding=FRAME_PADDING)
        roi_frame.place(x=675, y=415, width=250, height=125)

        self.roi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(roi_frame, text="Top ROI", variable=self.roi_var).pack(anchor="w")

        self.bottom_roi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(roi_frame, text="Bottom ROI", variable=self.bottom_roi_var).pack(anchor="w")

        self.lane_roi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(roi_frame, text="Lane ROI", variable=self.lane_roi_var).pack(anchor="w")

        # Conveyor Control - with resized buttons
        control_frame = ttk.LabelFrame(self, text="Conveyor Control", padding=FRAME_PADDING)
        control_frame.place(x=935, y=415, width=655, height=125)

        tk.Button(control_frame, text="ON",
                  command=lambda: self.set_mode("SCAN_PHASE"), bg=BUTTON_BACKGROUND_COLOR,
                  fg=BUTTON_TEXT_COLOR, activebackground=BUTTON_ACTIVE_COLOR,
                  font=self.font_button, relief="raised", borderwidth=2).place(x=0, y=0, width=320, height=45)
        tk.Button(control_frame, text="OFF",
                  command=lambda: self.set_mode("IDLE"), bg=BUTTON_BACKGROUND_COLOR,
                  fg=BUTTON_TEXT_COLOR, activebackground=BUTTON_ACTIVE_COLOR,
                  font=self.font_button, relief="raised", borderwidth=2).place(x=328, y=0, width=320, height=45)
        tk.Button(control_frame, text="CLOSE",
                  command=self.on_closing, bg="#8B0000",  # Dark red
                  fg="#FFE4E1", activebackground="#660000",  # Darker red on press
                  font=self.font_button, relief="raised", borderwidth=2).place(x=0, y=50, width=648, height=45)

        # Reports panel - with centered scrollable content (reduced height)
        reports_frame = ttk.LabelFrame(self, text="Reports", padding=FRAME_PADDING)
        reports_frame.place(x=1600, y=415, width=300, height=125)  # Reduced from 200 to 125

        # Create canvas for scrollable reports content
        reports_canvas = tk.Canvas(reports_frame, bg=BACKGROUND_COLOR, highlightthickness=0, borderwidth=0)
        reports_scrollbar = ttk.Scrollbar(reports_frame, orient="vertical", command=reports_canvas.yview)
        reports_content = ttk.Frame(reports_canvas)

        reports_content.bind("<Configure>", lambda e: reports_canvas.configure(scrollregion=reports_canvas.bbox("all")))
        reports_canvas.create_window((0, 0), window=reports_content, anchor="nw", width=280)  # Set width for centering
        reports_canvas.configure(yscrollcommand=reports_scrollbar.set)

        reports_canvas.pack(side="left", fill="both", expand=True)
        reports_scrollbar.pack(side="right", fill="y")

        # Reports content inside scrollable area - all centered with reduced spacing
        self.log_status_label = ttk.Label(reports_content, text="Log: Ready",
                                        foreground=STATUS_READY_COLOR, font=self.font_small,
                                        anchor="center")
        self.log_status_label.pack(pady=1, fill="x")  # Reduced padding from 2 to 1

        tk.Button(reports_content, text="Generate Report",
                  command=self.generate_report_placeholder, bg=BUTTON_BACKGROUND_COLOR,
                  fg=BUTTON_TEXT_COLOR, activebackground=BUTTON_ACTIVE_COLOR,
                  font=self.font_button, relief="raised", borderwidth=2).pack(pady=1, padx=20)  # Reduced padding

        tk.Button(reports_content, text="View Session Folder",
                  command=self.view_folder_placeholder, bg="#1E3A8A",  # Dark blue
                  fg="#E0E7FF", activebackground="#1E40AF",  # Slightly lighter blue
                  font=self.font_button, relief="raised", borderwidth=2).pack(pady=1, padx=20)  # Reduced padding

        self.show_report_notification = tk.BooleanVar(value=True)
        notification_check = ttk.Checkbutton(reports_content, text="Notifications",
                       variable=self.show_report_notification)
        notification_check.pack(pady=1)  # Reduced padding from 2 to 1
        # Center the checkbutton by packing in a centered frame
        reports_content.grid_columnconfigure(0, weight=1)

        self.last_report_label = ttk.Label(reports_content, text="Last: None",
                                          font=self.font_small, wraplength=260,
                                          anchor="center", justify="center")
        self.last_report_label.pack(pady=1, fill="x")  # Reduced padding from 2 to 1

        # Bind mousewheel to reports canvas ONLY when mouse is over it
        def _on_mousewheel_reports(event):
            reports_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel_reports(event):
            reports_canvas.bind_all("<MouseWheel>", _on_mousewheel_reports)
        
        def _unbind_mousewheel_reports(event):
            reports_canvas.unbind_all("<MouseWheel>")
        
        reports_canvas.bind("<Enter>", _bind_mousewheel_reports)
        reports_canvas.bind("<Leave>", _unbind_mousewheel_reports)

        # Statistics section
        self.create_statistics_section()

    def create_statistics_section(self):
        """Create the statistics section with tabs"""
        stats_frame = ttk.LabelFrame(self, text="Statistics", padding=FRAME_PADDING)
        stats_frame.place(x=0, rely=1.0, relwidth=1, height=500, anchor="sw")

        # Create notebook for tabbed statistics
        self.stats_notebook = ttk.Notebook(stats_frame, height=STATS_TAB_HEIGHT - 40)
        self.stats_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # Tab 1: Grade Summary
        grade_summary_tab = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(grade_summary_tab, text="SS-EN 1611-1 Summary")

        # Live Grading Section
        live_grading_frame = ttk.LabelFrame(grade_summary_tab, text="SS-EN 1611-1 Live Grading Results", padding="10")
        live_grading_frame.pack(fill="both", expand=True, pady=(10, 5), padx=10)

        live_grading_frame.grid_rowconfigure(0, weight=0)
        live_grading_frame.grid_rowconfigure(1, weight=1)
        live_grading_frame.grid_columnconfigure(0, weight=1)

        # Individual camera grades
        individual_grades_frame = ttk.Frame(live_grading_frame)
        individual_grades_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        individual_grades_frame.grid_columnconfigure(0, weight=3)
        individual_grades_frame.grid_columnconfigure(1, weight=3)
        individual_grades_frame.grid_columnconfigure(2, weight=4)

        # Top camera grade
        top_grade_container = ttk.Frame(individual_grades_frame)
        top_grade_container.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Label(top_grade_container, text="Top Camera:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.top_grade_label = ttk.Label(top_grade_container, text="No Wood Graded",
                                        foreground="gray", font=self.font_small)
        self.top_grade_label.pack(anchor="w")

        # Bottom camera grade
        bottom_grade_container = ttk.Frame(individual_grades_frame)
        bottom_grade_container.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Label(bottom_grade_container, text="Bottom Camera:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.bottom_grade_label = ttk.Label(bottom_grade_container, text="No Wood Graded",
                                           foreground="gray", font=self.font_small)
        self.bottom_grade_label.pack(anchor="w")

        # Combined grade
        combined_container = ttk.Frame(individual_grades_frame)
        combined_container.grid(row=0, column=2, sticky="ew")
        ttk.Label(combined_container, text="Final Grade:", font=("Arial", 12, "bold")).pack(anchor="w")
        self.combined_grade_label = ttk.Label(combined_container, text="No Wood Graded",
                                             font=("Arial", 11, "bold"), foreground="gray")
        self.combined_grade_label.pack(anchor="w")

        # Grade counts
        grade_counts_container = ttk.Frame(live_grading_frame)
        grade_counts_container.grid(row=1, column=0, sticky="nsew")

        grade_counts_container.grid_rowconfigure(0, weight=1)
        for i in range(5):
            grade_counts_container.grid_columnconfigure(i, weight=1)

        # Create grade count displays with dark mode borders
        self.live_stats_labels = {}
        grade_info = [
            ("grade1", "G2-0\n(Good)", GRADE_PERFECT_COLOR),
            ("grade2", "G2-1\n(Good)", GRADE_GOOD_COLOR),
            ("grade3", "G2-2\n(Fair)", GRADE_FAIR_COLOR),
            ("grade4", "G2-3\n(Fair)", GRADE_FAIR_COLOR),
            ("grade5", "G2-4\n(Poor)", GRADE_POOR_COLOR)
        ]

        for i, (grade_key, label_text, color) in enumerate(grade_info):
            # Use tk.Frame instead of ttk.Frame for better border control in dark mode
            grade_container = tk.Frame(grade_counts_container, relief="solid", 
                                      borderwidth=2, bg=FRAME_BACKGROUND_COLOR,
                                      highlightbackground="#555555", highlightthickness=1)
            grade_container.grid(row=0, column=i, sticky="nsew", padx=2, pady=5)
            grade_container.grid_columnconfigure(0, weight=1)
            grade_container.grid_rowconfigure(0, weight=1)
            grade_container.grid_rowconfigure(1, weight=1)

            inner_frame = tk.Frame(grade_container, bg=FRAME_BACKGROUND_COLOR)
            inner_frame.grid(row=0, column=0, sticky="nsew", rowspan=2)
            inner_frame.grid_columnconfigure(0, weight=1)
            inner_frame.grid_rowconfigure(0, weight=1)
            inner_frame.grid_rowconfigure(1, weight=1)

            title_label = tk.Label(inner_frame, text=label_text, font=("Arial", 12, "bold"),
                                  justify="center", wraplength=80, anchor="center",
                                  bg=FRAME_BACKGROUND_COLOR, fg=TEXT_COLOR)
            title_label.grid(row=0, column=0, sticky="ew", padx=2, pady=(8, 2))

            self.live_stats_labels[grade_key] = tk.Label(inner_frame, text="0",
                                                         foreground=color, font=("Arial", 32, "bold"),
                                                         anchor="center", bg=FRAME_BACKGROUND_COLOR)
            self.live_stats_labels[grade_key].grid(row=1, column=0, sticky="ew", padx=2, pady=(2, 8))

        # Tab 2: Grading Details
        grading_details_tab = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(grading_details_tab, text="Grading Standards")
        self.grading_details_frame = ttk.Frame(grading_details_tab)
        self.grading_details_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.create_grading_details_content()

        # Tab 3: Performance Metrics
        performance_tab = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(performance_tab, text="System Performance")
        self.performance_frame = ttk.Frame(performance_tab)
        self.performance_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.create_performance_content()

    def create_grading_details_content(self):
        """Create grading details tab content"""
        canvas = tk.Canvas(self.grading_details_frame, highlightthickness=0, borderwidth=0,
                          bg=BACKGROUND_COLOR)
        scrollbar = ttk.Scrollbar(self.grading_details_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BACKGROUND_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # Create window with proper width to stretch content
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind canvas width to stretch the scrollable frame
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        scrollbar.pack(side="right", fill="y")

        # Content
        thresholds_frame = tk.LabelFrame(scrollable_frame, text="SS-EN 1611-1 Pine Timber Grading Reference", 
                                        padx=10, pady=10, bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
                                        borderwidth=1, relief="solid")
        thresholds_frame.pack(fill="both", expand=True, pady=5, padx=5)

        threshold_text = "SS-EN 1611-1 Pine Timber Grading Standard\n\n"
        threshold_text += "This is a placeholder for grading standards.\n\n"
        threshold_text += "In the full application, this displays detailed grading criteria including:\n\n"
        threshold_text += "• Knot size limits per grade\n"
        threshold_text += "• Knot frequency limits\n"
        threshold_text += "• Wood width-based adjustments\n"
        threshold_text += "• Grading logic and decision rules\n"

        text_widget = tk.Text(thresholds_frame, wrap=tk.WORD, height=20, font=("TkDefaultFont", 13),
                             bg=FRAME_BACKGROUND_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                             relief="flat", padx=10, pady=10)
        text_widget.insert("1.0", threshold_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill="both", expand=True, padx=5, pady=5)

        # Bind mousewheel to grading details canvas ONLY when mouse is over it
        def _on_mousewheel_grading(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel_grading(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel_grading)
        
        def _unbind_mousewheel_grading(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", _bind_mousewheel_grading)
        canvas.bind("<Leave>", _unbind_mousewheel_grading)

    def create_performance_content(self):
        """Create performance metrics tab content"""
        canvas = tk.Canvas(self.performance_frame, highlightthickness=0, borderwidth=0,
                          bg=BACKGROUND_COLOR)
        scrollbar = ttk.Scrollbar(self.performance_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BACKGROUND_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # Create window with proper width to stretch content
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Bind canvas width to stretch the scrollable frame
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        scrollbar.pack(side="right", fill="y")

        # Content
        calibration_frame = tk.LabelFrame(scrollable_frame, text="System Configuration", 
                                         padx=10, pady=10, bg=BACKGROUND_COLOR, fg=TEXT_COLOR,
                                         borderwidth=1, relief="solid")
        calibration_frame.pack(fill="x", pady=5, padx=5)

        calibration_text = "System Performance Metrics\n\n"
        calibration_text += "This is a placeholder for performance data.\n\n"
        calibration_text += "In the full application, this displays real-time metrics including:\n\n"
        calibration_text += "• Processing speed and throughput\n"
        calibration_text += "• Camera calibration settings\n"
        calibration_text += "• Detection accuracy statistics\n"
        calibration_text += "• System resource usage\n"

        tk.Label(calibration_frame, text=calibration_text, font=("TkDefaultFont", 13),
                justify="left", anchor="w", bg=BACKGROUND_COLOR, fg=TEXT_COLOR).pack(fill="x", padx=10, pady=10)

        # Bind mousewheel to performance canvas ONLY when mouse is over it
        def _on_mousewheel_performance(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel_performance(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel_performance)
        
        def _unbind_mousewheel_performance(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", _bind_mousewheel_performance)
        canvas.bind("<Leave>", _unbind_mousewheel_performance)

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
        self.log_status_label.config(text="Log: Report generated (placeholder)", foreground="green")
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

    def on_closing(self):
        """Handle window closing"""
        print("Closing GUI design application...")
        self.destroy()


if __name__ == "__main__":
    app = GUIOnlyApp()
    app.mainloop()
