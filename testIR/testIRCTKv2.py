import tkinter as tk  # Still need standard tkinter for Canvas
from tkinter import ttk
import customtkinter as ctk  # Modern UI library
try:
    from CTkMessagebox import CTkMessagebox
except ImportError:
    print("CTkMessagebox not installed. Install with: pip install CTkMessagebox")
    CTkMessagebox = None
import cv2
from PIL import Image, ImageTk
import serial
import threading
import time
import queue

# Import AI libraries with error handling
try:
    import degirum as dg
    import degirum_tools
except ImportError as e:
    print(f"Warning: AI libraries not installed - {e}")
    print("Install with: pip install degirum degirum-tools")
    dg = None
    degirum_tools = None

import json
import os
import subprocess
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import numpy as np
from typing import Dict, List, Tuple, Optional

# =============================================================================
# MODERN MESSAGEBOX WRAPPER - CustomTkinter Compatible
# =============================================================================

class ModernMessageBox:
    """Modern messagebox wrapper compatible with CustomTkinter dark theme"""
    
    @staticmethod
    def showinfo(title, message, **kwargs):
        """Show info message with modern styling"""
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamped_message = f"[{timestamp}]\n{message}"
        
        if CTkMessagebox:
            msg = CTkMessagebox(
                title=title,
                message=timestamped_message,
                icon="info",
                option_1="OK",
                **kwargs
            )
            return msg.get()
        else:
            # Fallback to standard messagebox
            from tkinter import messagebox
            return messagebox.showinfo(title, timestamped_message)
    
    @staticmethod
    def showwarning(title, message, **kwargs):
        """Show warning message with modern styling"""
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamped_message = f"[{timestamp}]\n{message}"
        
        if CTkMessagebox:
            msg = CTkMessagebox(
                title=title,
                message=timestamped_message,
                icon="warning",
                option_1="OK",
                **kwargs
            )
            return msg.get()
        else:
            from tkinter import messagebox
            return messagebox.showwarning(title, timestamped_message)
    
    @staticmethod
    def showerror(title, message, **kwargs):
        """Show error message with modern styling"""
        # Add timestamp to message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamped_message = f"[{timestamp}]\n{message}"
        
        if CTkMessagebox:
            msg = CTkMessagebox(
                title=title,
                message=timestamped_message,
                icon="cancel",
                option_1="OK",
                **kwargs
            )
            return msg.get()
        else:
            from tkinter import messagebox
            return messagebox.showerror(title, timestamped_message)
    
    @staticmethod
    def askyesno(title, message, **kwargs):
        """Ask yes/no question with modern styling"""
        if CTkMessagebox:
            msg = CTkMessagebox(
                title=title,
                message=message,
                icon="question",
                option_1="No",
                option_2="Yes",
                **kwargs
            )
            return msg.get() == "Yes"
        else:
            from tkinter import messagebox
            return messagebox.askyesno(title, message)
    
    @staticmethod
    def askyesnocancel(title, message, **kwargs):
        """Ask yes/no/cancel question with modern styling"""
        if CTkMessagebox:
            msg = CTkMessagebox(
                title=title,
                message=message,
                icon="question",
                option_1="Cancel",
                option_2="No",
                option_3="Yes",
                **kwargs
            )
            result = msg.get()
            if result == "Yes":
                return True
            elif result == "No":
                return False
            else:
                return None
        else:
            from tkinter import messagebox
            return messagebox.askyesnocancel(title, message)
    
    @staticmethod
    def askokcancel(title, message, **kwargs):
        """Ask OK/Cancel question with modern styling"""
        if CTkMessagebox:
            msg = CTkMessagebox(
                title=title,
                message=message,
                icon="question",
                option_1="Cancel",
                option_2="OK",
                **kwargs
            )
            return msg.get() == "OK"
        else:
            from tkinter import messagebox
            return messagebox.askokcancel(title, message)

# Create a shorthand alias
messagebox = ModernMessageBox

# =============================================================================
# UI CONFIGURATION SECTION - Customize the user interface appearance and behavior
# =============================================================================

# ------------------------------------------------------------------------------
# WINDOW AND DISPLAY SETTINGS
# Adjust window sizing and display parameters
# ------------------------------------------------------------------------------
WINDOW_SCALE = 0.65              # Fraction of screen size for window (further reduced for smaller containers)
MIN_WINDOW_WIDTH = 800            # Minimum window width in pixels
MIN_WINDOW_HEIGHT = 600           # Minimum window height in pixels
ENABLE_FULLSCREEN_STARTUP = True # Automatically start in fullscreen mode (for kiosks/RPi)

# ------------------------------------------------------------------------------
# FONT SETTINGS
# Customize text appearance throughout the application
# ------------------------------------------------------------------------------
PRIMARY_FONT_FAMILY = "Helvetica"  # Primary font family for UI elements
BUTTON_FONT_FAMILY = "Helvetica"   # Font family for buttons
MONOSPACE_FONT_FAMILY = "Courier"  # Font family for code/logs

FONT_SIZE_DIVISOR = 60            # Divisor for responsive font sizing (changed from 80 for larger fonts)
FONT_SIZE_BASE_MIN = 10            # Minimum base font size (changed from 8)
FONT_SIZE_BASE_MAX = 16            # Maximum base font size (changed from 12)

# ------------------------------------------------------------------------------
# COLOR THEME SETTINGS - DARK MODE (CustomTkinter)
# Customize the color scheme of the application
# ------------------------------------------------------------------------------
# Main application colors
BACKGROUND_COLOR = "#1a1a1a"       # Dark background (inverted from #f0f0f0)
FRAME_BACKGROUND_COLOR = "#2d2d2d" # Dark frame background (inverted from #ffffff)
TEXT_COLOR = "#e0e0e0"            # Light text (inverted from #000000)
SECONDARY_TEXT_COLOR = "#999999"  # Light secondary text (inverted from #666666)

# Button colors
BUTTON_BACKGROUND_COLOR = "#3d3d3d"  # Dark button (inverted from #e0e0e0)
BUTTON_ACTIVE_COLOR = "#4d4d4d"      # Slightly lighter on press (inverted from #d0d0d0)
BUTTON_TEXT_COLOR = "#e0e0e0"        # Light button text (inverted from #000000)

# Status and grade colors
STATUS_READY_COLOR = "#28a745"      # Green for ready/active status
STATUS_WARNING_COLOR = "#ffc107"    # Yellow for warning status
STATUS_ERROR_COLOR = "#dc3545"      # Red for error status

GRADE_PERFECT_COLOR = "#32CD32"     # Bright green for perfect grade
GRADE_GOOD_COLOR = "#90EE90"        # Light green for good grade
GRADE_FAIR_COLOR = "#FFB347"        # Light orange for fair grade
GRADE_POOR_COLOR = "#FF6B6B"        # Light red for poor grade

# Detection overlay colors
DETECTION_BOX_COLOR = "#00FF00"     # Green for detection bounding boxes
ROI_OVERLAY_COLOR = "#FFFF00"       # Yellow for ROI overlay

# ------------------------------------------------------------------------------
# LAYOUT AND SPACING SETTINGS
# Adjust spacing, padding, and layout proportions
# ------------------------------------------------------------------------------
# Padding and margins (in pixels)
MAIN_PADDING = 5                   # Main window padding
FRAME_PADDING = 2                   # Frame/panel padding
CAMERA_FRAME_PADDING = 1            # Camera feed LabelFrame padding
ELEMENT_PADDING_X = 2              # Horizontal padding between elements
ELEMENT_PADDING_Y = 2              # Vertical padding between elements
LABEL_PADDING = 5                  # Label padding

# Grid layout weights (proportions)
CAMERA_FEEDS_WEIGHT = 0            # Weight for camera feeds section (relative to controls and stats)
CONTROLS_WEIGHT = 0                # Weight for controls section (compact)
STATS_WEIGHT = 1                   # Weight for statistics section
CAMERA_FEED_HEIGHT_WEIGHT = 0      # Weight for camera feeds row height (minimized for compact layout)

# Camera display settings
CAMERA_ASPECT_RATIO = "16:9"       # Target aspect ratio for camera displays
CAMERA_DISPLAY_MARGIN = -35          # Margin around camera displays (pixels)
CAMERA_FEED_MARGIN = 0             # White margin between and around camera feeds (pixels)

# ------------------------------------------------------------------------------
# UI BEHAVIOR SETTINGS
# Control interactive behavior and responsiveness
# ------------------------------------------------------------------------------
ENABLE_TOOLTIPS = True             # Show tooltips on hover
ENABLE_ANIMATIONS = False          # Enable UI animations (may impact performance)
AUTO_SCROLL_LOGS = True            # Automatically scroll logs to bottom
SCROLL_SENSITIVITY = 3             # Mouse wheel scroll sensitivity (lines per scroll)

# Update intervals (frames to skip between updates)
UI_UPDATE_SKIP = 3                 # Update UI elements every Nth frame
STATS_UPDATE_SKIP = 15             # Update statistics every Nth frame
LOG_UPDATE_SKIP = 10               # Update logs when no detection every Nth frame

# ------------------------------------------------------------------------------
# ADVANCED UI SETTINGS
# Fine-tune specific UI components
# ------------------------------------------------------------------------------
# Tabbed interface settings
STATS_TAB_HEIGHT = 500             # Minimum height for statistics tabs (increased from 200 to 500 for kiosk)
LOG_SCROLLABLE_HEIGHT = 200        # Height of scrollable log area (pixels)

# Status bar settings
STATUS_BAR_HEIGHT = 25             # Height of status bar (pixels)
STATUS_UPDATE_INTERVAL = 100       # Status update interval (milliseconds)

# Detection display settings
DETECTION_DETAILS_HEIGHT = 150     # Height of detection details panels (pixels)
MAX_DETECTION_ENTRIES = 50         # Maximum number of detection entries to keep in memory

# ------------------------------------------------------------------------------
# REGION OF INTEREST (ROI) SETTINGS
# Define areas to focus detection on (crop out irrelevant areas)
# Coordinates are in pixels: (x1, y1) to (x2, y2)
# ------------------------------------------------------------------------------
ROI_COORDINATES = {
    "top": {
        "x1": 345,  # Left boundary - exclude left equipment
        "y1": 0,   # Top boundary - exclude top area
        "x2": 880, # Right boundary - exclude right equipment
        "y2": 720   # Bottom boundary - focus on wood area
    },
    "bottom": {
        "x1": 350,    # Left boundary for bottom camera
        "y1": 0,      # Top boundary
        "x2": 965,   # Right boundary
        "y2": 720     # Bottom boundary
    },
    "wood_detection": {
        "x1": 100,  # Left boundary for wood detection
        "y1": 0,    # Top boundary
        "x2": 500,  # Right boundary for wood detection
        "y2": 300   # Bottom boundary for wood detection
    },
    "exit_wood": {
        "x1": 1175,  # Left boundary for exit wood ROI
        "y1": 0,    # Top boundary
        "x2": 1250, # Right boundary for exit wood ROI
        "y2": 720   # Bottom boundary for exit wood ROI
    }
}

# ------------------------------------------------------------------------------
# WOOD ALIGNMENT LANE ROIs (Highway Lane Style)
# Define top and bottom "lane" boundaries to detect misaligned wood
# Wood should stay within the center area, not touching these lanes
# ------------------------------------------------------------------------------
ALIGNMENT_LANE_ROIS = {
    "top": {
        "top_lane": {
            "x1": 345,  # Start from left edge of main ROI
            "y1": 0,    # Top edge
            "x2": 880,  # Right edge of main ROI
            "y2": 65    # Reduced from 100 to 65 (-35 pixels) - smaller red zone
        },
        "bottom_lane": {
            "x1": 345,  # Start from left edge of main ROI
            "y1": 655,  # Increased from 620 to 655 (+35 pixels) - smaller red zone
            "x2": 880,  # Right edge of main ROI
            "y2": 720   # Bottom edge
        }
    },
    "bottom": {
        "top_lane": {
            "x1": 350,  # Start from left edge of main ROI
            "y1": 0,    # Top edge
            "x2": 965,  # Right edge of main ROI
            "y2": 40    # Reduced from 75 to 40 (-35 pixels) - smaller red zone
        },
        "bottom_lane": {
            "x1": 350,  # Start from left edge of main ROI
            "y1": 685,  # Increased from 650 to 685 (+35 pixels) - smaller red zone
            "x2": 965,  # Right edge of main ROI
            "y2": 720   # Bottom edge
        }
    }
}

# =============================================================================
# END OF UI CONFIGURATION SECTION
# =============================================================================

class CameraHandler:
    def __init__(self):
        self.top_camera = None
        self.bottom_camera = None
        # Device paths for cameras (Rapoo for top, C922 for bottom)
        self.top_camera_devices = ['/dev/video0','/dev/video1', '/dev/video3']  # Rapoo Camera
        self.bottom_camera_devices = ['/dev/video2', '/dev/video4', '/dev/video5']  # C922 Pro Stream Webcam
        self.top_camera_device = None  # Will be set to successful device path
        self.bottom_camera_device = None  # Will be set to successful device path
        self.top_camera_settings = {
            'brightness': 0,
            'contrast': 32,
            'saturation': 64,
            'hue': 0,
            'exposure': -6,
            'white_balance': 4520,
            'gain': 0
        }
        self.bottom_camera_settings = {
            'brightness': 110,
            'contrast': 125,
            'saturation': 125,
            'hue': 0,
            'exposure': -6,
            'white_balance': 4850,
            'gain': 0,
            'backlight_compensation': 1
        }

    def _get_camera_device_info(self):
        """Get camera device information using v4l2-ctl to identify cameras by name"""
        try:
            print("🔍 Running v4l2-ctl --list-devices to detect cameras...")
            result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True, timeout=5)

            # Print the raw output for visibility
            print("📋 v4l2-ctl output:")
            print(result.stdout)
            print("📋 End of v4l2-ctl output")

            # Parse output even if returncode != 0, as v4l2-ctl may return 1 but still provide device list
            devices = {}
            lines = result.stdout.strip().split('\n')
            current_device = None

            for line in lines:
                # Check for device paths before stripping (preserve tabs)
                if line.startswith('\t/dev/video'):
                    # This is a device path
                    if current_device:
                        device_path = line.strip()
                        devices[device_path] = current_device
                elif line.strip() and not line.startswith('\t'):
                    # This is a device name (not indented)
                    current_device = line.strip()

            print(f"📊 Parsed {len(devices)} video devices: {list(devices.keys())}")
            return devices
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            print(f"❌ Error getting camera device info: {e}")
            return {}

    def _identify_camera_by_name(self, device_path):
        """Identify camera type by device name"""
        device_info = self._get_camera_device_info()
        device_name = device_info.get(device_path, "").lower()

        if "c922" in device_name or "stream webcam" in device_name:
            return "C922"
        elif "rapoo" in device_name:
            return "Rapoo"
        else:
            return "Unknown"

    def _initialize_camera_with_devices(self, device_list, camera_name):
        """Try to initialize camera using specific device paths"""
        for device_path in device_list:
            try:
                print(f"Trying to open {camera_name} camera at {device_path}...")
                cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
                if cap.isOpened():
                    # Try to read a frame to ensure camera is working
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Disable autofocus for consistent focus
                        try:
                            subprocess.run(['v4l2-ctl', '-d', device_path, '-c', 'focus_automatic_continuous=0'],
                                          capture_output=True, timeout=2)
                            print(f"Disabled autofocus for {device_path}")
                        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                            print(f"Warning: Could not disable autofocus for {device_path}")

                        camera_type = self._identify_camera_by_name(device_path)
                        print(f"Successfully opened {camera_name} camera at {device_path} (Type: {camera_type})")
                        return cap, device_path
                    else:
                        print(f"Camera at {device_path} opened but cannot read frames")
                        cap.release()
                else:
                    print(f"Failed to open camera at {device_path}")
            except Exception as e:
                print(f"Error opening camera at {device_path}: {e}")
                continue
        return None, None

    def initialize_cameras(self):
        try:
            # Try dynamic camera identification first
            success = self._dynamic_reassign_cameras()
            if success:
                print("Cameras initialized successfully using dynamic identification")
                return

            # Fallback to specific device paths
            print("Dynamic identification failed, trying specific device paths...")
            # Initialize top camera (Rapoo)
            self.top_camera, self.top_camera_device = self._initialize_camera_with_devices(
                self.top_camera_devices, "top")
            if self.top_camera is None:
                raise RuntimeError("Could not open top camera (Rapoo) on any device")

            # Initialize bottom camera (C922)
            self.bottom_camera, self.bottom_camera_device = self._initialize_camera_with_devices(
                self.bottom_camera_devices, "bottom")
            if self.bottom_camera is None:
                self.top_camera.release()
                raise RuntimeError("Could not open bottom camera (C922) on any device")

            # Set resolution and apply settings
            self.top_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.top_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.bottom_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.bottom_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            self._apply_camera_settings(self.top_camera, self.top_camera_settings)
            self._apply_camera_settings(self.bottom_camera, self.bottom_camera_settings)

            print("Cameras initialized successfully at 720p (1280x720)")
            print(f"Top camera (Rapoo): {self.top_camera_device}")
            print(f"Bottom camera (C922): {self.bottom_camera_device}")

        except Exception as e:
            self.release_cameras()
            raise RuntimeError(f"Failed to initialize cameras: {str(e)}")

    def _apply_camera_settings(self, camera, settings):
        try:
            camera.set(cv2.CAP_PROP_BRIGHTNESS, settings['brightness'])
            camera.set(cv2.CAP_PROP_CONTRAST, settings['contrast'])
            camera.set(cv2.CAP_PROP_SATURATION, settings['saturation'])
            camera.set(cv2.CAP_PROP_HUE, settings['hue'])
            camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
            camera.set(cv2.CAP_PROP_EXPOSURE, settings['exposure'])
            camera.set(cv2.CAP_PROP_AUTO_WB, 0)
            camera.set(cv2.CAP_PROP_WB_TEMPERATURE, settings['white_balance'])
            camera.set(cv2.CAP_PROP_GAIN, settings['gain'])
            camera.set(cv2.CAP_PROP_SHARPNESS, settings['sharpness'])
            camera.set(cv2.CAP_PROP_BACKLIGHT, settings['backlight_compensation'])
        except Exception as e:
            print(f"Warning: Some camera settings may not be supported: {e}")

    def reconnect_cameras(self):
        """Attempt to reconnect cameras if they become disconnected"""
        print("🔌 Attempting to reconnect cameras...")
        print("   This is called automatically when camera disconnections are detected")

        # Release current cameras
        self.release_cameras()

        try:
            # Try dynamic reassignment first
            success = self._dynamic_reassign_cameras()
            if success:
                print("✅ Dynamic camera reassignment successful")
                
                # Double-check that both cameras are actually working
                camera_status = self.check_camera_status()
                if camera_status['both_ok']:
                    print("✅ Verified: Both cameras are working properly")
                    return True
                else:
                    print("❌ Dynamic reassignment reported success but camera status check failed")
                    print(f"   Camera status: Top={camera_status['top_ok']}, Bottom={camera_status['bottom_ok']}")
                    print(f"   Errors: {camera_status['camera_errors']}")
                    # Don't return success if cameras aren't actually working
                    success = False
            
            if not success:
                print("🔄 Dynamic reassignment failed, trying original device paths...")
            if self.top_camera_device:
                print(f"Trying to reconnect top camera at {self.top_camera_device}")
                self.top_camera = cv2.VideoCapture(self.top_camera_device, cv2.CAP_V4L2)
                if self.top_camera.isOpened():
                    ret, _ = self.top_camera.read()
                    if ret:
                        print(f"✅ Reconnected top camera at {self.top_camera_device}")
                    else:
                        self.top_camera.release()
                        self.top_camera = None

            if self.bottom_camera_device:
                print(f"Trying to reconnect bottom camera at {self.bottom_camera_device}")
                self.bottom_camera = cv2.VideoCapture(self.bottom_camera_device, cv2.CAP_V4L2)
                if self.bottom_camera.isOpened():
                    ret, _ = self.bottom_camera.read()
                    if ret:
                        print(f"✅ Reconnected bottom camera at {self.bottom_camera_device}")
                    else:
                        self.bottom_camera.release()
                        self.bottom_camera = None

            # Apply settings if cameras are connected
            if self.top_camera:
                self.top_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.top_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self._apply_camera_settings(self.top_camera, self.top_camera_settings)

            if self.bottom_camera:
                self.bottom_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.bottom_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self._apply_camera_settings(self.bottom_camera, self.bottom_camera_settings)

            # Check final success
            if self.top_camera and self.bottom_camera:
                print("✅ Camera reconnection successful")
                print(f"   Top camera: {self.top_camera_device}")
                print(f"   Bottom camera: {self.bottom_camera_device}")
                return True
            else:
                print("❌ Camera reconnection failed - not all cameras reconnected")
                missing_cameras = []
                if not self.top_camera:
                    missing_cameras.append("top")
                if not self.bottom_camera:
                    missing_cameras.append("bottom")
                print(f"   Missing cameras: {', '.join(missing_cameras)}")
                return False

        except Exception as e:
            print(f"Camera reconnection failed: {e}")
            return False

    def _dynamic_reassign_cameras(self):
        """Dynamically scan and reassign cameras based on device identification"""
        print("🔄 Performing dynamic camera reassignment...")
        print("   This happens at startup and whenever camera disconnections are detected")

        # Release any existing cameras first
        self.release_cameras()

        # Get all available video devices
        device_info = self._get_camera_device_info()
        available_devices = list(device_info.keys())

        if len(available_devices) < 2:
            print(f"❌ Only {len(available_devices)} devices available, need at least 2")
            return False

        # Identify camera types
        c922_devices = []
        rapoo_devices = []

        for device_path in available_devices:
            camera_type = self._identify_camera_by_name(device_path)
            if camera_type == "C922":
                c922_devices.append(device_path)
            elif camera_type == "Rapoo":
                rapoo_devices.append(device_path)

        print(f"📷 Found C922 devices: {c922_devices}")
        print(f"📷 Found Rapoo devices: {rapoo_devices}")

        # Assign cameras based on identification
        top_device = None
        bottom_device = None

        # Rapoo for top
        if rapoo_devices:
            for device in rapoo_devices:
                try:
                    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        if ret:
                            top_device = device
                            cap.release()
                            break
                        cap.release()
                except:
                    continue

        # C922 for bottom
        if c922_devices:
            for device in c922_devices:
                try:
                    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
                    if cap.isOpened():
                        ret, _ = cap.read()
                        if ret:
                            bottom_device = device
                            cap.release()
                            break
                        cap.release()
                except:
                    continue

        if top_device and bottom_device:
            # Successfully identified both devices, now test if they actually work
            self.top_camera = cv2.VideoCapture(top_device, cv2.CAP_V4L2)
            self.bottom_camera = cv2.VideoCapture(bottom_device, cv2.CAP_V4L2)
            
            # Verify both cameras can actually read frames
            top_working = False
            bottom_working = False
            
            if self.top_camera and self.top_camera.isOpened():
                ret, _ = self.top_camera.read()
                top_working = ret
                
            if self.bottom_camera and self.bottom_camera.isOpened():
                ret, _ = self.bottom_camera.read()
                bottom_working = ret
            
            # Only proceed if BOTH cameras are actually working
            if top_working and bottom_working:
                self.top_camera_device = top_device
                self.bottom_camera_device = bottom_device

                # Disable autofocus for reconnected cameras
                for device in [top_device, bottom_device]:
                    try:
                        subprocess.run(['v4l2-ctl', '-d', device, '-c', 'focus_automatic_continuous=0'],
                                      capture_output=True, timeout=2)
                        print(f"Disabled autofocus for reconnected {device}")
                    except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                        print(f"Warning: Could not disable autofocus for reconnected {device}")

                # Apply settings
                self.top_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.top_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self._apply_camera_settings(self.top_camera, self.top_camera_settings)

                self.bottom_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.bottom_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self._apply_camera_settings(self.bottom_camera, self.bottom_camera_settings)

                print("Dynamic camera reassignment successful!")
                print(f"Top camera (Rapoo): {top_device}")
                print(f"Bottom camera (C922): {bottom_device}")
                return True
            else:
                # Release cameras that aren't working properly
                if not top_working:
                    print(f"❌ Top camera at {top_device} not working properly")
                    if self.top_camera:
                        self.top_camera.release()
                        self.top_camera = None
                if not bottom_working:
                    print(f"❌ Bottom camera at {bottom_device} not working properly")
                    if self.bottom_camera:
                        self.bottom_camera.release()
                        self.bottom_camera = None
                
                print("Dynamic reassignment failed - cameras found but not working properly")
                return False
        else:
            print("Dynamic reassignment failed - could not identify both camera types")
            return False

    def check_camera_status(self):
        """Check if cameras are still connected and working"""
        try:
            top_ok = False
            bottom_ok = False
            camera_errors = []

            if self.top_camera and self.top_camera.isOpened():
                # Try to read a frame multiple times to account for temporary failures
                for attempt in range(5):  # Increased from 3 to 5 retries
                    ret, _ = self.top_camera.read()
                    if ret:
                        top_ok = True
                        break
                    else:
                        time.sleep(0.2)  # Increased delay between retries
                if not top_ok:
                    print("⚠️ Top camera is not responding after retries")
                    camera_errors.append("top camera not responding")
            else:
                print("⚠️ Top camera is not opened")
                camera_errors.append("top camera not opened")

            if not top_ok:
                print("🔌 Top camera disconnection detected")

            if self.bottom_camera and self.bottom_camera.isOpened():
                # Try to read a frame multiple times to account for temporary failures
                for attempt in range(5):  # Increased from 3 to 5 retries
                    ret, _ = self.bottom_camera.read()
                    if ret:
                        bottom_ok = True
                        break
                    else:
                        time.sleep(0.2)  # Increased delay between retries
                if not bottom_ok:
                    print("⚠️ Bottom camera is not responding after retries")
                    camera_errors.append("bottom camera not responding")
            else:
                print("⚠️ Bottom camera is not opened")
                camera_errors.append("bottom camera not opened")

            if not bottom_ok:
                print("🔌 Bottom camera disconnection detected")

            # Return status and error details for the App class to handle
            return {
                'top_ok': top_ok,
                'bottom_ok': bottom_ok,
                'camera_errors': camera_errors,
                'both_ok': top_ok and bottom_ok
            }

        except Exception as e:
            print(f"❌ Error checking camera status: {e}")
            return {
                'top_ok': False,
                'bottom_ok': False,
                'camera_errors': [f"Camera status check failed: {str(e)}"],
                'both_ok': False
            }

    def reassign_cameras_runtime(self):
        """Runtime method to dynamically reassign cameras - can be called from UI or automatically"""
        print("Runtime camera reassignment requested...")
        success = self._dynamic_reassign_cameras()
        if success:
            print("Runtime camera reassignment successful")
            # Update any UI elements if needed
            if hasattr(self, 'status_label'):
                # status_label is a Text widget, not a Label widget
                self.status_label.config(state=tk.NORMAL)
                self.status_label.delete(1.0, tk.END)
                self.status_label.insert(1.0, "Status: Cameras reassigned successfully")
                self.status_label.config(foreground="green", state=tk.DISABLED)
        else:
            print("Runtime camera reassignment failed")
            if hasattr(self, 'status_label'):
                # status_label is a Text widget, not a Label widget
                self.status_label.config(state=tk.NORMAL)
                self.status_label.delete(1.0, tk.END)
                self.status_label.insert(1.0, "Status: Camera reassignment failed")
                self.status_label.config(foreground="red", state=tk.DISABLED)
        return success

    def reassign_arduino_runtime(self):
        """Runtime method to dynamically reassign Arduino port - can be called from UI or automatically"""
        print("Runtime Arduino reassignment requested...")
        try:
            # Close current connection
            if hasattr(self, 'ser') and self.ser:
                self.ser.close()
                self.ser = None

            # Try to setup again
            self.setup_arduino()
            if self.ser and self.ser.is_open:
                print("Runtime Arduino reassignment successful")
                if hasattr(self, 'status_label'):
                    # status_label is a Text widget, not a Label widget
                    self.status_label.config(state=tk.NORMAL)
                    self.status_label.delete(1.0, tk.END)
                    self.status_label.insert(1.0, "Status: Arduino reassigned successfully")
                    self.status_label.config(foreground="green", state=tk.DISABLED)
                return True
            else:
                print("Runtime Arduino reassignment failed")
                if hasattr(self, 'status_label'):
                    # status_label is a Text widget, not a Label widget
                    self.status_label.config(state=tk.NORMAL)
                    self.status_label.delete(1.0, tk.END)
                    self.status_label.insert(1.0, "Status: Arduino reassignment failed")
                    self.status_label.config(foreground="red", state=tk.DISABLED)
                return False
        except Exception as e:
            print(f"Error during runtime Arduino reassignment: {e}")
            if hasattr(self, 'status_label'):
                # status_label is a Text widget, not a Label widget
                self.status_label.config(state=tk.NORMAL)
                self.status_label.delete(1.0, tk.END)
                self.status_label.insert(1.0, "Status: Arduino reassignment error")
                self.status_label.config(foreground="red", state=tk.DISABLED)
            return False

    def release_cameras(self):
        if self.top_camera:
            try:
                self.top_camera.release()
            except Exception as e:
                print(f"Error releasing top camera: {e}")
            self.top_camera = None
        if self.bottom_camera:
            try:
                self.bottom_camera.release()
            except Exception as e:
                print(f"Error releasing bottom camera: {e}")
            self.bottom_camera = None
        print("Cameras released")

# SS-EN 1611-1 Grading Standards Implementation (Revised)
# Grade constants - Individual grades
GRADE_G2_0 = "G2-0"
GRADE_G2_1 = "G2-1"
GRADE_G2_2 = "G2-2"
GRADE_G2_3 = "G2-3"
GRADE_G2_4 = "G2-4"

class SSEN1611_1_PineGrader_Final:
    """
    Implements the appearance grading logic for PINE timber.

    This version excludes:
    1. Spike/Splay Knot checks.
    2. Encased Knot checks (Treated as NOT PERMITTED for all grades).

    The final grade is determined by the worst (lowest) quality face.
    """

    # G2-0 is the highest quality (best), G2-4 is the lowest (worst)
    GRADES = ["G2-0", "G2-1", "G2-2", "G2-3", "G2-4"]

    # ONLY these three types of knots are considered for size/number
    KNOT_TYPES = ["Sound Knots", "Dead Knots", "Unsound/Missing Knots"]

    # --- KNOT SIZE LIMITS (A) ---
    # Formula: max_size = (percent_width * wood_width_mm) + constant_mm + size_increase_mm
    # The order of the tuples must match the order of KNOT_TYPES.
    # (Sound Knots, Dead Knots, Unsound/Missing Knots)
    KNOT_SIZE_LIMITS = {
        # Unsound/Missing NOT PERMITTED (0.00, 0) in G2-0/G2-1
        "G2-0": [(0.10, 10), (0.10, 0), (0.00, 0)],      # Sound: 10%W+10, Dead: 10%W+0, Unsound: NOT PERMITTED
        "G2-1": [(0.10, 20), (0.10, 10), (0.00, 0)],     # Sound: 10%W+20, Dead: 10%W+10, Unsound: NOT PERMITTED
        "G2-2": [(0.10, 35), (0.10, 20), (0.10, 15)],    # Sound: 10%W+35, Dead: 10%W+20, Unsound: 10%W+15
        "G2-3": [(0.10, 50), (0.10, 50), (0.10, 40)],    # Sound: 10%W+50, Dead: 10%W+50, Unsound: 10%W+40
        "G2-4": [(1.00, 0), (1.00, 0), (1.00, 0)]        # All unlimited (formula allows any size)
    }

    # --- KNOT FREQUENCY LIMITS (C) ---
    # Limits are tuples: (Max Total Knots/m, Max Poor-Quality Knots/m)
    # Poor-Quality Knots are now ONLY Unsound/Missing.
    KNOT_NUMBER_LIMITS = {
        "G2-0": (2, 0), # Max 2 Total, 0 Unsound/Missing
        "G2-1": (4, 0), # Max 4 Total, 0 Unsound/Missing
        "G2-2": (6, 2), # Max 6 Total, 2 Unsound/Missing
        "G2-3": (float('inf'), 5), # Unlimited Total, 5 Unsound/Missing max
        "G2-4": (float('inf'), float('inf')) # Unlimited both
    }

    def __init__(self, width_mm):
        self.original_width = width_mm

        # PINE Note B: Size Increase for pieces >= 180 mm wide.
        self.size_increase_mm = 0
        if width_mm >= 180:
            self.size_increase_mm = 10

    def get_max_allowed_size(self, grade, knot_type):
        """Calculates the maximum allowed size for a specific knot type and grade."""
        grade_limits = self.KNOT_SIZE_LIMITS[grade]

        try:
            knot_index = self.KNOT_TYPES.index(knot_type)
        except ValueError:
            # If the user tries to check for an excluded knot type (like "Encased Knots")
            return 0

        percent_limit, absolute_limit = grade_limits[knot_index]
        max_size = (percent_limit * self.original_width) + absolute_limit + self.size_increase_mm

        # For Unsound/Missing in G2-0 and G2-1, the limit is strictly 0.
        if percent_limit == 0.00 and absolute_limit == 0:
             return 0

        return round(max_size)

    def _check_size_compliance(self, knot_data_size):
        """Internal function to check size compliance for a single face."""
        passed_grades = []
        for grade in self.GRADES:
            grade_passed = True
            for knot_type, max_size_found in knot_data_size.items():

                # IMPORTANT: Skip any knot type that is not used in this grading scheme
                if knot_type not in self.KNOT_TYPES:
                    continue

                allowed_size = self.get_max_allowed_size(grade, knot_type)

                if allowed_size == 0 and max_size_found > 0:
                    # Fails due to NOT PERMITTED (Unsound/Missing in G2-0/G2-1, or if a zero size Encased was passed)
                    grade_passed = False
                    break
                elif max_size_found > allowed_size:
                    grade_passed = False
                    break

            if grade_passed:
                passed_grades.append(grade)
        return passed_grades

    def _check_number_compliance(self, knot_data_number):
        """Internal function to check number compliance for a single face."""
        passed_grades = []

        # Note C: Knot Total Number Increase for pieces > 225 mm wide.
        number_increase_factor = 1.0
        if self.original_width > 225:
            number_increase_factor = 1.5

        total_knots_found = knot_data_number.get('total', 0)
        poor_quality_knots_found = knot_data_number.get('unsound_only', 0) # Only counting Unsound/Missing now

        for grade in self.GRADES:
            total_limit, poor_limit = self.KNOT_NUMBER_LIMITS[grade]
            grade_passed = True

            # 1. Check Total Number Limit
            if total_limit == float('inf'):
                adjusted_total_limit = float('inf')  # Keep as infinity
            else:
                adjusted_total_limit = int(total_limit * number_increase_factor)
            
            if total_knots_found > adjusted_total_limit:
                grade_passed = False

            # 2. Check Poor-Quality Knots Limit (ONLY Unsound/Missing)
            if grade_passed:
                if poor_quality_knots_found > poor_limit:
                    grade_passed = False

            if grade_passed:
                passed_grades.append(grade)

        return passed_grades

    def _determine_single_face_grade(self, knot_data_size, knot_data_number):
        """Determines the single highest grade achieved by one face."""
        size_passed = self._check_size_compliance(knot_data_size)
        number_passed = self._check_number_compliance(knot_data_number)

        final_grades_passed = [g for g in self.GRADES if g in size_passed and g in number_passed]

        if not final_grades_passed:
            return "Fails G2-4"

        return final_grades_passed[0]

    def determine_final_grade_dual_face(self, top_face_data, bottom_face_data):
        """
        Determines the final grade by finding the worst grade between the two faces.
        :param top_face_data: Dict with keys 'size' and 'number' for the top face.
        :param bottom_face_data: Dict with keys 'size' and 'number' for the bottom face.
        :return: The lowest (worst) grade achieved by either face.
        """
        top_grade = self._determine_single_face_grade(
            top_face_data['size'],
            top_face_data['number']
        )
        bottom_grade = self._determine_single_face_grade(
            bottom_face_data['size'],
            bottom_face_data['number']
        )

        if top_grade == "Fails G2-4" or bottom_grade == "Fails G2-4":
            return "Fails G2-4 (One face failed integrity check)"

        # Get the index of the grade (higher index = worse grade)
        top_index = self.GRADES.index(top_grade)
        bottom_index = self.GRADES.index(bottom_grade)

        # The worst grade is the one with the higher index
        worst_index = max(top_index, bottom_index)

        return self.GRADES[worst_index]

    def convert_measurements_to_knot_data(self, measurements):
        """Convert defect measurements to knot data format expected by PineGrader."""
        knot_data_size = {}
        knot_data_number = {'total': 0, 'unsound_only': 0}

        # Initialize all knot types with 0
        for knot_type in self.KNOT_TYPES:
            knot_data_size[knot_type] = 0

        # Process measurements
        for defect_type, size_mm, percentage in measurements:
            # Map defect types to knot types
            if defect_type in ['Sound_Knot', 'Sound Knot', 'live_knot', 'live knot']:
                knot_type = 'Sound Knots'
            elif defect_type in ['Dead_Knot', 'Dead Knot', 'dead_knot', 'dead knot']:
                knot_type = 'Dead Knots'
            elif defect_type in ['Unsound_Knot', 'Unsound Knot', 'unsound_knot', 'unsound knot',
                                'Crack_Knot', 'Knot with Crack', 'crack_knot', 'knot with crack',
                                'Missing_Knot', 'Missing Knot', 'missing_knot', 'missing knot']:
                knot_type = 'Unsound/Missing Knots'
            else:
                # Default to Unsound for unknown types
                knot_type = 'Unsound/Missing Knots'

            # Update max size for this knot type
            if knot_type in knot_data_size:
                knot_data_size[knot_type] = max(knot_data_size[knot_type], size_mm)

            # Count total knots
            knot_data_number['total'] += 1

            # Count unsound knots
            if knot_type == 'Unsound/Missing Knots':
                knot_data_number['unsound_only'] += 1

        return knot_data_size, knot_data_number

    def determine_surface_grade(self, measurements):
        """Determine grade for a single surface using SS-EN 1611-1 PineGrader."""
        if not measurements:
            return "G2-0"  # Best grade if no defects

        # Convert measurements to knot data format
        knot_data_size, knot_data_number = self.convert_measurements_to_knot_data(measurements)

        # Get grade from PineGrader
        grade = self._determine_single_face_grade(knot_data_size, knot_data_number)

        # Handle "Fails G2-4" case
        if grade == "Fails G2-4":
            return "G2-4"

        return grade

    def determine_final_grade(self, top_measurements, bottom_measurements):
        """Determine final grade using dual-face grading with SS-EN 1611-1 PineGrader."""
        # Convert measurements to knot data format
        top_knot_data_size, top_knot_data_number = self.convert_measurements_to_knot_data(top_measurements)
        bottom_knot_data_size, bottom_knot_data_number = self.convert_measurements_to_knot_data(bottom_measurements)

        # Get final grade from dual-face grading
        final_grade = self.determine_final_grade_dual_face(
            {'size': top_knot_data_size, 'number': top_knot_data_number},
            {'size': bottom_knot_data_size, 'number': bottom_knot_data_number}
        )

        # Handle "Fails G2-4" case
        if "Fails G2-4" in final_grade:
            return "G2-4"

        return final_grade

# Camera-specific calibration based on your setup
# Top camera: 37cm distance, Bottom camera: 29cm distance
# Assuming 1280x720 resolution with typical camera FOV
TOP_CAMERA_DISTANCE_CM = 28
BOTTOM_CAMERA_DISTANCE_CM = 27.5

# Actual pixel-to-millimeter factors (measured)
TOP_CAMERA_PIXEL_TO_MM = 2.96  # Top camera: 2.96 pixels per mm
BOTTOM_CAMERA_PIXEL_TO_MM = 3.5  # Bottom camera: 3.5 pixels per mm

# Dynamic wood pallet width storage - single variable for current wood piece
WOOD_PALLET_WIDTH_MM = 0  # Global variable for current detected wood width

# SS-EN 1611-1 Grading constants for size limits: limit = (0.10 * wood_width) + constant
# SS-EN 1611-1 Official Grading Constants (Constants for formula: 10% W + constant)
GRADING_CONSTANTS = {
    "Sound_Knot": {"G2-0": 10, "G2-1": 20, "G2-2": 35, "G2-3": 50},
    "Dead_Knot": {"G2-0": 0, "G2-1": 10, "G2-2": 20, "G2-3": 50},
    "Unsound_Knot": {"G2-2": 15, "G2-3": 40},  # Not permitted in G2-0, G2-1
    "Missing_Knot": {"G2-2": 15, "G2-3": 40},  # Same as Unsound_Knot
    "Crack_Knot": {"G2-2": 15, "G2-3": 40}  # Same as Unsound_Knot for "Knot with Crack"
}

# SS-EN 1611-1 Knot Frequency Limits (Total Knots per meter, Unsound Knots per meter)
KNOT_FREQUENCY_LIMITS = {
    "G2-0": {"total_per_meter": 2, "unsound_per_meter": 0},
    "G2-1": {"total_per_meter": 4, "unsound_per_meter": 0},
    "G2-2": {"total_per_meter": 6, "unsound_per_meter": 2},
    "G2-3": {"total_per_meter": float('inf'), "unsound_per_meter": 5},
    "G2-4": {"total_per_meter": float('inf'), "unsound_per_meter": float('inf')}
}

# Legacy compatibility - DEPRECATED: Use KNOT_FREQUENCY_LIMITS instead
KNOT_COUNT_LIMITS = {
    "G2-0": 0,  # Legacy - refers to unsound knots only
    "G2-1": 0,  # Legacy - refers to unsound knots only  
    "G2-2": 2,  # Legacy - refers to unsound knots only
    "G2-3": 5,  # Legacy - refers to unsound knots only
    "G2-4": float('inf')
}




class DetectionDeduplicator:
    """Deduplicates detections based on spatial and temporal proximity for low FPS scenarios"""

    def __init__(self, spatial_threshold_mm=10.0, temporal_threshold_sec=0.5):
        self.spatial_threshold_mm = spatial_threshold_mm  # Max distance to consider same defect
        self.temporal_threshold_sec = temporal_threshold_sec  # Max time gap to group detections

    def deduplicate(self, detections):
        """
        Group detections by spatial-temporal proximity and return best detection from each group
        detections: list of detection dicts with keys: timestamp, defect_type, size_mm, percentage
        """
        if not detections:
            return []

        # Sort detections by timestamp
        sorted_detections = sorted(detections, key=lambda x: x['timestamp'])

        # Group detections into clusters
        clusters = []
        current_cluster = [sorted_detections[0]]

        for detection in sorted_detections[1:]:
            # Check if this detection belongs to the current cluster
            if self._should_merge_with_cluster(detection, current_cluster):
                current_cluster.append(detection)
            else:
                # Start new cluster
                clusters.append(current_cluster)
                current_cluster = [detection]

        # Don't forget the last cluster
        if current_cluster:
            clusters.append(current_cluster)

        # For each cluster, select the best detection
        deduplicated = []
        for cluster in clusters:
            best_detection = self._select_best_detection(cluster)
            deduplicated.append(best_detection)

        return deduplicated

    def _should_merge_with_cluster(self, detection, cluster):
        """Check if detection should be merged with existing cluster"""
        # Check temporal proximity with the most recent detection in cluster
        last_detection = cluster[-1]
        time_diff = abs(self._timestamp_to_seconds(detection['timestamp']) -
                       self._timestamp_to_seconds(last_detection['timestamp']))

        if time_diff > self.temporal_threshold_sec:
            return False

        # Check spatial proximity with all detections in cluster
        for cluster_detection in cluster:
            # Must be same defect type AND similar size to be considered the same defect
            if (detection['defect_type'] == cluster_detection['defect_type'] and
                abs(detection['size_mm'] - cluster_detection['size_mm']) <= self.spatial_threshold_mm):
                
                # Additional check: If we have bbox information, check spatial overlap
                # This prevents deduplicating defects that are just similar in size but spatially separate
                detection_bbox = detection.get('bbox')
                cluster_bbox = cluster_detection.get('bbox')
                
                if detection_bbox and cluster_bbox:
                    # Calculate IoU (Intersection over Union) to check spatial overlap
                    iou = self._calculate_bbox_iou(detection_bbox, cluster_bbox)
                    # Only merge if there's significant spatial overlap (>50%)
                    if iou > 0.5:
                        return True
                else:
                    # If no bbox info, fall back to size-based deduplication (less reliable)
                    return True

        return False

    def _calculate_bbox_iou(self, bbox1, bbox2):
        """Calculate Intersection over Union (IoU) of two bounding boxes"""
        try:
            # Handle different bbox formats
            if len(bbox1) == 4 and len(bbox2) == 4:
                x1_1, y1_1, x2_1, y2_1 = bbox1
                x1_2, y1_2, x2_2, y2_2 = bbox2
                
                # Calculate intersection
                x1_i = max(x1_1, x1_2)
                y1_i = max(y1_1, y1_2)
                x2_i = min(x2_1, x2_2)
                y2_i = min(y2_1, y2_2)
                
                if x2_i <= x1_i or y2_i <= y1_i:
                    return 0.0
                
                intersection = (x2_i - x1_i) * (y2_i - y1_i)
                
                # Calculate areas
                area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
                area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
                union = area1 + area2 - intersection
                
                return intersection / union if union > 0 else 0.0
            else:
                return 0.0
        except Exception:
            return 0.0

    def _select_best_detection(self, cluster):
        """Select the best detection from a cluster (largest size, highest confidence)"""
        if len(cluster) == 1:
            return cluster[0]

        # Select detection with largest size (most conservative for grading)
        best_detection = max(cluster, key=lambda x: x['size_mm'])
        return best_detection

    def _timestamp_to_seconds(self, timestamp_str):
        """Convert ISO timestamp to seconds since epoch"""
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.timestamp()


class ColorWoodDetector:
    def __init__(self, parent_app=None):
        self.parent_app = parent_app  # Reference to main application for accessing GUI variables
        
        self.wood_color_profiles = {
            'top_panel': {
                'rgb_lower': np.array([160, 160, 160]),  # BGR
                'rgb_upper': np.array([225, 220, 210]),
                'name': 'Top Panel Wood'
            },
            'bottom_panel': {
                'rgb_lower': np.array([70, 70, 85]),  # BGR
                'rgb_upper': np.array([225, 220, 210]),
                'name': 'Bottom Panel Wood'
            }
        }
        
        # Detection parameters
        self.min_contour_area = 1000      # Increased for more reliable detection with tighter RGB ranges
        self.max_contour_area = 500000    # Slightly reduced for typical wood plank sizes
        self.min_aspect_ratio = 1.0       # Tightened for more rectangular wood shapes
        self.max_aspect_ratio = 10.0      # Reduced for more typical plank proportions
        self.contour_approximation = 0.025 # Slightly tighter for better shape approximation
        
        # Morphological operations
        self.morph_kernel_size = 11
        self.closing_iterations = 3
        self.opening_iterations = 2

        # Pixel to mm conversion parameters for width measurement
        self.pixel_per_mm_top = 2.96    # Placeholder: calibrate based on top camera distance (31cm)
        self.pixel_per_mm_bottom = 3.5  # Placeholder: calibrate based on bottom camera distance

        # Dynamic wood width storage - matches testIR.py functionality
        self.detected_wood_width_mm = {'top': 0, 'bottom': 0}
        self.wood_detection_results = {'top': None, 'bottom': None}
        self.dynamic_roi = {'top': None, 'bottom': None}

    def calculate_width_mm(self, bbox_pixels: int, camera: str = 'top') -> float:
        """Calculate width in mm from bounding box dimension in pixels using pixel_per_mm factors"""
        if camera == 'top':
            return bbox_pixels / self.pixel_per_mm_top
        elif camera == 'bottom':
            return bbox_pixels / self.pixel_per_mm_bottom
        else:
            raise ValueError("Camera must be 'top' or 'bottom'")
    
    def check_roi_collision(self, roi1_x, roi1_y, roi1_w, roi1_h, roi2_x, roi2_y, roi2_w, roi2_h):
        """
        Check if two rectangular ROIs overlap/collide.
        Returns True if they intersect, False otherwise.
        
        Args:
            roi1_x, roi1_y, roi1_w, roi1_h: First ROI (x, y, width, height)
            roi2_x, roi2_y, roi2_w, roi2_h: Second ROI (x, y, width, height)
        
        Returns:
            bool: True if ROIs overlap, False otherwise
        """
        # Calculate boundaries for both ROIs
        roi1_x2 = roi1_x + roi1_w
        roi1_y2 = roi1_y + roi1_h
        roi2_x2 = roi2_x + roi2_w
        roi2_y2 = roi2_y + roi2_h
        
        # Check if rectangles overlap using standard AABB collision detection
        # Two rectangles overlap if:
        # 1. Left edge of rect1 is to the left of right edge of rect2
        # 2. Right edge of rect1 is to the right of left edge of rect2
        # 3. Top edge of rect1 is above bottom edge of rect2
        # 4. Bottom edge of rect1 is below top edge of rect2
        overlap = (roi1_x < roi2_x2 and 
                  roi1_x2 > roi2_x and 
                  roi1_y < roi2_y2 and 
                  roi1_y2 > roi2_y)
        
        return overlap
    
    def calibrate_pixel_to_mm(self, reference_object_width_px, reference_object_width_mm, camera_name="top"):
        """Calibrate the pixel-to-millimeter conversion factor for specific camera"""
        global TOP_CAMERA_PIXEL_TO_MM, BOTTOM_CAMERA_PIXEL_TO_MM
        
        conversion_factor = reference_object_width_mm / reference_object_width_px
        
        if camera_name == "top":
            TOP_CAMERA_PIXEL_TO_MM = conversion_factor
            self.pixel_per_mm_top = conversion_factor
            print(f"Calibrated TOP camera pixel-to-mm factor: {TOP_CAMERA_PIXEL_TO_MM}")
        else:  # bottom camera
            BOTTOM_CAMERA_PIXEL_TO_MM = conversion_factor
            self.pixel_per_mm_bottom = conversion_factor
            print(f"Calibrated BOTTOM camera pixel-to-mm factor: {BOTTOM_CAMERA_PIXEL_TO_MM}")
        
        return conversion_factor

    def calibrate_with_wood_pallet(self, wood_pallet_width_px_top, wood_pallet_width_px_bottom):
        """Auto-calibrate both cameras using the known wood pallet width"""
        global WOOD_PALLET_WIDTH_MM
        
        print(f"Auto-calibrating cameras with {WOOD_PALLET_WIDTH_MM}mm wood pallet...")

        top_factor = self.calibrate_pixel_to_mm(wood_pallet_width_px_top, WOOD_PALLET_WIDTH_MM, "top")
        bottom_factor = self.calibrate_pixel_to_mm(wood_pallet_width_px_bottom, WOOD_PALLET_WIDTH_MM, "bottom")
        
        print(f"Calibration complete:")
        print(f"  Top camera (28cm): {top_factor:.4f} mm/pixel")
        print(f"  Bottom camera (27.5cm): {bottom_factor:.4f} mm/pixel")
        
        return top_factor, bottom_factor

    def update_wood_width_dynamic(self, camera_name: str, wood_candidates: List[Dict]) -> float:
        """Update global wood width based on detected wood dimensions - BOTTOM camera is authoritative"""
        global WOOD_PALLET_WIDTH_MM
        
        if wood_candidates:
            candidate = wood_candidates[0]  # Use best candidate
            x, y, w, h = candidate['bbox']
            detected_width_mm = self.calculate_width_mm(h, camera_name)  # Use height (cross-section)
            
            # Store the detected width for this camera
            self.detected_wood_width_mm[camera_name] = detected_width_mm
            
            # CRITICAL: Only use BOTTOM CAMERA as the authoritative source for global wood width
            if camera_name == 'bottom':
                # BOTTOM CAMERA: Update global wood width (authoritative source)
                WOOD_PALLET_WIDTH_MM = detected_width_mm
                print(f"🎯 Dynamic wood height updated: {detected_width_mm:.1f}mm (from bbox {w}x{h}px, BOTTOM camera - AUTHORITATIVE)")
                print(f"🔗 Synchronization check: detected_width_mm={detected_width_mm:.1f}mm, WOOD_PALLET_WIDTH_MM={WOOD_PALLET_WIDTH_MM:.1f}mm, self.detected_wood_width_mm[{camera_name}]={self.detected_wood_width_mm[camera_name]:.1f}mm")
                
                # Validation: Ensure all variables are exactly equal to detected_width_mm
                self._validate_wood_width_sync(detected_width_mm, camera_name)
            else:
                # TOP CAMERA: Only store locally, do NOT update global width
                print(f"📐 Top camera wood width detected: {detected_width_mm:.1f}mm (from bbox {w}x{h}px, camera: {camera_name}) - NOT used for global width")
                print(f"🔒 Global WOOD_PALLET_WIDTH_MM remains: {WOOD_PALLET_WIDTH_MM:.1f}mm (controlled by BOTTOM camera only)")
            
            return detected_width_mm
        
        return 0.0

    def _validate_wood_width_sync(self, detected_width_mm: float, camera_name: str):
        """Validate that all wood width variables are synchronized with detected_width_mm (BOTTOM CAMERA ONLY)"""
        global WOOD_PALLET_WIDTH_MM
        
        # Only validate synchronization for bottom camera since it's the authoritative source
        if camera_name != 'bottom':
            return
        
        sync_errors = []
        
        # Check WOOD_PALLET_WIDTH_MM synchronization
        if abs(WOOD_PALLET_WIDTH_MM - detected_width_mm) > 0.001:  # Allow tiny floating point differences
            sync_errors.append(f"WOOD_PALLET_WIDTH_MM={WOOD_PALLET_WIDTH_MM:.3f}mm != detected_width_mm={detected_width_mm:.3f}mm")
            # Force synchronization
            WOOD_PALLET_WIDTH_MM = detected_width_mm
            
        # Check self.detected_wood_width_mm synchronization for bottom camera
        if abs(self.detected_wood_width_mm[camera_name] - detected_width_mm) > 0.001:
            sync_errors.append(f"self.detected_wood_width_mm[{camera_name}]={self.detected_wood_width_mm[camera_name]:.3f}mm != detected_width_mm={detected_width_mm:.3f}mm")
            # Force synchronization
            self.detected_wood_width_mm[camera_name] = detected_width_mm
        
        if sync_errors:
            print(f"⚠️ Wood width synchronization errors detected and corrected:")
            for error in sync_errors:
                print(f"   - {error}")
            print(f"✅ All variables now synchronized to TOP camera detected_width_mm={detected_width_mm:.1f}mm")
        else:
            print(f"✅ Wood width synchronization validated: TOP camera controls all variables = {detected_width_mm:.1f}mm")

    def get_current_wood_width_mm(self) -> float:
        """Get the current authoritative wood width in mm"""
        global WOOD_PALLET_WIDTH_MM
        return WOOD_PALLET_WIDTH_MM

    def get_wood_width_for_grading(self, fallback_mm: float = 100.0) -> float:
        """Get wood width for grading calculations, with fallback if not detected"""
        global WOOD_PALLET_WIDTH_MM
        width = WOOD_PALLET_WIDTH_MM if WOOD_PALLET_WIDTH_MM > 0 else fallback_mm
        print(f"🔗 Wood width for grading: {width:.1f}mm (WOOD_PALLET_WIDTH_MM={WOOD_PALLET_WIDTH_MM:.1f}mm, fallback={fallback_mm:.1f}mm)")
        return width

    def report_wood_width_status(self, context: str = ""):
        """Report current status of all wood width variables - TOP CAMERA AUTHORITY"""
        global WOOD_PALLET_WIDTH_MM
        
        print(f"\n📊 WOOD WIDTH STATUS REPORT {f'({context})' if context else ''}")
        print(f"   🎯 AUTHORITATIVE SOURCE: Global WOOD_PALLET_WIDTH_MM: {WOOD_PALLET_WIDTH_MM:.1f}mm")
        print(f"   📐 Top camera detected: {self.detected_wood_width_mm.get('top', 'N/A')}mm (LOCAL ONLY)")
        print(f"   ✅ Bottom camera detected: {self.detected_wood_width_mm.get('bottom', 'N/A')}mm (CONTROLS GLOBAL)")
        print(f"   🔗 Authority chain: BOTTOM camera detected_width_mm → WOOD_PALLET_WIDTH_MM → all grading calculations")
        print(f"   ⚠️  Top camera measurements are for reference only and DO NOT affect global variables\n")

    def calculate_defect_size(self, detection_box, camera_name="top"):
        """Calculate defect size in mm and percentage from detection bounding box - matches testIR.py"""
        global WOOD_PALLET_WIDTH_MM, TOP_CAMERA_PIXEL_TO_MM, BOTTOM_CAMERA_PIXEL_TO_MM
        
        try:
            # Extract bounding box coordinates
            x1, y1, x2, y2 = detection_box['bbox']

            # Calculate defect dimensions in pixels
            width_px = abs(x2 - x1)   # Horizontal dimension (X-axis)
            height_px = abs(y2 - y1) # Vertical dimension (Y-axis)

            # For wood width measurement, use the vertical dimension (height_px) because camera is in landscape
            # Wood runs vertically in the camera view, so Y-axis represents wood width
            defect_size_px = height_px

            # Use camera-specific conversion factor
            if camera_name == "top":
                pixel_to_mm = TOP_CAMERA_PIXEL_TO_MM
            else:  # bottom camera
                pixel_to_mm = BOTTOM_CAMERA_PIXEL_TO_MM

            # Prevent division by zero
            if pixel_to_mm <= 0:
                pixel_to_mm = 2.96 if camera_name == "top" else 3.5
                print(f"Warning: pixel_to_mm was zero, using default {pixel_to_mm}")

            # Convert to millimeters using division (pixels per mm factor)
            size_mm = defect_size_px / pixel_to_mm

            # Calculate percentage of actual wood pallet width
            if WOOD_PALLET_WIDTH_MM > 0:
                percentage = (size_mm / WOOD_PALLET_WIDTH_MM) * 100
            else:
                percentage = 0.0  # Avoid division by zero

            # Debug logging to understand bounding box sizes
            print(f"DEBUG [{camera_name}]: bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) "
                  f"-> width_px={width_px:.1f}, height_px={height_px:.1f} "
                  f"-> defect_size_px={defect_size_px:.1f} (using Y-axis) -> size_mm={size_mm:.1f}")

            return size_mm, percentage

        except Exception as e:
            print(f"Error calculating defect size: {e}")
            # Return conservative values if calculation fails
            return 50.0, 35.0  # Assumes large defect for safety

    def analyze_image_colors(self, image_path: str) -> Dict:
        """Analyze the color composition of the captured image"""
        print(f"🎨 Analyzing colors in: {image_path}")
        
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Could not load image"}
        
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]

        analysis = {
            "image_size": f"{w}x{h}",
            "wood_profiles_detected": {},
            "dominant_colors": {},
            "recommendations": []
        }

        # Test each wood color profile
        for profile_name, profile in self.wood_color_profiles.items():
            mask = cv2.inRange(rgb, profile['rgb_lower'], profile['rgb_upper'])
            pixels_detected = cv2.countNonZero(mask)
            percentage = (pixels_detected / (h * w)) * 100

            analysis["wood_profiles_detected"][profile_name] = {
                "pixels": pixels_detected,
                "percentage": round(percentage, 2),
                "detected": percentage > 1.0  # Consider detected if >1% of image
            }

            if percentage > 1.0:
                print(f"  ✅ {profile['name']}: {percentage:.1f}% of image")
            else:
                print(f"  ❌ {profile['name']}: {percentage:.1f}% of image")

        # Find dominant colors in RGB
        rgb_flat = rgb.reshape(-1, 3)
        r_values = rgb_flat[:, 0]
        g_values = rgb_flat[:, 1]
        b_values = rgb_flat[:, 2]

        analysis["dominant_colors"] = {
            "red_mean": int(np.mean(r_values)),
            "red_std": int(np.std(r_values)),
            "green_mean": int(np.mean(g_values)),
            "blue_mean": int(np.mean(b_values))
        }
        
        # Generate recommendations
        best_profiles = []
        for name, data in analysis["wood_profiles_detected"].items():
            if data["detected"] and data["percentage"] > 5:
                best_profiles.append((name, data["percentage"]))
        
        if best_profiles:
            best_profiles.sort(key=lambda x: x[1], reverse=True)
            analysis["recommendations"].append(f"Use {best_profiles[0][0]} profile as primary detection method")
        else:
            analysis["recommendations"].append("Consider creating custom color profile for this wood type")
            analysis["recommendations"].append(f"Dominant RGB: R={analysis['dominant_colors']['red_mean']}, G={analysis['dominant_colors']['green_mean']}, B={analysis['dominant_colors']['blue_mean']}")
        
        return analysis
    
    def detect_document_style_edges(self, image: np.ndarray) -> np.ndarray:
        """Detect edges like a document scanner - find rectangular boundaries"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Apply Canny edge detection with wider thresholds for better edge detection
        edges = cv2.Canny(blurred, 75, 200)

        # Dilate edges to make them more visible and connect broken segments
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated_edges = cv2.dilate(edges, kernel, iterations=2)

        # Find contours in the edge image
        contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Create a mask from significant contours (like document scanning)
        edge_mask = np.zeros_like(edges)

        for contour in contours:
            area = cv2.contourArea(contour)
            # Only keep contours that are large enough to be potential wood boundaries
            if area > 1000:  # Minimum area threshold
                # Draw filled contour to create mask
                cv2.drawContours(edge_mask, [contour], -1, 255, thickness=cv2.FILLED)

        # Apply morphological operations to clean up the edge mask
        kernel_clean = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edge_mask = cv2.morphologyEx(edge_mask, cv2.MORPH_CLOSE, kernel_clean, iterations=2)
        edge_mask = cv2.morphologyEx(edge_mask, cv2.MORPH_OPEN, kernel_clean, iterations=1)

        return edge_mask

    def detect_wood_by_color(self, image: np.ndarray, profile_names: List[str] = None) -> Tuple[np.ndarray, List[Dict]]:
        """Detect wood using color-first approach with edge enhancement"""
        try:
            if profile_names is None:
                profile_names = list(self.wood_color_profiles.keys())

            # Validate input image
            if image is None or image.size == 0:
                print("❌ Error: Invalid input image for color detection")
                return np.zeros((100, 100), dtype=np.uint8), []

            # Step 1: Apply histogram equalization on V channel for better lighting compensation
            hsv_temp = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv_temp)
            v = cv2.equalizeHist(v)
            hsv_temp = cv2.merge([h, s, v])
            rgb = cv2.cvtColor(hsv_temp, cv2.COLOR_HSV2BGR)

            combined_mask = np.zeros(rgb.shape[:2], dtype=np.uint8)
            detections = []

            print(f"🎨 Using profiles: {profile_names}")

            # Combine masks from selected profiles
            for profile_name in profile_names:
                if profile_name in self.wood_color_profiles:
                    profile = self.wood_color_profiles[profile_name]
                    mask = cv2.inRange(rgb, profile['rgb_lower'], profile['rgb_upper'])
                    mask_pixels = cv2.countNonZero(mask)
                    total_pixels = rgb.shape[0] * rgb.shape[1]
                    mask_percentage = (mask_pixels / total_pixels) * 100
                    print(f"  📊 {profile_name}: RGB range {profile['rgb_lower']} - {profile['rgb_upper']}, mask {mask_pixels} pixels ({mask_percentage:.1f}%)")
                    combined_mask = cv2.bitwise_or(combined_mask, mask)

            # Step 2: Apply edge detection within the color mask to find wood boundaries
            # Convert color mask to find edges only within wood-colored regions
            color_mask_blurred = cv2.GaussianBlur(combined_mask, (5, 5), 0)
            color_edges = cv2.Canny(color_mask_blurred, 100, 200)

            # Dilate the edges to make them more visible in the mask
            kernel_edge = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            color_edges_dilated = cv2.dilate(color_edges, kernel_edge, iterations=1)

            # Combine the original color mask with edge information
            # This preserves the wood color regions but enhances boundaries
            enhanced_mask = cv2.bitwise_or(combined_mask, color_edges_dilated)

            edge_enhanced_pixels = cv2.countNonZero(enhanced_mask)
            edge_enhanced_percentage = (edge_enhanced_pixels / total_pixels) * 100
            print(f"🎨🔍 Color + Edge enhanced mask: {edge_enhanced_pixels} pixels ({edge_enhanced_percentage:.1f}%)")

            pre_morph_pixels = cv2.countNonZero(enhanced_mask)
            pre_morph_percentage = (pre_morph_pixels / total_pixels) * 100
            print(f"🔧 Pre-morph enhanced mask: {pre_morph_pixels} pixels ({pre_morph_percentage:.1f}%)")

            # Clean up mask with morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_kernel_size, self.morph_kernel_size))
            enhanced_mask = cv2.morphologyEx(enhanced_mask, cv2.MORPH_CLOSE, kernel, iterations=self.closing_iterations)
            enhanced_mask = cv2.dilate(enhanced_mask, kernel, iterations=1)
            enhanced_mask = cv2.morphologyEx(enhanced_mask, cv2.MORPH_OPEN, kernel, iterations=self.opening_iterations)

            post_morph_pixels = cv2.countNonZero(enhanced_mask)
            post_morph_percentage = (post_morph_pixels / total_pixels) * 100
            print(f"🔧 Post-morph enhanced mask: {post_morph_pixels} pixels ({post_morph_percentage:.1f}%)")

            # Additional logging for dominant colors
            rgb_flat = rgb.reshape(-1, 3)
            r_values = rgb_flat[:, 0]
            g_values = rgb_flat[:, 1]
            b_values = rgb_flat[:, 2]
            print(f"🎨 Dominant RGB in image: R={int(np.mean(r_values)):.0f}±{int(np.std(r_values)):.0f}, G={int(np.mean(g_values)):.0f}, B={int(np.mean(b_values)):.0f}")

            return enhanced_mask, detections
            
        except Exception as e:
            print(f"❌ Error in color detection: {e}")
            # Return empty mask and detections on error
            return np.zeros(image.shape[:2], dtype=np.uint8), []

    def update_rgb_ranges_based_on_dominant_colors(self, rgb):
        """Dynamically adjust RGB ranges based on dominant colors in the image"""
        rgb_flat = rgb.reshape(-1, 3)
        r_mean = int(np.mean(rgb_flat[:, 0]))
        g_mean = int(np.mean(rgb_flat[:, 1]))
        b_mean = int(np.mean(rgb_flat[:, 2]))

        # Update profiles based on dominant colors
        self.wood_color_profiles['top_panel']['rgb_lower'] = np.array([max(0, r_mean - 30), max(0, g_mean - 30), max(0, b_mean - 30)])
        self.wood_color_profiles['top_panel']['rgb_upper'] = np.array([min(255, r_mean + 30), min(255, g_mean + 30), min(255, b_mean + 30)])
        self.wood_color_profiles['bottom_panel']['rgb_lower'] = np.array([max(0, r_mean - 30), max(0, g_mean - 30), max(0, b_mean - 30)])
        self.wood_color_profiles['bottom_panel']['rgb_upper'] = np.array([min(255, r_mean + 30), min(255, g_mean + 30), min(255, b_mean + 30)])
        print(f"🔧 Dynamically updated RGB ranges: R=[{r_mean-30}-{r_mean+30}], G=[{g_mean-30}-{g_mean+30}], B=[{b_mean-30}-{b_mean+30}]")
    
    def detect_rectangular_contours(self, mask: np.ndarray, camera: str = 'top') -> List[Dict]:
        """Detect rectangular contours that could be wood planks - focusing on center area"""
        try:
            if mask is None or mask.size == 0:
                print("❌ Error: Invalid mask for contour detection")
                return []
                
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"📐 Found {len(contours)} total contours")

            # Get mask dimensions for center focus
            mask_height, mask_width = mask.shape
            center_x, center_y = mask_width // 2, mask_height // 2
            
            # Define center region (middle 60% of the image)
            center_margin_x = int(mask_width * 0.2)  # 20% margin on each side
            center_margin_y = int(mask_height * 0.2)  # 20% margin on top/bottom
            center_region = {
                'x_min': center_margin_x,
                'x_max': mask_width - center_margin_x,
                'y_min': center_margin_y,
                'y_max': mask_height - center_margin_y
            }
            
            print(f"🎯 Center focus region: x=[{center_region['x_min']}-{center_region['x_max']}], y=[{center_region['y_min']}-{center_region['y_max']}]")

            wood_candidates = []
            rejected_area = 0
            rejected_aspect = 0
            rejected_center = 0

            for i, contour in enumerate(contours):
                try:
                    area = cv2.contourArea(contour)

                    # Filter by area
                    if area < self.min_contour_area or area > self.max_contour_area:
                        rejected_area += 1
                        print(f"  ❌ Contour {i}: area {area:.0f} out of range [{self.min_contour_area}, {self.max_contour_area}]")
                        continue

                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Check if contour center is in the center region
                    contour_center_x = x + w // 2
                    contour_center_y = y + h // 2
                    
                    if not (center_region['x_min'] <= contour_center_x <= center_region['x_max'] and 
                            center_region['y_min'] <= contour_center_y <= center_region['y_max']):
                        rejected_center += 1
                        print(f"  ❌ Contour {i}: center ({contour_center_x}, {contour_center_y}) outside focus region")
                        continue

                    # Filter by minimum size to prevent small detections
                    if camera == 'top':
                        min_height = 266
                        min_width = 100
                    elif camera == 'bottom':
                        min_height = 286
                        min_width = 100
                    else:
                        min_height = 100
                        min_width = 100

                    if h < min_height or w < min_width:
                        rejected_area += 1
                        print(f"  ❌ Contour {i}: size {w}x{h} too small for {camera} camera (min {min_width}x{min_height})")
                        continue

                    aspect_ratio = max(w, h) / min(w, h)

                    # Filter by aspect ratio (wood planks are typically rectangular)
                    if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
                        rejected_aspect += 1
                        print(f"  ❌ Contour {i}: aspect {aspect_ratio:.2f} out of range [{self.min_aspect_ratio}, {self.max_aspect_ratio}]")
                        continue

                    # Approximate contour to polygon
                    epsilon = self.contour_approximation * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)

                    # Calculate additional metrics
                    hull = cv2.convexHull(contour)
                    hull_area = cv2.contourArea(hull)
                    solidity = area / hull_area if hull_area > 0 else 0

                    # Get rotated rectangle for better angle detection
                    rect = cv2.minAreaRect(contour)
                    box = cv2.boxPoints(rect)
                    box = np.intp(box)

                    confidence = self._calculate_wood_confidence(area, aspect_ratio, solidity, len(approx))

                    wood_candidate = {
                        'contour': contour,
                        'approx_points': approx,
                        'bbox': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'solidity': solidity,
                        'vertices': len(approx),
                        'rotated_rect': rect,
                        'corner_points': box,
                        'confidence': confidence
                    }

                    wood_candidates.append(wood_candidate)
                    print(f"  ✅ Contour {i}: area {area:.0f}, aspect {aspect_ratio:.2f}, solidity {solidity:.2f}, confidence {confidence:.2f}")
                        
                except Exception as contour_error:
                    print(f"  ❌ Error processing contour {i}: {contour_error}")
                    continue

            print(f"📊 Contour filtering: {len(contours)} total, {rejected_area} rejected by area, {rejected_aspect} by aspect, {rejected_center} rejected by center, {len(wood_candidates)} candidates")

            # Sort by confidence
            wood_candidates.sort(key=lambda x: x['confidence'], reverse=True)

            return wood_candidates
            
        except Exception as e:
            print(f"❌ Error in rectangular contour detection: {e}")
            return []
    
    def _calculate_wood_confidence(self, area: float, aspect_ratio: float, solidity: float, vertices: int) -> float:
        """Calculate confidence score for wood detection"""
        confidence = 0.0
        
        # Area score (larger is better, up to a point)
        if 10000 <= area <= 100000:
            confidence += 0.3
        elif area > 5000:
            confidence += 0.2
        
        # Aspect ratio score (rectangular is better)
        if 2.0 <= aspect_ratio <= 6.0:
            confidence += 0.3
        elif 1.5 <= aspect_ratio <= 8.0:
            confidence += 0.2
        
        # Solidity score (more solid shapes are better)
        if solidity > 0.7:
            confidence += 0.2
        elif solidity > 0.5:
            confidence += 0.1
        
        # Vertex count score (4-6 vertices for rectangular shapes)
        if vertices == 4:
            confidence += 0.2
        elif 4 <= vertices <= 6:
            confidence += 0.1
        
        return min(confidence, 1.0)

    def _detect_wood_by_texture(self, frame):
        """Detect wood using basic texture analysis"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Calculate texture using standard deviation in local neighborhoods
            kernel_size = 15
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))

            # Calculate local standard deviation (texture measure)
            mean = cv2.blur(blurred.astype(np.float32), (kernel_size, kernel_size))
            sqr_mean = cv2.blur((blurred.astype(np.float32))**2, (kernel_size, kernel_size))
            texture_variance = sqr_mean - mean**2
            texture_std = np.sqrt(np.maximum(texture_variance, 0))

            # Wood typically has moderate texture (not too smooth, not too rough)
            # Calculate confidence based on texture distribution
            texture_mean = np.mean(texture_std)
            texture_confidence = 0.0

            # Optimal texture range for wood (adjust based on testing)
            if 10 < texture_mean < 40:
                texture_confidence = 1.0 - abs(texture_mean - 25) / 15.0

            return max(0.0, min(1.0, texture_confidence))

        except Exception as e:
            print(f"Error in texture-based wood detection: {e}")
            return 0.0

    def _detect_wood_by_shape(self, frame):
        """Detect wood using contour and shape analysis"""
        try:
            # Convert to grayscale and apply edge detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return 0.0

            # Analyze largest contours for rectangular/wood-like shapes
            frame_area = frame.shape[0] * frame.shape[1]
            shape_confidence = 0.0

            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                area = cv2.contourArea(contour)

                # Skip very small contours
                if area < frame_area * 0.05:
                    continue

                # Calculate contour properties
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue

                # Aspect ratio analysis
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h

                # Wood planks typically have certain aspect ratios
                # Adjust these ranges based on your conveyor setup
                if 0.3 < aspect_ratio < 5.0:  # Not too square, not too thin
                    # Calculate rectangularity (how close to rectangle)
                    rect_area = w * h
                    rectangularity = area / rect_area

                    if rectangularity > 0.6:  # Reasonably rectangular
                        shape_confidence = max(shape_confidence, rectangularity)

            return min(1.0, shape_confidence)

        except Exception as e:
            print(f"Error in shape-based wood detection: {e}")
            return 0.0
    
    def generate_auto_roi(self, wood_candidates: List[Dict], image_shape: Tuple) -> Optional[Tuple[int, int, int, int]]:
        """Generate automatic ROI based on detected wood"""
        if not wood_candidates:
            return None
        
        # Use the highest confidence detection
        best_candidate = wood_candidates[0]
        x, y, w, h = best_candidate['bbox']
        
        # Add some padding around the detected wood
        padding_x = int(w * 0.1)  # 10% padding
        padding_y = int(h * 0.1)
        
        roi_x1 = max(0, x - padding_x)
        roi_y1 = max(0, y - padding_y)
        roi_x2 = min(image_shape[1], x + w + padding_x)
        roi_y2 = min(image_shape[0], y + h + padding_y)
        
        return (roi_x1, roi_y1, roi_x2 - roi_x1, roi_y2 - roi_y1)
    
    def detect_wood_comprehensive(self, image: np.ndarray, profile_names: List[str] = None, roi: Tuple[int, int, int, int] = None, camera: str = 'top') -> Dict:
        """Comprehensive wood detection combining color and shape analysis"""
        
        try:
            # Validate input image
            if image is None or image.size == 0:
                print("❌ Error: Invalid input image for comprehensive detection")
                return {
                    'wood_detected': False,
                    'wood_count': 0,
                    'wood_candidates': [],
                    'auto_roi': None,
                    'color_mask': np.zeros((100, 100), dtype=np.uint8),
                    'confidence': 0.0,
                    'texture_confidence': 0.0,
                    'error': 'Invalid input image'
                }

            print(f"🪵 Starting comprehensive wood detection on image shape: {image.shape}")

            # Step 1: Color-based detection with optional ROI
            # Use camera-specific profile if none specified
            if profile_names is None:
                if camera == 'top':
                    profile_names = ['top_panel']
                elif camera == 'bottom':
                    profile_names = ['bottom_panel']
                else:
                    profile_names = list(self.wood_color_profiles.keys())

            if roi is not None:
                x, y, w, h = roi
                cropped = image[y:y+h, x:x+w]
                color_mask_cropped, _ = self.detect_wood_by_color(cropped, profile_names)
                color_mask = np.zeros(image.shape[:2], dtype=np.uint8)
                color_mask[y:y+h, x:x+w] = color_mask_cropped
            else:
                color_mask, _ = self.detect_wood_by_color(image, profile_names)

            mask_pixels = cv2.countNonZero(color_mask)
            total_pixels = image.shape[0] * image.shape[1]
            mask_percentage = (mask_pixels / total_pixels) * 100
            print(f"🎨 Color mask: {mask_pixels} pixels ({mask_percentage:.1f}%)")

            # Step 2: Find rectangular contours
            wood_candidates = self.detect_rectangular_contours(color_mask, camera)
            print(f"📐 Found {len(wood_candidates)} wood candidates after contour filtering")

            # Step 3: Generate automatic ROI
            auto_roi = self.generate_auto_roi(wood_candidates, image.shape)
            if auto_roi:
                print(f"🎯 Auto ROI generated: {auto_roi}")
            else:
                print("❌ No auto ROI generated (no candidates)")

            # Step 4: Integrate texture analysis for enhanced confidence
            texture_confidence = self._detect_wood_by_texture(image)
            combined_confidence = (wood_candidates[0]['confidence'] + texture_confidence) / 2 if wood_candidates else texture_confidence

            # Step 5: Create result
            result = {
                'wood_detected': len(wood_candidates) > 0,
                'wood_count': len(wood_candidates),
                'wood_candidates': wood_candidates,
                'auto_roi': auto_roi,
                'color_mask': color_mask,
                'confidence': combined_confidence,
                'texture_confidence': texture_confidence
            }
            
            # Step 6: Update dynamic wood width if wood is detected (matches testIR.py)
            if result['wood_detected']:
                detected_width = self.update_wood_width_dynamic(camera, wood_candidates)
                result['detected_width_mm'] = detected_width
                
                # Store wood detection results for later use
                self.wood_detection_results[camera] = result
                self.dynamic_roi[camera] = auto_roi
                
                # Step 7: CHECK COLLISION WITH LANE BOUNDARIES
                # This is where we check if wood is misaligned (touching top/bottom lanes)
                if auto_roi and self.parent_app and hasattr(self.parent_app, 'lane_roi_var') and self.parent_app.lane_roi_var.get():
                    roi_x, roi_y, roi_w, roi_h = auto_roi
                    roi_y_bottom = roi_y + roi_h
                    
                    print(f"\n{'='*60}")
                    print(f"[COLLISION CHECK] Checking wood alignment for {camera.upper()} camera")
                    print(f"{'='*60}")
                    print(f"  Wood ROI: x={roi_x}, y={roi_y}, w={roi_w}, h={roi_h}")
                    print(f"  ROI Top Edge: y={roi_y}")
                    print(f"  ROI Bottom Edge: y={roi_y_bottom}")
                    
                    collision_detected = False
                    
                    # Get camera-specific lane boundaries from configuration
                    from testIRCTKv2 import ALIGNMENT_LANE_ROIS
                    camera_lanes = ALIGNMENT_LANE_ROIS.get(camera, {})
                    top_lane_config = camera_lanes.get('top_lane', {})
                    bottom_lane_config = camera_lanes.get('bottom_lane', {})
                    
                    # TOP LANE COLLISION: Use camera-specific boundary
                    top_lane_boundary = top_lane_config.get('y2', 100)  # Default to 100 if not configured
                    top_collision = (roi_y <= top_lane_boundary)
                    print(f"  Top Lane Boundary: y={top_lane_boundary} (camera-specific)")
                    print(f"  TOP COLLISION: {top_collision} (Wood top={roi_y} {'<=' if top_collision else '>'} {top_lane_boundary})")
                    
                    if top_collision:
                        collision_detected = True
                        result['lane_collision'] = 'TOP'
                        print(f"  ⚠️  MISALIGNMENT DETECTED: Wood is TOO HIGH (touching TOP lane)")
                        # Trigger notification
                        print(f"  📞 Checking if parent_app has show_alignment_warning method...")
                        if hasattr(self.parent_app, 'show_alignment_warning'):
                            print(f"  📞 Calling parent_app.show_alignment_warning('{camera}', 'TOP')...")
                            self.parent_app.show_alignment_warning(camera, "TOP")
                            print(f"  📞 show_alignment_warning() call completed")
                        else:
                            print(f"  ❌ parent_app does NOT have show_alignment_warning method!")

                    
                    # BOTTOM LANE COLLISION: Use camera-specific boundary
                    bottom_lane_boundary = bottom_lane_config.get('y1', 620)  # Default to 620 if not configured
                    bottom_collision = (roi_y_bottom >= bottom_lane_boundary)
                    print(f"  Bottom Lane Boundary: y={bottom_lane_boundary} (camera-specific)")
                    print(f"  BOTTOM COLLISION: {bottom_collision} (Wood bottom={roi_y_bottom} {'>=' if bottom_collision else '<'} {bottom_lane_boundary})")
                    
                    if bottom_collision:
                        collision_detected = True
                        result['lane_collision'] = 'BOTTOM'
                        print(f"  ⚠️  MISALIGNMENT DETECTED: Wood is TOO LOW (touching BOTTOM lane)")
                        # Trigger notification
                        print(f"  📞 Checking if parent_app has show_alignment_warning method...")
                        if hasattr(self.parent_app, 'show_alignment_warning'):
                            print(f"  📞 Calling parent_app.show_alignment_warning('{camera}', 'BOTTOM')...")
                            self.parent_app.show_alignment_warning(camera, "BOTTOM")
                            print(f"  📞 show_alignment_warning() call completed")
                        else:
                            print(f"  ❌ parent_app does NOT have show_alignment_warning method!")


                    
                    # Summary
                    if collision_detected:
                        print(f"  🚨 RESULT: COLLISION DETECTED - Wood is MISALIGNED!")
                    else:
                        result['lane_collision'] = None
                        print(f"  ✅ RESULT: NO COLLISION - Wood is properly aligned")
                        # Clear any previous warnings
                        if hasattr(self.parent_app, 'clear_alignment_warning'):
                            self.parent_app.clear_alignment_warning(camera)
                    
                    print(f"{'='*60}\n")
                else:
                    # Lane ROI is disabled or parent_app not available
                    if auto_roi:
                        if not self.parent_app:
                            print(f"[COLLISION CHECK] Skipped - parent_app not set")
                        elif not hasattr(self.parent_app, 'lane_roi_var'):
                            print(f"[COLLISION CHECK] Skipped - lane_roi_var not available")
                        elif not self.parent_app.lane_roi_var.get():
                            print(f"[COLLISION CHECK] Skipped - Lane ROI checkbox is unchecked")

                
                # Report wood width status to verify synchronization
                self.report_wood_width_status(f"after {camera} detection")
            else:
                # Clear results when no wood detected
                self.wood_detection_results[camera] = None
                self.dynamic_roi[camera] = None

            print(f"✅ Detection complete: wood_detected={result['wood_detected']}, count={result['wood_count']}, confidence={result['confidence']:.2f}")

            return result
            
        except Exception as e:
            print(f"❌ Error in comprehensive wood detection: {e}")
            return {
                'wood_detected': False,
                'wood_count': 0,
                'wood_candidates': [],
                'auto_roi': None,
                'color_mask': np.zeros(image.shape[:2] if image is not None else (100, 100), dtype=np.uint8),
                'confidence': 0.0,
                'texture_confidence': 0.0,
                'error': str(e)
            }
    
    def visualize_detection(self, image: np.ndarray, detection_result: Dict, output_path: str = None) -> np.ndarray:
        """Create visualization of wood detection results"""
        vis_image = image.copy()
        
        # Draw all wood candidates
        for i, candidate in enumerate(detection_result['wood_candidates']):
            # Draw bounding box
            x, y, w, h = candidate['bbox']
            color = (0, 255, 0) if i == 0 else (0, 255, 255)  # Best candidate in green, others in yellow
            cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 2)
            
            # Add confidence label
            label = f"Wood {i+1}: {candidate['confidence']:.2f}"
            cv2.putText(vis_image, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Add metrics
            metrics = f"AR:{candidate['aspect_ratio']:.1f} S:{candidate['solidity']:.2f}"
            cv2.putText(vis_image, metrics, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw auto ROI
        if detection_result['auto_roi']:
            roi_x, roi_y, roi_w, roi_h = detection_result['auto_roi']
            cv2.rectangle(vis_image, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (255, 255, 0), 3)
            cv2.putText(vis_image, "AUTO ROI", (roi_x, roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # Add summary info
        summary = f"Wood Detected: {detection_result['wood_detected']} | Count: {detection_result['wood_count']} | Confidence: {detection_result['confidence']:.2f}"
        cv2.putText(vis_image, summary, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Save if output path provided
        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
            print(f"💾 Visualization saved to: {output_path}")
        
        return vis_image
    
    def draw_wood_detection_overlay(self, frame, camera_name):
        """Draw wood detection overlay similar to testIR.py"""
        overlay_frame = frame.copy()
        
        # DEBUG: Print to verify function is called
        print(f"[DEBUG] draw_wood_detection_overlay called for {camera_name}")
        print(f"[DEBUG] lane_roi_var value: {self.lane_roi_var.get()}")
        print(f"[DEBUG] camera_name in ALIGNMENT_LANE_ROIS: {camera_name in ALIGNMENT_LANE_ROIS}")
        
        # Draw alignment lane ROIs (highway lane style) - horizontal lanes at top and bottom
        # ALWAYS show if Lane ROI checkbox is enabled
        if self.lane_roi_var.get() and camera_name in ALIGNMENT_LANE_ROIS:
            print(f"[DEBUG] Drawing lanes for {camera_name}!")
            lane_rois = ALIGNMENT_LANE_ROIS[camera_name]
            
            # Create semi-transparent overlay for lanes
            overlay = overlay_frame.copy()
            
            # Draw top lane with semi-transparent red fill
            top_lane = lane_rois['top_lane']
            cv2.rectangle(overlay, 
                         (top_lane['x1'], top_lane['y1']), 
                         (top_lane['x2'], top_lane['y2']), 
                         (0, 0, 255), -1)  # Filled rectangle
            
            # Draw bottom lane with semi-transparent red fill
            bottom_lane = lane_rois['bottom_lane']
            cv2.rectangle(overlay, 
                         (bottom_lane['x1'], bottom_lane['y1']), 
                         (bottom_lane['x2'], bottom_lane['y2']), 
                         (0, 0, 255), -1)  # Filled rectangle
            
            # Blend overlay with original frame (30% transparency)
            cv2.addWeighted(overlay, 0.3, overlay_frame, 0.7, 0, overlay_frame)
            
            # Draw lane borders (solid red lines)
            cv2.rectangle(overlay_frame, 
                         (top_lane['x1'], top_lane['y1']), 
                         (top_lane['x2'], top_lane['y2']), 
                         (0, 0, 255), 3)  # Red border, 3px thick
            cv2.rectangle(overlay_frame, 
                         (bottom_lane['x1'], bottom_lane['y1']), 
                         (bottom_lane['x2'], bottom_lane['y2']), 
                         (0, 0, 255), 3)  # Red border, 3px thick
            
            # Add lane labels (horizontal text)
            # Top lane label
            top_label_x = (top_lane['x1'] + top_lane['x2']) // 2 - 70
            top_label_y = (top_lane['y1'] + top_lane['y2']) // 2 + 10
            cv2.putText(overlay_frame, "TOP LANE", 
                       (top_label_x, top_label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Bottom lane label
            bottom_label_x = (bottom_lane['x1'] + bottom_lane['x2']) // 2 - 90
            bottom_label_y = (bottom_lane['y1'] + bottom_lane['y2']) // 2 + 10
            cv2.putText(overlay_frame, "BOTTOM LANE", 
                       (bottom_label_x, bottom_label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Get stored wood detection results
        if hasattr(self, 'wood_detection_results') and self.wood_detection_results.get(camera_name):
            wood_detection = self.wood_detection_results[camera_name]
            
            # Draw all wood candidates
            for i, candidate in enumerate(wood_detection.get('wood_candidates', [])):
                x, y, w, h = candidate['bbox']
                confidence = candidate['confidence']
                
                # Use different colors for different candidates
                color = (0, 255, 0) if i == 0 else (0, 255, 255)  # Green for best, yellow for others
                
                # Draw bounding box
                cv2.rectangle(overlay_frame, (x, y), (x + w, y + h), color, 2)
                
                # Add labels
                label = f"Wood {i+1}: {confidence:.2f}"
                cv2.putText(overlay_frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Add width measurement for best candidate
                if i == 0:
                    width_mm = self.calculate_width_mm(h, camera_name)  # Use height for cross-section
                    width_label = f"Width: {width_mm:.1f}mm"
                    cv2.putText(overlay_frame, width_label, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Draw auto ROI if available
            if wood_detection.get('auto_roi'):
                roi_x, roi_y, roi_w, roi_h = wood_detection['auto_roi']
                
                # Check if collision was detected in wood detection function
                lane_collision = wood_detection.get('lane_collision')
                
                if lane_collision:
                    # COLLISION DETECTED - Draw red warning overlay
                    warning_overlay = overlay_frame.copy()
                    cv2.rectangle(warning_overlay, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 0, 255), -1)
                    cv2.addWeighted(warning_overlay, 0.3, overlay_frame, 0.7, 0, overlay_frame)
                    
                    # Draw red border
                    cv2.rectangle(overlay_frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (0, 0, 255), 3)
                    
                    # Add warning text
                    warning_text = f"⚠ MISALIGNED - {lane_collision} LANE"
                    cv2.putText(overlay_frame, warning_text, 
                               (roi_x, roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    # NO COLLISION - Draw normal yellow AUTO ROI
                    cv2.rectangle(overlay_frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), (255, 255, 0), 2)
                    cv2.putText(overlay_frame, "AUTO ROI", (roi_x, roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)


        
        return overlay_frame

    def create_segment_visualization(self, frame, wood_detection_result, camera_name):
        """Create segment visualization for wood detection - matches testIR.py interface"""
        return self.draw_wood_detection_overlay(frame, camera_name)

    def detect_wood_presence(self, frame):
        color_conf = self._detect_wood_by_color(frame)
        texture_conf = self._detect_wood_by_texture(frame)
        shape_conf = self._detect_wood_by_shape(frame)
        
        # Combine confidences with weights (color most important for wood)
        combined_conf = (0.5 * color_conf + 0.3 * texture_conf + 0.2 * shape_conf)
        wood_detected = combined_conf > 0.3  # Lower threshold since multiple methods
        
        return wood_detected, combined_conf, {
            'color_confidence': color_conf,
            'texture_confidence': texture_conf,
            'shape_confidence': shape_conf
        }

    def detect_wood(self, frame):
        """
        Enhanced wood detection using the wood detection model.
        Falls back to visual detection if model is not available.
        Returns True if wood is detected, False otherwise.
        """
        wood_detected, confidence, _ = self.detect_wood_presence(frame)
        return wood_detected

    def _detect_wood_by_color(self, frame):
        """Detect wood using RGB color segmentation"""
        try:
            rgb_frame = frame

            # Use calibrated wood color profiles
            
            combined_mask = None
            for profile in self.wood_color_profiles.values():
                mask = cv2.inRange(rgb_frame, profile['rgb_lower'], profile['rgb_upper'])
                if combined_mask is None:
                    combined_mask = mask
                else:
                    combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            # Clean up mask with morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # Calculate percentage of wood-like pixels
            wood_pixel_count = cv2.countNonZero(combined_mask)
            total_pixels = frame.shape[0] * frame.shape[1]
            wood_percentage = (wood_pixel_count / total_pixels) * 100
            
            # Return confidence (normalized to 0-1)
            return min(wood_percentage / 20.0, 1.0)  # 20% wood pixels = 100% confidence
            
        except Exception as e:
            print(f"Error in color-based wood detection: {e}")
            return 0.0


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Set appearance mode and color theme for CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        self.title("Wood Sorting Application - Modern UI (CustomTkinter)")

        # Get screen dimensions for dynamic sizing
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate window size based on configuration
        if ENABLE_FULLSCREEN_STARTUP:
            self.attributes("-fullscreen", True)
            self.is_fullscreen = True
            window_width = screen_width
            window_height = screen_height
        else:
            window_width = int(screen_width * WINDOW_SCALE)
            window_height = int(screen_height * WINDOW_SCALE)

            # Center the window on screen
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

            # Set geometry with calculated dimensions
            self.geometry(f"{window_width}x{window_height}+{x}+{y}")

        # Make window resizable
        self.resizable(True, True)

        # Set minimum size to prevent too small windows
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # For Raspberry Pi - detect if running in fullscreen environment
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)

        # Auto-fullscreen for Raspberry Pi (configurable)
        if ENABLE_FULLSCREEN_STARTUP:
            self.after(100, self.auto_fullscreen_rpi)

        # Calculate responsive font sizes based on screen size
        base_font_size = max(FONT_SIZE_BASE_MIN, min(FONT_SIZE_BASE_MAX, int(screen_height / FONT_SIZE_DIVISOR)))
        self.font_small = (PRIMARY_FONT_FAMILY, base_font_size - 1)
        self.font_normal = (PRIMARY_FONT_FAMILY, base_font_size)
        self.font_large = (PRIMARY_FONT_FAMILY, base_font_size + 2, "bold")
        self.font_button = (BUTTON_FONT_FAMILY, base_font_size, "bold")  # Button font

        # Configure styles for white margins and custom button colors
        style = ttk.Style()
        style.configure("White.TFrame", background="white")

        # Configure custom button style with colors from UI config
        style.configure("Custom.TButton",
                       background=BUTTON_BACKGROUND_COLOR,
                       foreground=BUTTON_TEXT_COLOR,
                       font=self.font_button)
        style.map("Custom.TButton",
                 background=[("active", BUTTON_ACTIVE_COLOR),
                           ("pressed", BUTTON_ACTIVE_COLOR)])

        # Helper method for updating status label (Text widget)
        def update_status_text(text, color=None):
            self.status_label.config(state=tk.NORMAL)
            self.status_label.delete(1.0, tk.END)
            self.status_label.insert(1.0, text)
            if color:
                self.status_label.config(foreground=color)
            self.status_label.config(state=tk.DISABLED)

        self.update_status_text = update_status_text

        # Create message queue for thread communication
        self.message_queue = queue.Queue()

        # Initialize variables that might be accessed early by message processing
        self.total_pieces_processed = 0
        self.session_start_time = time.time()  # Track session start time for statistics
        self.grade_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}  # Arduino commands: 1=G2-0, 2=G2-1, 3=G2-2, 4=G2-3, 5=G2-4
        self.report_generated = False
        self.last_report_path = None
        self.last_activity_time = time.time()
        self.live_stats = {"grade1": 0, "grade2": 0, "grade3": 0, "grade4": 0, "grade5": 0}  # Arduino commands
        self._shutting_down = False  # Flag to indicate shutdown in progress
        self.session_log = [] # New: Log for individual piece details
        self._camera_check_cooldown = 0  # Timestamp to skip camera checks after mode changes


        # Cache for preventing unnecessary UI updates
        self._last_detection_content = {"top": "", "bottom": ""}
        self._last_stats_content = ""
        self._user_scrolling = {"top": False, "bottom": False}
        self._user_scrolling_stats = False
        self._scroll_positions = {"top": 0.0, "bottom": 0.0}
        
        # Test case tracking system
        self.test_case_counter = 0
        self.current_test_case = None
        self.detection_log = []
        self.test_cases_data = {}

        # Disconnection popup flags
        self.camera_disconnected_popup_shown = False
        self.arduino_disconnected_popup_shown = False
        self.arduino_recovery_attempted = False  # Track recovery attempts to prevent duplicates
        
        # Detection tracking variables
        self.detection_session_id = None
        self.piece_counter = 0
        self.current_piece_data = None
        
        # System mode tracking
        self.current_mode = "IDLE"  # Can be "IDLE", "TRIGGER", "CONTINUOUS", or "SCAN_PHASE"

        # Error Management System
        self.error_state = {
            "active_errors": set(),
            "error_count": {},
            "last_error_time": {},
            "system_paused": False,
            "manual_inspection_required": False,
            "error_recovery_attempts": {}
        }
        
        # Error type definitions
        self.ERROR_TYPES = {
            "NO_WOOD_DETECTED": {
                "name": "No Wood Detected",
                "severity": "WARNING",
                "max_retries": 3,
                "timeout": 5.0,
                "description": "Wood piece not detected in expected timeframe"
            },

            "CAMERA_DISCONNECTED": {
                "name": "Camera Disconnected",
                "severity": "CRITICAL",
                "max_retries": 3,
                "timeout": 10.0,
                "description": "Camera communication lost"
            },
            "ARDUINO_DISCONNECTED": {
                "name": "Arduino Disconnected", 
                "severity": "CRITICAL",
                "max_retries": 3,
                "timeout": 5.0,
                "description": "Arduino communication lost"
            },
            "RESOURCE_EXHAUSTION": {
                "name": "Resource Exhaustion",
                "severity": "CRITICAL",
                "max_retries": 1,
                "timeout": 15.0,
                "description": "System memory or CPU resources depleted"
            },
            "MODEL_LOADING_FAILED": {
                "name": "AI Model Loading Failed",
                "severity": "CRITICAL",
                "max_retries": 2,
                "timeout": 30.0,
                "description": "DeGirum AI model failed to load or initialize"
            }
        }
        
        # Detection threshold constants
        self.DETECTION_THRESHOLDS = {
            "MIN_CONFIDENCE": 0.25,  # Minimum confidence for defect detection (matches live_inference.py)
            "MIN_WOOD_CONFIDENCE": 0.4,  # Minimum confidence for wood presence
            "WOOD_DETECTION_TIMEOUT": 10.0,  # Seconds to wait for wood detection
            "ALIGNMENT_TOLERANCE": 50,  # Pixels tolerance for wood alignment
            "MIN_WOOD_AREA": 1000,  # Minimum area for valid wood detection
        }
        
        # Detection monitoring variables
        self.detection_monitoring = {
            "wood_detection_start_time": None,
            "last_wood_detected": None,
            "alignment_failures": 0,
            "detection_retries": 0
        }
        
        # Alignment warning tracking (to prevent notification spam)
        self.alignment_warnings = {
            "top": {"last_warning_time": 0, "warning_cooldown": 5.0, "current_warning": None},
            "bottom": {"last_warning_time": 0, "warning_cooldown": 5.0, "current_warning": None}
        }

        # SCAN_PHASE mode variables
        self.scan_phase_active = False
        self.current_wood_number = 0
        self.latest_wood_folder = None  # Store latest graded wood folder path
        self.scan_session_data = {}
        self.captured_frames = {"top": [], "bottom": []}
        self.segment_defects = {"top": [], "bottom": []}
        self.scan_session_start_time = None
        self.scan_session_folder = None

        # Automatic detection state (triggered by IR beam)
        self.live_detection_var = tk.BooleanVar(value=False) # For live inference mode
        self.auto_grade_var = tk.BooleanVar(value=False) # For auto grading in live mode
        self._last_auto_grade_time = 0
        self._in_active_inference = False  # Flag to prevent UI conflicts during inference
        self.has_current_grade = False  # Track if we have a current grade to display

        self.auto_detection_active = False
        self.detection_frames = []  # Store frames during detection
        self.detection_session_data = {
            "start_time": None,
            "end_time": None,
            "total_detections": {"top": [], "bottom": []},
            "best_frames": {"top": None, "bottom": None},
            "final_grade": None
        }

        # Store all detections throughout the session for deduplication
        self.session_detections = {"top": [], "bottom": []}
        self.final_deduplicated_defects = {"top": [], "bottom": []}

        # Flag to control processed frame display in SCAN_PHASE
        self.displaying_processed_frame = False
        self.processed_frame_timer = None  # Timer for processed frame display duration

        # Camera monitoring for automatic reconnection
        self.camera_monitor_active = True
        self.last_camera_check_time = 0
        self.camera_check_interval = 10.0  # Check every 10 seconds
        self.camera_reconnection_attempts = 0
        self.max_camera_reconnection_attempts = 5

        # --- DeGirum Model and Camera Initialization ---
        # DeGirum Configuration
        self.inference_host_address = "@local"
        self.zoo_url = "/home/inspectura/Desktop/InspecturaGUI/models/NonAugmentDefects--640x640_quant_hailort_hailo8_1"
        # Model configuration - MUST match live_inference.py
        self.model_name = "NonAugmentDefects--640x640_quant_hailort_hailo8_1"  
        
        # Load DeGirum model
        try:
            self.model = dg.load_model(
                model_name=self.model_name,
                inference_host_address=self.inference_host_address,
                zoo_url=self.zoo_url
            )
            print("DeGirum model loaded successfully.")
        except Exception as e:
            print(f"Error loading DeGirum model: {e}")
            messagebox.showerror("Model Error", f"Failed to load DeGirum model: {e}")
            self.model = None
        

        # Initialize detection deduplicator for low FPS scenarios
        # Deduplication for wood sorting (conservative settings to preserve all legitimate defects)
        self.deduplicator = DetectionDeduplicator(spatial_threshold_mm=5.0, temporal_threshold_sec=0.2)

        # Initialize Camera Handler with optimized settings
        self.camera_handler = CameraHandler()
        try:
            self.camera_handler.initialize_cameras()
            self.cap_top = self.camera_handler.top_camera
            self.cap_bottom = self.camera_handler.bottom_camera

            # Store camera resolution for display scaling
            self.camera_width = 1280
            self.camera_height = 720

            print("Camera handler initialized with optimized settings")
        except RuntimeError as e:
            print(f"Camera initialization failed: {e}")
            self.cap_top = None
            self.cap_bottom = None

        # Initialize RGB Wood Detector for dynamic ROI generation
        self.rgb_wood_detector = ColorWoodDetector(parent_app=self)
        print("RGB Wood Detector initialized for dynamic ROI generation")

        # Initialize dynamic ROI storage
        self.dynamic_roi = {}
        self.detected_wood_width_mm = {"top": None, "bottom": None}

        # Store wood detection results for visualization
        self.wood_detection_results = {"top": None, "bottom": None}

        # Live detection tracking
        self.live_detections = {"top": {}, "bottom": {}}
        self.live_grades = {"top": "", "bottom": ""}

        # ROI (Region of Interest) settings
        self.roi_enabled = {"top": True, "bottom": True, "wood_detection": True, "exit_wood": True, "lane_alignment": True}  # Enable ROI for both cameras, wood detection, and lane alignment
        self.roi_coordinates = ROI_COORDINATES.copy()

        # UI colors
        self.roi_overlay_color = ROI_OVERLAY_COLOR

        # Create canvases for camera feeds maintaining dynamic width and fixed height of 360 pixels
        self.canvas_width = screen_width // 2 - 25
        self.canvas_height = 360
        
        # Wood specification notice at the top center (CustomTkinter modern style)
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
        
        # Camera canvases (still using standard tk.Canvas for video display)
        self.top_canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, 
                                   bg='black', highlightbackground="#555555", highlightthickness=1)
        self.top_canvas.place(x=10, y=35, width=self.canvas_width, height=self.canvas_height)

        self.bottom_canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, 
                                      bg='black', highlightbackground="#555555", highlightthickness=1)
        self.bottom_canvas.place(x=self.canvas_width + 40, y=35, width=self.canvas_width, height=self.canvas_height)

        # Initialize canvas images
        self._top_photo = None
        self._bottom_photo = None

        # Place control frames at specific positions
        # Status panel under left camera (CustomTkinter)
        status_frame = ctk.CTkFrame(self, width=self.canvas_width, height=125, corner_radius=8)
        status_frame.place(x=10, y=415)
        status_frame.pack_propagate(False)

        ctk.CTkLabel(status_frame, text="System Status", font=("Arial", 14, "bold")).pack(pady=(8, 2))

        self.status_label = tk.Text(status_frame, font=("Arial", 12), wrap=tk.WORD,
                                   height=3, width=int(self.canvas_width/10), state=tk.DISABLED, relief="flat",
                                   background=FRAME_BACKGROUND_COLOR, foreground=TEXT_COLOR,
                                   insertbackground=TEXT_COLOR, borderwidth=0)
        self.status_label.pack(pady=(2, 5), padx=8, fill="both", expand=True)
        self.status_label.config(state=tk.NORMAL)
        self.status_label.insert(1.0, "Status: Initializing...")
        self.status_label.config(state=tk.DISABLED)

        # Calculate positions for panels under right camera
        right_camera_x = self.canvas_width + 20
        available_width_right = self.canvas_width
        
        # ROI panel (CustomTkinter) - smaller width
        roi_width = 250
        roi_frame = ctk.CTkFrame(self, width=roi_width, height=125, corner_radius=8)
        roi_frame.place(x=right_camera_x, y=415)
        roi_frame.pack_propagate(False)

        ctk.CTkLabel(roi_frame, text="ROI", font=("Arial", 14, "bold")).pack(pady=(8, 5))

        self.roi_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(roi_frame, text="Top ROI", variable=self.roi_var, 
                     command=self.toggle_roi, font=("Arial", 12)).pack(anchor="w", padx=15, pady=3)

        self.bottom_roi_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(roi_frame, text="Bottom ROI", variable=self.bottom_roi_var,
                     command=self.toggle_bottom_roi, font=("Arial", 12)).pack(anchor="w", padx=15, pady=3)

        self.lane_roi_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(roi_frame, text="Lane ROI", variable=self.lane_roi_var,
                     command=self.toggle_lane_roi, font=("Arial", 12)).pack(anchor="w", padx=15, pady=3)
        
        # Hidden test button (keep as tk.Button for compatibility)
        hidden_test_btn = tk.Button(roi_frame, text="", 
                                    command=self.test_low_confidence_notification,
                                    font=("Arial", 1), 
                                    bg=FRAME_BACKGROUND_COLOR,
                                    fg=FRAME_BACKGROUND_COLOR,
                                    activebackground=FRAME_BACKGROUND_COLOR,
                                    relief=tk.FLAT, 
                                    borderwidth=0,
                                    cursor="",
                                    width=2, height=1)
        hidden_test_btn.pack(anchor="e", padx=2, pady=2)

        # Conveyor Control (CustomTkinter) - positioned after ROI
        control_x = right_camera_x + roi_width + 10
        control_width = int((available_width_right - roi_width - 10) * 0.60)
        control_frame = ctk.CTkFrame(self, width=control_width, height=125, corner_radius=8)
        control_frame.place(x=control_x, y=415)
        control_frame.pack_propagate(False)

        ctk.CTkLabel(control_frame, text="Conveyor Control", 
                    font=("Arial", 14, "bold")).place(x=int(control_width/2 - 70), y=8)

        button_width = int((control_width - 20) / 2)
        ctk.CTkButton(
            control_frame, text="ON", command=self.set_scan_mode,
            fg_color="#28a745", hover_color="#218838", corner_radius=6,
            font=("Arial", 16, "bold"), width=button_width, height=45
        ).place(x=5, y=30)
        
        ctk.CTkButton(
            control_frame, text="OFF", command=self.set_idle_mode,
            fg_color="#6c757d", hover_color="#5a6268", corner_radius=6,
            font=("Arial", 16, "bold"), width=button_width, height=45
        ).place(x=button_width + 10, y=30)
        
        # CLOSE button
        close_button_width = (button_width * 2) + 5
        ctk.CTkButton(
            control_frame, text="CLOSE", command=self.on_closing,
            fg_color="#8B0000", hover_color="#660000", corner_radius=6,
            font=("Arial", 16, "bold"), width=close_button_width, height=45
        ).place(x=5, y=78)

        # Reports panel (CustomTkinter) - fills remaining space with scrollable content
        reports_x = control_x + control_width + 10
        reports_width = (right_camera_x + self.canvas_width) - reports_x
        reports_outer_frame = ctk.CTkFrame(self, width=reports_width, height=180, corner_radius=8)
        reports_outer_frame.place(x=reports_x, y=415)
        reports_outer_frame.pack_propagate(False)

        # Create scrollable frame for all reports content
        reports_scrollable = ctk.CTkScrollableFrame(
            reports_outer_frame,
            width=reports_width - 20,
            height=160,
            fg_color="transparent"
        )
        reports_scrollable.pack(fill="both", expand=True, padx=5, pady=5)

        # Wood Counter Display at the top
        wood_counter_frame = ctk.CTkFrame(reports_scrollable, fg_color="#1a4d2e", corner_radius=0, height=40)
        wood_counter_frame.pack(fill="x", padx=0, pady=(0, 5))
        wood_counter_frame.pack_propagate(False)
        
        self.wood_counter_label = ctk.CTkLabel(
            wood_counter_frame, 
            text="🪵 Current Wood: #0",
            font=("Arial", 16, "bold"),
            text_color="#90EE90"
        )
        self.wood_counter_label.pack(pady=8)

        ctk.CTkLabel(reports_scrollable, text="Last Graded Report", font=("Arial", 12, "bold")).pack(pady=(5, 2))

        # Defects report textbox (kiosk style - larger font for readability)
        self.defects_report_textbox = ctk.CTkTextbox(
            reports_scrollable,
            font=(MONOSPACE_FONT_FAMILY, 14),
            fg_color="#1a1a1a",
            text_color=TEXT_COLOR,
            wrap="word",
            height=80
        )
        self.defects_report_textbox.pack(fill="x", padx=3, pady=(0, 5))
        
        # Initial placeholder content
        self.defects_report_textbox.insert("1.0", "No wood graded yet.\nWaiting for first detection...")
        self.defects_report_textbox.configure(state="disabled")

        # Button row for reports
        reports_button_frame = ctk.CTkFrame(reports_scrollable, fg_color="transparent", height=35)
        reports_button_frame.pack(fill="x", padx=3, pady=(0, 5))
        reports_button_frame.pack_propagate(False)

        ctk.CTkButton(
            reports_button_frame, text="View Folder",
            command=self.view_latest_wood_folder,
            fg_color="#1E3A8A", hover_color="#1E40AF",
            corner_radius=6, height=28, font=("Arial", 11), width=100
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            reports_button_frame, text="Generate Report",
            command=self.manual_generate_report,
            fg_color=BUTTON_BACKGROUND_COLOR, hover_color=BUTTON_ACTIVE_COLOR,
            corner_radius=6, height=28, font=("Arial", 11), width=120
        ).pack(side="left")


        # Statistics section full width at bottom (CustomTkinter)
        stats_width = screen_width - 20
        
        stats_outer_frame = ctk.CTkFrame(self, width=stats_width, height=480, corner_radius=8)
        stats_outer_frame.place(x=10, rely=1.0, anchor="sw")
        stats_outer_frame.pack_propagate(False)

        # Create tabview for statistics (CustomTkinter)
        self.stats_tabview = ctk.CTkTabview(stats_outer_frame, height=455,
                                           segmented_button_fg_color="#2b2b2b",
                                           segmented_button_selected_color="#1f538d",
                                           segmented_button_selected_hover_color="#14375e")
        self.stats_tabview.pack(fill="both", expand=True, padx=8, pady=8)

        # Add tabs
        self.stats_tabview.add("SS-EN 1611-1 Summary")
        self.stats_tabview.add("Grading Standards")
        self.stats_tabview.add("System Performance")

        # Tab 1: Grade Summary (CustomTkinter)
        grade_summary_tab = self.stats_tabview.tab("SS-EN 1611-1 Summary")

        # Main container
        main_container = ctk.CTkFrame(grade_summary_tab, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # Title
        ctk.CTkLabel(main_container, text="SS-EN 1611-1 Live Grading Results", 
                    font=("Arial", 16, "bold")).pack(pady=(5, 10))

        # Camera grades row
        grades_row = ctk.CTkFrame(main_container, fg_color="transparent", height=75)
        grades_row.pack(fill="x", padx=5, pady=(0, 8))
        grades_row.pack_propagate(False)

        # Top Camera
        top_container = ctk.CTkFrame(grades_row, corner_radius=6)
        top_container.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(top_container, text="Top Camera:", 
                    font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.top_grade_label = ctk.CTkLabel(top_container, text="No Wood Graded", 
                                           text_color="gray", font=("Arial", 11))
        self.top_grade_label.pack(pady=(0, 10))

        # Bottom Camera
        bottom_container = ctk.CTkFrame(grades_row, corner_radius=6)
        bottom_container.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(bottom_container, text="Bottom Camera:", 
                    font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.bottom_grade_label = ctk.CTkLabel(bottom_container, text="No Wood Graded",
                                              text_color="gray", font=("Arial", 11))
        self.bottom_grade_label.pack(pady=(0, 10))

        # Final Grade
        final_container = ctk.CTkFrame(grades_row, corner_radius=6, 
                                      fg_color="#2d5016", border_width=1, 
                                      border_color="#4a7c2a")
        final_container.pack(side="left", fill="both", expand=True, padx=3)
        ctk.CTkLabel(final_container, text="Final Grade:", 
                    font=("Arial", 13, "bold")).pack(pady=(10, 0))
        self.combined_grade_label = ctk.CTkLabel(final_container, text="No Wood Graded",
                                                font=("Arial", 18, "bold"),  # Increased from 12 to 18 for kiosk
                                                text_color="gray")
        self.combined_grade_label.pack(pady=(0, 10))

        # Grade counters container
        counters_container = ctk.CTkFrame(main_container, fg_color="transparent")
        counters_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.live_stats_labels = {}
        grade_info = [
            ("grade1", "G2-0\n(Good)", GRADE_PERFECT_COLOR),
            ("grade2", "G2-1\n(Good)", GRADE_GOOD_COLOR),
            ("grade3", "G2-2\n(Fair)", GRADE_FAIR_COLOR),
            ("grade4", "G2-3\n(Poor)", GRADE_POOR_COLOR),
            ("grade5", "G2-4\n(Poor)", GRADE_POOR_COLOR)
        ]

        for grade_key, label_text, color in grade_info:
            grade_box = ctk.CTkFrame(counters_container, corner_radius=8, 
                                    border_width=2, border_color="#3a3a3a")
            grade_box.pack(side="left", fill="both", expand=True, padx=3)

            inner_box = ctk.CTkFrame(grade_box, fg_color="transparent")
            inner_box.pack(fill="both", expand=True)

            ctk.CTkLabel(inner_box, text=label_text, font=("Arial", 18, "bold"),  # Increased from 14 to 18 for kiosk
                        justify="center").pack(pady=(15, 5))

            self.live_stats_labels[grade_key] = ctk.CTkLabel(
                inner_box, text="0", font=("Arial", 52, "bold"), text_color=color,  # Increased from 42 to 52 for kiosk
                anchor="center", justify="center"
            )
            self.live_stats_labels[grade_key].pack(pady=(5, 15), expand=True)

        # Tab 2: Grading Details - SS-EN 1611-1 Standards (CustomTkinter)
        grading_details_tab = self.stats_tabview.tab("Grading Standards")

        # Grading details content - direct frame without scrolling (textbox handles scrolling)
        self.grading_details_frame = ctk.CTkFrame(
            grading_details_tab, 
            corner_radius=8,
            fg_color="#2b2b2b"
        )
        self.grading_details_frame.pack(fill="both", expand=True, padx=8, pady=8)

        # Tab 3: Performance Metrics (CustomTkinter)
        performance_tab = self.stats_tabview.tab("System Performance")

        # Performance metrics content - direct frame without scrolling (labels handle layout)
        self.performance_frame = ctk.CTkFrame(
            performance_tab, 
            corner_radius=8,
            fg_color="#2b2b2b"
        )
        self.performance_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        # Create simplified detection tracking (retain logic without complex UI)
        self.top_dashboard_widgets = self.create_simple_detection_tracker("top")
        self.bottom_dashboard_widgets = self.create_simple_detection_tracker("bottom")
        
        # Keep compatibility with existing code
        self.top_details = None
        self.bottom_details = None
        self.top_details_widgets = None
        self.bottom_details_widgets = None

        # Initialize live statistics display
        self.update_live_stats_display()

        # Initialize tab content (single call after frames are created)
        self.update_grade_details_tab()
        self.update_performance_tab()

        # Removed grading_status_label as requested

        # --- Arduino Communication ---
        self.setup_arduino()

        # Start the video feed update loop
        self.update_feeds()

        # Start processing messages from background threads
        self.process_message_queue()

        # --- System Health Monitoring ---
        self.start_health_monitoring()

        # --- Inactivity and Reporting ---
        self.check_inactivity()

        # Set the action for when the window is closed
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_live_grading_display(self):
        if self.current_mode == "IDLE":
            self.top_grade_label.configure(text="No Wood Graded", text_color="gray")
            self.bottom_grade_label.configure(text="No Wood Graded", text_color="gray")
            self.combined_grade_label.configure(text="No Wood Graded", text_color="gray")
        else:
            # Show current grades if available
            top_grade = self.live_grades.get("top", "No Wood Graded")
            bottom_grade = self.live_grades.get("bottom", "No Wood Graded")
            if isinstance(top_grade, dict):
                top_text = top_grade.get("text", "No Wood Graded")
                top_color = top_grade.get("color", "gray")
            else:
                top_text = top_grade
                top_color = "gray"
            if isinstance(bottom_grade, dict):
                bottom_text = bottom_grade.get("text", "No Wood Graded")
                bottom_color = bottom_grade.get("color", "gray")
            else:
                bottom_text = bottom_grade
                bottom_color = "gray"
            self.top_grade_label.configure(text=top_text, text_color=top_color)
            self.bottom_grade_label.configure(text=bottom_text, text_color=bottom_color)
            combined_info = self.live_grades.get("combined")
            if combined_info:
                combined_text = combined_info.get("text", "No Wood Graded")
                combined_color = combined_info.get("color", "gray")
            else:
                combined_text = self.live_grades.get("combined", "No Wood Graded")
                combined_color = "gray"
            self.combined_grade_label.configure(text=combined_text, text_color=combined_color)

    def calibrate_pixel_to_mm(self, reference_object_width_px, reference_object_width_mm, camera_name="top"):
        """Calibrate the pixel-to-millimeter conversion factor for specific camera"""
        global TOP_CAMERA_PIXEL_TO_MM, BOTTOM_CAMERA_PIXEL_TO_MM
        
        conversion_factor = reference_object_width_mm / reference_object_width_px
        
        if camera_name == "top":
            TOP_CAMERA_PIXEL_TO_MM = conversion_factor
            print(f"Calibrated TOP camera pixel-to-mm factor: {TOP_CAMERA_PIXEL_TO_MM}")
        else:  # bottom camera
            BOTTOM_CAMERA_PIXEL_TO_MM = conversion_factor
            print(f"Calibrated BOTTOM camera pixel-to-mm factor: {BOTTOM_CAMERA_PIXEL_TO_MM}")
        
        return conversion_factor

    def calibrate_with_wood_pallet(self, wood_pallet_width_px_top, wood_pallet_width_px_bottom):
        """Auto-calibrate both cameras using the known wood pallet width"""
        print(f"Auto-calibrating cameras with {WOOD_PALLET_WIDTH_MM}mm wood pallet...")

        top_factor = self.calibrate_pixel_to_mm(wood_pallet_width_px_top, WOOD_PALLET_WIDTH_MM, "top")
        bottom_factor = self.calibrate_pixel_to_mm(wood_pallet_width_px_bottom, WOOD_PALLET_WIDTH_MM, "bottom")
        
        print(f"Calibration complete:")
        print(f"  Top camera (37cm): {top_factor:.4f} mm/pixel")
        print(f"  Bottom camera (29cm): {bottom_factor:.4f} mm/pixel")
        
        return top_factor, bottom_factor

    def map_model_output_to_standard(self, model_label):
        """Map your model's output labels to standardized defect types"""
        # Mapping from your model's actual output labels to standard categories
        label_mapping = {
            # Your actual model outputs (case-insensitive)
            "dead knots": "Dead_Knot",
            "knots with crack": "Crack_Knot",  # Keep as Crack_Knot for display
            "live knots": "Sound_Knot",
            "missing knots": "Missing_Knot",   # Keep as Missing_Knot for display
            # Variations and alternatives
            "dead_knots": "Dead_Knot",
            "knots_with_crack": "Crack_Knot",
            "live_knots": "Sound_Knot",
            "missing_knots": "Missing_Knot",
            # Legacy mappings for backward compatibility
            "sound_knots": "Sound_Knot",
            "dead_knots": "Dead_Knot",
            "unsound_knots": "Unsound_Knot",
            "sound knots": "Sound_Knot",
            "dead knots": "Dead_Knot",
            "unsound knots": "Unsound_Knot",
            "knot with crack": "Crack_Knot",
            "live_knot": "Sound_Knot",
            "dead_knot": "Dead_Knot",
            "missing_knot": "Missing_Knot",
            "crack_knot": "Crack_Knot",
            "live knot": "Sound_Knot",
            # Generic fallback
            "knot": "Unsound_Knot"
        }

        # Normalize the label (lowercase, remove extra spaces)
        normalized_label = model_label.lower().strip().replace('_', ' ')

        # Return mapped label or default to unsound knot
        return label_mapping.get(normalized_label, "Unsound_Knot")

    def get_display_name_for_defect(self, defect_type):
        """Get human-readable display name for defect types with grading category in parentheses"""
        display_mapping = {
            "Sound_Knot": "Live Knot (Sound Knot)",
            "Live_Knot": "Live Knot", 
            "Dead_Knot": "Dead Knot",
            "Unsound_Knot": "Unsound Knot",
            "Missing_Knot": "Missing Knot (Unsound Knot)",
            "Crack_Knot": "Knot with Crack (Unsound Knot)",
            "Knots_With_Crack": "Knot with Crack (Unsound Knot)",
            "knots_with_crack": "Knot with Crack (Unsound Knot)",
            "missing_knots": "Missing Knot (Unsound Knot)",
            # Additional variants
            "live_knot": "Live Knot",
            "dead_knot": "Dead Knot",
            "sound_knot": "Sound Knot",
            "unsound_knot": "Unsound Knot",
            "missing_knot": "Missing Knot (Unsound Knot)",
            "crack_knot": "Knot with Crack (Unsound Knot)"
        }
        
        return display_mapping.get(defect_type, defect_type)

    def get_color_for_defect(self, defect_type):
        """Get BGR color for defect bounding boxes and backgrounds"""
        # Color mapping (BGR format for OpenCV - note: BGR is reversed from RGB)
        color_mapping = {
            # Sound & Live Knots = Light Blue (RGB: 100, 200, 255)
            "Sound_Knot": (255, 200, 100),    
            "Live_Knot": (255, 200, 100),     
            "sound_knot": (255, 200, 100),    
            "live_knot": (255, 200, 100),     
            
            # Dead Knots = Yellow (RGB: 255, 255, 0)
            "Dead_Knot": (0, 255, 255),       
            "dead_knot": (0, 255, 255),       
            
            # Missing Knots = Red (RGB: 255, 0, 0)
            "Missing_Knot": (0, 0, 255),      
            "missing_knot": (0, 0, 255),      
            "missing_knots": (0, 0, 255),     
            
            # Knots with Crack = Orange (RGB: 255, 165, 0)
            "Crack_Knot": (0, 165, 255),      
            "crack_knot": (0, 165, 255),      
            "Knots_With_Crack": (0, 165, 255), 
            "knots_with_crack": (0, 165, 255), 
            
            # Default for Unsound and unknown types = Orange (RGB: 255, 165, 0)
            "Unsound_Knot": (0, 165, 255),    
            "unsound_knot": (0, 165, 255),    
        }
        
        # Return color or default to green if not found
        return color_mapping.get(defect_type, (0, 255, 0))

    def calculate_defect_size(self, detection_box, camera_name="top"):
        """Calculate defect size in mm and percentage from detection bounding box"""
        try:
            # Extract bounding box coordinates
            x1, y1, x2, y2 = detection_box['bbox']

            # Calculate defect dimensions in pixels
            width_px = abs(x2 - x1)   # Horizontal dimension (X-axis)
            height_px = abs(y2 - y1) # Vertical dimension (Y-axis)

            # For wood width measurement, use the vertical dimension (height_px) because camera is in landscape
            # Wood runs vertically in the camera view, so Y-axis represents wood width
            defect_size_px = height_px

            # Use camera-specific conversion factor
            if camera_name == "top":
                pixel_to_mm = TOP_CAMERA_PIXEL_TO_MM
            else:  # bottom camera
                pixel_to_mm = BOTTOM_CAMERA_PIXEL_TO_MM

            # Prevent division by zero
            if pixel_to_mm <= 0:
                pixel_to_mm = 2.96 if camera_name == "top" else 3.5
                print(f"Warning: pixel_to_mm was zero, using default {pixel_to_mm}")

            # Convert to millimeters using division (pixels per mm factor)
            size_mm = defect_size_px / pixel_to_mm

            # Calculate percentage of actual wood pallet width
            if WOOD_PALLET_WIDTH_MM > 0:
                percentage = (size_mm / WOOD_PALLET_WIDTH_MM) * 100
            else:
                percentage = 0.0  # Avoid division by zero

            # Debug logging to understand bounding box sizes
            print(f"DEBUG [{camera_name}]: bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) "
                  f"-> width_px={width_px:.1f}, height_px={height_px:.1f} "
                  f"-> defect_size_px={defect_size_px:.1f} (using Y-axis) -> size_mm={size_mm:.1f}")

            return size_mm, percentage

        except Exception as e:
            print(f"Error calculating defect size: {e}")
            # Return conservative values if calculation fails
            return 50.0, 35.0  # Assumes large defect for safety

    def _convert_measurements_to_face_data(self, measurements):
        """Convert app measurements to PineGrader face data format"""
        knot_data_size = {}
        knot_data_number = {'total': 0, 'unsound_only': 0}

        # Map defect types to PineGrader format
        type_mapping = {
            "Sound_Knot": "Sound Knots",
            "Dead_Knot": "Dead Knots",
            "Unsound_Knot": "Unsound/Missing Knots",
            "Missing_Knot": "Unsound/Missing Knots",
            "Crack_Knot": "Unsound/Missing Knots"
        }

        for defect_type, size_mm, _ in measurements:
            mapped_type = type_mapping.get(defect_type, defect_type)
            if mapped_type not in knot_data_size:
                knot_data_size[mapped_type] = size_mm
            else:
                knot_data_size[mapped_type] = max(knot_data_size[mapped_type], size_mm)

            knot_data_number['total'] += 1
            if mapped_type == "Unsound/Missing Knots":
                knot_data_number['unsound_only'] += 1

        # Ensure all knot types are present
        for kt in ["Sound Knots", "Dead Knots", "Unsound/Missing Knots"]:
            if kt not in knot_data_size:
                knot_data_size[kt] = 0

        return {'size': knot_data_size, 'number': knot_data_number}

    def determine_surface_grade(self, defect_measurements, camera_name=None):
        """
        Determine overall surface grade based on worst knot size and knot count.
        defect_measurements: list of tuples [("Sound_Knot", size_mm), ...]
        camera_name: 'top' or 'bottom' - passed for context but ALWAYS uses bottom camera wood width
        """
        if not defect_measurements:
            return GRADE_G2_0

        # ALWAYS use BOTTOM camera wood width for grading (more consistent/accurate)
        if self.detected_wood_width_mm.get("bottom", 0) > 0:
            wood_width_mm = self.detected_wood_width_mm["bottom"]
            print(f"🎯 Using BOTTOM camera wood width: {wood_width_mm:.1f}mm for grading {camera_name or 'unknown'} camera")
        else:
            # Fallback to global if bottom camera width not available
            wood_width_mm = WOOD_PALLET_WIDTH_MM
            print(f"⚠️  Using global wood width: {wood_width_mm:.1f}mm for grading (bottom camera not available)")

        # Check if wood height has been measured
        if wood_width_mm <= 0:
            return GRADE_G2_4  # Cannot grade without wood dimensions

        # 1. Grade based on the size of the worst individual knot
        worst_grade_by_size = "G2-0"
        grade_order = ["G2-0", "G2-1", "G2-2", "G2-3", "G2-4"]

        dead_or_unsound_count = 0

        for defect_type, defect_size_mm, _ in defect_measurements:
            # Tally knots for count constraint
            if defect_type in ["Dead_Knot", "Unsound_Knot"]:
                dead_or_unsound_count += 1

            # Get individual knot grade using camera-specific wood width
            knot_grade = self.get_individual_knot_grade(defect_type, defect_size_mm, wood_width_mm)

            # Check if this knot's grade is worse than the current worst
            if grade_order.index(knot_grade) > grade_order.index(worst_grade_by_size):
                worst_grade_by_size = knot_grade

        # 2. Grade based on the count of Dead and Unsound knots
        grade_by_count = "G2-0"
        if dead_or_unsound_count > 5:
            grade_by_count = "G2-4"
        elif dead_or_unsound_count > 2:
            grade_by_count = "G2-3"
        elif dead_or_unsound_count > 1:
            grade_by_count = "G2-2"
        elif dead_or_unsound_count > 0:
            grade_by_count = "G2-1"

        # 3. The final grade for the surface is the WORST of the two criteria
        final_grade_index = max(grade_order.index(worst_grade_by_size), grade_order.index(grade_by_count))
        final_grade = grade_order[final_grade_index]

        # 4. Return the actual worst grade found (G2-0, G2-1, G2-2, G2-3, or G2-4)
        return final_grade

    def determine_final_grade(self, top_grade, bottom_grade):
        """Determine final grade based on worst surface (SS-EN 1611-1 standard)"""
        grade_hierarchy = [GRADE_G2_0, GRADE_G2_1, GRADE_G2_2, GRADE_G2_3, GRADE_G2_4]

        # Handle None values (no detection)
        if top_grade is None:
            top_grade = GRADE_G2_0
        if bottom_grade is None:
            bottom_grade = GRADE_G2_0

        # Get indices for comparison
        top_index = grade_hierarchy.index(top_grade) if top_grade in grade_hierarchy else 0
        bottom_index = grade_hierarchy.index(bottom_grade) if bottom_grade in grade_hierarchy else 0

        # Return the worse grade (higher index)
        final_grade = grade_hierarchy[max(top_index, bottom_index)]

        print(f"Final grading: Top={top_grade}, Bottom={bottom_grade}, Final={final_grade}")
        return final_grade

    def convert_grade_to_arduino_command(self, standard_grade):
        """Convert SS-EN 1611-1 grade to Arduino sorting command"""
        # Map individual grades to sorting gates:
        grade_to_command = {
            GRADE_G2_0: 1,    # Perfect (G2-0) - Gate 1
            GRADE_G2_1: 2,    # Good (G2-1) - Gate 2
            GRADE_G2_2: 2,    # Fair (G2-2) - Gate 2
            GRADE_G2_3: 3,    # Poor (G2-3) - Gate 3
            GRADE_G2_4: 3     # Poor (G2-4) - Gate 3
        }

        return grade_to_command.get(standard_grade, 3)  # Default to worst gate if unknown

    def get_grade_color(self, grade):
        """Get color coding for grades"""
        color_map = {
            GRADE_G2_0: 'dark green',
            GRADE_G2_1: 'green',
            GRADE_G2_2: 'orange',
            GRADE_G2_3: 'red',
            GRADE_G2_4: 'dark red'
        }
        return color_map.get(grade, 'gray')

    def create_section(self, parent, title, col):
        section_frame = ttk.LabelFrame(parent, text=title, padding="10")
        section_frame.grid(row=0, column=col, sticky="nsew", padx=5, pady=5)
        
        # Fixed proportions to prevent shrinking
        section_frame.grid_rowconfigure(0, weight=3, minsize=200)  # Live feed gets most space with minimum
        section_frame.grid_rowconfigure(1, weight=0, minsize=150)  # Details get fixed space
        section_frame.grid_columnconfigure(0, weight=1, minsize=350)  # Minimum width

        # Live feed area - now takes up most of the space with minimum size
        live_feed_label = ttk.Label(section_frame, background="black", text="Live Feed")
        live_feed_label.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        # Details area with proper wrapping, formatting and scrolling capability
        details_frame = ttk.Frame(section_frame)
        details_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        details_frame.grid_rowconfigure(0, weight=1)
        details_frame.grid_columnconfigure(0, weight=1)
        
        # Create scrollable text widget for details
        details_text = tk.Text(details_frame, wrap=tk.WORD, height=8, width=40, 
                              font=self.font_small, state=tk.DISABLED,
                              relief="sunken", borderwidth=1)
        details_scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=details_text.yview)
        details_text.configure(yscrollcommand=details_scrollbar.set)
        
        # Track user scrolling to prevent auto-updates during manual scrolling
        camera_name = "top" if col == 0 else "bottom"
        
        def on_scroll_start(event):
            self._user_scrolling[camera_name] = True
            # Clear the auto-scroll timer if it exists
            if hasattr(self, f'_scroll_timer_{camera_name}'):
                self.after_cancel(getattr(self, f'_scroll_timer_{camera_name}'))
        
        def on_scroll_end():
            # Allow updates again after 3 seconds of no scrolling
            timer_id = self.after(3000, lambda: self._user_scrolling.update({camera_name: False}))
            setattr(self, f'_scroll_timer_{camera_name}', timer_id)
        
        def on_scroll_event(event):
            on_scroll_start(event)
            on_scroll_end()
            # Store current scroll position
            self._scroll_positions[camera_name] = details_text.yview()[0]
        
        # Bind scroll events
        details_text.bind("<Button-4>", on_scroll_event)  # Mouse wheel up
        details_text.bind("<Button-5>", on_scroll_event)  # Mouse wheel down
        details_text.bind("<MouseWheel>", on_scroll_event)  # Windows mouse wheel
        details_scrollbar.bind("<ButtonPress-1>", on_scroll_start)
        details_scrollbar.bind("<B1-Motion>", on_scroll_event)
        
        details_text.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
        details_scrollbar.grid(row=0, column=1, sticky="ns")
        
        details_frame.grid_columnconfigure(0, weight=1)
        details_frame.grid_columnconfigure(1, weight=0)

        return live_feed_label, None, details_text

    def create_detection_details_section(self, parent, title, camera_name):
        """Create an object-based detection details section that updates efficiently"""
        frame = ttk.LabelFrame(parent, text=title, padding="5")
        
        # Create canvas and scrollbar for scrolling
        canvas = tk.Canvas(frame, height=150)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel with camera-specific scrolling detection
        def _on_mousewheel(event):
            self._user_scrolling[camera_name] = True
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            # Reset scroll flag after 3 seconds
            timer_id = self.after(3000, lambda: self._user_scrolling.update({camera_name: False}))
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        # Bind scrollbar interactions
        scrollbar.bind("<ButtonPress-1>", lambda e: self._user_scrolling.update({camera_name: True}))
        scrollbar.bind("<B1-Motion>", lambda e: self._user_scrolling.update({camera_name: True}))
        scrollbar.bind("<ButtonRelease-1>", lambda e: self.after(3000, lambda: self._user_scrolling.update({camera_name: False})))
        
        # Pack elements
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create the widget structure for detection details
        details_widgets = self.create_detection_widgets(scrollable_frame, camera_name)
        
        return frame, details_widgets

    def create_detection_widgets(self, parent, camera_name):
        """Create the widget structure for detection details"""
        widgets = {}
        
        # Header section
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=2)
        
        widgets['header_label'] = ttk.Label(header_frame, 
                                          text=f"SS-EN 1611-1 Grading ({camera_name.title()} Camera):",
                                          font=("Arial", 10, "bold"))
        widgets['header_label'].pack(anchor="w")
        
        # Calibration info section
        calib_frame = ttk.Frame(parent)
        calib_frame.pack(fill="x", pady=1)
        
        if camera_name == "top":
            calib_text = f"Distance: {TOP_CAMERA_DISTANCE_CM}cm, Factor: {TOP_CAMERA_PIXEL_TO_MM:.3f}mm/px"
        else:
            calib_text = f"Distance: {BOTTOM_CAMERA_DISTANCE_CM}cm, Factor: {BOTTOM_CAMERA_PIXEL_TO_MM:.3f}mm/px"
        
        widgets['calibration_label'] = ttk.Label(calib_frame, text=calib_text, font=self.font_small)
        widgets['calibration_label'].pack(anchor="w")
        
        widgets['wood_height_label'] = ttk.Label(calib_frame,
                                              text=f"Wood Height: {WOOD_PALLET_WIDTH_MM}mm",
                                              font=self.font_small)
        widgets['wood_width_label'].pack(anchor="w")
        
        # Separator
        separator1 = ttk.Separator(parent, orient="horizontal")
        separator1.pack(fill="x", pady=2)
        
        # Status section
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=2)
        
        widgets['status_label'] = ttk.Label(status_frame, 
                                          text="Status: Waiting for detection...",
                                          font=self.font_small, foreground="blue")
        widgets['status_label'].pack(anchor="w")
        
        widgets['defect_count_label'] = ttk.Label(status_frame, 
                                                text="No wood or defects detected",
                                                font=self.font_small)
        widgets['defect_count_label'].pack(anchor="w")
        
        # Defects container frame (will hold individual defect widgets)
        widgets['defects_container'] = ttk.Frame(parent)
        widgets['defects_container'].pack(fill="both", expand=True, pady=2)
        
        # Separator
        separator2 = ttk.Separator(parent, orient="horizontal")
        separator2.pack(fill="x", pady=2)
        
        # Grade summary section
        grade_frame = ttk.Frame(parent)
        grade_frame.pack(fill="x", pady=2)
        
        widgets['grade_label'] = ttk.Label(grade_frame, 
                                         text="Final Surface Grade: No detection",
                                         font=("Arial", 9, "bold"))
        widgets['grade_label'].pack(anchor="w")
        
        widgets['reasoning_label'] = ttk.Label(grade_frame, 
                                             text="Ready to analyze: Sound Knots, Unsound Knots",
                                             font=self.font_small, foreground="gray")
        widgets['reasoning_label'].pack(anchor="w")
        
    def create_tabbed_detection_details(self, parent, camera_name):
        """Create a tabbed interface for detection details - better for real-time updates"""
        notebook = ttk.Notebook(parent)
        
        # Tab 1: Current Detection
        current_tab = ttk.Frame(notebook)
        notebook.add(current_tab, text="Current")
        
        # Tab 2: Statistics
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="Statistics")
        
        # Tab 3: History (last 5 detections)
        history_tab = ttk.Frame(notebook)
        notebook.add(history_tab, text="History")
        
        notebook.pack(fill="both", expand=True)
        
        # Create widgets for each tab
        current_widgets = self.create_current_detection_widgets(current_tab, camera_name)
        stats_widgets = self.create_stats_widgets(stats_tab, camera_name)
        history_widgets = self.create_history_widgets(history_tab, camera_name)
        
        return {
            'notebook': notebook,
            'current': current_widgets,
            'stats': stats_widgets,
            'history': history_widgets
        }

    def create_current_detection_widgets(self, parent, camera_name):
        """Create widgets for current detection - fixed layout, no scrolling"""
        widgets = {}
        
        # Header with camera info
        header_frame = ttk.LabelFrame(parent, text=f"{camera_name.title()} Camera - Current Detection", padding="5")
        header_frame.pack(fill="x", pady=2)
        
        # Status display (always visible)
        widgets['status_label'] = ttk.Label(header_frame, text="Status: Waiting...", 
                                          font=("Arial", 10, "bold"), foreground="blue")
        widgets['status_label'].pack(anchor="w")
        
        # Quick summary (defect count, grade)
        summary_frame = ttk.Frame(header_frame)
        summary_frame.pack(fill="x", pady=2)
        
        widgets['defect_count'] = ttk.Label(summary_frame, text="Defects: 0", font=("Arial", 9))
        widgets['defect_count'].pack(side="left")
        
        widgets['grade_display'] = ttk.Label(summary_frame, text="Grade: No detection", 
                                           font=("Arial", 9, "bold"))
        widgets['grade_display'].pack(side="right")
        
        # Most significant defect display (only show worst one)
        defect_frame = ttk.LabelFrame(parent, text="Most Significant Defect", padding="5")
        defect_frame.pack(fill="both", expand=True, pady=2)
        
        widgets['main_defect_type'] = ttk.Label(defect_frame, text="None", font=("Arial", 10))
        widgets['main_defect_type'].pack(anchor="w")
        
        widgets['main_defect_size'] = ttk.Label(defect_frame, text="", font=("Arial", 9))
        widgets['main_defect_size'].pack(anchor="w")
        
        widgets['main_defect_grade'] = ttk.Label(defect_frame, text="", font=("Arial", 9))
        widgets['main_defect_grade'].pack(anchor="w")
        
        return widgets

    def create_grid_detection_display(self, parent, camera_name):
        """Create a fixed grid layout for detection display - no scrolling needed"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure grid weights
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=0)  # Status row
        main_frame.grid_rowconfigure(1, weight=1)  # Content row
        
        widgets = {}
        
        # Row 0: Status Bar (always visible)
        status_frame = ttk.Frame(main_frame, relief="sunken", borderwidth=1)
        status_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        
        widgets['status_bar'] = ttk.Label(status_frame, 
                                        text=f"{camera_name.title()}: Waiting for detection...",
                                        font=("Arial", 9, "bold"), background="lightgray")
        widgets['status_bar'].pack(fill="x", padx=5, pady=2)
        
        # Row 1, Col 0: Current Detection Info
        detection_frame = ttk.LabelFrame(main_frame, text="Current Detection", padding="5")
        detection_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 2))
        
        widgets['defect_count_label'] = ttk.Label(detection_frame, text="Defects: 0", font=("Arial", 10))
        widgets['defect_count_label'].pack(anchor="w", pady=1)
        
        widgets['worst_defect_label'] = ttk.Label(detection_frame, text="Worst: None", font=("Arial", 9))
        widgets['worst_defect_label'].pack(anchor="w", pady=1)
        
        widgets['grade_label'] = ttk.Label(detection_frame, text="Grade: No detection", 
                                         font=("Arial", 10, "bold"))
        widgets['grade_label'].pack(anchor="w", pady=1)
        
        # Row 1, Col 1: Camera Calibration (static info)
        calib_frame = ttk.LabelFrame(main_frame, text="Camera Info", padding="5")
        calib_frame.grid(row=1, column=1, sticky="nsew", padx=(2, 0))
        
        if camera_name == "top":
            calib_text = f"Distance: {TOP_CAMERA_DISTANCE_CM}cm\nFactor: {TOP_CAMERA_PIXEL_TO_MM:.3f}mm/px"
        else:
            calib_text = f"Distance: {BOTTOM_CAMERA_DISTANCE_CM}cm\nFactor: {BOTTOM_CAMERA_PIXEL_TO_MM:.3f}mm/px"
        
        calib_label = ttk.Label(calib_frame, text=calib_text, font=("Arial", 9))
        calib_label.pack(anchor="w")
        
        wood_label = ttk.Label(calib_frame, text=f"Wood Height: {WOOD_PALLET_WIDTH_MM}mm",
                             font=("Arial", 9))
        wood_label.pack(anchor="w", pady=(5, 0))
        
        standard_label = ttk.Label(calib_frame, text="Standard: SS-EN 1611-1", 
                                 font=("Arial", 9), foreground="blue")
        standard_label.pack(anchor="w", pady=(5, 0))
        
        return widgets

    def create_simple_detection_tracker(self, camera_name):
        """Create a simplified detection tracker that retains all logic but without complex UI"""
        # This maintains the detection tracking logic without the complex UI components
        # The actual detection data is still processed and logged as before
        tracker = {
            'camera_name': camera_name,
            'last_detection_time': None,
            'current_defects': {},
            'current_measurements': [],
            'surface_grade': None,
            'detection_active': False
        }
        return tracker

    def update_dashboard_display(self, camera_name, defect_dict, measurements=None):
        """Update simplified dashboard display and log detailed defect data"""
        # Update the simple tracker
        tracker = getattr(self, f'{camera_name}_dashboard_widgets', None)
        if tracker:
            tracker['current_defects'] = defect_dict.copy() if defect_dict else {}
            tracker['current_measurements'] = measurements.copy() if measurements else []
            tracker['detection_active'] = bool(defect_dict and measurements)
            tracker['last_detection_time'] = time.time() if defect_dict else None
            
            if measurements and defect_dict:
                tracker['surface_grade'] = self.determine_surface_grade(measurements, camera_name=camera_name)
        
        # Continue with the existing detailed logging logic (this is retained)
        if measurements and defect_dict:
            surface_grade = self.determine_surface_grade(measurements, camera_name=camera_name)
            surface_grade = self.determine_surface_grade(measurements)
            self.log_detection_details(camera_name, defect_dict, measurements, surface_grade)

    def create_dashboard_detection_display(self, parent, camera_name):
        """Compatibility method - creates the simple tracker"""
        return self.create_simple_detection_tracker(camera_name)

    def log_detection_details(self, camera_name, defect_dict, measurements, surface_grade):
        """Log detailed defect information for documentation and analysis"""
        import datetime
        import json
        
        # Create detection entry
        detection_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "camera": camera_name,
            "piece_number": getattr(self, 'piece_counter', 0),
            "test_case": getattr(self, 'current_test_case', 'N/A'),
            "total_defects": len(measurements),
            "final_grade": surface_grade,
            "defects": []
        }
        
        # Add camera calibration info
        detection_entry["camera_info"] = {
            "distance_cm": TOP_CAMERA_DISTANCE_CM if camera_name == "top" else BOTTOM_CAMERA_DISTANCE_CM,
            "pixel_to_mm": TOP_CAMERA_PIXEL_TO_MM if camera_name == "top" else BOTTOM_CAMERA_PIXEL_TO_MM,
            "wood_height_mm": WOOD_PALLET_WIDTH_MM
        }
        
        # Add individual defect details
        for i, (defect_type, size_mm, percentage) in enumerate(measurements, 1):
            individual_grade = self.get_individual_knot_grade(defect_type, size_mm, WOOD_PALLET_WIDTH_MM)
            
            defect_detail = {
                "defect_id": i,
                "type": defect_type,
                "size_mm": round(size_mm, 2),
                "percentage_of_width": round(percentage, 2),
                "individual_grade": individual_grade,
                "grading_standard": "SS-EN 1611-1"
            }
            
            # Add threshold information for new grading system
            constants = GRADING_CONSTANTS.get(defect_type, {})
            defect_detail["applied_threshold"] = f"Limit = (0.10 * {WOOD_PALLET_WIDTH_MM}mm) + constant"
            defect_detail["threshold_grade"] = individual_grade
            
            detection_entry["defects"].append(defect_detail)
        
        # Add grading reasoning
        total_defects = len(measurements)
        if total_defects > 6:
            detection_entry["grading_reason"] = "More than 6 defects detected - Automatic G2-4 (SS-EN 1611-1)"
        elif total_defects > 4:
            detection_entry["grading_reason"] = "More than 4 defects detected - Maximum G2-3 (SS-EN 1611-1)"
        elif total_defects > 2:
            detection_entry["grading_reason"] = "More than 2 defects detected - Maximum G2-2 (SS-EN 1611-1)"
        else:
            detection_entry["grading_reason"] = "≤2 defects detected - Based on individual grades (SS-EN 1611-1)"
        
        # Store in detection log
        self.detection_log.append(detection_entry)
        
        # Save to file for documentation
        self.save_detection_log(detection_entry)
        
        # Update piece counter
        self.piece_counter += 1

    def save_detection_log(self, detection_entry):
        """Save detection log entry to file for test case documentation"""
        import json
        import os
        from datetime import datetime, timedelta
        
        # Create logs directory if it doesn't exist
        log_dir = "detection_logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create filename with date
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"detection_log_{date_str}.json")
        
        # Load existing log or create new one
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    log_data = json.load(f)
            except:
                log_data = {"detections": []}
        else:
            log_data = {"detections": []}
        
        # Add new detection
        log_data["detections"].append(detection_entry)
        
        # Save updated log
        try:
            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            print(f"Failed to save detection log: {e}")

    def start_test_case(self, test_case_number):
        """Start a new test case for documentation"""
        self.test_case_counter = test_case_number
        self.current_test_case = f"TEST_CASE_{test_case_number:02d}"
        self.piece_counter = 0
        print(f"Started {self.current_test_case}")

    def export_test_case_summary(self, test_case_number):
        """Export summary of a specific test case for documentation"""
        import json
        from datetime import datetime, timedelta
        
        # Filter detections for this test case
        test_case_name = f"TEST_CASE_{test_case_number:02d}"
        test_detections = [d for d in self.detection_log if d.get("test_case") == test_case_name]
        
        if not test_detections:
            print(f"No detections found for {test_case_name}")
            return
        
        # Create summary
        summary = {
            "test_case": test_case_name,
            "export_timestamp": datetime.now().isoformat(),
            "total_pieces": len(test_detections),
            "grade_distribution": {},
            "defect_statistics": {},
            "camera_performance": {"top": 0, "bottom": 0},
            "detections": test_detections
        }
        
        # Calculate statistics
        for detection in test_detections:
            # Grade distribution
            grade = detection["final_grade"]
            summary["grade_distribution"][grade] = summary["grade_distribution"].get(grade, 0) + 1
            
            # Camera performance
            camera = detection["camera"]
            summary["camera_performance"][camera] += 1
            
            # Defect statistics
            for defect in detection["defects"]:
                defect_type = defect["type"]
                summary["defect_statistics"][defect_type] = summary["defect_statistics"].get(defect_type, 0) + 1
        
        # Save summary
        summary_file = f"TEST_CASE_{test_case_number:02d}_Summary.json"
        try:
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            print(f"Test case summary exported to {summary_file}")
        except Exception as e:
            print(f"Failed to export summary: {e}")

    def update_detection_details_widgets(self, camera_name, defect_dict, measurements=None):
        """Update detection details using widget objects instead of text replacement"""
        
        # Check if user is currently scrolling - if so, don't update
        if self._user_scrolling.get(camera_name, False):
            return
        
        # Get the widgets for this camera
        if camera_name == "top":
            widgets = getattr(self, 'top_details_widgets', None)
        elif camera_name == "bottom":
            widgets = getattr(self, 'bottom_details_widgets', None)
        else:
            return
            
        if not widgets:
            return
        
        # Update status and defect count
        if defect_dict and measurements:
            total_defects = len(measurements)
            widgets['status_label'].config(text="Status: Active detection", foreground="green")
            widgets['defect_count_label'].config(text=f"Defects detected: {total_defects}")
            
            # Clear previous defect widgets
            for widget in widgets['defects_container'].winfo_children():
                widget.destroy()
            
            # Create individual defect widgets
            for i, (defect_type, size_mm, percentage) in enumerate(measurements, 1):
                defect_frame = ttk.LabelFrame(widgets['defects_container'], 
                                            text=f"Defect {i}: {defect_type.replace('_', ' ')}", 
                                            padding="3")
                defect_frame.pack(fill="x", pady=1)
                
                # Defect details
                individual_grade = self.get_individual_knot_grade(defect_type, size_mm, WOOD_PALLET_WIDTH_MM)
                
                size_label = ttk.Label(defect_frame, 
                                     text=f"Size: {size_mm:.1f}mm ({percentage:.1f}% of width)",
                                     font=self.font_small)
                size_label.pack(anchor="w")
                
                grade_color = self.get_grade_color(individual_grade)
                grade_label = ttk.Label(defect_frame, 
                                      text=f"Individual Grade: {individual_grade}",
                                      font=self.font_small, foreground=grade_color)
                grade_label.pack(anchor="w")
                
                # Show threshold info for new grading system
                constants = GRADING_CONSTANTS.get(defect_type, {})
                limit = (0.10 * WOOD_PALLET_WIDTH_MM) + constants.get(individual_grade, 0)
                threshold_text = f"Threshold: ≤{limit:.1f}mm (0.10*{WOOD_PALLET_WIDTH_MM} + {constants.get(individual_grade, 0)})"
                
                threshold_label = ttk.Label(defect_frame, text=threshold_text, 
                                          font=self.font_small, foreground="gray")
                threshold_label.pack(anchor="w")
            
            # Update final grade
            surface_grade = self.determine_surface_grade(measurements)
            grade_color = self.get_grade_color(surface_grade)
            widgets['grade_label'].config(text=f"Final Surface Grade: {surface_grade}", 
                                        foreground=grade_color)
            
            # Update reasoning
            if total_defects > 6:
                reasoning_text = "Reasoning: >6 defects = Automatic G2-4 (SS-EN 1611-1)"
            elif total_defects > 4:
                reasoning_text = "Reasoning: >4 defects = Maximum G2-3 (SS-EN 1611-1)"
            elif total_defects > 2:
                reasoning_text = "Reasoning: >2 defects = Maximum G2-2 (SS-EN 1611-1)"
            else:
                reasoning_text = "Reasoning: ≤2 defects = Use individual grades (SS-EN 1611-1)"
            
            widgets['reasoning_label'].config(text=reasoning_text, foreground="black")
            
        elif defect_dict:
            # Simple detection mode
            total_defects = sum(defect_dict.values())
            widgets['status_label'].config(text="Status: Simple detection mode", foreground="orange")
            widgets['defect_count_label'].config(text=f"Total defects: {total_defects}")
            
            # Clear previous defect widgets
            for widget in widgets['defects_container'].winfo_children():
                widget.destroy()
            
            # Show simple defect counts
            sorted_defects = sorted(defect_dict.items(), key=lambda x: x[1], reverse=True)
            for defect_type, count in sorted_defects:
                defect_frame = ttk.Frame(widgets['defects_container'])
                defect_frame.pack(fill="x", pady=1)
                
                formatted_name = defect_type.replace('_', ' ').title()
                defect_label = ttk.Label(defect_frame, 
                                       text=f"• {formatted_name}: {count} detected",
                                       font=self.font_small)
                defect_label.pack(anchor="w")
            
            widgets['grade_label'].config(text="Final Surface Grade: Simple mode (no size data)", 
                                        foreground="gray")
            widgets['reasoning_label'].config(text="Note: Size measurements not available in simple mode", 
                                            foreground="gray")
        else:
            # No detection
            widgets['status_label'].config(text="Status: Waiting for detection...", foreground="blue")
            widgets['defect_count_label'].config(text="No wood or defects detected")
            
            # Clear defect widgets
            for widget in widgets['defects_container'].winfo_children():
                widget.destroy()
            
            widgets['grade_label'].config(text="Final Surface Grade: No detection", foreground="gray")
            widgets['reasoning_label'].config(text="Ready to analyze: Sound Knots, Unsound Knots", 
                                            foreground="gray")

    def update_feeds(self):
        # Skip updating live feeds if we're displaying processed frames
        if self.displaying_processed_frame:
            # Schedule next update and return early
            self.after(33, self.update_feeds)
            return
            
        self.update_single_feed(self.cap_top, self.top_canvas, "top")
        self.update_single_feed(self.cap_bottom, self.bottom_canvas, "bottom")

        # Reduce update frequency for non-critical components to prevent UI lag
        # Only update every 20th frame (~1.5 FPS for dashboard updates) to reduce load
        if not hasattr(self, '_frame_counter'):
            self._frame_counter = 0

        self._frame_counter += 1
        if self._frame_counter % 20 == 0:
            # Check camera status and reconnect if needed (skip during cooldown after mode changes)
            # Also skip during grace period after recent reconnection
            current_time = time.time()
            
            # Check if we're in grace period after reconnection
            in_grace_period = False
            if hasattr(self, 'camera_reconnection_grace_start'):
                grace_elapsed = current_time - self.camera_reconnection_grace_start
                if grace_elapsed < self.camera_reconnection_grace_period:
                    in_grace_period = True
            
            if current_time > self._camera_check_cooldown and not in_grace_period:
                camera_status = self.camera_handler.check_camera_status()
                if not camera_status['both_ok']:
                    print("Camera status check failed - attempting reconnection...")
                    if not self.camera_disconnected_popup_shown:
                        self.show_toast_notification(
                            "⚠️ Camera Disconnection",
                            "Camera disconnection detected.\nAttempting automatic reconnection...",
                            duration=5000,
                            type="warning"
                        )
                        self.camera_disconnected_popup_shown = True
                    if self.camera_handler.reassign_cameras_runtime():
                        # Update the cap references after successful reconnection
                        self.cap_top = self.camera_handler.top_camera
                        self.cap_bottom = self.camera_handler.bottom_camera
                        print("Camera reconnection successful during runtime")
                        self.show_toast_notification(
                            "✅ Camera Reconnection",
                            "Cameras reconnected successfully.",
                            duration=5000,
                            type="success"
                        )
                        self.camera_disconnected_popup_shown = False
                        if hasattr(self, 'status_label'):
                            # status_label is a Text widget, not a Label widget
                            self.status_label.config(state=tk.NORMAL)
                            self.status_label.delete(1.0, tk.END)
                            self.status_label.insert(1.0, "Status: Cameras reconnected")
                            self.status_label.config(foreground="green", state=tk.DISABLED)
                    else:
                        print("Camera reconnection failed during runtime")
                        if hasattr(self, 'status_label'):
                            # status_label is a Text widget, not a Label widget
                            self.status_label.config(state=tk.NORMAL)
                            self.status_label.delete(1.0, tk.END)
                            self.status_label.insert(1.0, "Status: Camera reconnection failed")
                            self.status_label.config(foreground="red", state=tk.DISABLED)

            # Update detection status
            self.update_detection_status_display()

            # Monitor camera connectivity for automatic reconnection
            self.monitor_camera_connectivity()

            # Only update details if not in active inference to prevent interference
            if not getattr(self, '_in_active_inference', False):
                self.ensure_detection_details_updated()

        # Optimize for smoother display - update every 33ms for ~30 FPS (more realistic for camera feeds)
        self.after(33, self.update_feeds)
        
        # Start system health monitoring
        self.start_health_monitoring()

    def ensure_detection_details_updated(self):
        """Ensure detection details are showing current state, even when not actively detecting"""
        # Update detection details for both cameras using dashboard approach
        for camera_name in ["top", "bottom"]:
            # If automatic detection is off, make sure we show the waiting state
            if not self.auto_detection_active:
                self.update_dashboard_display(camera_name, {}, [])
            # If automatic detection is on but no recent detections, also update to show waiting state
            elif not hasattr(self, 'live_detections') or not self.live_detections.get(camera_name):
                self.update_dashboard_display(camera_name, {}, [])
        
        # Also update the live grading display and statistics
        self.update_live_grading_display()
        self.update_detailed_statistics()

    def update_detection_status_display(self):
        """Update status display based on current detection state"""
        if hasattr(self, 'status_label'):
            # Helper function to update Text widget properly
            def update_status_text(text, foreground="black"):
                self.status_label.config(state=tk.NORMAL)
                self.status_label.delete(1.0, tk.END)
                self.status_label.insert(1.0, text)
                if foreground != "black":
                    self.status_label.config(foreground=foreground)
                self.status_label.config(state=tk.DISABLED)

            if self.auto_detection_active:
                total_detections = (len(self.detection_session_data["total_detections"]["top"]) +
                                  len(self.detection_session_data["total_detections"]["bottom"]))
                update_status_text(f"Status: AUTO (IR) DETECTION ACTIVE 🔍 ({total_detections} detections)", "orange")
            elif self.live_detection_var.get():
                update_status_text(f"Status: {self.current_mode} MODE - Live Detection ACTIVE", "blue")
            elif self.current_mode == "IDLE":
                update_status_text("Status: IDLE MODE - System disabled, no operations", "gray")
            elif self.current_mode == "TRIGGER":
                update_status_text("Status: TRIGGER MODE - Waiting for IR beam trigger", "green")
            elif self.current_mode == "CONTINUOUS":
                update_status_text("Status: CONTINUOUS MODE - Live detection enabled", "blue")
            else:
                # Fallback for unknown states
                update_status_text(f"Status: {self.current_mode} MODE - Ready", "green")

    def toggle_live_detection_mode(self):
        """Handle toggling between IR trigger and live detection modes."""
        # Clear wood detection results when toggling live detection off
        if not self.live_detection_var.get():
            self.wood_detection_results = {"top": None, "bottom": None}
            self.dynamic_roi = {}
        self.update_detection_status_display()

    def toggle_roi(self):
        """Toggle ROI for top camera"""
        self.roi_enabled["top"] = self.roi_var.get()
        status = "enabled" if self.roi_enabled["top"] else "disabled"
        print(f"ROI for top camera {status}")

    def toggle_bottom_roi(self):
        """Toggle ROI for bottom camera"""
        self.roi_enabled["bottom"] = self.bottom_roi_var.get()
        status = "enabled" if self.roi_enabled["bottom"] else "disabled"
        print(f"ROI for bottom camera {status}")

    def toggle_lane_roi(self):
        """Toggle lane ROI visibility for alignment detection"""
        self.roi_enabled["lane_alignment"] = self.lane_roi_var.get()
        status = "enabled" if self.roi_enabled["lane_alignment"] else "disabled"
        print(f"Lane ROI display {status}")

    def test_low_confidence_notification(self):
        """Test method to trigger low confidence notification (hidden button)"""
        print("\n" + "="*60)
        print("🧪 TEST: Low Confidence Notification Triggered")
        print("="*60)
        
        try:
            self.show_toast_notification(
                "⚠️ Low Confidence Detection",
                "Low confidence detections found.\nAI model detected objects with lower confidence levels.",
                duration=6000,
                type="warning"
            )
            print("✅ Low confidence notification displayed successfully")
        except Exception as e:
            print(f"❌ Error showing notification: {e}")
        
        print("="*60 + "\n")

    def show_alignment_warning(self, camera_name, lane_type):
        """
        Show notification warning when wood touches alignment lanes.
        Uses cooldown to prevent notification spam.
        
        Args:
            camera_name: "top" or "bottom"
            lane_type: "TOP" or "BOTTOM" lane
        """
        print(f"[DEBUG] show_alignment_warning called: camera={camera_name}, lane={lane_type}")
        
        current_time = time.time()
        warning_state = self.alignment_warnings[camera_name]
        
        # Check if we're in cooldown period
        time_since_last = current_time - warning_state["last_warning_time"]
        if time_since_last < warning_state["warning_cooldown"]:
            print(f"[DEBUG] In cooldown: {time_since_last:.1f}s < {warning_state['warning_cooldown']}s")
            return  # Skip notification during cooldown
        
        # Check if this is a new warning (different from current)
        warning_key = f"{lane_type}_LANE"
        if warning_state["current_warning"] == warning_key:
            print(f"[DEBUG] Duplicate warning: {warning_key} already active")
            return  # Same warning still active
        
        print(f"[DEBUG] Showing new warning: {warning_key}")
        
        # Update warning state
        warning_state["last_warning_time"] = current_time
        warning_state["current_warning"] = warning_key
        
        # Show notification popup
        warning_title = "⚠ WOOD MISALIGNMENT DETECTED"
        warning_message = "The wood is misaligned."
        
        # Use message queue to show popup from main thread
        print(f"[DEBUG] Putting warning message into queue...")
        self.message_queue.put(("warning", warning_title, warning_message))
        print(f"[DEBUG] Warning message queued successfully")
        
        # Also log to console
        from datetime import datetime as dt
        print(f"\n{'='*60}")
        print(f"⚠ ALIGNMENT WARNING - {camera_name.upper()} CAMERA")
        print(f"{'='*60}")
        print(f"Lane: {lane_type} LANE")
        print(f"Coordinate: y = {100 if lane_type == 'TOP' else 620} pixels")
        print(f"Timestamp: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
    
    def clear_alignment_warning(self, camera_name):
        """Clear current alignment warning for a camera"""
        self.alignment_warnings[camera_name]["current_warning"] = None

    def start_automatic_detection(self):
        """Start automatic detection when IR beam detects object"""
        self.auto_detection_active = True
        self._in_active_inference = True  # Flag to prevent UI conflicts during inference
        self.detection_session_data = {
            "start_time": datetime.now(),
            "end_time": None,
            "total_detections": {"top": [], "bottom": []},
            "best_frames": {"top": None, "bottom": None},
            "final_grade": None
        }
        self.detection_frames = []


        # Clear trackers for new session
        self.trackers["top"].clear()
        self.trackers["bottom"].clear()

        # Clear session detections for new piece
        self.session_detections = {"top": [], "bottom": []}
        self.final_deduplicated_defects = {"top": [], "bottom": []}

        # Clear previous live detections
        self.live_detections = {"top": {}, "bottom": {}}
        self.live_grades = {"top": "Detecting...", "bottom": "Detecting..."}

        # Reset wood detection reporting flags for new session
        self._wood_reported = {'top': False, 'bottom': False}

        print("🔍 Automatic detection STARTED - Object detected by IR beam")
        print("🎯 Custom object trackers initialized for unique defect counting")
        self.log_action("Automatic detection started - IR beam triggered")

    def stop_automatic_detection_and_grade(self):
        """Stop automatic detection and send grade when object clears IR beam"""
        if not self.auto_detection_active:
            return

        self.auto_detection_active = False
        self._in_active_inference = False  # Clear inference flag to resume normal UI updates
        self.detection_session_data["end_time"] = datetime.now()

        # Collect ALL detections from the entire session (every frame during the detection period)
        all_measurements = []
        top_measurements = []
        bottom_measurements = []

        # Process all detections from top camera session data
        for detection_entry in self.detection_session_data["total_detections"]["top"]:
            measurements = detection_entry.get("measurements", [])
            for measurement in measurements:
                top_measurements.append(measurement)
                all_measurements.append(measurement)

        # Process all detections from bottom camera session data
        for detection_entry in self.detection_session_data["total_detections"]["bottom"]:
            measurements = detection_entry.get("measurements", [])
            for measurement in measurements:
                bottom_measurements.append(measurement)
                all_measurements.append(measurement)

        # STEP 4 & 5: List all Wood and Defect Details and Grade the wood based on the list and logic of the grading system
        print("\n" + "="*80)
        print("FINAL WOOD AND DEFECT ANALYSIS REPORT")
        print("="*80)

        # Report wood detection results
        print("\nWOOD DETECTION SUMMARY:")
        print("-" * 40)
        if hasattr(self, 'wood_detection_results') and self.wood_detection_results:
            for camera_name in ["top", "bottom"]:
                if camera_name in self.wood_detection_results and self.wood_detection_results[camera_name]:
                    detection = self.wood_detection_results[camera_name]
                    if detection.get('wood_detected', False):
                        candidates = detection.get('wood_candidates', [])
                        confidence = detection.get('confidence', 0)
                        print(f"📷 {camera_name.upper()} CAMERA:")
                        print(f"   ✓ Wood detected (confidence: {confidence:.2f})")
                        print(f"   ✓ {len(candidates)} wood piece(s) found:")
                        for i, candidate in enumerate(candidates, 1):
                            bbox = candidate['bbox']
                            area = candidate['area']
                            conf = candidate['confidence']
                            print(f"      {i}. Position: {bbox}, Area: {area:.0f}px, Confidence: {conf:.2f}")
                    else:
                        print(f"📷 {camera_name.upper()} CAMERA:")
                        print("   ✗ No wood detected")
        else:
            print("   No wood detection data available")

        # Report defect detection results (ALL detections from session)
        print("\nDEFECT DETECTION SUMMARY:")
        print("-" * 40)
        print(f"🎯 TOP CAMERA: {len(top_measurements)} defect(s) detected across {len(self.detection_session_data['total_detections']['top'])} frames")
        for i, (defect_type, size_mm, percentage) in enumerate(top_measurements, 1):
            print(f"   {i}. {defect_type} - Size: {size_mm:.1f}mm")

        print(f"🎯 BOTTOM CAMERA: {len(bottom_measurements)} defect(s) detected across {len(self.detection_session_data['total_detections']['bottom'])} frames")
        for i, (defect_type, size_mm, percentage) in enumerate(bottom_measurements, 1):
            print(f"   {i}. {defect_type} - Size: {size_mm:.1f}mm")

        # Determine final grades from tracked objects with camera-specific wood widths
        final_top_grade = self.determine_surface_grade(top_measurements, camera_name="top")
        final_bottom_grade = self.determine_surface_grade(bottom_measurements, camera_name="bottom")

        # Combine grades for final decision
        combined_grade = self.determine_final_grade(final_top_grade, final_bottom_grade)
        self.detection_session_data["final_grade"] = combined_grade

        print("\nGRADING ANALYSIS:")
        print("-" * 40)
        print(f"📊 Top Surface Grade: {final_top_grade}")
        print(f"📊 Bottom Surface Grade: {final_bottom_grade}")
        print(f"🏆 Final Combined Grade: {combined_grade}")

        # Show grading reasoning
        print("\nGRADING REASONING:")
        print("-" * 40)
        total_defects = len(all_measurements)
        if total_defects > 6:
            print("Reasoning: More than 6 defects detected - Automatic G2-4 (SS-EN 1611-1)")
        elif total_defects > 4:
            print("Reasoning: More than 4 defects detected - Maximum G2-3 (SS-EN 1611-1)")
        elif total_defects > 2:
            print("Reasoning: More than 2 defects detected - Maximum G2-2 (SS-EN 1611-1)")
        else:
            print("Reasoning: Based on individual defect sizes (SS-EN 1611-1)")

        print("="*80 + "\n")

        # Log the final grading with tracked objects
        self.finalize_grading(combined_grade, all_measurements)

        # Update live grading display
        self.live_grades["top"] = final_top_grade
        self.live_grades["bottom"] = final_bottom_grade
        self.update_live_grading_display()

        # Clear trackers for next piece
        self.trackers["top"].clear()
        self.trackers["bottom"].clear()

        # Clear detection data for next piece
        self.detection_frames = []
        self.session_detections = {"top": [], "bottom": []}
        self.final_deduplicated_defects = {"top": [], "bottom": []}

        # Clear wood detection results for next piece
        self.wood_detection_results = {"top": None, "bottom": None}
        self.dynamic_roi = {}

    def determine_final_grade_from_session(self, camera_name, detections_list):
        """Determine final grade from all detections collected during session"""
        if not detections_list:
            return GRADE_G2_0 # No defects found, perfect grade

        # Combine all defect counts from the session
        all_measurements = [m for d in detections_list for m in d.get("measurements", [])]

        # Use sophisticated grading if measurements available with camera-specific wood width
        if all_measurements:
            return self.determine_surface_grade(all_measurements, camera_name=camera_name)
        else:
            # Fall back to simple grading if no measurements (should not happen in normal operation)
            combined_defects = {}
            for detection_data in detections_list:
                defect_dict = detection_data.get("defects", {})
                for defect_type, count in defect_dict.items():
                    combined_defects[defect_type] = combined_defects.get(defect_type, 0) + count

            grade_info = self.calculate_grade(combined_defects)
            # Map numeric grade back to standard grade text
            grade_map = {0: GRADE_G2_0, 1: GRADE_G2_0, 2: GRADE_G2_2, 3: GRADE_G2_4}
            return grade_map.get(grade_info.get('grade'), GRADE_G2_4)

    def save_detection_session(self):
        """Save the complete detection session data"""
        session_data = {
            "session_id": f"AUTO_{int(time.time())}",
            "timestamp": self.detection_session_data["start_time"].isoformat(),
            "duration_seconds": (self.detection_session_data["end_time"] - self.detection_session_data["start_time"]).total_seconds(),
            "detection_data": self.detection_session_data,
            "total_frames_captured": len(self.detection_frames),
            "trigger_method": "IR_BEAM_AUTOMATIC"
        }
        
        # Save to JSON log
        self.save_detection_log(session_data)
        
        # Save best frames as images if available
        if self.detection_session_data["best_frames"]["top"] is not None:
            self.save_detection_frame("top", self.detection_session_data["best_frames"]["top"])
        if self.detection_session_data["best_frames"]["bottom"] is not None:
            self.save_detection_frame("bottom", self.detection_session_data["best_frames"]["bottom"])

    def save_detection_frame(self, camera_name, frame):
        """Save a detection frame as image file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"detection_{camera_name}_{timestamp}.jpg"
            filepath = os.path.join("detection_frames", filename)
            
            # Create directory if it doesn't exist
            os.makedirs("detection_frames", exist_ok=True)
            
            # Convert from RGB back to BGR for OpenCV
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            else:
                frame_bgr = frame
            
            cv2.imwrite(filepath, frame_bgr)
            print(f"📸 Saved detection frame: {filepath}")
            
        except Exception as e:
            print(f"❌ Error saving detection frame: {e}")


    def apply_roi(self, frame, camera_name, custom_roi_coords=None):
        """Apply Region of Interest (ROI) to frame for focused detection"""
        # Use custom ROI if provided, otherwise check if ROI is enabled
        if custom_roi_coords:
            roi_coords = custom_roi_coords
        elif not self.roi_enabled.get(camera_name, False):
            return frame, None
        else:
            roi_coords = self.roi_coordinates.get(camera_name, {})

        if not roi_coords:
            return frame, None

        x1, y1 = roi_coords.get("x1", 0), roi_coords.get("y1", 0)
        x2, y2 = roi_coords.get("x2", frame.shape[1]), roi_coords.get("y2", frame.shape[0])

        # Ensure coordinates are within frame bounds
        x1 = max(0, min(x1, frame.shape[1]))
        y1 = max(0, min(y1, frame.shape[0]))
        x2 = max(x1, min(x2, frame.shape[1]))
        y2 = max(y1, min(y2, frame.shape[0]))

        # Extract ROI
        roi_frame = frame[y1:y2, x1:x2]
        roi_info = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}

        return roi_frame, roi_info

    def draw_roi_overlay(self, frame, camera_name):
        """Draw ROI rectangle overlay on frame for visualization"""
        if not self.roi_enabled.get(camera_name, False):
            return frame

        roi_coords = self.roi_coordinates.get(camera_name, {})
        if not roi_coords:
            return frame

        frame_copy = frame.copy()
        x1, y1 = roi_coords.get("x1", 0), roi_coords.get("y1", 0)
        x2, y2 = roi_coords.get("x2", frame.shape[1]), roi_coords.get("y2", frame.shape[0])

        # Ensure coordinates are within frame bounds
        x1 = max(0, min(x1, frame.shape[1]))
        y1 = max(0, min(y1, frame.shape[0]))
        x2 = max(x1, min(x2, frame.shape[1]))
        y2 = max(y1, min(y2, frame.shape[0]))

        # Draw ROI rectangle (yellow border)
        cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 255), 3)

        # Add ROI label
        # cv2.putText(frame_copy, f"ROI - {camera_name.upper()}",
        #           (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        return frame_copy

    def bbox_intersects_roi(self, bbox, camera_name):
        """Check if bounding box intersects with ROI"""
        if not self.roi_enabled.get(camera_name, False):
            return True  # No ROI means all detections count

        # Scale bbox from model coordinates (640x640) to original frame coordinates (1280x720)
        x1, y1, x2, y2 = bbox[:4]
        scale_x = 1280.0 / 640.0  # Original width / model width
        scale_y = 720.0 / 640.0   # Original height / model height

        x1_orig = x1 * scale_x
        y1_orig = y1 * scale_y
        x2_orig = x2 * scale_x
        y2_orig = y2 * scale_y

        roi_coords = self.roi_coordinates.get(camera_name, {})
        roi_x1 = roi_coords.get("x1", 0)
        roi_y1 = roi_coords.get("y1", 0)
        roi_x2 = roi_coords.get("x2", 1280)
        roi_y2 = roi_coords.get("y2", 720)

        # Check for intersection between scaled bounding box and ROI
        return not (x2_orig < roi_x1 or x1_orig > roi_x2 or y2_orig < roi_y1 or y1_orig > roi_y2)

    def draw_wood_detection_overlay(self, frame, camera_name):
        """Draw wood detection results overlay on frame for visualization"""
        frame_copy = frame.copy()

        # Draw alignment lane ROIs (highway lane style) - horizontal lanes at top and bottom
        # ALWAYS show if Lane ROI checkbox is enabled (independent of Live Detection)
        if self.lane_roi_var.get() and camera_name in ALIGNMENT_LANE_ROIS:
            lane_rois = ALIGNMENT_LANE_ROIS[camera_name]
            
            # Create semi-transparent overlay for lanes
            overlay = frame_copy.copy()
            
            # Draw top lane with semi-transparent red fill
            top_lane = lane_rois['top_lane']
            cv2.rectangle(overlay, 
                         (top_lane['x1'], top_lane['y1']), 
                         (top_lane['x2'], top_lane['y2']), 
                         (0, 0, 255), -1)  # Filled rectangle
            
            # Draw bottom lane with semi-transparent red fill
            bottom_lane = lane_rois['bottom_lane']
            cv2.rectangle(overlay, 
                         (bottom_lane['x1'], bottom_lane['y1']), 
                         (bottom_lane['x2'], bottom_lane['y2']), 
                         (0, 0, 255), -1)  # Filled rectangle
            
            # Blend overlay with original frame (30% transparency)
            cv2.addWeighted(overlay, 0.3, frame_copy, 0.7, 0, frame_copy)
            
            # Draw lane borders (solid red lines)
            cv2.rectangle(frame_copy, 
                         (top_lane['x1'], top_lane['y1']), 
                         (top_lane['x2'], top_lane['y2']), 
                         (0, 0, 255), 3)  # Red border, 3px thick
            cv2.rectangle(frame_copy, 
                         (bottom_lane['x1'], bottom_lane['y1']), 
                         (bottom_lane['x2'], bottom_lane['y2']), 
                         (0, 0, 255), 3)  # Red border, 3px thick
            
            # Add lane labels (horizontal text)
            # Top lane label
            top_label_x = (top_lane['x1'] + top_lane['x2']) // 2 - 70
            top_label_y = (top_lane['y1'] + top_lane['y2']) // 2 + 10
            cv2.putText(frame_copy, "TOP LANE", 
                       (top_label_x, top_label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            # Bottom lane label
            bottom_label_x = (bottom_lane['x1'] + bottom_lane['x2']) // 2 - 90
            bottom_label_y = (bottom_lane['y1'] + bottom_lane['y2']) // 2 + 10
            cv2.putText(frame_copy, "BOTTOM LANE", 
                       (bottom_label_x, bottom_label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Check if we should show wood detection overlay
        # Lanes are ALWAYS visible when checkbox is checked (above code)
        # Wood detection overlay only shown when live detection is active or in scan mode
        if not self.live_detection_var.get() and self.current_mode != "SCAN_PHASE":
            # Return frame with lanes visible but without wood detection overlay
            return frame_copy

        # Check if we have wood detection results
        if hasattr(self, 'wood_detection_results') and self.wood_detection_results:
            detection_result = self.wood_detection_results.get(camera_name)

            if detection_result and detection_result.get('wood_detected', False):
                # Wood detected - draw detection results
                wood_candidates = detection_result.get('wood_candidates', [])
                for i, candidate in enumerate(wood_candidates):
                    x, y, w, h = candidate['bbox']
                    confidence = candidate['confidence']

                    # Draw bounding box (green for wood detection)
                    cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (0, 255, 0), 3)

                    # Add wood detection label with confidence
                    label = f"Wood {i+1}: {confidence:.2f}"
                    cv2.putText(frame_copy, label, (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                # Draw dynamic ROI if available
                if hasattr(self, 'dynamic_roi') and self.dynamic_roi and camera_name in self.dynamic_roi:
                    roi = self.dynamic_roi[camera_name]
                    if roi:
                        x, y, w, h = roi
                        
                        # Check if collision was detected in wood detection function
                        lane_collision = detection_result.get('lane_collision')
                        
                        if lane_collision:
                            # COLLISION DETECTED - Draw red warning overlay
                            warning_overlay = frame_copy.copy()
                            cv2.rectangle(warning_overlay, (x, y), (x + w, y + h), (0, 0, 255), -1)
                            cv2.addWeighted(warning_overlay, 0.3, frame_copy, 0.7, 0, frame_copy)
                            
                            # Draw red border
                            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (0, 0, 255), 3)
                            
                            # Add warning text
                            warning_text = f"⚠ MISALIGNED - {lane_collision} LANE"
                            cv2.putText(frame_copy, warning_text,
                                        (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        else:
                            # NO COLLISION - Draw normal blue AUTO ROI
                            cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (255, 0, 0), 2)
                            cv2.putText(frame_copy, "AUTO ROI",
                                        (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)



                # Add wood detection summary
                wood_count = detection_result.get('wood_count', 0)
                confidence = detection_result.get('confidence', 0.0)
                summary_text = f"Wood: {wood_count} detected (conf: {confidence:.2f})"
                cv2.putText(frame_copy, summary_text, (10, frame.shape[0] - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                # No wood detected - show clear message
                h, w = frame_copy.shape[:2]
                cv2.putText(frame_copy, "NO WOOD DETECTED", (w//2 - 150, h//2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        else:
            # No detection results yet - show waiting message
            h, w = frame_copy.shape[:2]
            cv2.putText(frame_copy, "INITIALIZING WOOD DETECTION", (w//2 - 180, h//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 165, 0), 2)
            cv2.putText(frame_copy, "Please wait...",
                        (w//2 - 60, h//2 + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)

        return frame_copy

    def update_single_feed(self, cap, label, camera_name):
        ret, frame = cap.read()
        if ret:
            # Mirror the bottom camera horizontally from the start for consistent perspective
            if camera_name == "bottom":
                frame = cv2.flip(frame, 1)  # Horizontal flip

            # Skip detection processing for smoother frame rate - only detect every 3rd frame
            if not hasattr(self, '_detection_frame_skip'):
                self._detection_frame_skip = {"top": 0, "bottom": 0}

            # Skip heavy detection processing to maintain smooth frame rate
            self._detection_frame_skip[camera_name] += 1
            should_run_detection = (self._detection_frame_skip[camera_name] % 3 == 0)

            # Initialize memory management counter
            if not hasattr(self, '_memory_cleanup_counter'):
                self._memory_cleanup_counter = 0

            # Perform memory cleanup every 150 frames (~15 seconds at 10 FPS) - less frequent
            self._memory_cleanup_counter += 1
            if self._memory_cleanup_counter % 150 == 0:
                import gc
                gc.collect()  # Force garbage collection
                
                # Clear cached dimensions periodically to handle window resizing
                if hasattr(self, '_label_dimensions'):
                    self._label_dimensions.clear()
                
                # Limit detection frames to prevent memory buildup
                if hasattr(self, 'detection_frames') and len(self.detection_frames) > 30:
                    # Keep only the most recent 30 frames
                    self.detection_frames = self.detection_frames[-30:]
                
                # Clear old PhotoImage references
                if hasattr(self, '_old_photos'):
                    if len(self._old_photos) > 20:  # Keep last 20 references
                        self._old_photos = self._old_photos[-20:]
                else:
                    self._old_photos = []
                    
                print(f"Memory cleanup performed at frame {self._memory_cleanup_counter} - Frames: {len(self.detection_frames) if hasattr(self, 'detection_frames') else 0}")
            
            # Process detection based on automatic IR beam OR live detection toggle
            should_detect = should_run_detection and (self.auto_detection_active or (self.live_detection_var.get() and self.current_mode != "TRIGGER"))
            
            # Check for error states that should prevent detection
            if self.error_state["system_paused"]:
                should_detect = False
                print("Detection disabled due to system pause")
            
            if self.error_state["manual_inspection_required"] and should_detect:
                print("Detection limited due to manual inspection requirement")
                # Allow detection but flag for manual review

            # For bottom camera, only detect if top camera detected wood (synchronized detection)
            # But wood detection is done per camera, so bottom camera can detect wood independently
            # Defect detection on bottom camera only happens if wood was detected on bottom camera

            # Only perform wood detection when detection is active (not in idle mode)
            if should_detect:
                try:
                    # Always use wood_detection ROI (Yellow ROI) for wood detection to maintain hierarchy
                    wood_roi_coords = self.roi_coordinates.get("wood_detection", {})
                    if wood_roi_coords and self.roi_enabled.get("wood_detection", True):
                        x1, y1 = wood_roi_coords.get("x1", 0), wood_roi_coords.get("y1", 0)
                        x2, y2 = wood_roi_coords.get("x2", frame.shape[1]), wood_roi_coords.get("y2", frame.shape[0])
                        cropped_frame = frame[y1:y2, x1:x2]
                        wood_detection = self.rgb_wood_detector.detect_wood_comprehensive(cropped_frame, camera=camera_name)
                        # Adjust auto_roi coordinates back to full frame
                        if wood_detection.get('auto_roi'):
                            ax, ay, aw, ah = wood_detection['auto_roi']
                            wood_detection['auto_roi'] = (x1 + ax, y1 + ay, aw, ah)
                    else:
                        # Fallback to full frame if wood_detection ROI not configured
                        wood_detection = self.rgb_wood_detector.detect_wood_comprehensive(frame, camera=camera_name)

                    # Store wood detection results for overlay display
                    self.wood_detection_results[camera_name] = wood_detection

                    # Check for wood lane alignment (highway lane style check)
                    self.check_wood_lane_alignment(camera_name)

                    # Store dynamic ROI for defect detection
                    self.dynamic_roi[camera_name] = wood_detection.get('auto_roi')

                    # Check if wood is detected (any candidates found)
                    wood_detected = wood_detection['wood_detected']

                    if wood_detected:
                        # The wood width is already updated by ColorWoodDetector.detect_wood_comprehensive()
                        # via update_wood_width_dynamic(), so we don't need to recalculate it here
                        
                        # STEP 4: List wood detection details (only once per camera per detection session in auto mode)
                        if self.auto_detection_active and (not hasattr(self, '_wood_reported') or not self._wood_reported.get(camera_name, False)):
                            if not hasattr(self, '_wood_reported'):
                                self._wood_reported = {'top': False, 'bottom': False}

                            candidates = wood_detection.get('wood_candidates', [])
                            print(f"🪵 {camera_name.upper()} CAMERA: {len(candidates)} wood pieces detected (confidence: {wood_detection.get('confidence', 0):.2f})")
                            for i, candidate in enumerate(candidates, 1):
                                bbox = candidate['bbox']
                                confidence = candidate['confidence']
                                area = candidate['area']
                                print(f"   {i}. Wood piece: {bbox} (confidence: {confidence:.2f}, area: {area:.0f}px)")

                            self._wood_reported[camera_name] = True
                    else:
                        # No wood detected - clear ROI and skip defect detection
                        self.dynamic_roi[camera_name] = None
                        if not hasattr(self, '_wood_reported'):
                            self._wood_reported = {'top': False, 'bottom': False}
                        self._wood_reported[camera_name] = False
                except Exception as e:
                    print(f"❌ Error in wood detection for {camera_name}: {e}")
                    self.dynamic_roi[camera_name] = None
                    # Clear wood detection results on error
                    self.wood_detection_results[camera_name] = None
            else:
                # When not detecting (idle mode), clear wood detection results and ROI
                self.dynamic_roi[camera_name] = None
                self.wood_detection_results[camera_name] = None

            # Only proceed with defect detection if wood was detected (for hierarchy)
            has_wood_detected = (hasattr(self, 'wood_detection_results') and
                                self.wood_detection_results.get(camera_name) and
                                self.wood_detection_results[camera_name].get('wood_detected', False))

            if should_detect and has_wood_detected:
                # STEP 3: Detect Defects only in the Green ROI (static camera ROI)
                # Use the static Green ROI for defect detection to maintain hierarchy
                detection_frame, roi_info = self.apply_roi(frame, camera_name)
                print(f"🎯 Using Green ROI for {camera_name} defect detection")

                # Pre-resize frame for faster processing if it's very large
                height, width = detection_frame.shape[:2]
                if width > 1280 or height > 720:
                    # Resize for detection processing to improve speed
                    scale_factor = min(1280/width, 720/height)
                    new_width = int(width * scale_factor)
                    new_height = int(height * scale_factor)
                    resized_frame = cv2.resize(detection_frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

                    # Run detection on resized ROI frame
                    result = self.analyze_frame(resized_frame, camera_name, run_defect_model=True)

                    # Scale detection results back to ROI size
                    if len(result) == 3:
                        annotated_frame, defect_dict, detections_for_grading = result
                        # Scale annotated frame back to ROI size
                        annotated_frame = cv2.resize(annotated_frame, (width, height), interpolation=cv2.INTER_LINEAR)
                    else:
                        annotated_frame, defect_dict = result
                        annotated_frame = cv2.resize(annotated_frame, (width, height), interpolation=cv2.INTER_LINEAR)
                        detections_for_grading = []
                else:
                    # ROI frame is already optimal size, process normally
                    result = self.analyze_frame(detection_frame, camera_name, run_defect_model=True)

                    # Handle both old and new return formats for compatibility
                    if len(result) == 3:
                        annotated_frame, defect_dict, detections_for_grading = result
                    else:
                        annotated_frame, defect_dict = result
                        detections_for_grading = []

                # If ROI was applied, place the annotated ROI back into the full frame
                if roi_info is not None:
                    full_frame_annotated = frame.copy()
                    full_frame_annotated[roi_info["y1"]:roi_info["y2"], roi_info["x1"]:roi_info["x2"]] = annotated_frame
                    # Add ROI overlay to show the detection area
                    annotated_frame = self.draw_roi_overlay(full_frame_annotated, camera_name)
                else:
                    # No ROI applied, use the annotated frame as is
                    pass

                # Add wood detection overlay if available
                annotated_frame = self.draw_wood_detection_overlay(annotated_frame, camera_name)

                # Store the detection results for automatic detection session
                self.live_detections[camera_name] = defect_dict

                # Store measurements for sophisticated grading
                if not hasattr(self, 'live_measurements'):
                    self.live_measurements = {"top": [], "bottom": []}
                self.live_measurements[camera_name] = detections_for_grading

                # During automatic detection, store frame for potential PDF report
                if self.auto_detection_active:
                    # Keep the original session data structure for compatibility
                    detection_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "camera": camera_name,
                        "defects": defect_dict.copy(),
                        "measurements": detections_for_grading.copy() if detections_for_grading else [],
                        "frame_captured": True
                    }

                    # Add to session data
                    self.detection_session_data["total_detections"][camera_name].append(detection_entry)

                    # Save best frame (frame with most detections or first significant detection)
                    if (self.detection_session_data["best_frames"][camera_name] is None or
                        sum(defect_dict.values()) > 0):
                        # Convert frame to RGB and resize for memory efficiency
                        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                        frame_rgb_resized = cv2.resize(frame_rgb, (640, 360), interpolation=cv2.INTER_LINEAR)
                        self.detection_session_data["best_frames"][camera_name] = frame_rgb_resized

                    # Store frame for potential PDF report with stricter memory limits
                    if len(self.detection_frames) < 20:  # Reduced from 50 to 20 frames to prevent memory issues
                        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                        # Resize frame before storing to save memory
                        frame_rgb_resized = cv2.resize(frame_rgb, (640, 360), interpolation=cv2.INTER_LINEAR)
                        self.detection_frames.append({
                            "camera": camera_name,
                            "timestamp": datetime.now().isoformat(),
                            "frame": frame_rgb_resized,  # Store smaller frame
                            "defects": defect_dict.copy()
                        })

                # Calculate grade for this camera using sophisticated grading with camera-specific wood width
                if detections_for_grading:
                    surface_grade = self.determine_surface_grade(detections_for_grading, camera_name=camera_name)
                    grade_info = {
                        'grade': surface_grade,
                        'text': f'{surface_grade} - SS-EN 1611-1 ({camera_name.title()} Camera)',
                        'total_defects': len(detections_for_grading),
                        'color': self.get_grade_color(surface_grade)
                    }
                else:
                    grade_info = self.calculate_grade(defect_dict)  # Fallback to simple grading

                self.live_grades[camera_name] = grade_info

                # Update dashboard every 10th frame for smoother updates (reduced frequency)
                if self._detection_frame_skip[camera_name] % 10 == 0:
                    self.update_dashboard_display(camera_name, defect_dict, detections_for_grading)

                # Update the live grading display every 8th frame (reduced frequency)
                if self._detection_frame_skip[camera_name] % 8 == 0:
                    self.update_live_grading_display()

                cv2image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            else:
                # No defect detection (either not should_detect or no wood detected)
                # Just show raw feed without detection processing
                # Add ROI overlay to show the detection area even when not detecting
                frame_with_roi = self.draw_roi_overlay(frame, camera_name)
                # Add wood detection overlay if available (skip for scan mode live feed)
                if self.current_mode != "SCAN_PHASE":
                    frame_with_overlays = self.draw_wood_detection_overlay(frame_with_roi, camera_name)
                else:
                    # For scan mode, only show yellow ROI on live feed (green overlay only on captured frames)
                    frame_with_overlays = self.draw_roi_overlay(frame, camera_name)  # Yellow ROI only
                cv2image = cv2.cvtColor(frame_with_overlays, cv2.COLOR_BGR2RGB)

                # Reset detections only when automatic detection is not active
                if not self.auto_detection_active:
                    self.live_detections[camera_name] = {}
                    self.live_grades[camera_name] = " "
                    if hasattr(self, 'live_measurements'):
                        self.live_measurements[camera_name] = []
                    # Update dashboard every 15th frame when no detection (further reduced)
                    if self._detection_frame_skip[camera_name] % 15 == 0:
                        self.update_dashboard_display(camera_name, {}, [])
                        self.update_live_grading_display()
            
            # Convert to PIL Image
            img = Image.fromarray(cv2image)
            
            # Always resize to 360p (640x360) for consistent display
            display_width = 640
            display_height = 360
            img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
            
            imgtk = ImageTk.PhotoImage(image=img)

            # Handle both Label and Canvas widgets
            if hasattr(label, 'configure') and 'image' in label.configure():
                # This is a Label widget
                label.imgtk = imgtk
                label.configure(image=imgtk)
            else:
                # This is a Canvas widget - use create_image method
                label.delete("all")  # Clear previous image
                label.create_image(0, 0, image=imgtk, anchor="nw")
                label.imgtk = imgtk  # Store reference to prevent garbage collection

    def calculate_grade(self, defect_dict):
        """Fallback grade calculation based on defect dictionary - simplified version"""
        total_defects = sum(defect_dict.values()) if defect_dict else 0

        if total_defects == 0:
            return {
                'grade': GRADE_G2_0,
                'text': 'Perfect (No Defects)',
                'total_defects': 0,
                'color': 'dark green'
            }
        elif total_defects <= 2:
            return {
                'grade': GRADE_G2_0,
                'text': f'Good (G2-0) - {total_defects} defects',
                'total_defects': total_defects,
                'color': 'dark green'
            }
        elif total_defects <= 6:
            return {
                'grade': GRADE_G2_2,
                'text': f'Fair (G2-2) - {total_defects} defects',
                'total_defects': total_defects,
                'color': 'orange'
            }
        else:
            return {
                'grade': GRADE_G2_4,
                'text': f'Poor (G2-4) - {total_defects} defects',
                'total_defects': total_defects,
                'color': 'red'
            }

    def update_live_grading_display(self):
        """Update the live grading display with current detection results using SS-EN 1611-1"""
        # Update mode status display
        if hasattr(self, 'mode_status_label'):
            if self.current_mode == "IDLE":
                self.mode_status_label.config(text=" ", foreground="gray")
            elif self.current_mode == "TRIGGER":
                self.mode_status_label.config(text="Waiting for Detection Process", foreground="blue")
            elif self.current_mode == "SCAN_PHASE":
                self.mode_status_label.config(text="Waiting for Detection Process", foreground="blue")
            elif self.current_mode == "CONTINUOUS":
                self.mode_status_label.config(text="Live Detection Active", foreground="green")
            else:
                self.mode_status_label.config(text="", foreground="black")

        # Update individual camera grades
        top_grade = self.live_grades["top"]
        bottom_grade = self.live_grades["bottom"]

        if isinstance(top_grade, dict):
            self.top_grade_label.configure(text=top_grade['text'], text_color=top_grade['color'])
        else:
            self.top_grade_label.configure(text=top_grade, text_color="gray")

        if isinstance(bottom_grade, dict):
            self.bottom_grade_label.configure(text=bottom_grade['text'], text_color=bottom_grade['color'])
        else:
            self.bottom_grade_label.configure(text=bottom_grade, text_color="gray")

        # Calculate combined grade using sophisticated method
        wood_detected = False
        top_surface_grade = None
        bottom_surface_grade = None

        # Get sophisticated grades from measurements if available
        if hasattr(self, 'live_measurements'):
            if self.live_measurements.get("top"):
                wood_detected = True
                top_surface_grade = self.determine_surface_grade(self.live_measurements["top"], camera_name="top")

            if self.live_measurements.get("bottom"):
                wood_detected = True
                bottom_surface_grade = self.determine_surface_grade(self.live_measurements["bottom"], camera_name="bottom")

        # Fallback to detection-based grading if measurements not available
        if not wood_detected:
            for camera_name in ["top", "bottom"]:
                if self.live_detections[camera_name]:
                    wood_detected = True
                    break

        # For scan mode, use the per-side grades from live_grades if available
        if self.current_mode == "SCAN_PHASE" and isinstance(top_grade, dict) and isinstance(bottom_grade, dict):
            top_surface_grade = top_grade['grade']
            bottom_surface_grade = bottom_grade['grade']
            wood_detected = True

        if wood_detected:
            # Use sophisticated grading if measurements available
            if top_surface_grade is not None or bottom_surface_grade is not None:
                final_grade = self.determine_final_grade(top_surface_grade, bottom_surface_grade)
                combined_text = f"Final Grade: {final_grade} (SS-EN 1611-1)"
                combined_color = self.get_grade_color(final_grade)
            else:
                # Fallback to simple combined defect counting
                combined_defects = {}
                for camera_name in ["top", "bottom"]:
                    if self.live_detections[camera_name]:
                        for defect, count in self.live_detections[camera_name].items():
                            combined_defects[defect] = combined_defects.get(defect, 0) + count

                combined_grade = self.calculate_grade(combined_defects)
                combined_text = combined_grade['text']
                combined_color = combined_grade['color']
                final_grade = None

            self.combined_grade_label.configure(text=combined_text, text_color=combined_color)

            # Auto-grade functionality - COMPLETELY DISABLED
            # Grading only happens when beam clears in TRIGGER mode
            # This ensures accurate grading based on complete defect tracking
            pass

        else:
            self.combined_grade_label.configure(text=" ", text_color="gray")

    def update_detection_details(self, camera_name, defect_dict, measurements=None):
        """Update the detection details display for a specific camera with SS-EN 1611-1 details"""
        # Determine which details text widget to update
        if camera_name == "top":
            details_widget = self.top_details
        elif camera_name == "bottom":
            details_widget = self.bottom_details
        else:
            return
        
        # Check if user is currently scrolling - if so, don't update
        if self._user_scrolling.get(camera_name, False):
            return
        
        # Format the detection details with sophisticated grading info
        if defect_dict and measurements:
            # Create a formatted string showing SS-EN 1611-1 grading details
            details_text = f"SS-EN 1611-1 Grading ({camera_name.title()} Camera):\n"
            
            # Show camera calibration info
            if camera_name == "top":
                details_text += f"Distance: {TOP_CAMERA_DISTANCE_CM}cm, Factor: {TOP_CAMERA_PIXEL_TO_MM:.3f}mm/px\n"
            else:
                details_text += f"Distance: {BOTTOM_CAMERA_DISTANCE_CM}cm, Factor: {BOTTOM_CAMERA_PIXEL_TO_MM:.3f}mm/px\n"
            
            total_defects = len(measurements)
            details_text += f"Wood Height: {WOOD_PALLET_WIDTH_MM}mm | Defects: {total_defects}\n"
            details_text += "═" * 50 + "\n"
            
            # Show individual defect analysis
            for i, (defect_type, size_mm, percentage) in enumerate(measurements, 1):
                individual_grade = self.grade_individual_defect(defect_type, size_mm, percentage)
                details_text += f"{i}. {defect_type.replace('_', ' ')}\n"
                details_text += f"   Size: {size_mm:.1f}mm ({percentage:.1f}% of width)\n"
                details_text += f"   Individual Grade: {individual_grade}\n"
                details_text += f"   Threshold Info: "
                
                # Show which threshold was applied using new grading system
                constants = GRADING_CONSTANTS.get(defect_type, {})
                limit = (0.10 * WOOD_PALLET_WIDTH_MM) + constants.get(individual_grade, 0)
                details_text += f"Limit: ≤{limit:.1f}mm (0.10×{WOOD_PALLET_WIDTH_MM}mm + {constants.get(individual_grade, 0)})\n"
                
                details_text += "\n"
            
            details_text += "═" * 50 + "\n"
            
            # Show surface grade determination
            surface_grade = self.determine_surface_grade(measurements)
            details_text += f"Final Surface Grade: {surface_grade}\n"
            
            # Show grade reasoning with detailed explanation
            if total_defects > 6:
                details_text += "Grade Reasoning: More than 6 defects detected\n"
                details_text += "SS-EN 1611-1 Rule: >6 defects = Automatic G2-4"
            elif total_defects > 4:
                details_text += "Grade Reasoning: More than 4 defects detected\n"
                details_text += "SS-EN 1611-1 Rule: >4 defects = Maximum G2-3"
            elif total_defects > 2:
                details_text += "Grade Reasoning: More than 2 defects detected\n"
                details_text += "SS-EN 1611-1 Rule: >2 defects = Maximum G2-2"
            else:
                details_text += "Grade Reasoning: Based on worst individual defect grade\n"
                details_text += "SS-EN 1611-1 Rule: ≤2 defects = Use individual grades"
                
        elif defect_dict:
            # Fallback to simple display if measurements not available
            details_text = f"Simple Detection ({camera_name.title()} Camera):\n"
            
            # Show camera info
            if camera_name == "top":
                details_text += f"Distance: {TOP_CAMERA_DISTANCE_CM}cm\n"
            else:
                details_text += f"Distance: {BOTTOM_CAMERA_DISTANCE_CM}cm\n"
            
            total_defects = sum(defect_dict.values())
            details_text += f"Total Defects: {total_defects}\n"
            details_text += "─" * 40 + "\n"
            
            # Sort defects by count (highest first)
            sorted_defects = sorted(defect_dict.items(), key=lambda x: x[1], reverse=True)
            
            for defect_type, count in sorted_defects:
                formatted_name = defect_type.replace('_', ' ').title()
                details_text += f"• {formatted_name}: {count} detected\n"
            
            details_text += "─" * 40 + "\n"
            details_text += f"Status: {len(defect_dict)} defect type(s) detected\n"
            details_text += "Note: Size measurements not available in simple mode"
        else:
            details_text = f"SS-EN 1611-1 Grading ({camera_name.title()}):\n"
            
            # Show camera calibration even when no detection
            if camera_name == "top":
                details_text += f"Distance: {TOP_CAMERA_DISTANCE_CM}cm, {TOP_CAMERA_PIXEL_TO_MM:.3f}mm/px\n"
            else:
                details_text += f"Distance: {BOTTOM_CAMERA_DISTANCE_CM}cm, {BOTTOM_CAMERA_PIXEL_TO_MM:.3f}mm/px\n"
            
            details_text += f"Wood Height: {WOOD_PALLET_WIDTH_MM}mm\n"
            details_text += "═" * 50 + "\n"
            details_text += "No wood or defects detected\n"
            details_text += "═" * 50 + "\n"
            details_text += "Status: Waiting for detection...\n"
            details_text += "\nReady to analyze:\n"
            details_text += "• Sound Knots (Live knots)\n"
            details_text += "• Unsound Knots (Dead/Missing/Crack knots)\n"
            details_text += "\nGrading according to SS-EN 1611-1 standard"
        
        # Only update if content has actually changed OR if this is the first update
        if (details_text != self._last_detection_content.get(camera_name, "") or 
            not self._last_detection_content.get(camera_name)):
            # Store current scroll position before update
            current_scroll_pos = details_widget.yview()[0]
            
            # Update the text widget
            details_widget.config(state=tk.NORMAL)
            details_widget.delete(1.0, tk.END)
            details_widget.insert(1.0, details_text)
            details_widget.config(state=tk.DISABLED)
            
            # Restore scroll position if user was scrolling, otherwise scroll to top for new content
            if current_scroll_pos > 0.1:  # If user had scrolled down
                try:
                    details_widget.yview_moveto(current_scroll_pos)
                except:
                    pass  # If restore fails, just continue
            else:
                details_widget.see(1.0)  # Scroll to top for new content
            
            # Cache the content
            self._last_detection_content[camera_name] = details_text

    def _identify_arduino_port(self):
        """Identify Arduino port by testing communication"""
        import glob

        # Get all potential serial ports
        ports_to_try = [
            # ACM ports (Arduino Uno R3, Leonardo, Micro with native USB)
            '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2', '/dev/ttyACM3',
            # USB ports (Arduino Nano, Pro Mini with FTDI/CH340)
            '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3',
            # Reassigned ports (when disconnection occurs)
            '/dev/ttyUSB01', '/dev/ttyACM01',
            # Windows COM ports
            'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10'
        ]

        # Also check for any ttyACM* or ttyUSB* devices that might exist
        acm_ports = glob.glob('/dev/ttyACM*')
        usb_ports = glob.glob('/dev/ttyUSB*')
        all_ports = list(set(ports_to_try + acm_ports + usb_ports))

        arduino_ports = []

        for port in all_ports:
            try:
                print(f"Testing Arduino port {port}...")
                # Try to open the port (same settings as setup_arduino)
                ser = serial.Serial(
                    port=port,
                    baudrate=9600,
                    timeout=2,
                    write_timeout=2,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False
                )

                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                # Test communication by sending stop command (same as setup_arduino)
                ser.write(b'X')
                ser.flush()
                time.sleep(0.5)  # Give Arduino time to process

                # If we get here without exception, port is accessible
                arduino_ports.append(port)
                print(f"✅ Found accessible serial port {port}")
                ser.close()

            except (serial.SerialException, OSError, UnicodeDecodeError) as e:
                print(f"❌ Port {port} not accessible: {e}")
                continue

        return arduino_ports

    def setup_arduino(self):
        # Don't attempt to setup Arduino if shutting down
        if hasattr(self, '_shutting_down') and self._shutting_down:
            return

        try:
            # Close existing connection if any
            if hasattr(self, 'ser') and self.ser:
                try:
                    self.ser.close()
                except:
                    pass

            # Try dynamic Arduino identification first
            arduino_ports = self._identify_arduino_port()
            if arduino_ports:
                port = arduino_ports[0]  # Use first found Arduino
                print(f"Using dynamically identified Arduino port: {port}")
            else:
                # Fallback to manual port list
                ports_to_try = [
                    '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2', '/dev/ttyACM3',
                    '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3',
                    '/dev/ttyUSB01', '/dev/ttyACM01',
                    'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10'
                ]
                port = None
                for p in ports_to_try:
                    try:
                        print(f"Trying to connect to Arduino on {p}...")
                        ser = serial.Serial(
                            port=p,
                            baudrate=9600,
                            timeout=2,
                            write_timeout=2,
                            bytesize=serial.EIGHTBITS,
                            parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE,
                            xonxoff=False,
                            rtscts=False,
                            dsrdtr=False
                        )
                        time.sleep(2)
                        ser.reset_input_buffer()
                        ser.reset_output_buffer()
                        ser.write(b'X')
                        ser.flush()
                        time.sleep(0.5)
                        port = p
                        ser.close()
                        print(f"✅ Arduino connected successfully on {p}")
                        break
                    except (serial.SerialException, OSError):
                        continue

                if not port:
                    raise serial.SerialException("No Arduino found on any port")

            # Connect to the identified port
            self.ser = serial.Serial(
                port=port,
                baudrate=9600,
                timeout=2,
                write_timeout=2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            # Extended stabilization time for voltage drop recovery
            stabilization_delay = 0.5  
            print(f"🔋 Arduino voltage stabilization delay: {stabilization_delay}s")
            time.sleep(stabilization_delay)

            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            # Start Arduino listener thread if not already running and not shutting down
            if not (hasattr(self, '_shutting_down') and self._shutting_down):
                if not hasattr(self, 'arduino_thread') or not self.arduino_thread.is_alive():
                    self.arduino_thread = threading.Thread(target=self.listen_for_arduino, daemon=True)
                    self.arduino_thread.start()

            if hasattr(self, 'status_label'):
                self.update_status_text("Status: Arduino connected. Ready for automatic detection.")
                self.update_status_text("Status: Ready - Waiting for IR beam trigger", STATUS_READY_COLOR)

        except serial.SerialException as e:
            self.ser = None
            print(f"Arduino connection failed: {e}")
            if hasattr(self, 'status_label'):
                self.update_status_text("Status: Arduino not found. Running in manual mode.", STATUS_WARNING_COLOR)

    def process_message_queue(self):
        """Process messages from background threads safely in the main thread"""
        try:
            while True:
                msg_type, *data = self.message_queue.get_nowait()
                
                # Handle alignment warning notifications
                if msg_type == "warning":
                    print(f"[DEBUG QUEUE] Processing warning message from queue...")
                    warning_title, warning_message = data
                    print(f"[DEBUG QUEUE] Title: {warning_title}")
                    print(f"[DEBUG QUEUE] Message: {warning_message[:50]}...")
                    print(f"[DEBUG QUEUE] Showing toast notification...")
                    self.show_toast_notification(
                        warning_title,
                        warning_message,
                        duration=6000,
                        type="warning"
                    )
                    print(f"[DEBUG QUEUE] Toast notification shown successfully")
                    continue
                
                if msg_type == "arduino_message":
                    message = data[0] if data else None
                    if not message:
                        continue

                    # --- IR BEAM HANDLING (Arduino sends "B" for beam broken) ---
                    if message == "B":
                        print("🔥 ARDUINO SENT 'B' - IR BEAM BROKEN DETECTED! 🔥")
                        # Respond to IR triggers in TRIGGER or SCAN_PHASE mode
                        if self.current_mode == "TRIGGER":
                            if not self.auto_detection_active:
                                print("✅ TRIGGER MODE: Starting detection...")
                                print("🔧 Arduino should now set motorActiveForTrigger = true")
                                print("⚡ Stepper motor should start running NOW!")

                                if hasattr(self, 'status_label'):
                                    # status_label is a Text widget, not a Label widget
                                    self.status_label.config(state=tk.NORMAL)
                                    self.status_label.delete(1.0, tk.END)
                                    self.status_label.insert(1.0, "Status: IR TRIGGERED - Motor should be running!")
                                    self.status_label.config(foreground="orange", state=tk.DISABLED)
                                self.start_automatic_detection()
                                # Keep auto_grade_var False in TRIGGER mode - grading triggered by beam clear
                                print(f"After 'B': live_detection_var: {self.live_detection_var.get()}, auto_grade_var: {self.auto_grade_var.get()}")
                            else:
                                print("⚠️ IR beam broken but detection already active")
                        elif self.current_mode == "SCAN_PHASE":
                            if not self.scan_phase_active:
                                print("✅ SCAN_PHASE MODE: Starting segmented scanning...")
                                print("🔧 Arduino should now start segmented scanning")
                                print("⚡ Stepper motor should start running NOW!")

                                if hasattr(self, 'status_label'):
                                    self.status_label.config(state=tk.NORMAL)
                                    self.status_label.delete(1.0, tk.END)
                                    self.status_label.insert(1.0, "Status: SCAN_PHASE STARTED - Scanning segments...")
                                    self.status_label.config(foreground="orange", state=tk.DISABLED)
                                self.start_scan_phase()
                            else:
                                print("⚠️ IR beam broken but scan already active")
                        else:
                            # In IDLE or CONTINUOUS mode, just log the IR signal but don't act on it
                            print(f"❌ IR beam broken received but system is in {self.current_mode} mode - ignoring trigger")
                        continue  # skip other checks for this message

                    # --- SCAN PHASE SEGMENT HANDLING ---
                    if "complete. Pausing" in message and self.scan_phase_active:
                        # Extract segment number
                        try:
                            segment_num = int(message.split()[1])
                            self.capture_segment_frame(segment_num)
                        except (ValueError, IndexError):
                            print(f"Could not parse segment number from: {message}")
                        continue

                    # --- PAUSE COMPLETE HANDLING ---
                    if message == "PAUSE_COMPLETE":
                        print("Arduino signaled pause complete - resuming live feed")
                        self.resume_live_feed()
                        continue

                    # --- SCAN PHASE COMPLETION ---
                    if "Last scan phase complete" in message and self.scan_phase_active:
                        self.grade_all_woods()
                        continue

                    # --- CAPTURE HANDLING (Arduino sends "CAPTURE:X" for frame capture) ---
                    if message.startswith("CAPTURE:"):
                        try:
                            segment_num = int(message.split(':')[1])
                            print(f"Arduino signaled to capture segment {segment_num}")

                            # Set display to "No Wood Graded" when beam is blocked (moved here as cue)
                            self.live_grades = {"top": " ", "bottom": " "}
                            self.update_live_grading_display()

                            self.capture_segment_frame(segment_num)
                        except (ValueError, IndexError):
                            print(f"Could not parse CAPTURE message: {message}")
                        continue  # skip other checks for this message

                    # --- RESUME LIVE FEED HANDLING (Arduino sends "RESUME_LIVE_FEED" after pause) ---
                    if message == "RESUME_LIVE_FEED":
                        print("Arduino signaled to resume live feed")
                        self.resume_live_feed()
                        continue  # skip other checks for this message

                    # --- LENGTH HANDLING (Arduino sends "L:duration" when beam clears) ---
                    if message.startswith("L:"):
                        try:
                            duration_ms = int(message.split(':')[1])
                            # Length calculation removed - only measuring defect width

                            # In TRIGGER mode, process grading if detection was active
                            if self.current_mode == "TRIGGER":
                                # Stop detection when beam clears, regardless of whether detection was active
                                self.auto_grade_var.set(False)
                                print("IR beam cleared – stopping detection")
                                print(f"After 'L': live_detection_var: {self.live_detection_var.get()}, auto_grade_var: {self.auto_grade_var.get()}")

                                if self.auto_detection_active:
                                    if hasattr(self, 'status_label'):
                                        # status_label is a Text widget, not a Label widget
                                        self.status_label.config(state=tk.NORMAL)
                                        self.status_label.delete(1.0, tk.END)
                                        self.status_label.insert(1.0, "Status: Processing results...")
                                        self.status_label.config(foreground="red", state=tk.DISABLED)
                                    self.stop_automatic_detection_and_grade()
                                    if hasattr(self, 'status_label'):
                                        # status_label is a Text widget, not a Label widget
                                        self.status_label.config(state=tk.NORMAL)
                                        self.status_label.delete(1.0, tk.END)
                                        self.status_label.insert(1.0, "Status: Ready - Waiting for IR beam trigger")
                                        self.status_label.config(foreground="green", state=tk.DISABLED)
                                else:
                                    print(f"Length signal received (duration: {duration_ms}ms) but no detection was active")
                            else:
                                print(f"Length signal received (duration: {duration_ms}ms) but system is in {self.current_mode} mode")
                        except (ValueError, IndexError):
                            print(f"Could not parse length message: {message}")
                        continue  # skip other checks for this message

                    # --- SCAN COMPLETE HANDLING ---
                    elif "Last scan phase complete" in message:
                        print("Arduino signaled scan phase complete")
                        self.grade_all_woods()
                        continue

                    # --- ARDUINO RECOVERY/STATUS MESSAGES ---
                    if message == "ARDUINO_READY":
                        print("🚀 Arduino startup detected - system ready")
                        continue
                    
                    if message.startswith("SYSTEM_STATUS:"):
                        print(f"📊 Arduino system status: {message}")
                        # Could parse status details here for monitoring
                        continue
                        
                    if message.startswith("RECOVERY:"):
                        recovery_type = message.split(":", 1)[1] if ":" in message else ""
                        if recovery_type == "MANUAL_RESTART_RECOMMENDED":
                            print("ℹ️ Arduino recommends manual restart - user should click ON button")
                        elif recovery_type == "MODE_SET_TO_IDLE":
                            print("ℹ️ Arduino mode set to IDLE")
                        continue

                    if message.startswith("STATUS:"):
                        status_type = message.split(":", 1)[1] if ":" in message else ""
                        if status_type == "RECONNECTED_AWAITING_USER_INPUT":
                            print("⏳ Arduino reconnected and awaiting user input")
                        continue

                    # --- OTHER ARDUINO MESSAGES ---
                    else:
                        # Filter out repetitive STATUS_PAUSED messages to reduce spam
                        if message.startswith("STATUS_PAUSED:"):
                            # Only log STATUS_PAUSED messages if it's been a while since the last one
                            current_time = time.time()
                            if not hasattr(self, '_last_status_paused_log'):
                                self._last_status_paused_log = 0
                            
                            if current_time - self._last_status_paused_log > 10.0:  # Log at most every 10 seconds
                                print(f"Arduino message received: '{message}' (suppressing further duplicates for 10s)")
                                self._last_status_paused_log = current_time
                            # Update status but don't spam console
                            if hasattr(self, 'status_label'):
                                self.status_label.config(state=tk.NORMAL)
                                self.status_label.delete(1.0, tk.END)
                                self.status_label.insert(1.0, f"Status: Arduino: {message}")
                                self.status_label.config(state=tk.DISABLED)
                        else:
                            # Normal message processing for non-STATUS_PAUSED messages
                            print(f"Arduino message received: '{message}'")
                            if hasattr(self, 'status_label'):
                                # status_label is a Text widget, not a Label widget
                                self.status_label.config(state=tk.NORMAL)
                                self.status_label.delete(1.0, tk.END)
                                self.status_label.insert(1.0, f"Status: Arduino: {message}")
                                self.status_label.config(state=tk.DISABLED)

                elif msg_type == "status_update":
                    if hasattr(self, 'status_label'):
                        # status_label is a Text widget, not a Label widget
                        self.status_label.config(state=tk.NORMAL)
                        self.status_label.delete(1.0, tk.END)
                        self.status_label.insert(1.0, f"Status: {data}")
                        self.status_label.config(state=tk.DISABLED)
                    
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error in process_message_queue: {e}")
        
        # Schedule next check
        self.after(50, self.process_message_queue)

    def listen_for_arduino(self):
        """Robust Arduino listener with automatic reconnection"""
        reconnect_attempts = 0
        max_reconnect_attempts = 10  # Increased max attempts

        while True:
            try:
                # Check if we're shutting down
                if hasattr(self, '_shutting_down') and self._shutting_down:
                    print("Arduino listener: Shutdown detected, exiting thread")
                    break

                # Check if serial connection exists and is open
                if self.ser and hasattr(self.ser, 'is_open') and self.ser.is_open:
                    if self.ser.in_waiting > 0:
                        try:
                            message = self.ser.readline().decode('utf-8').strip()
                            if not message:
                                continue

                            self.reset_inactivity_timer()
                            print(f"📨 Arduino Message: '{message}' (Port: {self.ser.port})")

                            # Put message in queue for main thread to process
                            self.message_queue.put(("arduino_message", message))
                            reconnect_attempts = 0  # Reset counter on successful communication

                        except UnicodeDecodeError as e:
                            print(f"⚠️ Arduino message decode error: {e}")
                            # Clear the buffer and continue
                            try:
                                self.ser.reset_input_buffer()
                            except:
                                pass
                            continue

                elif not self.ser or (hasattr(self.ser, 'is_open') and not self.ser.is_open):
                    # Serial connection is closed or doesn't exist
                    if reconnect_attempts < max_reconnect_attempts:
                        reconnect_attempts += 1
                        print(f"🔄 Arduino disconnected, attempting reconnection {reconnect_attempts}/{max_reconnect_attempts}...")
                        if not self.arduino_disconnected_popup_shown:
                            # Enhanced disconnection message with restart recommendation
                            disconnect_message = "Arduino disconnected. Attempting reconnection..."
                            if self.current_mode == "SCAN_PHASE":
                                disconnect_message += "\n\nIMPORTANT: Restart scan manually after reconnection to ensure proper detection."
                            
                            # Use non-blocking toast notification
                            self.show_toast_notification(
                                "⚠️ Arduino Disconnection",
                                disconnect_message,
                                duration=7000,
                                type="warning"
                            )
                            self.arduino_disconnected_popup_shown = True
                        time.sleep(3)  # Increased wait time for Arduino to stabilize

                        # Try to reconnect with multiple attempts per reconnection cycle
                        reconnected = False
                        for attempt in range(3):  # Try 3 times per reconnection attempt
                            try:
                                self.setup_arduino()
                                if self.ser and self.ser.is_open:
                                    print(f"✅ Arduino reconnected successfully on {self.ser.port}")
                                    
                                    # Enhanced reconnection message
                                    reconnect_message = f"Arduino reconnected on {self.ser.port}"
                                    if self.current_mode == "SCAN_PHASE":
                                        reconnect_message += "\n\nREMINDER: Restart scan manually by clicking ON button."
                                    
                                    # Use non-blocking toast notification
                                    self.show_toast_notification(
                                        "✅ Arduino Reconnected",
                                        reconnect_message,
                                        duration=7000,
                                        type="success"
                                    )
                                    self.arduino_disconnected_popup_shown = False
                                    reconnect_attempts = 0
                                    reconnected = True
                                    
                                    # Check for Arduino mode recovery
                                    self.handle_arduino_reconnection_recovery()
                                    
                                    break
                                else:
                                    print(f"❌ Reconnection sub-attempt {attempt + 1} failed, retrying...")
                                    time.sleep(1)
                            except Exception as e:
                                print(f"❌ Reconnection sub-attempt {attempt + 1} failed: {e}")
                                time.sleep(1)

                        if not reconnected:
                            print(f"❌ All reconnection sub-attempts failed for attempt {reconnect_attempts}")
                    else:
                        print(f"❌ Max reconnection attempts ({max_reconnect_attempts}) reached, exiting listener thread")
                        break

                time.sleep(0.1)  # Small delay to prevent CPU spinning

            except (serial.SerialException, OSError, TypeError) as e:
                print(f"🔥 Arduino communication error: {e}")

                # Check if this is due to application shutdown
                if hasattr(self, '_shutting_down') and self._shutting_down:
                    print("Arduino listener: Application shutting down, exiting thread")
                    break

                # Attempt reconnection with enhanced logic
                if reconnect_attempts < max_reconnect_attempts:
                    reconnect_attempts += 1
                    print(f"🔄 Communication error, attempting reconnection {reconnect_attempts}/{max_reconnect_attempts}...")
                    time.sleep(3)  # Increased wait time

                    # Multiple reconnection attempts
                    reconnected = False
                    for attempt in range(3):
                        try:
                            self.setup_arduino()
                            if self.ser and self.ser.is_open:
                                print(f"✅ Arduino reconnected after error on {self.ser.port}")
                                reconnect_attempts = 0
                                reconnected = True
                                
                                # Check for Arduino mode recovery
                                self.handle_arduino_reconnection_recovery()
                                
                                break
                            time.sleep(1)
                        except Exception as reconnect_error:
                            print(f"❌ Reconnection sub-attempt {attempt + 1} failed: {reconnect_error}")
                            time.sleep(1)

                    if not reconnected:
                        print(f"❌ All reconnection attempts failed")
                else:
                    print(f"❌ Max reconnection attempts reached after error, exiting thread")
                    break

            except Exception as e:
                print(f"❌ Unexpected error in Arduino listener: {e}")
                time.sleep(1)
                self.message_queue.put(("status_update", "Arduino connection lost"))
                break

    def send_arduino_command(self, command):
        # Don't send commands if shutting down
        if hasattr(self, '_shutting_down') and self._shutting_down:
            return
            
        self.reset_inactivity_timer()
        
        # Check if this is a grading command (high-power operation)
        is_grading_command = command.isdigit() and len(command) == 1 and command in ['1', '2', '3', '4', '5']
        is_critical_command = command in ['C', 'T', 'S', 'X'] or is_grading_command
        is_error_command = command.startswith('ERROR:') or command.startswith('CLEAR_ERROR:')
        
        # Add power stabilization delays for critical commands
        if is_critical_command:
            print(f"🔋 Power stabilization: Preparing to send critical command '{command}'")
            time.sleep(0.2)  # Pre-command stabilization delay
        
        # Add rate limiting to prevent overwhelming Arduino (but allow error commands through)
        current_time = time.time()
        if hasattr(self, '_last_command_time') and not is_error_command:
            time_since_last = current_time - self._last_command_time
            min_delay = 0.3 if is_critical_command else 0.1  # Longer delay for critical commands
            if time_since_last < min_delay:
                delay_needed = min_delay - time_since_last
                print(f"⏱️ Rate limiting: Waiting {delay_needed:.2f}s before sending command")
                time.sleep(delay_needed)
        
        # Initialize _last_command_time if it doesn't exist
        if not hasattr(self, '_last_command_time'):
            self._last_command_time = 0
            
        # Prevent duplicate commands from being sent too frequently (but allow error commands through)
        if hasattr(self, '_last_command_sent') and not is_error_command:
            cooldown_time = 3.0 if is_grading_command else 2.0  # Longer cooldown for grading commands
            if self._last_command_sent == command and current_time - self._last_command_time < cooldown_time:
                print(f"⚠️ Skipping duplicate command: {command} (cooldown: {cooldown_time}s)")
                return
        
        self._last_command_sent = command
        
        try:
            if self.ser:
                # Check if serial connection is still valid
                if not hasattr(self.ser, 'is_open') or not self.ser.is_open:
                    print("Serial connection is closed, attempting to reconnect...")
                    self.setup_arduino()
                    if not self.ser:
                        return
                
                # Clear buffers before sending command to prevent overflow
                try:
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                except:
                    pass
                
                # Additional voltage stabilization for grading commands
                if is_grading_command:
                    print(f"🔋 Voltage drop mitigation: Preparing power system for grading command '{command}'")
                    time.sleep(0.5)  # Extended pre-transmission delay for grading commands
                
                # Send command with error handling and retry logic for critical commands
                max_retries = 3 if is_critical_command else 1
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        command_bytes = command.encode('utf-8')
                        self.ser.write(command_bytes)
                        self.ser.flush()  # Ensure data is sent immediately
                        
                        # Post-transmission power stabilization for grading commands
                        if is_grading_command:
                            print(f"🔋 Post-transmission stabilization: Allowing power system to recover after grading command '{command}'")
                            time.sleep(1.0)  # Extended post-transmission delay for power recovery
                        
                        # Record timestamp for rate limiting
                        self._last_command_time = time.time()
                        
                        print(f"✅ Sent command to Arduino: '{command}' (Port: {self.ser.port})")
                        # Clear Arduino disconnection error on successful communication
                        self.clear_error("ARDUINO_DISCONNECTED")
                        return  # Success, exit retry loop
                        
                    except (serial.SerialException, OSError, TypeError) as retry_error:
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"⚠️ Command transmission failed (attempt {retry_count}/{max_retries}): {retry_error}")
                            print(f"🔄 Retrying command '{command}' in 0.5s...")
                            time.sleep(0.5)  # Wait before retry
                        else:
                            raise retry_error  # Re-raise the last error if all retries failed
                            
            else:
                print("❌ Cannot send command: Arduino not connected.")
                # Register Arduino disconnection error
                self.register_error("ARDUINO_DISCONNECTED", "Arduino not connected for command transmission")
                if hasattr(self, 'status_label'):
                    # status_label is a Text widget, not a Label widget
                    self.status_label.config(state=tk.NORMAL)
                    self.status_label.delete(1.0, tk.END)
                    self.status_label.insert(1.0, "Status: Arduino not connected.")
                    self.status_label.config(state=tk.DISABLED)
                    
        except (serial.SerialException, OSError, TypeError) as e:
            print(f"🔥 Arduino communication error: {e}")
            
            # Special handling for voltage drop scenarios
            if "Input/output error" in str(e) or "device reports readiness" in str(e):
                print(f"🔋 Voltage drop detected during command '{command}' transmission")
                if is_grading_command:
                    print(f"⚡ Critical: Voltage drop during grading command - implementing recovery protocol")
                
            # Register Arduino disconnection error with specific details
            self.register_error("ARDUINO_DISCONNECTED", f"Command '{command}' failed: {str(e)}")
            if hasattr(self, 'status_label'):
                # status_label is a Text widget, not a Label widget
                self.status_label.config(state=tk.NORMAL)
                self.status_label.delete(1.0, tk.END)
                self.status_label.insert(1.0, "Status: Arduino communication error - attempting reconnect...")
                self.status_label.config(state=tk.DISABLED)
            
            # Try to reconnect only if not shutting down
            if not (hasattr(self, '_shutting_down') and self._shutting_down):
                print("🔄 Attempting Arduino reconnection...")
                self.ser = None
                
                # Extended recovery time for voltage drop scenarios
                recovery_delay = 3.0 if is_grading_command else 1.0
                print(f"🔋 Power recovery delay: {recovery_delay}s to allow voltage stabilization")
                time.sleep(recovery_delay)
                
                self.setup_arduino()

    def set_continuous_mode(self):
        """Sets the system to fully automatic continuous mode."""
        # Check for system errors before switching modes
        if self.error_state["system_paused"]:
            print("Cannot switch to CONTINUOUS mode: System is paused due to errors")
            self.show_error_alert("SYSTEM_PAUSED", "Cannot start continuous mode while system has critical errors", "ERROR")
            return False
            
        if self.error_state["manual_inspection_required"]:
            print("Cannot switch to CONTINUOUS mode: Manual inspection required")
            self.show_error_alert("MANUAL_INSPECTION_REQUIRED", "Please resolve manual inspection before starting continuous mode", "ERROR")
            return False
            
        print("Setting Continuous (Live + Auto Grade) Mode")
        self.current_mode = "CONTINUOUS"
        self.send_arduino_command('C')  # Send command to Arduino
        self.live_detection_var.set(True)
        self.auto_grade_var.set(True)
        self.update_status_text("Status: CONTINUOUS", STATUS_READY_COLOR)
        self.update_detection_status_display() # Update the status label
        return True

    def set_trigger_mode(self):
        """Sets the system to wait for an IR beam trigger."""
        # Check for system errors before switching modes
        if self.error_state["system_paused"]:
            print("Cannot switch to TRIGGER mode: System is paused due to errors")
            self.show_error_alert("SYSTEM_PAUSED", "Cannot start trigger mode while system has critical errors", "ERROR")
            return False
            
        if self.error_state["manual_inspection_required"]:
            print("Cannot switch to TRIGGER mode: Manual inspection required")
            self.show_error_alert("MANUAL_INSPECTION_REQUIRED", "Please resolve manual inspection before starting trigger mode", "ERROR")
            return False
            
        print("Setting Trigger Mode")
        self.current_mode = "TRIGGER"
        print(f"Sending 'T' command to Arduino...")
        self.send_arduino_command('T')  # Send command to Arduino
        self.live_detection_var.set(True)  # Enable live detection for triggering
        self.auto_grade_var.set(False)
        self.update_status_text("Status: TRIGGER", STATUS_READY_COLOR)
        self.update_detection_status_display() # Update the status label
        print(f"Trigger mode set - Python mode: {self.current_mode}")
        return True

    def set_idle_mode(self):
        """Disables all operations and stops the conveyor."""
        print("Setting IDLE Mode")
        self.current_mode = "IDLE"
        
        # Only send command to Arduino if it's connected
        if self.ser and hasattr(self.ser, 'is_open') and self.ser.is_open:
            self.send_arduino_command('X')  # Send stop command to Arduino
        else:
            print("⚠️ Arduino not connected, skipping 'X' command")
        
        self.live_detection_var.set(False)
        self.auto_grade_var.set(False)
        self.auto_detection_active = False  # Ensure automatic detection is disabled
        # Clear wood detection results when entering idle mode
        self.wood_detection_results = {"top": None, "bottom": None}
        self.dynamic_roi = {}
        # Reset grades to empty when entering idle mode
        self.live_grades = {"top": "", "bottom": ""}
        self.update_live_grading_display()
        
        # Clear system pause state when manually switching to idle
        if self.error_state["system_paused"]:
            print("Clearing system pause state due to manual IDLE mode selection")
            
        # status_label is a Text widget, not a Label widget
        self.status_label.config(state=tk.NORMAL)
        self.status_label.delete(1.0, tk.END)
        self.status_label.insert(1.0, "Status: IDLE")
        self.status_label.config(foreground="gray", state=tk.DISABLED)
        return True

    def set_scan_mode(self):
        """Sets the system to SCAN_PHASE mode for segmented scanning."""
        # Check for system errors before switching modes
        if self.error_state["system_paused"]:
            print("Cannot switch to SCAN_PHASE mode: System is paused due to errors")
            self.show_error_alert("SYSTEM_PAUSED", "Cannot start scan mode while system has critical errors", "ERROR")
            return False
            
        if self.error_state["manual_inspection_required"]:
            print("Cannot switch to SCAN_PHASE mode: Manual inspection required")
            self.show_error_alert("MANUAL_INSPECTION_REQUIRED", "Please resolve manual inspection before starting scan mode", "ERROR")
            return False
            
        print("Setting SCAN_PHASE Mode")
        self.current_mode = "SCAN_PHASE"
        self.send_arduino_command('S')  # Send scan phase command to Arduino
        self.live_detection_var.set(False)  # Disable live detection - only show live feed with ROI
        self.auto_grade_var.set(False)  # Grading happens after scan completion
        self.update_status_text("Status: SCAN_PHASE", STATUS_READY_COLOR)
        self.update_detection_status_display()
        print(f"Scan mode set - Python mode: {self.current_mode}")
        return True

    def start_scan_phase(self):
        """Initialize scan phase when Arduino detects beam break in SCAN_PHASE mode."""
        print("Starting SCAN_PHASE detection...")
        self.scan_phase_active = True
        self.current_wood_number += 1  # Increment for each new wood piece
        
        # Update the wood counter display
        self.update_wood_counter_display()
        
        self.scan_session_start_time = time.time()
        if not hasattr(self, 'scan_session_folder') or not self.scan_session_folder:
            self.scan_session_folder = self.create_session_folder()
        self.captured_frames = {"top": [], "bottom": []}
        self.segment_defects = {"top": [], "bottom": []}
        self.scan_session_data = {}

        # Update live grading display to show scanning in progress
        self.live_grades = {
            "top": "",
            "bottom": "",
            "combined": ""
        }
        self.update_live_grading_display()

        self.update_status_text("Status: SCAN_PHASE active", STATUS_READY_COLOR)

    def create_segment_visualization(self, frame, wood_detection_result, camera_name):
        """Create visualization - currently just returns the frame as-is (no overlays)."""
        # For now, return the frame without any overlays to focus on basic capture
        return frame.copy()

    def create_session_folder(self):
        """Create session folder with timestamp."""
        timestamp = datetime.now().strftime("%m%d%Y:%H%M") + "H-Session"
        folder = os.path.join("testIR", "Detections", timestamp)
        os.makedirs(folder, exist_ok=True)
        print(f"Created session folder: {folder}")
        return folder

    def capture_segment_frame(self, segment_num):
        """Capture and save frames for a specific segment with ROI-based detection."""
        print(f"Capturing frames for segment {segment_num}...")

        # Capture frames from both cameras
        ret_top, frame_top = self.cap_top.read()
        ret_bottom, frame_bottom = self.cap_bottom.read()

        if not ret_top or not ret_bottom:
            print(f"Failed to capture frames for segment {segment_num}")
            return

        # Flip bottom camera frame horizontally (matching the other app)
        frame_bottom = cv2.flip(frame_bottom, 1)

        # Process each camera with wood detection first, then defect detection
        processed_frames = {}
        for camera_name, frame in [("top", frame_top), ("bottom", frame_bottom)]:
            print(f"Processing {camera_name} camera for segment {segment_num}")

            # Step 1: Run wood detection ONLY within Yellow ROI (camera ROI)
            wood_detection_result = None
            if self.roi_enabled.get(camera_name, True):
                roi_coords = self.roi_coordinates.get(camera_name)
                if roi_coords:
                    x1, y1, x2, y2 = roi_coords["x1"], roi_coords["y1"], roi_coords["x2"], roi_coords["y2"]
                    yellow_roi_frame = frame[y1:y2, x1:x2]
                    print(f"Running wood detection on Yellow ROI: x1={x1}, y1={y1}, x2={x2}, y2={y2}")

                    wood_detection_result = self.rgb_wood_detector.detect_wood_comprehensive(
                        yellow_roi_frame, camera=camera_name
                    )

                    # Adjust bounding boxes back to full frame coordinates
                    if wood_detection_result.get('wood_detected', False):
                        for candidate in wood_detection_result['wood_candidates']:
                            bbox_x, bbox_y, bbox_w, bbox_h = candidate['bbox']
                            candidate['bbox'] = (bbox_x + x1, bbox_y + y1, bbox_w, bbox_h)

                        if wood_detection_result.get('auto_roi'):
                            roi_x, roi_y, roi_w, roi_h = wood_detection_result['auto_roi']
                            wood_detection_result['auto_roi'] = (roi_x + x1, roi_y + y1, roi_w, roi_h)
                else:
                    print(f"No Yellow ROI defined, skipping wood detection")
            else:
                print(f"Wood detection ROI disabled")

            # Store wood detection results
            self.wood_detection_results[camera_name] = wood_detection_result
            
            # Store Dynamic Wood ROI for defect filtering (in full frame coordinates)
            if wood_detection_result and wood_detection_result.get('auto_roi'):
                self.dynamic_roi[camera_name] = wood_detection_result['auto_roi']
                roi_x, roi_y, roi_w, roi_h = wood_detection_result['auto_roi']
                print(f"📍 Dynamic Wood ROI set [{camera_name}]: ({roi_x}, {roi_y}, {roi_w}, {roi_h}) - FULL FRAME COORDINATES")
            else:
                self.dynamic_roi[camera_name] = None
                print(f"⚠️  No Dynamic Wood ROI available [{camera_name}] - all detections will be rejected")

            # The wood width is already updated by ColorWoodDetector.detect_wood_comprehensive()
            # via update_wood_width_dynamic(), so we don't need to recalculate it here

            # Step 2: Run defect detection on FULL FRAME (NOT Yellow ROI)
            # CRITICAL: Model was trained on FULL camera feeds (1280x720), not ROI crops
            # This matches live_inference.py behavior exactly
            # We'll use the Dynamic Wood ROI for filtering detections later
            if wood_detection_result and wood_detection_result.get('wood_detected', False):
                print(f"Wood detected on {camera_name}, running defect detection on FULL FRAME")

                # Step 3: Run defect detection on FULL FRAME (same as live_inference.py)
                # The model expects full 1280x720 frame, not cropped ROI
                result = self.analyze_frame(frame, camera_name, run_defect_model=True)

                if len(result) == 3:
                    annotated_frame, defect_dict, detections_for_grading = result
                else:
                    annotated_frame, defect_dict = result
                    detections_for_grading = []

                # Step 4: Add wood detection overlay to show detected wood pieces
                final_frame = self.draw_wood_detection_overlay(annotated_frame, camera_name)

                # Step 6: Add ROI overlay to show detection area
                final_frame = self.draw_roi_overlay(final_frame, camera_name)

                processed_frames[camera_name] = final_frame

                # Store detection results for this segment
                if not hasattr(self, 'segment_defects'):
                    self.segment_defects = {"top": [], "bottom": []}
                
                # STRICT RULE VERIFICATION: Log what's being stored vs what's detected
                print(f"🔍 STRICT SEGMENT STORAGE: {camera_name} segment {segment_num}")
                print(f"🔍 DETECTED: {len(detections_for_grading)} defects detected and stored for grading")
                print(f"🔍 DEFECT TYPES: {defect_dict}")
                
                self.segment_defects[camera_name].append({
                    "segment": segment_num,
                    "defects": defect_dict,
                    "measurements": detections_for_grading,
                    "detected_count": len(detections_for_grading)  # Track for verification
                })

            else:
                # No wood detected, show wood detection attempt
                print(f"No wood detected on {camera_name} in Yellow ROI")
                final_frame = self.draw_wood_detection_overlay(frame, camera_name)
                final_frame = self.draw_roi_overlay(final_frame, camera_name)
                processed_frames[camera_name] = final_frame

        # Update UI with processed frames FIRST (so user can see them before saving)
        self.display_captured_frames(processed_frames["top"], processed_frames["bottom"])

        # Save processed frames with ROI-based detection results AFTER display
        self.save_segment_frames(self.current_wood_number, segment_num,
                                processed_frames["top"], processed_frames["bottom"])

        print(f"Frames captured, ROI-processed, and saved for segment {segment_num}")

    def save_segment_frames(self, wood_number, segment_num, top_frame, bottom_frame):
        """Save captured frames for a specific segment of a wood piece."""
        wood_folder = os.path.join(self.scan_session_folder, f"Wood ({wood_number})")
        top_folder = os.path.join(wood_folder, "Top Panel")
        bottom_folder = os.path.join(wood_folder, "Bottom Panel")

        os.makedirs(top_folder, exist_ok=True)
        os.makedirs(bottom_folder, exist_ok=True)

        # Save frames with segment-specific names
        top_filename = f"detection_segment_{segment_num}.jpg"
        bottom_filename = f"detection_segment_{segment_num}.jpg"

        top_path = os.path.join(top_folder, top_filename)
        bottom_path = os.path.join(bottom_folder, bottom_filename)

        # Save frames directly (already in BGR format from camera)
        success_top = cv2.imwrite(top_path, top_frame)
        success_bottom = cv2.imwrite(bottom_path, bottom_frame)

        if success_top and success_bottom:
            print(f"Saved segment {segment_num} frames for Wood {wood_number}")
        else:
            print(f"Failed to save segment {segment_num} frames: top={success_top}, bottom={success_bottom}")

    def save_final_wood_data(self, wood_number, top_grade=None, bottom_grade=None, final_grade=None):
        """Save accumulated defect data after all segments are captured for a wood piece."""
        if wood_number not in self.scan_session_data:
            return

        wood_folder = os.path.join(self.scan_session_folder, f"Wood ({wood_number})")
        data = self.scan_session_data[wood_number]

        # Use per-wood width if available, else fallback
        # CRITICAL: session data 'width_mm' contains the detected_width_mm value stored during grading
        wood_width = data.get('width_mm', WOOD_PALLET_WIDTH_MM if WOOD_PALLET_WIDTH_MM > 0 else 100)
        print(f"🔗 Save data synchronization: Using wood_width={wood_width:.1f}mm (from session data 'width_mm'={data.get('width_mm', 'N/A')}, fallback WOOD_PALLET_WIDTH_MM={WOOD_PALLET_WIDTH_MM:.1f}mm)")
        print(f"🔍 Authority chain: detected_width_mm → session_data['width_mm'] → wood_width = {wood_width:.1f}mm")

        # Use provided grades or get from live_grades
        if top_grade is None:
            top_grade = self.live_grades.get("top", {}).get("grade", "Unknown") if isinstance(self.live_grades.get("top"), dict) else "Unknown"
        if bottom_grade is None:
            bottom_grade = self.live_grades.get("bottom", {}).get("grade", "Unknown") if isinstance(self.live_grades.get("bottom"), dict) else "Unknown"
        if final_grade is None:
            grader = SSEN1611_1_PineGrader_Final(width_mm=wood_width)
            # Convert grade strings back to measurements for proper grading
            # For now, use placeholder - this should be improved to store actual measurements
            final_grade = grader.determine_final_grade([], [])  # Empty measurements for now

        # Defect display name mapping
        defect_display_names = {
            "Sound_Knot": "Live Knot",
            "Dead_Knot": "Dead Knot",
            "Missing_Knot": "Missing Knot",
            "Crack_Knot": "Knot with Crack",
            "Unsound_Knot": "Unsound Knot"  # Includes Crack Knots
        }

        # Save accumulated defect details with timestamps
        print(f"🔍 STRICT VERIFICATION: Saving defects.txt for Wood {wood_number}")
        print(f"🔍 STRICT VERIFICATION: Top defects to write: {data['top_defects']}")
        print(f"🔍 STRICT VERIFICATION: Bottom defects to write: {data['bottom_defects']}")
        
        # Count total defects for verification
        total_top_defects = len(data['top_defects'])
        total_bottom_defects = len(data['bottom_defects'])
        total_defects = total_top_defects + total_bottom_defects
        
        print(f"✅ STRICT RULE VERIFICATION: Recording {total_top_defects} top + {total_bottom_defects} bottom = {total_defects} total defects")
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(os.path.join(wood_folder, "defects.txt"), "w") as f:
            f.write(f"Detection Timestamp: {timestamp}\n")
            f.write(f"Wood No. ({wood_number}) - {wood_width}mm\n")
            f.write(f"Top Panel Grade: {top_grade}\n")
            f.write(f"Bottom Panel Grade: {bottom_grade}\n")
            f.write(f"Final Grade: {final_grade}\n\n")
            f.write("Top Panel Defects:\n")
            if data['top_defects']:
                for i, (defect_type, size_mm, percentage) in enumerate(data['top_defects'], 1):
                    display_name = defect_display_names.get(defect_type, defect_type.replace('_', ' '))
                    defect_line = f"{i}. {display_name} - {size_mm:.1f}mm\n"
                    f.write(defect_line)
                    print(f"✅ RECORDED: Top defect {i}: {defect_line.strip()}")
            else:
                f.write("No defects detected\n")
                print(f"✅ RECORDED: No top defects")
            f.write("\nBottom Panel Defects:\n")
            if data['bottom_defects']:
                for i, (defect_type, size_mm, percentage) in enumerate(data['bottom_defects'], 1):
                    display_name = defect_display_names.get(defect_type, defect_type.replace('_', ' '))
                    defect_line = f"{i}. {display_name} - {size_mm:.1f}mm\n"
                    f.write(defect_line)
                    print(f"✅ RECORDED: Bottom defect {i}: {defect_line.strip()}")
            else:
                f.write("No defects detected\n")
                print(f"✅ RECORDED: No bottom defects")

        print(f"Saved final defect data for Wood {wood_number}")
        
        # Update the GUI defects report display instead of popup
        self.update_defects_report_display(wood_number, wood_folder)

    def update_defects_report_display(self, wood_number, wood_folder):
        """Update the defects report textbox in the main GUI"""
        defects_file_path = os.path.join(wood_folder, "defects.txt")
        
        # Read the defects file
        try:
            with open(defects_file_path, "r") as f:
                defects_content = f.read()
        except Exception as e:
            print(f"Error reading defects file: {e}")
            return
        
        # Update the textbox
        self.defects_report_textbox.configure(state="normal")
        self.defects_report_textbox.delete("1.0", "end")
        self.defects_report_textbox.insert("1.0", defects_content)
        self.defects_report_textbox.configure(state="disabled")
        
        # Store the latest wood folder path for the "View Folder" button
        self.latest_wood_folder = wood_folder
        
        print(f"Updated defects report display for Wood {wood_number}")
    
    def view_latest_wood_folder(self):
        """Open the latest graded wood folder or main session folder in File Explorer"""
        folder_to_open = None
        
        # First priority: Open latest graded wood folder if it exists (check for None!)
        if hasattr(self, 'latest_wood_folder') and self.latest_wood_folder is not None and os.path.exists(self.latest_wood_folder):
            folder_to_open = self.latest_wood_folder
        # Second priority: Open main session folder if it exists (check for None!)
        elif hasattr(self, 'scan_session_folder') and self.scan_session_folder is not None and os.path.exists(self.scan_session_folder):
            folder_to_open = self.scan_session_folder
        # Fallback: Create and open main detections folder
        else:
            detections_folder = os.path.join("testIR", "Detections")
            os.makedirs(detections_folder, exist_ok=True)
            folder_to_open = detections_folder
        
        # Open the selected folder
        try:
            # Cross-platform file explorer opening
            if os.name == 'nt':  # Windows
                subprocess.Popen(['explorer', folder_to_open])
            elif os.name == 'posix':  # Linux/Mac
                subprocess.Popen(['xdg-open', folder_to_open])
            else:
                raise OSError("Unsupported operating system")
        except Exception as e:
            print(f"Error opening folder: {e}")
            self.show_toast_notification(
                "❌ Error Opening Folder",
                f"Could not open folder:\n{str(e)[:100]}",
                duration=5000,
                type="error"
            )
    
    def update_wood_counter_display(self):
        """Update the wood counter label in the GUI"""
        if hasattr(self, 'wood_counter_label'):
            wood_num = self.current_wood_number if hasattr(self, 'current_wood_number') else 0
            self.wood_counter_label.configure(text=f"🪵 Current Wood: #{wood_num}")

    def _display_frame_on_canvas(self, frame, canvas):
        """Convert frame to PhotoImage and display on canvas at 360p resolution, centered"""
        try:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Convert to PIL Image
            pil_image = Image.fromarray(frame_rgb)

            # Always resize to 360p (640x360) resolution for display
            display_width = 640
            display_height = 360
            pil_image = pil_image.resize((display_width, display_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(pil_image)

            # Properly manage old PhotoImage references to prevent memory leaks
            if not hasattr(self, '_old_photos'):
                self._old_photos = []
            
            # Store reference to prevent garbage collection and manage old ones
            if canvas == self.top_canvas:
                if self._top_photo is not None:
                    self._old_photos.append(self._top_photo)
                self._top_photo = photo
            elif canvas == self.bottom_canvas:
                if self._bottom_photo is not None:
                    self._old_photos.append(self._bottom_photo)
                self._bottom_photo = photo

            # Clear canvas and display on canvas, centered
            canvas.delete("all")  # Clear any existing content

            # Calculate center position
            canvas_width = self.canvas_width
            canvas_height = self.canvas_height
            x = (canvas_width - display_width) // 2
            y = (canvas_height - display_height) // 2

            canvas.create_image(x, y, anchor=tk.NW, image=photo)

        except Exception as e:
            print(f"Error displaying frame on canvas: {e}")
            import traceback
            traceback.print_exc()

    def display_captured_frames(self, top_frame, bottom_frame):
        """Display captured frames with overlays in the UI canvases."""
        print("Displaying processed frames from detection phase...")
        
        # Convert to PhotoImage and display both processed frames immediately
        self._display_frame_on_canvas(top_frame, self.top_canvas)
        self._display_frame_on_canvas(bottom_frame, self.bottom_canvas)

        # Set flag to indicate we're displaying processed frames
        self.displaying_processed_frame = True

        # Schedule live feed resumption after 3000ms (3 seconds)
        if self.processed_frame_timer:
            self.after_cancel(self.processed_frame_timer)
        self.processed_frame_timer = self.after(3000, self.resume_live_feed)
        
        print("Processed frames displayed for 3 seconds before resuming live feed")

    def resume_live_feed(self):
        """Resume live feed after processed frame display period"""
        self.displaying_processed_frame = False
        self.processed_frame_timer = None
        print("Resumed live feed after processed frame display")

    def grade_all_woods(self):
        """Grade all detected woods after scan phase completion using segment defect data."""
        print("Grading all detected woods from segment data...")

        # Only process if we have exactly one wood piece (current implementation processes all segments as one wood)
        if self.current_wood_number > 0:
            wood_num = self.current_wood_number  # Process only the current wood
            print(f"Processing Wood {wood_num}...")

            # Collect all defects from all segments for this wood piece
            wood_top_defects = []
            wood_bottom_defects = []

            # Aggregate defects from all segments
            print(f"🔍 STRICT AGGREGATION: Processing {len(self.segment_defects['top'])} top segments and {len(self.segment_defects['bottom'])} bottom segments")
            
            total_annotated_top = 0
            total_annotated_bottom = 0
            
            for i, segment_data in enumerate(self.segment_defects["top"]):
                if segment_data.get("measurements"):
                    segment_defects = segment_data["measurements"]
                    detected_count = segment_data.get("detected_count", len(segment_defects))
                    total_annotated_top += detected_count
                    print(f"🔍 TOP Segment {i+1}: {len(segment_defects)} stored, {detected_count} detected")
                    wood_top_defects.extend(segment_defects)

            for i, segment_data in enumerate(self.segment_defects["bottom"]):
                if segment_data.get("measurements"):
                    segment_defects = segment_data["measurements"]
                    detected_count = segment_data.get("detected_count", len(segment_defects))
                    total_annotated_bottom += detected_count
                    print(f"🔍 BOTTOM Segment {i+1}: {len(segment_defects)} stored, {detected_count} detected")
                    wood_bottom_defects.extend(segment_defects)
            
            print(f"🔍 STRICT AGGREGATION SUMMARY:")
            print(f"   Top: {len(wood_top_defects)} stored vs {total_annotated_top} detected")
            print(f"   Bottom: {len(wood_bottom_defects)} stored vs {total_annotated_bottom} detected")
            print(f"🔍 TOTAL: {len(wood_top_defects) + len(wood_bottom_defects)} raw defects collected")

            # Deduplicate defects before grading to prevent overcounting
            # Convert defect tuples to detection dicts for deduplication
            top_detections_for_dedup = []
            bottom_detections_for_dedup = []

            # Create detection dicts with proper ISO timestamps based on segment order
            base_time = datetime.now()
            segment_timestamp = 0
            for segment_data in self.segment_defects["top"]:
                if segment_data.get("measurements"):
                    segment_time = base_time + timedelta(seconds=segment_timestamp)
                    for defect_type, size_mm, percentage in segment_data["measurements"]:
                        top_detections_for_dedup.append({
                            'timestamp': segment_time.isoformat(),
                            'defect_type': defect_type,
                            'size_mm': size_mm,
                            'percentage': percentage,
                            'segment': segment_data.get("segment", 0)  # Add segment info for better deduplication
                        })
                segment_timestamp += 0.1  # Increment timestamp for each segment

            segment_timestamp = 0
            for segment_data in self.segment_defects["bottom"]:
                if segment_data.get("measurements"):
                    segment_time = base_time + timedelta(seconds=segment_timestamp)
                    for defect_type, size_mm, percentage in segment_data["measurements"]:
                        bottom_detections_for_dedup.append({
                            'timestamp': segment_time.isoformat(),
                            'defect_type': defect_type,
                            'size_mm': size_mm,
                            'percentage': percentage,
                            'segment': segment_data.get("segment", 0)  # Add segment info for better deduplication
                        })
                segment_timestamp += 0.1  # Increment timestamp for each segment

            # STRICT RULE: NO DEDUPLICATION - Annotations must match defects.txt exactly
            print(f"🔍 STRICT MODE: Preserving ALL annotated defects without deduplication")
            print(f"🔍 DEBUG: Total detections - Top: {len(top_detections_for_dedup)}, Bottom: {len(bottom_detections_for_dedup)}")
            
            # Use ALL detections without any deduplication to ensure annotation-recording synchronization
            deduplicated_top = top_detections_for_dedup  # No deduplication
            deduplicated_bottom = bottom_detections_for_dedup  # No deduplication

            # Convert back to defect tuples for grading
            deduplicated_top_defects = [(d['defect_type'], d['size_mm'], d['percentage']) for d in deduplicated_top]
            deduplicated_bottom_defects = [(d['defect_type'], d['size_mm'], d['percentage']) for d in deduplicated_bottom]

            print(f"🔍 STRICT MODE: After NO deduplication - Top: {len(deduplicated_top_defects)} defects, Bottom: {len(deduplicated_bottom_defects)} defects")
            print(f"🔍 STRICT MODE: Final top defects for recording: {deduplicated_top_defects}")
            print(f"🔍 STRICT MODE: Final bottom defects for recording: {deduplicated_bottom_defects}")
            print(f"✅ STRICT RULE ENFORCED: All {len(wood_top_defects)} top + {len(wood_bottom_defects)} bottom annotated defects will be recorded")

            # Store deduplicated defects in scan session data
            # CRITICAL: Use the authoritative WOOD_PALLET_WIDTH_MM (which follows detected_width_mm)
            wood_width = WOOD_PALLET_WIDTH_MM if WOOD_PALLET_WIDTH_MM > 0 else 100  # Use current detected width
            print(f"🔗 Grading synchronization: Using wood_width={wood_width:.1f}mm (from WOOD_PALLET_WIDTH_MM={WOOD_PALLET_WIDTH_MM:.1f}mm)")
            print(f"🔍 Confirming detected_width_mm authority: wood_width={wood_width:.1f}mm follows detected_width_mm")
            
            self.scan_session_data[wood_num] = {
                'top_defects': deduplicated_top_defects,
                'bottom_defects': deduplicated_bottom_defects,
                'width_mm': wood_width  # This stores the detected_width_mm value
            }

            # Grade the wood piece using PineGrader
            # Use wood width for this piece
            grader = SSEN1611_1_PineGrader_Final(width_mm=wood_width)

            # Get grades from PineGrader
            all_measurements = deduplicated_top_defects + deduplicated_bottom_defects
            top_grade = grader.determine_surface_grade(deduplicated_top_defects)
            bottom_grade = grader.determine_surface_grade(deduplicated_bottom_defects)
            final_grade = grader.determine_final_grade(deduplicated_top_defects, deduplicated_bottom_defects)

            # Save final defect data (this will also display the popup)
            self.save_final_wood_data(wood_num, top_grade, bottom_grade, final_grade)

            print(f"Wood {wood_num}: Top={top_grade}, Bottom={bottom_grade}, Final={final_grade}")
            print(f"  Total defects: Top={len(wood_top_defects)}, Bottom={len(wood_bottom_defects)}")

            # Update live grades for UI display (per-side grading)
            self.live_grades["top"] = {
                'grade': top_grade,
                'text': f'{top_grade} - SS-EN 1611-1 (Top Camera)',
                'color': self.get_grade_color(top_grade)
            }
            self.live_grades["bottom"] = {
                'grade': bottom_grade,
                'text': f'{bottom_grade} - SS-EN 1611-1 (Bottom Camera)',
                'color': self.get_grade_color(bottom_grade)
            }

            # Update the live grading display to show per-side grades
            self.update_live_grading_display()

            # Only call finalize_grading once for this wood piece
            self.finalize_grading(final_grade, all_measurements)
            
            # Clear segment defects after processing to prevent reprocessing
            self.segment_defects = {"top": [], "bottom": []}
            print(f"Cleared segment defects after processing Wood {wood_num}")

        self.scan_phase_active = False
        self.update_status_text("Status: SCAN_PHASE completed - grading finished", STATUS_READY_COLOR)

    def _scan_mode_deduplicate(self, detections):
        """Conservative deduplication for scan mode - only remove true duplicates within same segment"""
        if not detections:
            return []
        
        # Group detections by segment first
        segments = {}
        for detection in detections:
            segment_id = detection.get('segment', 0)
            if segment_id not in segments:
                segments[segment_id] = []
            segments[segment_id].append(detection)
        
        # Only deduplicate within each segment, preserve all cross-segment detections
        deduplicated = []
        for segment_id, segment_detections in segments.items():
            print(f"🔍 DEBUG: Processing segment {segment_id} with {len(segment_detections)} detections")
            
            # For each segment, only remove exact duplicates (same type, very similar size)
            segment_unique = []
            for detection in segment_detections:
                is_duplicate = False
                for existing in segment_unique:
                    if (detection['defect_type'] == existing['defect_type'] and
                        abs(detection['size_mm'] - existing['size_mm']) < 2.0):  # Very strict threshold
                        print(f"🔍 DEBUG: Removing duplicate in segment {segment_id}: {detection['defect_type']} {detection['size_mm']:.1f}mm (similar to {existing['size_mm']:.1f}mm)")
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    segment_unique.append(detection)
            
            print(f"🔍 DEBUG: Segment {segment_id}: {len(segment_detections)} -> {len(segment_unique)} after conservative deduplication")
            deduplicated.extend(segment_unique)
        
        return deduplicated

    def finalize_grading(self, final_grade, all_measurements):
        """Central function to log piece details, update stats, and send Arduino command."""
        # 1. Convert grade to Arduino command for sorting and stats
        arduino_command = self.convert_grade_to_arduino_command(final_grade)

        # 2. Increment piece count and create log entry
        self.total_pieces_processed += 1
        piece_number = self.total_pieces_processed
        
        defects_for_log = []
        if all_measurements:
            # Summarize defects for cleaner logging
            defect_summary = {}
            for defect_type, size_mm, percentage in all_measurements:
                # Group defects by type
                if defect_type not in defect_summary:
                    defect_summary[defect_type] = {'count': 0, 'sizes_mm': []}
                defect_summary[defect_type]['count'] += 1
                defect_summary[defect_type]['sizes_mm'].append(f"{size_mm:.1f}")

            # Format the summary for the log
            for defect_type, data in defect_summary.items():
                defects_for_log.append({
                    'type': defect_type.replace('_', ' '),
                    'count': data['count'],
                    'sizes': ', '.join(data['sizes_mm'])
                })
        
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "piece_number": piece_number,
            "final_grade": final_grade,
            "defects": defects_for_log
        }
        self.session_log.append(log_entry)

        # 3. Update UI statistics (count by grade, not by command)
        grade_to_stat_index = {
            GRADE_G2_0: 1,
            GRADE_G2_1: 2,
            GRADE_G2_2: 3,
            GRADE_G2_3: 4,
            GRADE_G2_4: 5
        }
        stat_index = grade_to_stat_index.get(final_grade, 5)
        self.grade_counts[stat_index] += 1
        self.live_stats[f"grade{stat_index}"] += 1
        self.update_live_stats_display()

        # 4. Send command to Arduino if it's connected with voltage drop protection
        if self.ser and self.ser.is_open:
            print(f"🔋 Preparing to send grading command '{arduino_command}' with voltage drop protection")
            print(f"Final grading: Top={self.live_grades.get('top', {}).get('grade', 'Unknown')}, Bottom={self.live_grades.get('bottom', {}).get('grade', 'Unknown')}, Final={final_grade}")
            
            # Pre-grading system stabilization
            print("🔋 Pre-grading stabilization: Ensuring power system is ready for sorting mechanism")
            time.sleep(0.3)  # Brief stabilization before sending grading command
            
            self.send_arduino_command(str(arduino_command))
        else:
            print("Arduino not connected. Command not sent.")

        # 5. Update status label and console
        status_text = f"Piece #{piece_number} Graded: {final_grade} (Cmd: {arduino_command})"
        print(f"✅ Grading Finalized - {status_text}")
        self.update_status_text(f"Status: {status_text}", STATUS_READY_COLOR)
        self.log_action(f"Graded Piece #{piece_number} as {final_grade} -> Arduino Cmd: {arduino_command}")


    def _execute_manual_grade(self):
        """Execute manual grading based on current detections."""
        wood_detected = False
        all_measurements = self.live_measurements.get("top", []) + self.live_measurements.get("bottom", [])

        if all_measurements:
            wood_detected = True

        if wood_detected:
            # Use current wood width (default to 100mm if not detected)
            # CRITICAL: WOOD_PALLET_WIDTH_MM follows detected_width_mm as the authoritative source
            wood_width = WOOD_PALLET_WIDTH_MM if WOOD_PALLET_WIDTH_MM > 0 else 100
            print(f"🔗 Manual grading synchronization: Using wood_width={wood_width:.1f}mm (from WOOD_PALLET_WIDTH_MM={WOOD_PALLET_WIDTH_MM:.1f}mm)")
            print(f"🔍 Authority chain: detected_width_mm → WOOD_PALLET_WIDTH_MM → wood_width = {wood_width:.1f}mm")

            # Create grader instance
            grader = SSEN1611_1_PineGrader_Final(width_mm=wood_width)

            # Get final grade from PineGrader
            final_grade = grader.determine_final_grade(
                self.live_measurements.get("top", []),
                self.live_measurements.get("bottom", [])
            )
            print(f"Manual grade trigger - SS-EN 1611-1 Final grade: {final_grade}")
            self.finalize_grading(final_grade, all_measurements)
        else:
            print("Manual grade trigger - No wood currently detected")
            # status_label is a Text widget, not a Label widget
            self.status_label.config(state=tk.NORMAL)
            self.status_label.delete(1.0, tk.END)
            self.status_label.insert(1.0, "Status: Manual grade - no wood detected")
            self.status_label.config(state=tk.DISABLED)

    def bbox_inside_roi(self, bbox, roi, overlap_threshold=0.7):
        """
        Check if a bounding box has significant overlap with ROI (>70% by default)
        This allows large defects near wood edges to be detected
        
        Args:
            bbox: Detection bounding box [x1, y1, x2, y2] or tuple
            roi: ROI tuple (x, y, w, h) from Dynamic Wood ROI
            overlap_threshold: Minimum overlap ratio to accept (default 0.7 = 70%)
            
        Returns:
            bool: True if bbox has significant overlap with ROI, False otherwise
        """
        if roi is None:
            # If no ROI defined, accept all detections (fallback)
            return True
        
        # Unpack ROI
        roi_x, roi_y, roi_w, roi_h = roi
        roi_x2 = roi_x + roi_w
        roi_y2 = roi_y + roi_h
        
        # Unpack detection bbox (handle both list and tuple formats)
        if len(bbox) == 4:
            det_x1, det_y1, det_x2, det_y2 = bbox
        else:
            # Fallback for unexpected format
            return True
        
        # Calculate intersection area
        intersect_x1 = max(det_x1, roi_x)
        intersect_y1 = max(det_y1, roi_y)
        intersect_x2 = min(det_x2, roi_x2)
        intersect_y2 = min(det_y2, roi_y2)
        
        # Check if there's any intersection
        if intersect_x2 <= intersect_x1 or intersect_y2 <= intersect_y1:
            return False  # No overlap at all
        
        # Calculate intersection area
        intersect_area = (intersect_x2 - intersect_x1) * (intersect_y2 - intersect_y1)
        
        # Calculate detection bbox area
        det_area = (det_x2 - det_x1) * (det_y2 - det_y1)
        
        # Calculate overlap ratio
        if det_area <= 0:
            return False
        
        overlap_ratio = intersect_area / det_area
        
        # Accept if significant overlap (default 70%)
        return overlap_ratio >= overlap_threshold

    def resize_to_640(self, frame):
        """
        Resize frame to 640x640 WITH PADDING to maintain aspect ratio
        This prevents distortion of defects (copied from live_inference.py)
        
        Returns:
            resized_frame: 640x640 image with padding
            scale: uniform scale factor used
            pad_x: left padding pixels
            pad_y: top padding pixels
        """
        h, w = frame.shape[:2]
        MODEL_INPUT_SIZE = 640
        
        # Calculate scale to fit the larger dimension to 640
        scale = MODEL_INPUT_SIZE / max(h, w)
        
        # Calculate new dimensions
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize maintaining aspect ratio
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Create black canvas 640x640
        canvas = np.zeros((MODEL_INPUT_SIZE, MODEL_INPUT_SIZE, 3), dtype=np.uint8)
        
        # Calculate padding to center the image
        pad_x = (MODEL_INPUT_SIZE - new_w) // 2
        pad_y = (MODEL_INPUT_SIZE - new_h) // 2
        
        # Place resized image on canvas
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        
        return canvas, scale, pad_x, pad_y

    def analyze_frame(self, frame, camera_name="top", run_defect_model=True):
        """Analyze frame using DeGirum model with object tracking and error detection"""
        if self.model is None:
            self.register_error("MODEL_LOADING_FAILED", "DeGirum model not loaded")
            return frame, {}, [], []

        try:
            # Get original frame dimensions
            original_h, original_w = frame.shape[:2]
            print(f"🖼️  Analyzing frame: {original_w}x{original_h}, camera: {camera_name}")
            
            # Resize frame to 640x640 with padding (maintains aspect ratio)
            frame_640, scale, pad_x, pad_y = self.resize_to_640(frame)
            print(f"📐 Resized to 640x640 with padding: scale={scale:.3f}, pad_x={pad_x}, pad_y={pad_y}")
            
            # Run inference using DeGirum on padded 640x640 frame
            inference_result = self.model(frame_640)
            
            # Debug: Print all raw detections with area information
            print(f"📊 RAW DETECTIONS [{camera_name}] (total: {len(inference_result.results)}):")
            for i, det in enumerate(inference_result.results):
                label = det.get('label', 'unknown')
                confidence = det.get('confidence', 0.0)
                bbox = det.get('bbox', [0, 0, 0, 0])
                bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                bbox_width = bbox[2] - bbox[0]
                bbox_height = bbox[3] - bbox[1]
                print(f"   #{i+1}: {label} @ {confidence:.3f} | bbox: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}] | size: {bbox_width:.0f}x{bbox_height:.0f} (area={bbox_area:.0f}px²)")            # Get Dynamic Wood ROI for filtering detections
            dynamic_wood_roi = self.dynamic_roi.get(camera_name)
            
            # Process detections for object tracking
            current_detections = []
            low_confidence_count = 0
            uncertain_confidence_count = 0  # Track 25-30% range for Test Case 3.1
            rejected_by_roi = 0
            
            for det in inference_result.results:
                model_label = det['label']
                bbox = det['bbox']
                confidence = det.get('confidence', 0.7)

                # WORKAROUND: Accept 0.000 confidence (Hailo-8 quantization bug - these ARE valid detections)
                # For non-zero confidence, apply threshold filtering
                # Reject detections with low confidence (0 < confidence < MIN_CONFIDENCE)
                if confidence != 0.0 and confidence < self.DETECTION_THRESHOLDS["MIN_CONFIDENCE"]:
                    low_confidence_count += 1
                    print(f"   ❌ Rejected (low confidence): {model_label} @ {confidence:.3f}")
                    continue  # Skip low confidence detections

                # Test Case 3.1: Track uncertain detections (25-30% confidence range)
                # These represent poor image quality or unclear defects
                if 0.25 <= confidence <= 0.30:
                    uncertain_confidence_count += 1
                    print(f"   ⚠️  UNCERTAIN detection (Test Case 3.1): {model_label} @ {confidence:.3f} - Low confidence accepted")

                # Adjust bounding box coordinates from 640x640 padded back to original frame
                # Remove padding offset and apply inverse scale
                x1 = (bbox[0] - pad_x) / scale
                y1 = (bbox[1] - pad_y) / scale
                x2 = (bbox[2] - pad_x) / scale
                y2 = (bbox[3] - pad_y) / scale
                
                # Clip to original frame bounds
                x1 = max(0, min(x1, original_w))
                y1 = max(0, min(y1, original_h))
                x2 = max(0, min(x2, original_w))
                y2 = max(0, min(y2, original_h))
                
                # Only keep detections that are within the valid area (not in padding)
                if x2 <= x1 or y2 <= y1:
                    print(f"   ⚠️  Skipping detection in padding area: {model_label}")
                    continue
                
                # Create adjusted bbox in original frame coordinates
                adjusted_bbox = [x1, y1, x2, y2]
                
                # ✅ NEW: Filter detections by Wood ROI - accept if 70%+ overlap with wood area
                if not self.bbox_inside_roi(adjusted_bbox, dynamic_wood_roi):
                    rejected_by_roi += 1
                    standard_defect_type = self.map_model_output_to_standard(model_label)
                    # Calculate overlap percentage for debugging
                    det_w = x2 - x1
                    det_h = y2 - y1
                    if dynamic_wood_roi:
                        roi_x, roi_y, roi_w, roi_h = dynamic_wood_roi
                        roi_x2, roi_y2 = roi_x + roi_w, roi_y + roi_h
                        # Calculate intersection
                        intersect_x1 = max(x1, roi_x)
                        intersect_y1 = max(y1, roi_y)
                        intersect_x2 = min(x2, roi_x2)
                        intersect_y2 = min(y2, roi_y2)
                        if intersect_x2 > intersect_x1 and intersect_y2 > intersect_y1:
                            intersect_area = (intersect_x2 - intersect_x1) * (intersect_y2 - intersect_y1)
                            det_area = det_w * det_h
                            overlap_pct = (intersect_area / det_area * 100) if det_area > 0 else 0
                        else:
                            overlap_pct = 0
                        roi_str = f"ROI={dynamic_wood_roi}, overlap={overlap_pct:.1f}%"
                    else:
                        roi_str = "ROI=None"
                    print(f"   🚫 Rejected (low Wood ROI overlap): {standard_defect_type} @ [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}] size={det_w:.0f}x{det_h:.0f}, {roi_str}")
                    continue
                
                bbox_info = {'bbox': adjusted_bbox}

                # Calculate defect size in mm and percentage using camera-specific calibration
                size_mm, percentage = self.calculate_defect_size(bbox_info, camera_name)

                # Map to standard defect type
                standard_defect_type = self.map_model_output_to_standard(model_label)

                # Prepare detection for tracker (bbox, defect_type, size_mm, confidence)
                current_detections.append((adjusted_bbox, standard_defect_type, size_mm, confidence))

            print(f"🔍 Filtered detections [{camera_name}]: {len(current_detections)} (0.000 always accepted, others >= {self.DETECTION_THRESHOLDS['MIN_CONFIDENCE']})")
            if low_confidence_count > 0:
                print(f"   ❌ Rejected by confidence filter: {low_confidence_count} detection(s)")
            if rejected_by_roi > 0:
                print(f"   🚫 Rejected by Wood ROI filter: {rejected_by_roi} detection(s)")

            # Test Case 3.1: Alert operator for uncertain detections (25-30% confidence)
            if uncertain_confidence_count > 0:
                warning_msg = f"⚠️ Low confidence detection: {uncertain_confidence_count} uncertain detection(s) (25-30% confidence) on {camera_name} camera"
                print(warning_msg)
                # Show warning notification for operator review
                try:
                    self.show_toast_notification(
                        "⚠️ Low Confidence Detection",
                        f"{uncertain_confidence_count} low confidence detection(s) on {camera_name} camera",
                        duration=6000,
                        type="warning"
                    )
                except Exception as e:
                    print(f"Could not show warning notification: {e}")
            
            # Also notify if rejected detections were found (for debugging)
            elif low_confidence_count > 0:
                print(f"   📊 Info: {low_confidence_count} detection(s) rejected (<25% confidence) on {camera_name} camera")

            # Check for wood detection issues (if this is a wood detection analysis)
            if run_defect_model and hasattr(self, 'wood_detection_results'):
                self.check_wood_detection_status(frame, camera_name)

            # Filter overlapping detections to prevent multiple detections in same area
            print(f"🔄 Before overlap filter: {len(current_detections)} detection(s)")
            filtered_detections = self.filter_overlapping_detections(current_detections, overlap_threshold=0.3)
            if len(filtered_detections) < len(current_detections):
                removed = len(current_detections) - len(filtered_detections)
                print(f"   ⚠️  Overlap filter removed {removed} detection(s) (IoU > 0.3)")

            # Check for plank alignment issues
            if filtered_detections:
                self.check_plank_alignment(filtered_detections, frame, camera_name)

            # Process filtered detections for grading
            detections_for_grading = []
            final_defect_dict = {}

            for bbox, defect_type, size_mm, confidence in filtered_detections:
                # Use detection information directly for grading (already within cropped area)
                # Round to 1 decimal place for consistent formatting
                size_mm_rounded = round(size_mm, 1)
                detections_for_grading.append((defect_type, size_mm_rounded, 0.0))  # percentage not needed for grading

                # Count by defect type for display
                if defect_type in final_defect_dict:
                    final_defect_dict[defect_type] += 1
                else:
                    final_defect_dict[defect_type] = 1

            # Create custom annotated frame with defect names and size measurements
            annotated_frame = self.draw_custom_annotations(frame, filtered_detections, camera_name)

            return annotated_frame, final_defect_dict, detections_for_grading

        except Exception as e:
            print(f"Error during DeGirum inference on {camera_name} camera: {e}")
            return frame, {}, []

    def draw_custom_annotations(self, frame, detections, camera_name="top"):
        """Draw custom annotations with defect names and size measurements"""
        annotated_frame = frame.copy()
        frame_height, frame_width = frame.shape[:2]
        
        for bbox, defect_type, size_mm, confidence in detections:
            x1, y1, x2, y2 = bbox
            
            # Get color based on defect type
            color = self.get_color_for_defect(defect_type)
            
            # Draw bounding box with defect-specific color
            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # Get display name with grading category
            display_name = self.get_display_name_for_defect(defect_type)
            
            # Create label with display name and size measurement
            label = f"{display_name} - {size_mm:.1f}mm"
            
            # Add confidence if it's reasonably high
            if confidence > 0.5:
                label += f" ({confidence:.2f})"
            
            # Calculate text size for background
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            
            # Smart text positioning to ensure it stays within frame bounds
            text_x = int(x1)
            text_y = int(y1) - 10
            
            # Adjust horizontal position if text would go outside frame
            if text_x + text_width > frame_width:
                text_x = frame_width - text_width - 5
            if text_x < 0:
                text_x = 5
            
            # Adjust vertical position if text would go outside frame
            if text_y < text_height + baseline:
                # Place text below the bounding box if it would go above frame
                text_y = int(y2) + text_height + baseline + 10
                # If that would also go outside frame, place it inside the box
                if text_y > frame_height - 5:
                    text_y = int(y1) + text_height + baseline + 5
            
            # Ensure text doesn't go below frame
            if text_y > frame_height - 5:
                text_y = frame_height - 10
            
            # Draw background rectangle for text with proper bounds checking (same color as bounding box)
            bg_x1 = max(0, text_x)
            bg_y1 = max(0, text_y - text_height - baseline)
            bg_x2 = min(frame_width, text_x + text_width)
            bg_y2 = min(frame_height, text_y + baseline)
            
            cv2.rectangle(annotated_frame, 
                         (bg_x1, bg_y1),
                         (bg_x2, bg_y2),
                         color, -1)
            
            # Draw text (black text for good contrast on colored backgrounds)
            cv2.putText(annotated_frame, label, (text_x, text_y), 
                       font, font_scale, (0, 0, 0), thickness)
        
        return annotated_frame

    def filter_overlapping_detections(self, detections, overlap_threshold=0.3):
        """Filter overlapping detections, keeping only the most confident one per area"""
        if len(detections) <= 1:
            return detections
        
        def calculate_iou(box1, box2):
            """Calculate Intersection over Union (IoU) of two bounding boxes"""
            x1_1, y1_1, x2_1, y2_1 = box1
            x1_2, y1_2, x2_2, y2_2 = box2
            
            # Calculate intersection
            x1_i = max(x1_1, x1_2)
            y1_i = max(y1_1, y1_2)
            x2_i = min(x2_1, x2_2)
            y2_i = min(y2_1, y2_2)
            
            if x2_i <= x1_i or y2_i <= y1_i:
                return 0.0
            
            intersection = (x2_i - x1_i) * (y2_i - y1_i)
            
            # Calculate areas
            area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
            area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
            union = area1 + area2 - intersection
            
            return intersection / union if union > 0 else 0.0
        
        # Sort detections by confidence (highest first)
        sorted_detections = sorted(detections, key=lambda x: x[3], reverse=True)
        
        filtered_detections = []
        
        for detection in sorted_detections:
            bbox, defect_type, size_mm, confidence = detection
            
            # Check if this detection overlaps significantly with any already selected detection
            is_overlapping = False
            for selected_detection in filtered_detections:
                selected_bbox = selected_detection[0]
                iou = calculate_iou(bbox, selected_bbox)
                
                if iou > overlap_threshold:
                    is_overlapping = True
                    break
            
            # Only add if it doesn't overlap significantly with existing detections
            if not is_overlapping:
                filtered_detections.append(detection)
        
        return filtered_detections

    def log_action(self, message):
        """Log actions to file with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} - {message}\n"
            
            with open("wood_sorting_activity_log.txt", "a") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error logging action: {e}")

    def update_live_stats_display(self):
        """Update the live statistics display with enhanced tabbed interface and thread safety"""
        # Skip update if currently in active inference to prevent UI conflicts
        if getattr(self, '_in_active_inference', False):
            return
            
        # Safety check to ensure all required attributes exist
        if not hasattr(self, 'live_stats'):
            self.live_stats = {"grade0": 0, "grade1": 0, "grade2": 0, "grade3": 0}
        if not hasattr(self, 'live_stats_labels'):
            return  # Skip update if labels aren't initialized yet
            
        # Update basic grade counts in the Grade Summary tab with error handling
        try:
            for grade_key, count in self.live_stats.items():
                if grade_key in self.live_stats_labels and self.live_stats_labels[grade_key].winfo_exists():
                    # Use after_idle to ensure UI updates happen on main thread
                    self.after_idle(lambda key=grade_key, cnt=count: 
                                  self._safe_update_label(key, cnt))
        except Exception as e:
            print(f"Error updating live stats display: {e}")
        
        # Update other tabs with thread safety
        try:
            self.update_grade_details_tab()
            self.update_performance_tab()
        except Exception as e:
            print(f"Error updating statistics tabs: {e}")
    
    def _safe_update_label(self, grade_key, count):
        """Safely update a label with error handling"""
        try:
            if (grade_key in self.live_stats_labels and 
                self.live_stats_labels[grade_key].winfo_exists()):
                self.live_stats_labels[grade_key].configure(text=str(count))
        except Exception as e:
            print(f"Error updating label {grade_key}: {e}")

    def update_grade_details_tab(self):
        """Update the Grade Details tab with current grade information"""
        if not hasattr(self, 'grading_details_frame'):
            return
            
        # Clear existing content
        for widget in self.grading_details_frame.winfo_children():
            widget.destroy()
        
        # Use dark theme colors from configuration
        tab_bg = FRAME_BACKGROUND_COLOR
        text_color = TEXT_COLOR
        
        # Calculate dynamic thresholds based on current wood width
        wood_width = WOOD_PALLET_WIDTH_MM if WOOD_PALLET_WIDTH_MM > 0 else 115  # Default to 115mm if not detected

        threshold_text = f"SS-EN 1611-1 Pine Timber Grading Standard (Official Implementation)\n"
        threshold_text += f"Current Wood Width: {wood_width:.1f}mm\n\n"
        
        threshold_text += "GRADING CRITERIA (G2-0 = Best Quality):\n"
        threshold_text += "• G2-0 (Good): Max 2 knots/meter, 0 unsound knots\n"
        threshold_text += "• G2-1 (Good): Max 4 knots/meter, 0 unsound knots\n"
        threshold_text += "• G2-2 (Fair): Max 6 knots/meter, 2 unsound knots\n"
        threshold_text += "• G2-3 (Poor): Unlimited knots, 5 unsound knots max\n"
        threshold_text += "• G2-4 (Poor): Unlimited knots and defects\n\n"
        
        threshold_text += "KNOT SIZE LIMITS (Formula: 10% × Width + Constant):\n\n"

        # Calculate size adjustment for display
        size_adjustment = 10 if wood_width >= 180 else 0
        adjustment_note = f" (+{size_adjustment}mm for ≥180mm width)" if size_adjustment > 0 else ""

        # Sound Knots thresholds
        sound_limits = {}
        for grade, constant in GRADING_CONSTANTS["Sound_Knot"].items():
            limit = (0.10 * wood_width) + constant + size_adjustment
            sound_limits[grade] = limit

        threshold_text += f"Sound Knots (Live Knots){adjustment_note}:\n"
        threshold_text += f"  G2-0: ≤{sound_limits.get('G2-0', 21.5):.1f}mm | G2-1: ≤{sound_limits.get('G2-1', 31.5):.1f}mm | G2-2: ≤{sound_limits.get('G2-2', 46.5):.1f}mm | G2-3: ≤{sound_limits.get('G2-3', 61.5):.1f}mm\n\n"

        # Dead Knots thresholds
        dead_limits = {}
        for grade, constant in GRADING_CONSTANTS["Dead_Knot"].items():
            limit = (0.10 * wood_width) + constant + size_adjustment
            dead_limits[grade] = limit

        threshold_text += f"Dead Knots{adjustment_note}:\n"
        threshold_text += f"  G2-0: ≤{dead_limits.get('G2-0', 11.5):.1f}mm | G2-1: ≤{dead_limits.get('G2-1', 21.5):.1f}mm | G2-2: ≤{dead_limits.get('G2-2', 31.5):.1f}mm | G2-3: ≤{dead_limits.get('G2-3', 61.5):.1f}mm\n\n"

        # Unsound Knots thresholds (includes Crack Knots)
        unsound_limits = {}
        for grade, constant in GRADING_CONSTANTS["Unsound_Knot"].items():
            limit = (0.10 * wood_width) + constant + size_adjustment
            unsound_limits[grade] = limit

        threshold_text += f"Unsound/Missing Knots (incl. Knots with Cracks){adjustment_note}:\n"
        threshold_text += f"  G2-0: NOT PERMITTED | G2-1: NOT PERMITTED\n"
        threshold_text += f"  G2-2: ≤{unsound_limits.get('G2-2', 25.5):.1f}mm | G2-3: ≤{unsound_limits.get('G2-3', 50.5):.1f}mm\n\n"

        # Number adjustments
        number_adjustment = 1.5 if wood_width > 225 else 1.0
        number_note = f" (×{number_adjustment:.1f} for >225mm width)" if number_adjustment > 1.0 else ""

        threshold_text += f"KNOT FREQUENCY LIMITS (Per Meter){number_note}:\n"
        threshold_text += f"  G2-0: Max {int(2 * number_adjustment)} total knots, 0 unsound\n"
        threshold_text += f"  G2-1: Max {int(4 * number_adjustment)} total knots, 0 unsound\n"
        threshold_text += f"  G2-2: Max {int(6 * number_adjustment)} total knots, 2 unsound\n"
        threshold_text += f"  G2-3: Unlimited total knots, 5 unsound max\n"
        threshold_text += f"  G2-4: Unlimited both\n\n"

        threshold_text += "WIDTH-BASED ADJUSTMENTS:\n"
        threshold_text += "• Size Adjustment: +10mm to ALL knot limits if width ≥ 180mm\n"
        threshold_text += "• Number Adjustment: +50% to total knot limits if width > 225mm\n"
        threshold_text += "• Unsound knot frequency limits are NOT adjusted\n\n"

        threshold_text += "GRADING LOGIC:\n"
        threshold_text += "1. Both size AND frequency limits must be satisfied\n"
        threshold_text += "2. Final grade = WORST grade between top and bottom surfaces\n"
        threshold_text += "3. Any Encased knot automatically fails G2-0 and G2-1\n"
        threshold_text += "4. Grade assigned is the BEST grade that passes all criteria\n\n"
        
        threshold_text += "DETECTION MAPPING:\n"
        threshold_text += "• Sound_Knot → Sound Knots (best quality)\n"
        threshold_text += "• Dead_Knot → Dead Knots (reduced quality)\n"
        threshold_text += "• Crack_Knot → Unsound Knots (poor quality)\n"
        threshold_text += "• Missing_Knot → Unsound Knots (poor quality)\n"
        threshold_text += "• Unsound_Knot → Unsound Knots (poor quality)"

        # Use CustomTkinter textbox for better dark theme compatibility
        text_widget = ctk.CTkTextbox(
            self.grading_details_frame,
            wrap="word",
            font=("Arial", 14, "bold"),  # Increased from 11 to 14 for kiosk readability
            fg_color=tab_bg,
            text_color=text_color,
            border_width=1,
            border_color="#3a3a3a",
            height=450  # Set explicit height for better kiosk display
        )
        text_widget.pack(fill="both", expand=True, padx=8, pady=8)
        text_widget.insert("1.0", threshold_text)
        text_widget.configure(state="disabled")  # Make it read-only

    def update_performance_tab(self):
        """Update the Performance Metrics tab with CustomTkinter widgets"""
        if not hasattr(self, 'performance_frame'):
            return
            
        # Clear existing content
        for widget in self.performance_frame.winfo_children():
            widget.destroy()
        
        # Use dark theme colors from configuration
        tab_bg = FRAME_BACKGROUND_COLOR
        text_color = TEXT_COLOR
        
        # System calibration info (simplified for kiosk)
        calibration_text = f"Grading Standard: SS-EN 1611-1 European Pine Timber\n\n"
        calibration_text += f"Frame Rate: 30 FPS (optimized for smooth display)\n\n"
        calibration_text += f"Wood Pallet Width: {WOOD_PALLET_WIDTH_MM:.1f}mm\n\n"
        calibration_text += f"Top Camera: {TOP_CAMERA_DISTANCE_CM}cm distance, {TOP_CAMERA_PIXEL_TO_MM:.3f}mm/pixel\n\n"
        calibration_text += f"Bottom Camera: {BOTTOM_CAMERA_DISTANCE_CM}cm distance, {BOTTOM_CAMERA_PIXEL_TO_MM:.3f}mm/pixel"
        
        calibration_label = ctk.CTkLabel(
            self.performance_frame,
            text=calibration_text,
            font=("Arial", 18, "bold"),  # Increased to 18 for better kiosk readability
            justify="left",
            anchor="w",
            text_color=text_color
        )
        calibration_label.pack(fill="both", expand=True, padx=20, pady=20)

    def update_detailed_statistics(self):
        """Legacy method - functionality removed since Recent Activity tab was removed"""
        pass

    def _generate_stats_content(self):
        """Generate a string representation of current stats for change detection"""
        content = f"processed:{getattr(self, 'total_pieces_processed', 0)}"

        grade_counts = getattr(self, 'grade_counts', {1: 0, 2: 0, 3: 0})
        for grade, count in grade_counts.items():
            content += f",g{grade}:{count}"

        # Include session log count for change detection
        if hasattr(self, 'session_log'):
            content += f",log_entries:{len(self.session_log)}"

        return content


    def cleanup_memory_resources(self):
        """Explicit cleanup of memory resources to prevent X11 BadAlloc errors"""
        try:
            # Clear PhotoImage references
            self._top_photo = None
            self._bottom_photo = None
            if hasattr(self, '_old_photos'):
                self._old_photos.clear()
            
            # Clear detection frames
            if hasattr(self, 'detection_frames'):
                self.detection_frames.clear()
            
            # Clear session data frames
            if hasattr(self, 'detection_session_data'):
                if 'best_frames' in self.detection_session_data:
                    self.detection_session_data['best_frames'] = {"top": None, "bottom": None}
                if 'total_detections' in self.detection_session_data:
                    self.detection_session_data['total_detections'] = {"top": [], "bottom": []}
            
            # Clear cached frames
            if hasattr(self, 'captured_frames'):
                self.captured_frames = {"top": [], "bottom": []}
            
            # Force garbage collection
            import gc
            gc.collect()
            
            print("Memory resources cleaned up successfully")
            
        except Exception as e:
            print(f"Error during memory cleanup: {e}")

    # ==================== ERROR MANAGEMENT SYSTEM ====================
    
    def register_error(self, error_type, details=""):
        """Register a new error and manage error state"""
        try:
            current_time = time.time()
            
            # Add to active errors
            self.error_state["active_errors"].add(error_type)
            
            # Update error count
            if error_type not in self.error_state["error_count"]:
                self.error_state["error_count"][error_type] = 0
            self.error_state["error_count"][error_type] += 1
            
            # Record error time
            self.error_state["last_error_time"][error_type] = current_time
            
            # Get error configuration
            error_config = self.ERROR_TYPES.get(error_type, {})
            error_name = error_config.get("name", error_type)
            severity = error_config.get("severity", "WARNING")
            
            print(f"ERROR REGISTERED: {error_name} - {details}")
            
            # Handle based on severity
            if severity in ["CRITICAL", "ERROR"]:
                self.handle_critical_error(error_type, details)
                # Show critical alert to operator
                self.show_error_alert(error_type, details, severity)
            elif severity == "WARNING":
                self.handle_warning_error(error_type, details)
                # Show warning alert (less intrusive)
                if self.error_state["error_count"][error_type] <= 2:  # Only show first few warnings
                    self.show_error_alert(error_type, details, severity)
                
            # Update UI status
            self.update_error_status_display()
            
            # Update error status panel if available
            if hasattr(self, 'update_error_status_panel'):
                self.update_error_status_panel()
            
        except Exception as e:
            print(f"Error in register_error: {e}")
    
    def clear_error(self, error_type):
        """Clear a specific error from active errors"""
        try:
            # Check if error is actually active before clearing
            if error_type not in self.error_state["active_errors"]:
                # Silently return without logging if error isn't active - avoids spam
                return  # Error not active, no need to clear
                
            print(f"🔄 Clearing active error: {error_type}")
                
            # Rate limiting for Arduino commands - prevent spam
            import time
            current_time = time.time()
            if hasattr(self, '_last_clear_commands'):
                if error_type in self._last_clear_commands:
                    if current_time - self._last_clear_commands[error_type] < 5.0:  # 5 second cooldown
                        print(f"⏱️ Too soon to clear {error_type} again, waiting...")
                        return  # Too soon to send another clear command
            else:
                self._last_clear_commands = {}
            
            self.error_state["active_errors"].discard(error_type)
            print(f"📝 Removed {error_type} from active errors")
            
            # CRITICAL FIX: Clear system_paused flag if no more active errors
            if len(self.error_state["active_errors"]) == 0:
                self.error_state["system_paused"] = False
                self.error_state["manual_inspection_required"] = False
                print(f"✅ All errors cleared - system_paused = False")
            
            # Reset recovery attempts for this error
            if error_type in self.error_state["error_recovery_attempts"]:
                self.error_state["error_recovery_attempts"][error_type] = 0
                
            # Send clear command to Arduino with rate limiting
            print(f"📤 Sending clear command to Arduino for {error_type}")
            self.send_error_clear_to_arduino(error_type)
            self._last_clear_commands[error_type] = current_time
                
            print(f"ERROR CLEARED: {error_type}")
            self.update_error_status_display()
            
        except Exception as e:
            print(f"Error in clear_error: {e}")
    
    def send_error_to_arduino(self, error_type, details):
        """Send error information to Arduino for immediate response"""
        try:
            # Truncate details to prevent Arduino buffer overflow
            short_details = details[:25] if len(details) > 25 else details
            
            # Format error command for Arduino: "ERROR:ERROR_TYPE:Description"
            error_command = f"ERROR:{error_type}:{short_details}"
            self.send_arduino_command(error_command)
            print(f"Sent error to Arduino: {error_type}")
            
        except Exception as e:
            print(f"Error sending error to Arduino: {e}")
    
    def send_error_clear_to_arduino(self, error_type):
        """Send error clear command to Arduino with improved synchronization"""
        try:
            clear_command = f"CLEAR_ERROR:{error_type}"
            print(f"📤 Sending clear command: {clear_command}")
            
            # Flush any pending messages before sending clear command
            if hasattr(self, 'ser') and self.ser and self.ser.is_open:
                try:
                    self.ser.reset_input_buffer()
                    print("🧹 Flushed Arduino input buffer before sending clear command")
                except:
                    pass
            
            self.send_arduino_command(clear_command)
            print(f"✅ Sent error clear to Arduino: {error_type}")
            
            # Extended delay to ensure Arduino processes the command fully
            time.sleep(0.5)  # Increased from 0.2s to 0.5s
            
            # Send a second flush to clear any remaining status messages
            if hasattr(self, 'ser') and self.ser and self.ser.is_open:
                try:
                    self.ser.reset_input_buffer()
                    print("🧹 Final flush after clear command")
                except:
                    pass
            
        except Exception as e:
            print(f"❌ Error sending error clear to Arduino: {e}")
    
    def handle_arduino_reconnection_recovery(self):
        """Handle Arduino reconnection - notify user instead of auto-recovery"""
        try:
            # Prevent duplicate recovery attempts
            if self.arduino_recovery_attempted:
                print("ℹ️ Arduino recovery notification already shown, skipping")
                return
                
            print("🔄 Arduino reconnected - notifying user...")
            self.arduino_recovery_attempted = True
            
            # Wait for Arduino to initialize (it sends ARDUINO_READY on startup)
            time.sleep(2)
            
            # Request status from Arduino to understand its current state
            self.send_arduino_command("STATUS_REQUEST")
            time.sleep(1)
            
            # Check if we were in SCAN_PHASE before disconnection
            if (self.current_mode == "SCAN_PHASE" and 
                "ARDUINO_DISCONNECTED" in self.error_state["errors"]):
                
                print("ℹ️ SCAN_PHASE was active before disconnection - recommending manual restart")
                
                # Show notification recommending manual restart
                self.show_error_alert(
                    "Arduino Reconnected", 
                    "Arduino has been reconnected successfully!\n\n"
                    "RECOMMENDATION: Please restart the scanning process manually "
                    "to ensure proper wood detection and avoid numbering conflicts.\n\n"
                    "Click the ON button when ready to resume scanning.",
                    "warning"
                )
                
                print("⚠️ User notified about Arduino reconnection - manual restart recommended")
                
            else:
                # Simple reconnection notification for non-SCAN modes
                self.show_error_alert(
                    "Arduino Reconnected", 
                    "Arduino has been reconnected successfully and is ready for operation.",
                    "info"
                )
                print("ℹ️ Arduino reconnected - system ready for operation")
                
        except Exception as e:
            print(f"Error in Arduino reconnection recovery: {e}")
        finally:
            # Reset recovery flag after a delay to allow future notifications if needed
            self.after(10000, lambda: setattr(self, 'arduino_recovery_attempted', False))
    
    def handle_critical_error(self, error_type, details):
        """Handle critical errors that require system pause"""
        try:
            print(f"CRITICAL ERROR HANDLING: {error_type}")
            
            # Pause system operations
            self.error_state["system_paused"] = True
            
            # Handle disconnection errors specially during SCAN_PHASE
            if error_type in ["CAMERA_DISCONNECTED", "ARDUINO_DISCONNECTED"]:
                if self.current_mode == "SCAN_PHASE":
                    print(f"🚨 CRITICAL: {error_type} during SCAN_PHASE - Switching to IDLE mode immediately")
                    # Show critical alert for scan interruption
                    self.show_error_alert(
                        error_type, 
                        f"SCAN INTERRUPTED: {details}\n\nScan phase has been stopped for safety. Please resolve the issue and restart scanning.",
                        "CRITICAL"
                    )
                    # Force switch to IDLE mode for safety
                    self.set_idle_mode()
                    # Clear scan state since it's interrupted
                    self._clear_scan_state()
                else:
                    # Try to send error to Arduino if it's not Arduino disconnection
                    if error_type != "ARDUINO_DISCONNECTED":
                        self.send_error_to_arduino(error_type, details)
                    self.set_idle_mode()
            else:
                # For other critical errors, try to send to Arduino first
                self.send_error_to_arduino(error_type, details)
                
                # Handle based on current mode
                if self.current_mode == "SCAN_PHASE":
                    # Don't switch to IDLE immediately for non-disconnection errors - let Arduino handle the pause
                    print(f"SCAN_PHASE paused due to critical error: {error_type}")
                elif self.current_mode != "IDLE":
                    print("Switching to IDLE mode due to critical error")
                    self.set_idle_mode()
            
            # Check if manual inspection is required
            error_config = self.ERROR_TYPES.get(error_type, {})
            max_retries = error_config.get("max_retries", 1)
            
            if error_type not in self.error_state["error_recovery_attempts"]:
                self.error_state["error_recovery_attempts"][error_type] = 0
            
            if self.error_state["error_recovery_attempts"][error_type] >= max_retries:
                self.error_state["manual_inspection_required"] = True
                print(f"Manual inspection required for {error_type} after {max_retries} attempts")
                
                # Send manual inspection command to Arduino
                self.send_arduino_command("ERROR:MANUAL_INSPECTION_REQUIRED:Max retries exceeded")
                
                # Show manual inspection dialog if in interactive mode
                if hasattr(self, 'show_manual_inspection_dialog'):
                    error_config = self.ERROR_TYPES.get(error_type, {})
                    error_name = error_config.get("name", error_type)
                    self.show_manual_inspection_dialog(f"{error_name}: {details}")
            else:
                # Attempt automatic recovery
                self.attempt_error_recovery(error_type)
                
        except Exception as e:
            print(f"Error in handle_critical_error: {e}")
    
    def _clear_scan_state(self):
        """Clear scan phase state when scan is interrupted"""
        try:
            self.scan_phase_active = False
            self.current_wood_number = 0
            
            # Update the wood counter display
            self.update_wood_counter_display()
            
            self.captured_frames = {"top": [], "bottom": []}
            self.segment_defects = {"top": [], "bottom": []}
            if hasattr(self, 'scan_session_data'):
                self.scan_session_data = {}
            print("Scan state cleared due to interruption")
            
            # Log scan interruption for tracking
            self.log_action(f"SCAN INTERRUPTED: Scan state cleared due to system error")
            
        except Exception as e:
            print(f"Error clearing scan state: {e}")
    
    def notify_scan_interruption(self, error_type, details):
        """Send comprehensive notifications for scan interruption"""
        try:
            # Console notification
            print("="*60)
            print("🚨 SCAN PHASE INTERRUPTION DETECTED")
            print(f"Error Type: {error_type}")
            print(f"Details: {details}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("Action: Switching to IDLE mode for safety")
            print("="*60)
            
            # Update status with urgent message
            self.update_status_text(f"🚨 SCAN INTERRUPTED - {error_type}", "red")
            
            # Show visual alert (handled in show_error_alert)
            # Desktop notification (handled in show_error_alert)
            # Audio alert (handled in show_error_alert)
            
        except Exception as e:
            print(f"Error in notify_scan_interruption: {e}")
    
    def handle_warning_error(self, error_type, details):
        """Handle warning errors that may allow continued operation"""
        try:
            print(f"WARNING ERROR HANDLING: {error_type}")
            
            # Check retry count
            error_config = self.ERROR_TYPES.get(error_type, {})
            max_retries = error_config.get("max_retries", 2)
            
            if error_type not in self.error_state["error_recovery_attempts"]:
                self.error_state["error_recovery_attempts"][error_type] = 0
            
            if self.error_state["error_recovery_attempts"][error_type] >= max_retries:
                # Escalate to critical if retries exceeded
                print(f"Escalating {error_type} to critical after {max_retries} attempts")
                self.handle_critical_error(error_type, details)
            else:
                # Attempt recovery while continuing operation
                self.attempt_error_recovery(error_type)
                
        except Exception as e:
            print(f"Error in handle_warning_error: {e}")
    
    def attempt_error_recovery(self, error_type):
        """Attempt automatic recovery for specific error types"""
        try:
            # Rate limiting for recovery attempts
            import time
            current_time = time.time()
            
            # Initialize recovery tracking if needed
            if not hasattr(self, '_last_recovery_attempts'):
                self._last_recovery_attempts = {}
            
            # Check if we should skip this recovery attempt (rate limiting)
            if error_type in self._last_recovery_attempts:
                time_since_last = current_time - self._last_recovery_attempts[error_type]
                if time_since_last < 30.0:  # 30 second cooldown between recovery attempts
                    return  # Skip recovery, too soon
            
            self.error_state["error_recovery_attempts"][error_type] = \
                self.error_state["error_recovery_attempts"].get(error_type, 0) + 1
            
            recovery_attempt = self.error_state["error_recovery_attempts"][error_type]
            
            # Limit total recovery attempts per error type
            if recovery_attempt > 3:  # Max 3 attempts
                print(f"❌ Max recovery attempts reached for {error_type} (attempted {recovery_attempt} times)")
                return
                
            print(f"Attempting recovery for {error_type} (attempt {recovery_attempt})")
            self._last_recovery_attempts[error_type] = current_time
            
            # Specific recovery actions based on error type
            if error_type == "CAMERA_DISCONNECTED":
                self.recover_camera_connection()
            elif error_type == "ARDUINO_DISCONNECTED":
                self.recover_arduino_connection()
            elif error_type == "RESOURCE_EXHAUSTION":
                self.recover_system_resources()
            elif error_type == "MODEL_LOADING_FAILED":
                self.recover_ai_model()
            elif error_type == "NO_WOOD_DETECTED":
                self.recover_detection_issues(error_type)
            else:
                print(f"No specific recovery action for {error_type}")
                
        except Exception as e:
            print(f"Error in attempt_error_recovery: {e}")
    
    def recover_camera_connection(self):
        """Attempt to recover camera connection"""
        try:
            print("Attempting camera reconnection...")
            # Use camera handler's reconnect_cameras method
            success = self.camera_handler.reconnect_cameras()
            if success:
                # Update the cap references after successful reconnection
                self.cap_top = self.camera_handler.top_camera
                self.cap_bottom = self.camera_handler.bottom_camera
                
                # Clear the error (this sends CLEAR_ERROR to Arduino)
                self.clear_error("CAMERA_DISCONNECTED")
                
                # Give Arduino more time to process the clear command and stop sending status messages
                print("🕐 Waiting for Arduino to process CLEAR_ERROR command...")
                time.sleep(2.0)  # Increased from 1.0s to 2.0s for better synchronization
                
                # Flush any remaining STATUS_PAUSED messages from Arduino buffer
                if hasattr(self, 'ser') and self.ser and self.ser.is_open:
                    try:
                        self.ser.reset_input_buffer()
                        print("🧹 Flushed remaining Arduino messages after error clear")
                    except:
                        pass
                
                print("✅ Camera connection recovered successfully")
                
                # Give cameras additional time to stabilize before final verification
                print("⏳ Allowing cameras to stabilize...")
                time.sleep(3.0)  # Additional stabilization time
                
                # Final verification with retry mechanism
                print("🔍 Performing final verification...")
                verification_success = False
                for verify_attempt in range(3):
                    time.sleep(1.0)  # Wait between verification attempts
                    final_status = self.camera_handler.check_camera_status()
                    if final_status['both_ok']:
                        verification_success = True
                        print(f"✅ Verification successful on attempt {verify_attempt + 1}")
                        break
                    else:
                        print(f"⚠️ Verification attempt {verify_attempt + 1} failed - retrying...")
                
                if verification_success:
                    # 1. SET GRACE PERIOD FIRST (before any notifications)
                    self.camera_reconnection_grace_start = time.time()
                    self.camera_reconnection_grace_period = 30.0  # 30 seconds grace period
                    print("🛡️ Camera reconnection grace period activated (30 seconds)")
                    
                    # 2. CLEAR ERROR STATE IMMEDIATELY
                    if "CAMERA_DISCONNECTED" in self.error_state["active_errors"]:
                        try:
                            self.error_state["active_errors"].remove("CAMERA_DISCONNECTED")
                            print("✅ Removed CAMERA_DISCONNECTED from active errors")
                        except ValueError:
                            pass  # Already removed
                    
                    # 3. UPDATE STATUS IMMEDIATELY (non-blocking)
                    self.update_status_text("Status: Cameras reconnected successfully", STATUS_READY_COLOR)
                    
                    # 4. RESET RECONNECTION ATTEMPTS
                    self.camera_reconnection_attempts = 0
                    
                    # 5. NOW SHOW NON-BLOCKING NOTIFICATIONS (safe because grace period is active)
                    self.show_reconnection_success_notification()
                    
                    return True
                else:
                    print("⚠️ Warning: Final camera status check failed after apparent success")
                    print(f"   Final status: Top={'✅ OK' if final_status['top_ok'] else '❌ FAIL'}, Bottom={'✅ OK' if final_status['bottom_ok'] else '❌ FAIL'}")
                    # Don't show success notification if final check fails
                    return False
            else:
                print("Camera reconnection failed - not all cameras reconnected")
                
                # Check which cameras failed and register specific error
                missing_cameras = []
                if not self.camera_handler.top_camera:
                    missing_cameras.append("top")
                if not self.camera_handler.bottom_camera:
                    missing_cameras.append("bottom")
                    
                error_details = f"Failed to reconnect {', '.join(missing_cameras)} camera(s)"
                self.register_error("CAMERA_DISCONNECTED", error_details)
                return False
        except Exception as e:
            print(f"Error in recover_camera_connection: {e}")
            self.register_error("CAMERA_DISCONNECTED", f"Recovery exception: {str(e)}")
            return False

    def monitor_camera_connectivity(self):
        """Periodically monitor camera connectivity and attempt automatic reconnection"""
        if not self.camera_monitor_active:
            return
            
        current_time = time.time()
        
        # Only check cameras at specified intervals
        if current_time - self.last_camera_check_time < self.camera_check_interval:
            return
            
        self.last_camera_check_time = current_time
        
        # Check if in grace period (but don't return - just note it for logging)
        in_grace_period = False
        if hasattr(self, 'camera_reconnection_grace_start'):
            grace_elapsed = current_time - self.camera_reconnection_grace_start
            if grace_elapsed < self.camera_reconnection_grace_period:
                in_grace_period = True
                remaining = self.camera_reconnection_grace_period - grace_elapsed
                if int(remaining) % 5 == 0:  # Log every 5 seconds
                    print(f"🛡️ Camera grace period active - {remaining:.1f}s remaining (but monitoring continues)")
        
        try:
            # Check if we have a CAMERA_DISCONNECTED error
            if "CAMERA_DISCONNECTED" in self.error_state["active_errors"]:
                # Skip reconnection attempts during grace period to avoid race conditions
                if in_grace_period:
                    print("🛡️ Skipping reconnection attempt during grace period")
                    return
                    
                print("🔍 Camera monitor: Detected active camera disconnection error - attempting automatic reconnection")
                
                # Only attempt reconnection if we haven't exceeded max attempts
                if self.camera_reconnection_attempts < self.max_camera_reconnection_attempts:
                    self.camera_reconnection_attempts += 1
                    print(f"🔄 Automatic camera reconnection attempt {self.camera_reconnection_attempts}/{self.max_camera_reconnection_attempts}")
                    
                    success = self.recover_camera_connection()
                    if success:
                        print("🎉 Automatic camera reconnection successful!")
                        # Status and notification are now handled in recover_camera_connection()
                    else:
                        print(f"❌ Automatic camera reconnection attempt {self.camera_reconnection_attempts} failed")
                        
                        # If we've reached max attempts, show a message
                        if self.camera_reconnection_attempts >= self.max_camera_reconnection_attempts:
                            print("⚠️ Maximum camera reconnection attempts reached - manual intervention may be required")
                            # Use non-blocking toast instead of blocking alert
                            self.show_toast_notification(
                                "⚠️ Camera Reconnection Failed",
                                "Automatic reconnection failed after multiple attempts.\nPlease check camera connections manually.",
                                duration=8000,  # 8 seconds for important warning
                                type="warning"
                            )
                            # Reset counter to allow future attempts after some time
                            self.camera_reconnection_attempts = 0
                            # Increase interval for next attempts
                            self.camera_check_interval = 30.0  # Check less frequently
                else:
                    # Wait a bit longer before trying again
                    if current_time - self.last_camera_check_time > 60.0:  # Wait 1 minute before resetting
                        print("🔄 Resetting camera reconnection attempts after waiting period")
                        self.camera_reconnection_attempts = 0
                        self.camera_check_interval = 10.0  # Reset to normal interval
            else:
                # No camera errors - reset reconnection attempts and interval
                if self.camera_reconnection_attempts > 0:
                    self.camera_reconnection_attempts = 0
                    self.camera_check_interval = 10.0
                    
        except Exception as e:
            print(f"Error in monitor_camera_connectivity: {e}")
            
        # Schedule next check (will be called from the main update loop)
        # Don't use self.after here to avoid recursion

    def show_reconnection_success_notification(self):
        """Show success notification when cameras are reconnected - NON-BLOCKING"""
        try:
            # Use non-blocking toast notification instead of modal popup
            self.show_toast_notification(
                "🎉 Cameras Reconnected Successfully",
                "Both cameras are ready for operation.\nYou can continue with wood inspection and grading.",
                duration=6000,  # 6 seconds
                type="success"
            )
            
            # Update status display 
            self.update_status_text("Status: Cameras ready - reconnection successful", STATUS_READY_COLOR)
            
            # Show desktop notification (also non-blocking)
            self.show_desktop_notification(
                "🎉 Cameras Reconnected", 
                "Both cameras successfully reconnected and ready", 
                "INFO"
            )
            
            print("🎉 Success notification shown to user (non-blocking)")
            
        except Exception as e:
            print(f"Error showing reconnection success notification: {e}")

    def manual_camera_reconnection(self):
        """Manually trigger camera reconnection attempt"""
        print("🔄 Manual camera reconnection triggered by user")
        
        # Reset reconnection attempts to allow immediate attempt
        self.camera_reconnection_attempts = 0
        self.camera_check_interval = 10.0  # Reset to normal interval
        
        # Force immediate reconnection attempt
        success = self.recover_camera_connection()
        
        if success:
            print("✅ Manual camera reconnection successful!")
            self.update_status_text("Status: Cameras manually reconnected", STATUS_READY_COLOR)
            # Use non-blocking toast instead of blocking alert
            self.show_toast_notification(
                "✅ Camera Reconnected",
                "Cameras manually reconnected successfully and ready for operation.",
                duration=5000,
                type="success"
            )
            return True
        else:
            print("❌ Manual camera reconnection failed")
            # Use non-blocking toast instead of blocking alert
            self.show_toast_notification(
                "❌ Reconnection Failed",
                "Manual camera reconnection failed. Please check connections and try again.",
                duration=5000,
                type="error"
            )
            return False
    
    def recover_arduino_connection(self):
        """Attempt to recover Arduino connection with enhanced voltage drop handling"""
        try:
            print("Attempting Arduino reconnection...")
            # Close existing connection
            if hasattr(self, 'ser') and self.ser and self.ser.is_open:
                self.ser.close()
            
            # Extended delay for voltage drop recovery
            print("🔋 Extended power recovery delay for voltage drop scenarios")
            time.sleep(2.0)  # Extended delay for voltage stabilization
            
            # Attempt reconnection using existing setup
            self.setup_arduino()
            
            # Test connection with a safe command
            if hasattr(self, 'ser') and self.ser and self.ser.is_open:
                # Send a test command to verify connection stability
                try:
                    test_command = "STATUS_REQUEST"
                    self.ser.write(test_command.encode('utf-8'))
                    self.ser.flush()
                    time.sleep(0.5)  # Wait for response
                    
                    self.clear_error("ARDUINO_DISCONNECTED")
                    print("✅ Arduino connection recovered and tested successfully")
                    return True
                except Exception as test_error:
                    print(f"⚠️ Arduino reconnected but test command failed: {test_error}")
                    return False
            else:
                print("❌ Arduino reconnection failed")
                return False
        except Exception as e:
            print(f"Error in recover_arduino_connection: {e}")
            return False
    
    def recover_system_resources(self):
        """Attempt to recover system resources"""
        try:
            print("Attempting system resource recovery...")
            # Use existing cleanup method
            self.cleanup_memory_resources()
            
            # Additional resource cleanup
            import gc
            gc.collect()
            
            # Check if recovery was successful (simplified check)
            self.clear_error("RESOURCE_EXHAUSTION")
            print("System resource recovery completed")
            return True
        except Exception as e:
            print(f"Error in recover_system_resources: {e}")
            return False
    
    def recover_ai_model(self):
        """Attempt to recover AI model"""
        try:
            print("Attempting AI model recovery...")
            # Reload DeGirum model
            if hasattr(self, 'load_models_on_startup'):
                self.load_models_on_startup()
                self.clear_error("MODEL_LOADING_FAILED")
                print("AI model recovery completed")
                return True
            else:
                print("AI model recovery failed - no model loading method")
                return False
        except Exception as e:
            print(f"Error in recover_ai_model: {e}")
            return False
    
    def recover_detection_issues(self, error_type):
        """Attempt to recover from detection-related issues"""
        try:
            print(f"Attempting recovery for detection issue: {error_type}")
            
            # Wait a short time for conditions to improve
            error_config = self.ERROR_TYPES.get(error_type, {})
            timeout = error_config.get("timeout", 3.0)
            time.sleep(min(timeout, 2.0))  # Cap wait time
            
            # Clear the error to allow retry
            self.clear_error(error_type)
            print(f"Detection issue recovery completed for {error_type}")
            return True
            
        except Exception as e:
            print(f"Error in recover_detection_issues: {e}")
            return False
    
    def check_error_recovery_timeout(self):
        """Check if error recovery has timed out and escalate if needed"""
        try:
            current_time = time.time()
            
            for error_type in list(self.error_state["active_errors"]):
                error_config = self.ERROR_TYPES.get(error_type, {})
                timeout = error_config.get("timeout", 10.0)
                
                if error_type in self.error_state["last_error_time"]:
                    time_since_error = current_time - self.error_state["last_error_time"][error_type]
                    
                    if time_since_error > timeout:
                        print(f"Error recovery timeout for {error_type} ({time_since_error:.1f}s > {timeout}s)")
                        self.handle_critical_error(error_type, "Recovery timeout exceeded")
                        
        except Exception as e:
            print(f"Error in check_error_recovery_timeout: {e}")
    
    def update_error_status_display(self):
        """Update UI to show current error status"""
        try:
            if self.error_state["active_errors"]:
                error_count = len(self.error_state["active_errors"])
                error_list = ", ".join(list(self.error_state["active_errors"])[:3])  # Show first 3
                if len(self.error_state["active_errors"]) > 3:
                    error_list += "..."
                
                if self.error_state["system_paused"]:
                    status_text = f"SYSTEM PAUSED - {error_count} Error(s): {error_list}"
                    color = "red"
                elif self.error_state["manual_inspection_required"]:
                    status_text = f"MANUAL INSPECTION REQUIRED - {error_count} Error(s): {error_list}"
                    color = "orange"
                else:
                    status_text = f"WARNING - {error_count} Error(s): {error_list}"
                    color = "yellow"
                    
                self.update_status_text(status_text, color)
            else:
                # No errors - show normal status
                if hasattr(self, 'update_detection_status_display'):
                    self.update_detection_status_display()
                    
        except Exception as e:
            print(f"Error in update_error_status_display: {e}")

    def clear_all_errors(self):
        """Clear all active errors and reset error state"""
        try:
            # Store if system was paused before clearing
            was_paused = self.error_state["system_paused"]
            
            self.error_state["active_errors"].clear()
            self.error_state["system_paused"] = False
            self.error_state["manual_inspection_required"] = False
            self.error_state["error_recovery_attempts"].clear()
            
            # If system was paused and we're in SCAN_PHASE, resume operations
            if was_paused and self.current_mode == "SCAN_PHASE":
                self.send_arduino_command("RESUME_SYSTEM")
                print("All errors cleared - resuming SCAN_PHASE operations")
            else:
                print("All errors cleared - system ready")
                
            self.update_error_status_display()
        except Exception as e:
            print(f"Error in clear_all_errors: {e}")

    def get_system_health_status(self):
        """Get current system health status"""
        try:
            health_status = {
                "overall_status": "HEALTHY",
                "active_errors": len(self.error_state["active_errors"]),
                "system_paused": self.error_state["system_paused"],
                "manual_inspection_required": self.error_state["manual_inspection_required"],
                "error_details": {}
            }
            
            # Check for any critical conditions
            if self.error_state["system_paused"]:
                health_status["overall_status"] = "PAUSED"
            elif self.error_state["manual_inspection_required"]:
                health_status["overall_status"] = "MANUAL_INSPECTION"
            elif self.error_state["active_errors"]:
                health_status["overall_status"] = "WARNING"
            
            # Add error details
            for error_type in self.error_state["active_errors"]:
                error_config = self.ERROR_TYPES.get(error_type, {})
                health_status["error_details"][error_type] = {
                    "name": error_config.get("name", error_type),
                    "severity": error_config.get("severity", "UNKNOWN"),
                    "count": self.error_state["error_count"].get(error_type, 0),
                    "recovery_attempts": self.error_state["error_recovery_attempts"].get(error_type, 0)
                }
            
            return health_status
            
        except Exception as e:
            print(f"Error in get_system_health_status: {e}")
            return {"overall_status": "ERROR", "error": str(e)}

    # ==================== END ERROR MANAGEMENT SYSTEM ====================

    # ==================== DETECTION FAILURE HANDLING ====================
    
    def check_wood_detection_status(self, frame, camera_name):
        """Check for wood detection issues and register errors if needed"""
        try:
            # Check if we should be detecting wood (conveyor is running)
            if self.current_mode in ["CONTINUOUS", "TRIGGER", "SCAN_PHASE"]:
                
                # Check wood detection results
                wood_result = self.wood_detection_results.get(camera_name)
                
                if wood_result is None or not wood_result.get('wood_detected', False):
                    # Check if we're waiting too long for wood detection
                    current_time = time.time()
                    
                    if self.detection_monitoring["wood_detection_start_time"] is None:
                        self.detection_monitoring["wood_detection_start_time"] = current_time
                    
                    wait_time = current_time - self.detection_monitoring["wood_detection_start_time"]
                    
                    if wait_time > self.DETECTION_THRESHOLDS["WOOD_DETECTION_TIMEOUT"]:
                        self.register_error("NO_WOOD_DETECTED", 
                                          f"No wood detected for {wait_time:.1f} seconds")
                        # Reset timer after registering error
                        self.detection_monitoring["wood_detection_start_time"] = current_time
                else:
                    # Wood detected successfully
                    self.detection_monitoring["wood_detection_start_time"] = None
                    self.clear_error("NO_WOOD_DETECTED")
            else:
                # Not in detection mode, clear wood detection errors
                self.detection_monitoring["wood_detection_start_time"] = None
                self.clear_error("NO_WOOD_DETECTED")
                
        except Exception as e:
            print(f"Error in check_wood_detection_status: {e}")
    
    def check_plank_alignment(self, detections, frame, camera_name):
        """Check if wood plank is properly aligned based on detection positions"""
        try:
            if not detections:
                return
                
            frame_height, frame_width = frame.shape[:2]
            frame_center_x = frame_width // 2
            frame_center_y = frame_height // 2
            
            # Calculate detection positions relative to frame center
            detection_centers = []
            for bbox, defect_type, size_mm, confidence in detections:
                x1, y1, x2, y2 = bbox
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                detection_centers.append((center_x, center_y))
            
            # Check for significant misalignment
            misalignment_detected = False
            
            for center_x, center_y in detection_centers:
                # Check horizontal alignment (wood should be centered)
                horizontal_offset = abs(center_x - frame_center_x)
                vertical_offset = abs(center_y - frame_center_y)
                
                if (horizontal_offset > self.DETECTION_THRESHOLDS["ALIGNMENT_TOLERANCE"] or
                    vertical_offset > self.DETECTION_THRESHOLDS["ALIGNMENT_TOLERANCE"]):
                    misalignment_detected = True
                    break
            
            if misalignment_detected:
                self.detection_monitoring["alignment_failures"] += 1
            else:
                self.detection_monitoring["alignment_failures"] = 0
                
        except Exception as e:
            print(f"Error in check_plank_alignment: {e}")
    
    def check_wood_lane_alignment(self, camera_name):
        """Check if wood detection bounding box touches the lane ROIs (highway lane style check)"""
        try:
            # Get wood detection results for this camera
            if not hasattr(self, 'wood_detection_results') or not self.wood_detection_results.get(camera_name):
                return  # No wood detected, skip check
            
            wood_detection = self.wood_detection_results[camera_name]
            wood_candidates = wood_detection.get('wood_candidates', [])
            
            if not wood_candidates:
                return  # No wood candidates, skip check
            
            # Get the best wood candidate (first one)
            best_candidate = wood_candidates[0]
            wood_bbox = best_candidate['bbox']  # (x, y, w, h)
            wx, wy, ww, wh = wood_bbox
            
            # Convert to (x1, y1, x2, y2) format
            wood_x1, wood_y1 = wx, wy
            wood_x2, wood_y2 = wx + ww, wy + wh
            
            # Get lane ROIs for this camera
            if camera_name not in ALIGNMENT_LANE_ROIS:
                print(f"No lane ROIs defined for camera: {camera_name}")
                return
            
            lane_rois = ALIGNMENT_LANE_ROIS[camera_name]
            misalignment_detected = False
            touched_lane = None
            
            # Check top lane
            top_lane = lane_rois['top_lane']
            if self._check_bbox_intersection(wood_x1, wood_y1, wood_x2, wood_y2,
                                            top_lane['x1'], top_lane['y1'],
                                            top_lane['x2'], top_lane['y2']):
                misalignment_detected = True
                touched_lane = "top"
            
            # Check bottom lane
            bottom_lane = lane_rois['bottom_lane']
            if self._check_bbox_intersection(wood_x1, wood_y1, wood_x2, wood_y2,
                                            bottom_lane['x1'], bottom_lane['y1'],
                                            bottom_lane['x2'], bottom_lane['y2']):
                misalignment_detected = True
                touched_lane = "bottom" if not touched_lane else "both"
            
            # Display warning if misalignment detected
            if misalignment_detected:
                warning_msg = f"⚠️ Wood Misalignment Detected on {camera_name.upper()} camera!\n"
                warning_msg += f"Wood is touching the {touched_lane} lane boundary."
                print(warning_msg)
                
                # Show warning notification (non-blocking toast)
                try:
                    self.show_toast_notification(
                        "⚠️ Wood Misalignment",
                        f"Wood touching {touched_lane} lane on {camera_name.upper()} camera",
                        duration=6000,
                        type="warning"
                    )
                except Exception as e:
                    print(f"Could not show warning notification: {e}")
                
        except Exception as e:
            print(f"Error in check_wood_lane_alignment: {e}")
    
    def _check_bbox_intersection(self, box1_x1, box1_y1, box1_x2, box1_y2,
                                  box2_x1, box2_y1, box2_x2, box2_y2):
        """Check if two bounding boxes intersect (overlap)"""
        # Check if boxes do NOT intersect, then negate
        no_intersection = (box1_x2 < box2_x1 or  # box1 is to the left of box2
                          box1_x1 > box2_x2 or  # box1 is to the right of box2
                          box1_y2 < box2_y1 or  # box1 is above box2
                          box1_y1 > box2_y2)    # box1 is below box2
        
        return not no_intersection
    
    def check_detection_quality(self, detections, frame_area):
        """Check overall detection quality and flag issues"""
        try:
            if not detections:
                return True  # No detections is valid
            
            # Check for reasonable detection density
            total_detection_area = 0
            for bbox, defect_type, size_mm, confidence in detections:
                x1, y1, x2, y2 = bbox
                detection_area = (x2 - x1) * (y2 - y1)
                total_detection_area += detection_area
            
            # If detections cover more than 50% of frame, might be an issue
            detection_ratio = total_detection_area / frame_area
            if detection_ratio > 0.5:
                print(f"Warning: High detection density ({detection_ratio:.1%} of frame)")
                return False
            
            # Check for minimum size detections
            small_detections = 0
            for bbox, defect_type, size_mm, confidence in detections:
                x1, y1, x2, y2 = bbox
                detection_area = (x2 - x1) * (y2 - y1)
                if detection_area < 100:  # Very small detection
                    small_detections += 1
            
            if small_detections > len(detections) * 0.7:  # More than 70% small detections
                print(f"Warning: High number of small detections ({small_detections}/{len(detections)})")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error in check_detection_quality: {e}")
            return True

    def monitor_detection_performance(self):
        """Monitor overall detection performance and register issues"""
        try:
            # This method can be called periodically to check detection performance
            current_time = time.time()
            
            # Check error recovery timeouts
            self.check_error_recovery_timeout()
            
            # Reset detection monitoring counters periodically
            if hasattr(self, '_last_monitoring_reset'):
                if current_time - self._last_monitoring_reset > 60:  # Reset every minute
                    self.detection_monitoring["alignment_failures"] = 0
                    self._last_monitoring_reset = current_time
            else:
                self._last_monitoring_reset = current_time
                
        except Exception as e:
            print(f"Error in monitor_detection_performance: {e}")

    # ==================== END DETECTION FAILURE HANDLING ====================

    # ==================== SYSTEM HEALTH MONITORING ====================
    
    def start_health_monitoring(self):
        """Start continuous system health monitoring"""
        try:
            print("Starting system health monitoring...")
            # Initialize monitoring timer
            self.schedule_health_check()
            
        except Exception as e:
            print(f"Error starting health monitoring: {e}")
    
    def schedule_health_check(self):
        """Schedule the next health check"""
        try:
            # Perform health check
            self.perform_health_check()
            
            # Schedule next check in 10 seconds (reduced frequency to reduce system load)
            self.after(10000, self.schedule_health_check)
            
        except Exception as e:
            print(f"Error in schedule_health_check: {e}")
            # Try to reschedule even if there was an error
            self.after(10000, self.schedule_health_check)
    
    def perform_health_check(self):
        """Perform comprehensive system health check"""
        try:
            # Monitor camera health
            self.monitor_camera_health()
            
            # Monitor Arduino health
            self.monitor_arduino_health()
            
            # Monitor resource usage
            self.monitor_resource_usage()
            
            # Monitor AI model health
            self.monitor_ai_model_health()
            
            # Monitor detection performance
            self.monitor_detection_performance()
            
            # Check for any error recovery timeouts
            self.check_error_recovery_timeout()
            
        except Exception as e:
            print(f"Error in perform_health_check: {e}")
    
    def monitor_camera_health(self):
        """Monitor camera connection and performance"""
        try:
            # Check if we're in a grace period after recent reconnection
            if hasattr(self, 'camera_reconnection_grace_start'):
                grace_elapsed = time.time() - self.camera_reconnection_grace_start
                if grace_elapsed < self.camera_reconnection_grace_period:
                    # Still in grace period - skip health checks
                    if not hasattr(self, '_grace_period_logged'):
                        print(f"🛡️ Skipping camera health check - grace period active ({self.camera_reconnection_grace_period - grace_elapsed:.1f}s remaining)")
                        self._grace_period_logged = True
                    return
                else:
                    # Grace period expired - remove grace period attributes
                    delattr(self, 'camera_reconnection_grace_start')
                    if hasattr(self, '_grace_period_logged'):
                        delattr(self, '_grace_period_logged')
                    print("🛡️ Camera reconnection grace period expired - resuming health monitoring")
            
            # Use existing check_camera_status method
            camera_status = self.camera_handler.check_camera_status()
            
            if not camera_status['both_ok']:
                # Handle camera disconnection errors with better logging
                error_details = "; ".join(camera_status['camera_errors'])
                print(f"🚨 Camera health check detected issues: {error_details}")
                print(f"   Status: Top={'✅ OK' if camera_status['top_ok'] else '❌ FAIL'}, Bottom={'✅ OK' if camera_status['bottom_ok'] else '❌ FAIL'}")
                
                # Special handling for SCAN_PHASE disconnection
                if self.current_mode == "SCAN_PHASE":
                    print("🚨 CRITICAL: Camera disconnection during SCAN_PHASE")
                    enhanced_details = f"{error_details}. System will attempt automatic reconnection in the background."
                    self.register_error("CAMERA_DISCONNECTED", enhanced_details)
                    # The error handler will show the alert and switch to IDLE
                else:
                    enhanced_details = f"{error_details}. System will attempt automatic reconnection in the background."
                    self.register_error("CAMERA_DISCONNECTED", enhanced_details)
                
                # If we're in an active mode, switch to IDLE to prevent unsafe operations
                if self.current_mode in ["CONTINUOUS", "TRIGGER", "SCAN_PHASE"]:
                    print("Switching to IDLE mode due to camera disconnection")
                    self.set_idle_mode()
            else:
                # Clear camera disconnection error if both cameras are working AND error is active
                if "CAMERA_DISCONNECTED" in self.error_state["active_errors"]:
                    print("✅ Camera health check: Both cameras working, clearing disconnection error")
                    self.clear_error("CAMERA_DISCONNECTED")
                
            # Log status periodically (not every check to avoid spam)
            if not camera_status['both_ok']:
                top_status = '✅ OK' if camera_status['top_ok'] else '❌ FAIL'
                bottom_status = '✅ OK' if camera_status['bottom_ok'] else '❌ FAIL'
                print(f"📊 Camera status check: Top={top_status}, Bottom={bottom_status}")
            
            # Additional camera health checks
            if hasattr(self, 'cap_top') and self.cap_top:
                # Check frame rate and quality periodically
                if hasattr(self, '_camera_frame_count'):
                    self._camera_frame_count += 1
                else:
                    self._camera_frame_count = 1
                    
                # Every 100 frames, check frame rate
                if self._camera_frame_count % 100 == 0:
                    current_time = time.time()
                    if hasattr(self, '_camera_health_last_check'):
                        time_diff = current_time - self._camera_health_last_check
                        frame_rate = 100 / time_diff
                        if frame_rate < 5:  # Less than 5 FPS
                            print(f"Warning: Low camera frame rate: {frame_rate:.1f} FPS")
                    self._camera_health_last_check = current_time
                    
        except Exception as e:
            print(f"Error in monitor_camera_health: {e}")
    
    def monitor_arduino_health(self):
        """Monitor Arduino connection and communication"""
        try:
            if hasattr(self, 'ser') and self.ser:
                # Check if serial connection is still open
                if not self.ser.is_open:
                    self.register_error("ARDUINO_DISCONNECTED", "Arduino serial connection closed")
                else:
                    # Clear Arduino disconnection error if connection is good AND error is active
                    if "ARDUINO_DISCONNECTED" in self.error_state["active_errors"]:
                        self.clear_error("ARDUINO_DISCONNECTED")
                    
                    # Additional health checks could be added here
                    # For example, sending a ping command and waiting for response
                    
            else:
                self.register_error("ARDUINO_DISCONNECTED", "Arduino serial object not available")
                
        except Exception as e:
            print(f"Error in monitor_arduino_health: {e}")
            self.register_error("ARDUINO_DISCONNECTED", f"Arduino health check failed: {str(e)}")
    
    def monitor_resource_usage(self):
        """Monitor system resource usage"""
        try:
            import psutil
            import gc
            
            # Check memory usage
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            
            if memory_percent > 90:
                self.register_error("RESOURCE_EXHAUSTION", f"High memory usage: {memory_percent:.1f}%")
            elif memory_percent > 80:
                print(f"Warning: High memory usage: {memory_percent:.1f}%")
                # Trigger memory cleanup
                self.cleanup_memory_resources()
            else:
                # Clear resource exhaustion error if memory usage is acceptable AND error is active
                if "RESOURCE_EXHAUSTION" in self.error_state["active_errors"]:
                    self.clear_error("RESOURCE_EXHAUSTION")
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 95:
                print(f"Warning: High CPU usage: {cpu_percent:.1f}%")
            
            # Check available disk space
            disk_info = psutil.disk_usage('/')
            disk_percent = (disk_info.used / disk_info.total) * 100
            if disk_percent > 95:
                print(f"Warning: Low disk space: {disk_percent:.1f}% used")
            
            # Trigger garbage collection if memory usage is high
            if memory_percent > 70:
                gc.collect()
                
        except ImportError:
            # psutil not available, use basic checks
            self.monitor_basic_resources()
        except Exception as e:
            print(f"Error in monitor_resource_usage: {e}")
    
    def monitor_basic_resources(self):
        """Basic resource monitoring when psutil is not available"""
        try:
            import gc
            
            # Get object count before and after garbage collection
            initial_objects = len(gc.get_objects())
            gc.collect()
            final_objects = len(gc.get_objects())
            
            if initial_objects > 50000:  # Arbitrary threshold
                print(f"High object count: {initial_objects} objects in memory")
                
        except Exception as e:
            print(f"Error in monitor_basic_resources: {e}")
    
    def monitor_ai_model_health(self):
        """Monitor AI model status and performance"""
        try:
            if self.model is None:
                self.register_error("MODEL_LOADING_FAILED", "DeGirum model is not loaded")
            else:
                # Clear model loading error if model is loaded AND error is active
                if "MODEL_LOADING_FAILED" in self.error_state["active_errors"]:
                    self.clear_error("MODEL_LOADING_FAILED")
                
                # Additional model health checks could be added here
                # For example, testing inference with a dummy frame
                
        except Exception as e:
            print(f"Error in monitor_ai_model_health: {e}")
            self.register_error("MODEL_LOADING_FAILED", f"AI model health check failed: {str(e)}")
    
    def get_detailed_health_report(self):
        """Get detailed system health report"""
        try:
            health_report = {
                "timestamp": time.time(),
                "system_status": self.get_system_health_status(),
                "active_modes": self.current_mode,
                "cameras": {
                    "top_connected": hasattr(self, 'cap_top') and self.cap_top and self.cap_top.isOpened(),
                    "bottom_connected": hasattr(self, 'cap_bottom') and self.cap_bottom and self.cap_bottom.isOpened()
                },
                "arduino": {
                    "connected": hasattr(self, 'ser') and self.ser and self.ser.is_open
                },
                "ai_model": {
                    "loaded": self.model is not None
                },
                "detection_monitoring": self.detection_monitoring.copy(),
                "error_state": {
                    "active_errors": list(self.error_state["active_errors"]),
                    "error_counts": self.error_state["error_count"].copy(),
                    "system_paused": self.error_state["system_paused"],
                    "manual_inspection_required": self.error_state["manual_inspection_required"]
                }
            }
            
            # Add resource information if available
            try:
                import psutil
                health_report["resources"] = {
                    "memory_percent": psutil.virtual_memory().percent,
                    "cpu_percent": psutil.cpu_percent(),
                    "disk_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
                }
            except ImportError:
                health_report["resources"] = {"status": "monitoring_unavailable"}
            
            return health_report
            
        except Exception as e:
            print(f"Error generating health report: {e}")
            return {"error": str(e), "timestamp": time.time()}

    # ==================== END SYSTEM HEALTH MONITORING ====================

    # ==================== OPERATOR ALERT SYSTEM ====================
    
    def show_error_alert(self, error_type, message, severity="WARNING"):
        """Show visual error alert to operator"""
        try:
            error_config = self.ERROR_TYPES.get(error_type, {})
            error_name = error_config.get("name", error_type)
            
            # Determine icon and urgency based on severity
            if severity == "CRITICAL":
                icon = "error"
                title = "CRITICAL SYSTEM ERROR"
                color = "red"
            elif severity == "ERROR":
                icon = "warning"
                title = "SYSTEM ERROR"
                color = "orange"
            else:
                icon = "warning"
                title = "SYSTEM WARNING"
                color = "yellow"
            
            # Special handling for disconnection during SCAN_PHASE
            if error_type in ["CAMERA_DISCONNECTED", "ARDUINO_DISCONNECTED"] and self.current_mode == "SCAN_PHASE":
                title = "🚨 SCAN PHASE INTERRUPTED"
                
                if error_type == "CAMERA_DISCONNECTED":
                    scan_message = (
                        "CAMERA DISCONNECTION DETECTED!\n\n"
                        "The scanning process has been STOPPED for safety.\n"
                        "Current scan data may be lost.\n\n"
                        "Actions taken:\n"
                        "• Conveyor stopped immediately\n"
                        "• System switched to IDLE mode\n"
                        "• Scan session data cleared\n"
                        "• Automatic reconnection started\n\n"
                        "System will automatically attempt to reconnect cameras.\n"
                        "You will be notified when cameras are ready.\n\n"
                        "To resume:\n"
                        "1. Wait for automatic reconnection (or reconnect manually)\n"
                        "2. Restart scan phase\n"
                        "3. Re-scan the wood piece"
                    )
                elif error_type == "ARDUINO_DISCONNECTED":
                    scan_message = (
                        "ARDUINO DISCONNECTION DETECTED!\n\n"
                        "The scanning process has been STOPPED for safety.\n"
                        "Conveyor control is lost.\n\n"
                        "Actions taken:\n"
                        "• System switched to IDLE mode\n"
                        "• Scan session data cleared\n\n"
                        "To resume:\n"
                        "1. Reconnect Arduino\n"
                        "2. Restart scan phase\n"
                        "3. Re-scan the wood piece"
                    )
                message = scan_message
            
            # Show popup alert
            if error_type == "CAMERA_DISCONNECTED" and self.current_mode != "SCAN_PHASE":
                # Enhanced message for camera disconnection outside scan phase
                alert_message = (
                    f"{error_name}\n\n{message}\n\n"
                    "The system will automatically attempt to reconnect cameras in the background.\n"
                    "You will be notified when cameras are ready.\n\n"
                    "Please check camera connections and ensure they are properly plugged in."
                )
            else:
                alert_message = f"{error_name}\n\n{message}\n\nPlease check system status and take appropriate action."
            
            # Use toast for warnings, modal popup for critical errors only
            if severity == "CRITICAL":
                # Critical errors still use modal popup - user MUST acknowledge
                messagebox.showerror(title, alert_message)
            else:
                # Warnings and errors use non-blocking toast
                toast_type = "error" if severity == "ERROR" else "warning"
                self.show_toast_notification(
                    title,
                    alert_message[:200],  # Truncate for toast display
                    duration=8000,  # 8 seconds for important errors
                    type=toast_type
                )
                
            # Update status display with error information
            self.update_status_text(f"{title}: {error_name}", color)
            
            # Play audio alert if available
            self.play_audio_alert(severity)
            
            # Show desktop notification if possible
            self.show_desktop_notification(title, error_name, severity)
            
        except Exception as e:
            print(f"Error showing alert: {e}")
    
    def show_desktop_notification(self, title, message, severity="WARNING"):
        """Show desktop notification for system events"""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            
            if system == "Linux":
                # Use notify-send for Linux desktop notifications (if available)
                try:
                    # Check if notify-send is available
                    result = subprocess.run(["which", "notify-send"], capture_output=True, timeout=2)
                    if result.returncode != 0:
                        print("notify-send not available - skipping desktop notification")
                        return
                    
                    if severity == "CRITICAL":
                        urgency = "critical"
                        icon = "error"
                    elif severity == "INFO":
                        urgency = "normal"
                        icon = "info"
                    else:
                        urgency = "normal"
                        icon = "warning"
                    
                    subprocess.run([
                        "notify-send", 
                        "--urgency", urgency,
                        "--icon", icon,
                        "--app-name", "Wood Sorting System",
                        title, 
                        message
                    ], capture_output=True, timeout=5)
                    
                    print(f"Desktop notification sent: {title}")
                    
                except subprocess.TimeoutExpired:
                    print("Desktop notification timed out")
                except FileNotFoundError:
                    print("notify-send not found - desktop notifications disabled")
                except Exception as notify_error:
                    print(f"Failed to send desktop notification: {notify_error}")
                
        except Exception as e:
            print(f"Could not send desktop notification: {e}")
    
    def play_audio_alert(self, severity="WARNING"):
        """Play audio alert for error conditions"""
        try:
            # Different sounds for different severities
            if severity == "CRITICAL":
                # Play urgent beep pattern
                self.play_system_beep(pattern="urgent")
            elif severity == "ERROR":
                # Play warning beep pattern
                self.play_system_beep(pattern="warning")
            else:
                # Play simple beep
                self.play_system_beep(pattern="simple")
                
        except Exception as e:
            print(f"Error playing audio alert: {e}")
    
    def play_system_beep(self, pattern="simple"):
        """Play system beep with different patterns"""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            
            if pattern == "urgent":
                # Urgent: 3 quick beeps
                for _ in range(3):
                    if system == "Linux":
                        subprocess.run(["pactl", "upload-sample", "/usr/share/sounds/alsa/Front_Left.wav", "beep"], 
                                     capture_output=True, timeout=1)
                        subprocess.run(["pactl", "play-sample", "beep"], capture_output=True, timeout=1)
                    time.sleep(0.2)
            elif pattern == "warning":
                # Warning: 2 medium beeps
                for _ in range(2):
                    if system == "Linux":
                        subprocess.run(["pactl", "upload-sample", "/usr/share/sounds/alsa/Front_Right.wav", "warning"], 
                                     capture_output=True, timeout=1)
                        subprocess.run(["pactl", "play-sample", "warning"], capture_output=True, timeout=1)
                    time.sleep(0.5)
            else:
                # Simple: 1 beep
                if system == "Linux":
                    subprocess.run(["pactl", "upload-sample", "/usr/share/sounds/alsa/Front_Center.wav", "simple"], 
                                 capture_output=True, timeout=1)
                    subprocess.run(["pactl", "play-sample", "simple"], capture_output=True, timeout=1)
                    
        except Exception as e:
            # Fallback to basic system bell
            try:
                print("\a")  # ASCII bell character
            except:
                pass
            print(f"Error playing system beep: {e}")
    
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
    
    def show_manual_inspection_dialog(self, error_details):
        """Show dialog for manual inspection routing"""
        try:
            # Show manual inspection required dialog
            message = (
                "Manual Inspection Required\n\n"
                f"Error Details: {error_details}\n\n"
                "The system has detected issues that require manual inspection.\n"
                "Please inspect the wood piece and choose an action:\n\n"
                "• ACCEPT - Continue processing with manual override\n"
                "• REJECT - Route to reject bin\n"
                "• RETRY - Attempt automatic processing again\n"
                "• PAUSE - Pause system for maintenance"
            )
            
            # Custom dialog with buttons
            result = messagebox.askyesnocancel(
                "Manual Inspection Required", 
                message + "\n\nYes=Accept, No=Reject, Cancel=Pause"
            )
            
            if result is True:
                action = "ACCEPT"
            elif result is False:
                action = "REJECT"
            else:
                action = "PAUSE"
                
            # Handle the selected action
            self.handle_manual_inspection_action(action, error_details)
            
            return action
            
        except Exception as e:
            print(f"Error showing manual inspection dialog: {e}")
            return "PAUSE"  # Default to pause on error
    
    def handle_manual_inspection_action(self, action, error_details):
        """Handle the action selected during manual inspection"""
        try:
            print(f"Manual inspection action: {action} for error: {error_details}")
            
            if action == "ACCEPT":
                # Clear errors and continue processing
                self.clear_all_errors()
                # Notify Arduino that manual inspection is complete
                self.send_arduino_command("MANUAL_INSPECTION_COMPLETE")
                print("Manual override: Accepting piece and continuing processing")
                
            elif action == "REJECT":
                # Send reject command to Arduino
                self.send_arduino_command('R')  # Reject command for Arduino
                self.clear_all_errors()
                print("Manual override: Rejecting piece")
                
            elif action == "RETRY":
                # Clear errors and retry detection
                self.clear_all_errors()
                # Resume system operations
                self.send_arduino_command("RESUME_SYSTEM")
                print("Manual override: Retrying automatic processing")
                
            elif action == "PAUSE":
                # Keep system paused and switch to IDLE mode
                self.send_arduino_command("PAUSE_SYSTEM")
                self.set_idle_mode()
                print("Manual override: System paused for maintenance")
                
            # Update operator about the action taken
            self.update_status_text(f"Manual Inspection: {action} completed", "blue")
            
        except Exception as e:
            print(f"Error handling manual inspection action: {e}")
    
    def create_error_status_panel(self, parent_frame):
        """Create a visual error status panel in the UI"""
        try:
            # Create error status frame
            error_frame = tk.Frame(parent_frame, relief=tk.RAISED, bd=2)
            error_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Error indicator light
            self.error_indicator = tk.Label(error_frame, text="●", font=("Arial", 16), fg="green")
            self.error_indicator.pack(side=tk.LEFT, padx=5)
            
            # Error status text
            self.error_status_text = tk.Label(error_frame, text="System Healthy", font=("Arial", 10))
            self.error_status_text.pack(side=tk.LEFT, padx=5)
            
            # Manual inspection button (initially hidden)
            self.manual_inspection_btn = tk.Button(
                error_frame, 
                text="Manual Inspection", 
                command=self.open_manual_inspection_dialog,
                bg="orange", 
                fg="white",
                font=("Arial", 10, "bold")
            )
            # Don't pack initially - will be shown when needed
            
            # Clear all errors button
            self.clear_errors_btn = tk.Button(
                error_frame,
                text="Clear Errors",
                command=self.clear_all_errors_ui,
                bg="red",
                fg="white",
                font=("Arial", 8)
            )
            # Don't pack initially - will be shown when needed
            
            return error_frame
            
        except Exception as e:
            print(f"Error creating error status panel: {e}")
            return None
    
    def update_error_status_panel(self):
        """Update the visual error status panel"""
        try:
            if not hasattr(self, 'error_indicator'):
                return
                
            if self.error_state["active_errors"]:
                # Has errors - update indicator
                error_count = len(self.error_state["active_errors"])
                
                if self.error_state["system_paused"]:
                    self.error_indicator.config(fg="red", text="●")
                    self.error_status_text.config(text=f"SYSTEM PAUSED - {error_count} Error(s)")
                elif self.error_state["manual_inspection_required"]:
                    self.error_indicator.config(fg="orange", text="●")
                    self.error_status_text.config(text=f"MANUAL INSPECTION - {error_count} Error(s)")
                    # Show manual inspection button
                    if hasattr(self, 'manual_inspection_btn'):
                        self.manual_inspection_btn.pack(side=tk.RIGHT, padx=5)
                else:
                    self.error_indicator.config(fg="yellow", text="●")
                    self.error_status_text.config(text=f"WARNING - {error_count} Error(s)")
                
                # Show clear errors button
                if hasattr(self, 'clear_errors_btn'):
                    self.clear_errors_btn.pack(side=tk.RIGHT, padx=5)
                    
            else:
                # No errors - healthy status
                self.error_indicator.config(fg="green", text="●")
                self.error_status_text.config(text="System Healthy")
                
                # Hide action buttons
                if hasattr(self, 'manual_inspection_btn'):
                    self.manual_inspection_btn.pack_forget()
                if hasattr(self, 'clear_errors_btn'):
                    self.clear_errors_btn.pack_forget()
                    
        except Exception as e:
            print(f"Error updating error status panel: {e}")
    
    def open_manual_inspection_dialog(self):
        """Open manual inspection dialog from UI button"""
        try:
            active_errors = list(self.error_state["active_errors"])
            error_details = ", ".join(active_errors) if active_errors else "System requires manual inspection"
            self.show_manual_inspection_dialog(error_details)
            
        except Exception as e:
            print(f"Error opening manual inspection dialog: {e}")
    
    def clear_all_errors_ui(self):
        """Clear all errors from UI button"""
        try:
            self.clear_all_errors()
            self.update_error_status_panel()
            
        except Exception as e:
            print(f"Error clearing errors from UI: {e}")

    # ==================== END OPERATOR ALERT SYSTEM ====================

    def on_closing(self):
        print("Releasing resources...")
        
        # Set a flag to indicate shutdown is in progress
        self._shutting_down = True
        
        # Stop camera monitoring
        self.camera_monitor_active = False
        
        # Clean up memory resources first to prevent X11 errors
        self.cleanup_memory_resources()
        
        # Close Arduino connection first to stop the listener thread
        if hasattr(self, 'ser') and self.ser:
            try:
                print("Closing Arduino connection...")
                self.ser.close()
                self.ser = None
            except Exception as e:
                print(f"Error closing Arduino connection: {e}")
        
        # Wait a moment for the Arduino thread to exit gracefully
        if hasattr(self, 'arduino_thread') and self.arduino_thread.is_alive():
            print("Waiting for Arduino thread to close...")
            self.arduino_thread.join(timeout=2.0)  # Wait up to 2 seconds
        
        # Release camera resources using CameraHandler
        try:
            print("Releasing camera resources...")
            if hasattr(self, 'camera_handler'):
                self.camera_handler.release_cameras()
        except Exception as e:
            print(f"Error releasing cameras: {e}")
        
        # Close the application
        try:
            self.destroy()
        except Exception as e:
            print(f"Error during application shutdown: {e}")

    def reset_inactivity_timer(self):
        self.last_activity_time = time.time()
        if hasattr(self, 'report_generated'):
            self.report_generated = False

    def check_inactivity(self):
        # Generate report after 30 seconds of inactivity (auto-log feature)
        if (not self.report_generated and
            (time.time() - self.last_activity_time > 30) and
            self.total_pieces_processed > 0): # Only generate if something was processed
            self.generate_report()
            self.report_generated = True
        self.after(1000, self.check_inactivity)

    def update_feeds(self):
        """Update camera feeds on canvases, but skip if displaying processed frame"""
        if self.displaying_processed_frame:
            # Skip updating live feed while showing processed frame
            self.after(100, self.update_feeds)
            return

        try:
            # Read frames from cameras independently
            ret_top, frame_top = self.cap_top.read() if self.cap_top else (False, None)
            ret_bottom, frame_bottom = self.cap_bottom.read() if self.cap_bottom else (False, None)

            # Process top camera frame if available
            if ret_top and frame_top is not None:
                # Apply ROI overlay to live feed if enabled
                if self.roi_enabled.get("top", True):
                    frame_top = self.draw_roi_overlay(frame_top, "top")
                # Display on top canvas
                self._display_frame_on_canvas(frame_top, self.top_canvas)

            # Process bottom camera frame if available
            if ret_bottom and frame_bottom is not None:
                # Flip bottom frame horizontally (matching the other app)
                frame_bottom = cv2.flip(frame_bottom, 1)
                # Apply ROI overlay to live feed if enabled
                if self.roi_enabled.get("bottom", True):
                    frame_bottom = self.draw_roi_overlay(frame_bottom, "bottom")
                # Display on bottom canvas
                self._display_frame_on_canvas(frame_bottom, self.bottom_canvas)

        except Exception as e:
            print(f"Error updating feeds: {e}")

        # Schedule next update
        self.after(100, self.update_feeds)

    def generate_report(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        base_filename = f"report_{timestamp}"
        txt_filename = f"{base_filename}.txt"
        pdf_filename = f"{base_filename}.pdf"
        log_filename = "wood_sorting_log.txt"
        
        # --- Build Report Content ---
        content = f"--- SS-EN 1611-1 Wood Sorting Report ---\n"
        content += f"Generated at: {timestamp}\n\n"
        content += "--- Session Summary ---\n"
        content += f"Total Pieces Processed: {self.total_pieces_processed}\n"
        content += f"Grade G2-0: {self.grade_counts.get(1, 0)}\n"
        content += f"Grade G2-1: {self.grade_counts.get(2, 0)}\n"
        content += f"Grade G2-2: {self.grade_counts.get(3, 0)}\n"
        content += f"Grade G2-3: {self.grade_counts.get(4, 0)}\n"
        content += f"Grade G2-4: {self.grade_counts.get(5, 0)}\n"
        
        content += "\n\n--- Individual Piece Log ---\n"
        if not self.session_log:
            content += "No pieces were processed in this session.\n"
        else:
            for entry in self.session_log:
                content += f"\nPiece #{entry['piece_number']}: Grade {entry['final_grade']}\n"
                if not entry['defects']:
                    content += "  - No defects detected.\n"
                else:
                    for defect in entry['defects']:
                        content += f"  - Defect: {defect['type']}, Count: {defect['count']}, Sizes (mm): {defect['sizes']}\n"

        # Save individual report files
        try:
            with open(txt_filename, 'w') as f:
                f.write(content)
            print(f"SS-EN 1611-1 report generated: {txt_filename}")
        except Exception as e:
            print(f"Error generating TXT report: {e}")
            self.show_toast_notification(
                "❌ Report Error",
                f"Could not save TXT report:\n{str(e)[:100]}",
                duration=6000,
                type="error"
            )
            return

        # Append to main log file
        try:
            log_entry = f"{timestamp} | Pieces: {self.total_pieces_processed} | G2-0: {self.grade_counts.get(1, 0)} | G2-1: {self.grade_counts.get(2, 0)} | G2-2: {self.grade_counts.get(3, 0)} | G2-3: {self.grade_counts.get(4, 0)} | G2-4: {self.grade_counts.get(5, 0)}\n"
            with open(log_filename, 'a') as f:
                f.write(log_entry)
            print(f"Entry added to log file: {log_filename}")
            if hasattr(self, 'log_status_label'):
                self.log_status_label.configure(text="Log: Updated", text_color="blue")
        except Exception as e:
            print(f"Error updating log file: {e}")
            if hasattr(self, 'log_status_label'):
                self.log_status_label.configure(text="Log: Error", text_color="red")

        # Generate PDF Report
        try:
            c = canvas.Canvas(pdf_filename, pagesize=letter)
            width, height = letter
            
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2.0, height - 1*inch, "SS-EN 1611-1 Wood Sorting System Report")
            c.setFont("Helvetica", 12)
            
            text = c.beginText(1*inch, height - 1.5*inch)
            text.textLine(f"Generated at: {timestamp}")
            text.textLine("")
            text.setFont("Helvetica-Bold", 12)
            text.textLine("Session Summary")
            text.setFont("Helvetica", 12)
            text.textLine(f"Total Pieces Processed: {self.total_pieces_processed}")
            text.textLine(f"Grade G2-0: {self.grade_counts.get(1, 0)}")
            text.textLine(f"Grade G2-1: {self.grade_counts.get(2, 0)}")
            text.textLine(f"Grade G2-2: {self.grade_counts.get(3, 0)}")
            text.textLine(f"Grade G2-3: {self.grade_counts.get(4, 0)}")
            text.textLine(f"Grade G2-4: {self.grade_counts.get(5, 0)}")
            text.textLine("")
            text.textLine("")
            text.setFont("Helvetica-Bold", 12)
            text.textLine("Individual Piece Log")
            text.setFont("Helvetica", 12)

            if not self.session_log:
                text.textLine("No pieces were processed in this session.")
            else:
                for entry in self.session_log:
                    # Check if we need a new page before drawing the next entry
                    if text.getY() < 2 * inch:
                        c.drawText(text)
                        c.showPage()
                        c.setFont("Helvetica", 12)
                        text = c.beginText(1*inch, height - 1*inch)

                    text.textLine("")
                    text.setFont("Helvetica-Bold", 10)
                    text.textLine(f"Piece #{entry['piece_number']}: Grade {entry['final_grade']}")
                    text.setFont("Helvetica", 10)
                    if not entry['defects']:
                        text.textLine("  - No defects detected.")
                    else:
                        for defect in entry['defects']:
                            text.textLine(f"  - Defect: {defect['type']}, Count: {defect['count']}, Sizes (mm): {defect['sizes']}")
            
            c.drawText(text)
            c.save()
            print(f"SS-EN 1611-1 PDF report generated: {pdf_filename}")
            
            self.last_report_path = pdf_filename
            self.last_report_label.configure(text=f"Last Report: {os.path.basename(self.last_report_path)}")
            
            # Show notification only if toggle is enabled - use non-blocking toast
            if self.show_report_notification.get():
                self.show_toast_notification(
                    "📄 Report Generated",
                    f"Reports saved:\n{os.path.basename(txt_filename)}\n{os.path.basename(pdf_filename)}",
                    duration=6000,
                    type="success"
                )

        except Exception as e:
            print(f"Error generating PDF report: {e}")
            self.show_toast_notification(
                "❌ Report Error",
                f"Could not save PDF report:\n{str(e)[:100]}",
                duration=6000,
                type="error"
            )
            
        # Reset the session log after generating the report
        self.session_log = []
        print("Session log has been cleared for the next report.")


    def manual_generate_report(self):
        """Manually generate a report"""
        self.generate_report()
        if hasattr(self, 'log_status_label'):
            self.log_status_label.configure(text="Log: Manual report generated", text_color="green")

    def view_session_folder(self):
        """Open the current session folder in file explorer"""
        import os
        import subprocess
        import platform

        try:
            # Check if we have a current session folder
            if hasattr(self, 'scan_session_folder') and self.scan_session_folder and os.path.exists(self.scan_session_folder):
                folder_path = self.scan_session_folder
            else:
                # Fallback to the Detections directory
                folder_path = os.path.join("testIR", "Detections")
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)

            # Open folder based on platform
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])

            print(f"Opened session folder: {folder_path}")
            if hasattr(self, 'log_status_label'):
                self.log_status_label.configure(text="Log: Session folder opened", text_color="blue")

        except Exception as e:
            print(f"Error opening session folder: {e}")
            if hasattr(self, 'log_status_label'):
                self.log_status_label.configure(text="Log: Error opening folder", text_color="red")

    def _reassign_cameras_ui(self):
        """UI wrapper for camera reassignment"""
        try:
            success = self.camera_handler.reassign_cameras_runtime()
            if success:
                # Update the cap references
                self.cap_top = self.camera_handler.top_camera
                self.cap_bottom = self.camera_handler.bottom_camera
                self.show_toast_notification(
                    "✅ Success",
                    "Cameras reassigned successfully!",
                    duration=5000,
                    type="success"
                )
            else:
                self.show_toast_notification(
                    "❌ Error",
                    "Camera reassignment failed.\nCheck console for details.",
                    duration=5000,
                    type="error"
                )
        except Exception as e:
            self.show_toast_notification(
                "❌ Error",
                f"Camera reassignment error:\n{str(e)[:100]}",
                duration=5000,
                type="error"
            )

    def _reassign_arduino_ui(self):
        """UI wrapper for Arduino reassignment"""
        try:
            success = self.reassign_arduino_runtime()
            if success:
                self.show_toast_notification(
                    "✅ Success",
                    "Arduino reassigned successfully!",
                    duration=5000,
                    type="success"
                )
            else:
                self.show_toast_notification(
                    "❌ Error",
                    "Arduino reassignment failed.\nCheck console for details.",
                    duration=5000,
                    type="error"
                )
        except Exception as e:
            self.show_toast_notification(
                "❌ Error",
                f"Arduino reassignment error:\n{str(e)[:100]}",
                duration=5000,
                type="error"
            )

    def simulate_ir_events(self):
        """Simulate IR beam events for testing TRIGGER mode"""
        print("Simulating IR beam events for testing...")

        # Simulate 'B' message (beam broken)
        print("Simulating 'B' message (beam broken)...")
        self.message_queue.put(("arduino_message", "B"))

        # Wait a moment then simulate 'L' message (beam clear with duration)
        self.after(2000, lambda: self.simulate_beam_clear())

    def simulate_scan_events(self):
        """Simulate SCAN_PHASE events for testing"""
        print("Simulating SCAN_PHASE events for testing...")

        # Simulate 'B' message (beam broken)
        print("Simulating 'B' message (beam broken)...")
        self.message_queue.put(("arduino_message", "B"))

        # Simulate segment captures
        self.after(1000, lambda: self.simulate_segment_capture(1))
        self.after(3000, lambda: self.simulate_segment_capture(2))
        self.after(5000, lambda: self.simulate_segment_capture(3))
        self.after(7000, lambda: self.simulate_scan_complete())

    def simulate_segment_capture(self, segment_num):
        """Simulate segment capture message"""
        print(f"Simulating 'CAPTURE:{segment_num}'")
        self.message_queue.put(("arduino_message", f"CAPTURE:{segment_num}"))

    def simulate_scan_complete(self):
        """Simulate scan completion"""
        print("Simulating 'Last scan phase complete. Clearing tail...'")
        self.message_queue.put(("arduino_message", "Last scan phase complete. Clearing tail..."))

    def simulate_beam_clear(self):
        """Simulate beam clear message"""
        print("Simulating 'L:1000' message (beam clear, 1000ms duration)...")
        self.message_queue.put(("arduino_message", "L:1000"))

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode (F11 key)"""
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        """Exit fullscreen mode (Escape key)"""
        self.is_fullscreen = False
        self.attributes("-fullscreen", False)
        return "break"

    def auto_fullscreen_rpi(self):
        """Automatically enable fullscreen for Raspberry Pi deployment"""
        try:
            # Check if running on Raspberry Pi
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    print("Raspberry Pi detected - enabling fullscreen mode")
                    self.is_fullscreen = True
                    self.attributes("-fullscreen", True)
        except FileNotFoundError:
            # Not running on Raspberry Pi, continue normally
            pass
        except Exception as e:
            print(f"Error checking system: {e}")

if __name__ == "__main__":
    import sys
    app = App()
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        app.set_trigger_mode()
        app.after(1000, app.simulate_ir_events)  # Start simulation after 1 second
    elif len(sys.argv) > 1 and sys.argv[1] == 'scan':
        app.set_scan_mode()
        app.after(1000, app.simulate_scan_events)  # Start scan simulation after 1 second
    app.mainloop()

