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
WINDOW_SCALE = 1.0
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
# COLOR THEME SETTINGS - LIGHT MODE
# ------------------------------------------------------------------------------
BACKGROUND_COLOR = "#f0f0f0"  # Light background
FRAME_BACKGROUND_COLOR = "#ffffff"  # Light frame background
TEXT_COLOR = "#000000"  # Dark text
SECONDARY_TEXT_COLOR = "#666666"  # Dark secondary text

BUTTON_BACKGROUND_COLOR = "#e0e0e0"  # Light button
BUTTON_ACTIVE_COLOR = "#d0d0d0"  # Slightly darker on press
BUTTON_TEXT_COLOR = "#000000"  # Dark button text

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
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
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
        self.last_report = {}
        
        # Camera display dimensions - match GUIonly.py exactly
        self.canvas_width = screen_width // 2 - 25
        self.canvas_height = 360

        self.create_gui()
        
        # Set close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_gui(self):
        """Create all GUI components with CustomTkinter"""

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Account for tabview padding
        tabview_padding = 10
        available_width = screen_width - 2 * tabview_padding
        available_height = screen_height - 2 * tabview_padding

        # Create tabview
        self.tabview = ctk.CTkTabview(self, width=available_width, height=available_height)
        self.tabview.pack(fill="both", expand=True, padx=tabview_padding, pady=tabview_padding)

        # Add tabs
        self.live_tab = self.tabview.add("Live View")
        self.reports_tab = self.tabview.add("Reports")

        # Configure grid for reports tab
        self.reports_tab.grid_rowconfigure(0, weight=10)
        self.reports_tab.grid_rowconfigure(1, weight=1)
        self.reports_tab.grid_columnconfigure(0, weight=1)

        # Set default tab
        self.tabview.set("Live View")

        # Calculate layout dimensions for live tab
        padding = 10
        top_section_height = int(available_height * 0.5)  # 50% for camera feeds
        middle_section_height = int(available_height * 0.3)  # 30% for defect panels
        bottom_section_height = int(available_height * 0.2)  # 20% for controls

        # =====================
        # TOP SECTION - Camera Feeds (side by side)
        # =====================

        camera_width = (available_width - 3 * padding) // 2
        camera_height = top_section_height - 2 * padding

        # Left Camera Feed
        self.left_canvas = tk.Canvas(self.live_tab, width=camera_width, height=camera_height,
                                    bg='lightgray', highlightbackground="#cccccc", highlightthickness=2)
        self.left_canvas.place(x=padding, y=padding)

        # Right Camera Feed
        self.right_canvas = tk.Canvas(self.live_tab, width=camera_width, height=camera_height,
                                     bg='lightgray', highlightbackground="#cccccc", highlightthickness=2)
        self.right_canvas.place(x=padding + camera_width + padding, y=padding)

        # =====================
        # MIDDLE SECTION - Defect Classification Panels (4 panels in a row)
        # =====================

        middle_y = padding + top_section_height + padding
        defect_panel_width = (available_width - 5 * padding) // 4
        defect_panel_height = middle_section_height - 2 * padding

        defect_titles = ["DEAD KNOTS", "LIVE KNOTS", "MISSING KNOTS", "KNOTS W/ CRACKS"]
        self.defect_labels = {}

        for i, title in enumerate(defect_titles):
            x_pos = padding + i * (defect_panel_width + padding)

            defect_frame = ctk.CTkFrame(self.live_tab, width=defect_panel_width, height=defect_panel_height,
                                       corner_radius=6, fg_color="white")
            defect_frame.place(x=x_pos, y=middle_y)
            defect_frame.pack_propagate(False)

            # Title label
            ctk.CTkLabel(defect_frame, text=title, font=("Arial", 24, "bold"), text_color="black").pack(pady=(10, 5))

            # Scrollable container for detections
            defect_scroll = ctk.CTkScrollableFrame(defect_frame, width=defect_panel_width - 20,
                                                  height=defect_panel_height - 60, fg_color="transparent")
            defect_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 10))

            # Label for displaying detections
            defect_label = ctk.CTkLabel(defect_scroll, text="No detected items",
                                       text_color="gray", font=("Arial", 14))
            defect_label.pack(pady=10)

            self.defect_labels[title] = defect_label

        # =====================
        # BOTTOM SECTION - Status & Controls
        # =====================

        bottom_y = middle_y + middle_section_height + padding
        bottom_left_width = (available_width - 3 * padding) // 2
        bottom_right_width = bottom_left_width

        # Left side - Wood's Grade and Status
        grade_frame = ctk.CTkFrame(self.live_tab, width=bottom_left_width, height=100,
                                    corner_radius=6, fg_color=FRAME_BACKGROUND_COLOR)
        grade_frame.place(x=padding, y=bottom_y)
        grade_frame.pack_propagate(False)

        self.grade_label = ctk.CTkLabel(grade_frame, text="WOOD'S GRADE: G2-0",
                                       font=("Arial", 24, "bold"), text_color="black")
        self.grade_label.pack(pady=(10, 5))

        self.status_label = ctk.CTkLabel(grade_frame, text="Status: IDLE",
                                        font=("Arial", 16, "bold"), text_color="green")
        self.status_label.pack(pady=(5, 10))

        # Right side - Control buttons
        button_frame = ctk.CTkFrame(self.live_tab, width=bottom_right_width, height=100,
                                    corner_radius=6, fg_color=FRAME_BACKGROUND_COLOR)
        button_frame.place(x=padding + bottom_left_width + padding, y=bottom_y)
        button_frame.pack_propagate(False)

        # Buttons frame for horizontal layout
        buttons_subframe = ctk.CTkFrame(button_frame, fg_color="transparent")
        buttons_subframe.pack(fill="both", expand=True, padx=5, pady=20)

        # START button
        start_button = ctk.CTkButton(
            buttons_subframe, text="START", command=lambda: self.set_mode("SCAN_PHASE"),
            fg_color="#28a745", hover_color="#218838", corner_radius=6,
            font=("Arial", 20, "bold")
        )
        start_button.pack(side="left", fill="both", expand=True, padx=(0, 2))

        # STOP button
        stop_button = ctk.CTkButton(
            buttons_subframe, text="STOP", command=lambda: self.set_mode("IDLE"),
            fg_color="#dc3545", hover_color="#c82333", corner_radius=6,
            font=("Arial", 20, "bold")
        )
        stop_button.pack(side="left", fill="both", expand=True, padx=(2, 0))

        # =====================
        # REPORTS TAB CONTENT
        # =====================

        # Last Graded Report Section
        report_frame = ctk.CTkFrame(self.reports_tab, corner_radius=6)
        report_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(report_frame, text="Last Graded Report", font=("Arial", 34, "bold")).pack(pady=(10, 5))

        self.last_report_text = ctk.CTkTextbox(report_frame, wrap="word", font=("Arial", 15))
        self.last_report_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.last_report_text.insert("0.0", "No reports available yet.\n\nLast graded piece details will appear here.")
        self.last_report_text.configure(state="disabled")

        # Live Grading Result Section
        live_frame = ctk.CTkFrame(self.reports_tab, corner_radius=6)
        live_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        ctk.CTkLabel(live_frame, text="Live Grading Results", font=("Arial", 34, "bold")).pack(pady=(10, 5))

        # Grades container
        grades_frame = ctk.CTkFrame(live_frame, fg_color="transparent")
        grades_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        grades = ["G2-0", "G2-1", "G2-2", "G2-3", "G2-4"]
        colors = ["#32CD32", "#90EE90", "#FFB347", "#FF6B6B", "#8B0000"]  # perfect to worst
        self.count_labels = {}

        for i, (grade, color) in enumerate(zip(grades, colors)):
            grade_container = ctk.CTkFrame(grades_frame, fg_color=color, corner_radius=6)
            grade_container.pack(side="left", fill="both", expand=True, padx=(0 if i==0 else 2, 2 if i<4 else 0))
            grade_label = ctk.CTkLabel(grade_container, text=grade, font=("Arial", 20, "bold"), text_color="black")
            grade_label.pack(pady=(15, 0))
            count_label = ctk.CTkLabel(grade_container, text=str(self.grade_counts.get(i+1, 0)), font=("Arial", 40, "bold"), text_color="black")
            count_label.pack(pady=(0, 15))
            self.count_labels[grade] = count_label

        self.update_live_results()

    def update_status_text(self, text, color=None):
        """Update status text widget"""
        self.status_label.configure(text=text, text_color=color)

    def update_live_results(self):
        """Update the live grading results display"""
        for grade_num, count in self.grade_counts.items():
            grade = f"G2-{grade_num-1}"
            if grade in self.count_labels:
                self.count_labels[grade].configure(text=str(count))

    def update_last_report(self):
        """Update the last graded report display"""
        if self.last_report:
            report = f"Timestamp: {self.last_report['timestamp']}\n"
            report += f"Grade: {self.last_report['grade']}\n"
            report += f"Defects Detected: {', '.join(self.last_report['defects'])}\n"
        else:
            report = "No reports available yet.\n\nLast graded piece details will appear here."
        self.last_report_text.configure(state="normal")
        self.last_report_text.delete("0.0", "end")
        self.last_report_text.insert("0.0", report)
        self.last_report_text.configure(state="disabled")

    def set_mode(self, mode):
        """Set system mode (GUI only - no actual functionality)"""
        self.current_mode = mode
        if mode == "SCAN_PHASE":
            # Simulate grading a piece
            self.total_pieces_processed += 1
            grade = 2  # Simulate grade
            self.grade_counts[grade] += 1
            self.last_report = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "grade": f"G{grade}-0",
                "defects": ["Dead Knot", "Live Knot"]
            }
            self.update_last_report()
            self.update_live_results()
            self.grade_label.configure(text=f"WOOD'S GRADE: G{grade}-0")
        self.update_status_text(f"Status: {mode}", STATUS_READY_COLOR)
        print(f"Mode set to: {mode}")

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
