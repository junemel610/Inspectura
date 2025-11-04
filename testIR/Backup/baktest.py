import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import serial
import threading
import time
import queue
import degirum as dg
import degirum_tools
import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import numpy as np
from scipy.optimize import linear_sum_assignment
from filterpy.kalman import KalmanFilter
import copy
from typing import Dict


class CameraHandler:
    def __init__(self):
        self.top_camera = None
        self.bottom_camera = None
        self.top_camera_index = 0  # Cam0
        self.bottom_camera_index = 2  # Cam2
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
            'brightness': 85,
            'contrast': 125,
            'saturation': 125,
            'hue': 0,
            'exposure': -6,
            'white_balance': 4850,
            'gain': 0,
            'backlight_compensation': 1
        }

    def initialize_cameras(self):
        try:
            self.top_camera = cv2.VideoCapture(self.top_camera_index)
            if not self.top_camera.isOpened():
                raise RuntimeError(f"Could not open top camera (Cam0 - index {self.top_camera_index})")
            self.bottom_camera = cv2.VideoCapture(self.bottom_camera_index)
            if not self.bottom_camera.isOpened():
                self.top_camera.release()
                raise RuntimeError(f"Could not open bottom camera (Cam2 - index {self.bottom_camera_index})")
            self.top_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.top_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.bottom_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.bottom_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self._apply_camera_settings(self.top_camera, self.top_camera_settings)
            self._apply_camera_settings(self.bottom_camera, self.bottom_camera_settings)
            print("Cameras initialized successfully at 720p (1280x720)")
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

    def release_cameras(self):
        if self.top_camera:
            self.top_camera.release()
            self.top_camera = None
        if self.bottom_camera:
            self.bottom_camera.release()
            self.bottom_camera = None
        print("Cameras released")

# SS-EN 1611-1 Grading Standards Implementation (Revised)
# Grade constants - Individual grades
GRADE_G2_0 = "G2-0"
GRADE_G2_1 = "G2-1"
GRADE_G2_2 = "G2-2"
GRADE_G2_3 = "G2-3"
GRADE_G2_4 = "G2-4"

# Camera-specific calibration based on your setup
# Top camera: 37cm distance, Bottom camera: 29cm distance
# Assuming 1280x720 resolution with typical camera FOV
TOP_CAMERA_DISTANCE_CM = 37
BOTTOM_CAMERA_DISTANCE_CM = 29

# Actual pixel-to-millimeter factors (measured)
TOP_CAMERA_PIXEL_TO_MM = 2.96  # Top camera: 2.96 pixels per mm
BOTTOM_CAMERA_PIXEL_TO_MM = 3.18  # Bottom camera: 3.18 pixels per mm

# Your actual wood pallet width
WOOD_PALLET_WIDTH_MM = 115  # 11.5cm = 115mm

# SS-EN 1611-1 Grading constants for size limits: limit = (0.10 * wood_width) + constant
GRADING_CONSTANTS = {
    "Sound_Knot": {"G2-0": 10, "G2-1": 20, "G2-2": 35, "G2-3": 50},
    "Dead_Knot": {"G2-0": 0, "G2-1": 10, "G2-2": 20, "G2-3": 50},  # Using stricter limits
    "Unsound_Knot": {"G2-2": 15, "G2-3": 40}  # Not permitted in G2-0, G2-1
}

# Knot count limits per meter for Dead and Unsound knots
KNOT_COUNT_LIMITS = {
    "G2-0": 0,
    "G2-1": 1,
    "G2-2": 2,
    "G2-3": 5,
    "G2-4": float('inf')
}


class Track:
    """Represents a single object track"""
    def __init__(self, track_id, bbox, defect_type, size_mm, confidence=0.5):
        self.track_id = track_id
        self.defect_type = defect_type
        self.size_mm = size_mm
        self.confidence = confidence
        self.age = 1  # How many frames this track has been alive
        self.time_since_update = 0  # Frames since last update
        self.hits = 1  # Number of successful updates
        self.hit_streak = 1  # Consecutive hits

        # Initialize Kalman filter for position prediction
        self.kalman = self._init_kalman_filter(bbox)

        # Store original detection info
        self.bbox = bbox
        self.first_seen = datetime.now().isoformat()
        self.last_seen = datetime.now().isoformat()

    def _init_kalman_filter(self, bbox):
        """Initialize Kalman filter for bounding box tracking"""
        kf = KalmanFilter(dim_x=4, dim_z=4)  # 4 state vars, 4 measurement vars

        # State: [x, y, w, h, vx, vy, vw, vh] but we'll use 4D for simplicity
        kf.x = np.array([bbox[0], bbox[1], bbox[2]-bbox[0], bbox[3]-bbox[1]]).reshape(4, 1)

        # State transition matrix (constant velocity model)
        kf.F = np.array([[1, 0, 0, 0],
                        [0, 1, 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1]])

        # Measurement matrix (we measure position and size directly)
        kf.H = np.eye(4)

        # Process noise (higher for fast-moving objects)
        kf.Q = np.eye(4) * 0.5

        # Measurement noise (detection uncertainty)
        kf.R = np.eye(4) * 0.5

        # Initial covariance
        kf.P = np.eye(4) * 10.0

        return kf

    def predict(self):
        """Predict next position using Kalman filter"""
        self.kalman.predict()
        self.age += 1
        self.time_since_update += 1
        return self.get_state()

    def update(self, bbox, confidence=0.5):
        """Update track with new detection"""
        self.time_since_update = 0
        self.hits += 1
        self.hit_streak += 1

        # Update Kalman filter
        measurement = np.array([bbox[0], bbox[1], bbox[2]-bbox[0], bbox[3]-bbox[1]]).reshape(4, 1)
        self.kalman.update(measurement)

        # Update stored bbox and confidence
        self.bbox = bbox
        self.confidence = max(self.confidence, confidence)  # Keep highest confidence
        self.last_seen = datetime.now().isoformat()

    def get_state(self):
        """Get current state as bbox [x1, y1, x2, y2]"""
        state = self.kalman.x.flatten()
        x1, y1, w, h = state
        return [x1, y1, x1 + w, y1 + h]


class CustomObjectTracker:
    """Custom object tracker similar to SORT algorithm"""
    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3):
        self.tracks = []
        self.track_id_count = 0
        self.max_age = max_age  # Maximum frames a track can go without update
        self.min_hits = min_hits  # Minimum hits to consider track confirmed
        self.iou_threshold = iou_threshold  # IOU threshold for matching

    def update(self, detections):
        """
        Update tracks with new detections
        detections: list of (bbox, defect_type, size_mm, confidence) tuples
        """
        # Predict new locations for existing tracks
        for track in self.tracks:
            track.predict()

        # Associate detections with existing tracks
        matched, unmatched_dets, unmatched_tracks = self._associate_detections(detections)

        # Update matched tracks
        for track_idx, det_idx in matched:
            self.tracks[track_idx].update(detections[det_idx][0], detections[det_idx][3])

        # Create new tracks for unmatched detections
        for det_idx in unmatched_dets:
            bbox, defect_type, size_mm, confidence = detections[det_idx]
            if confidence > 0.3:  # Only create tracks for reasonably confident detections
                self._create_track(bbox, defect_type, size_mm, confidence)

        # Mark unmatched tracks as lost
        for track_idx in unmatched_tracks:
            self.tracks[track_idx].time_since_update += 1

        # Remove dead tracks
        self.tracks = [t for t in self.tracks if t.time_since_update <= self.max_age]

        # Return active tracks
        return [t for t in self.tracks if t.hits >= self.min_hits]

    def _associate_detections(self, detections):
        """Associate detections with existing tracks using IoU"""
        if len(self.tracks) == 0:
            return [], list(range(len(detections))), []

        if len(detections) == 0:
            return [], [], list(range(len(self.tracks)))

        # Calculate IoU matrix
        iou_matrix = np.zeros((len(detections), len(self.tracks)))
        for d, det in enumerate(detections):
            for t, track in enumerate(self.tracks):
                iou_matrix[d, t] = self._calculate_iou(det[0], track.get_state())

        # Use Hungarian algorithm for optimal assignment
        det_indices, track_indices = linear_sum_assignment(-iou_matrix)  # Maximize IoU

        # Filter matches above threshold
        matched = []
        unmatched_dets = list(range(len(detections)))
        unmatched_tracks = list(range(len(self.tracks)))

        for d, t in zip(det_indices, track_indices):
            if iou_matrix[d, t] >= self.iou_threshold:
                matched.append((t, d))  # (track_idx, det_idx)
                unmatched_dets.remove(d)
                unmatched_tracks.remove(t)

        return matched, unmatched_dets, unmatched_tracks

    def _calculate_iou(self, bbox1, bbox2):
        """Calculate Intersection over Union of two bounding boxes"""
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

        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def _create_track(self, bbox, defect_type, size_mm, confidence):
        """Create a new track"""
        track = Track(self.track_id_count, bbox, defect_type, size_mm, confidence)
        self.tracks.append(track)
        self.track_id_count += 1
        return track

    def get_tracks(self):
        """Get all active tracks"""
        return [t for t in self.tracks if t.hits >= self.min_hits]

    def clear(self):
        """Clear all tracks"""
        self.tracks = []
        self.track_id_count = 0


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
            if (detection['defect_type'] == cluster_detection['defect_type'] and
                abs(detection['size_mm'] - cluster_detection['size_mm']) <= self.spatial_threshold_mm):
                return True

        return False

    def _select_best_detection(self, cluster):
        """Select the best detection from a cluster (largest size, highest confidence)"""
        if len(cluster) == 1:
            return cluster[0]

        # Select detection with largest size (most conservative for grading)
        best_detection = max(cluster, key=lambda x: x['size_mm'])
        return best_detection

    def _timestamp_to_seconds(self, timestamp_str):
        """Convert ISO timestamp to seconds since epoch"""
        from datetime import datetime
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.timestamp()


class ColorWoodDetector:
    def __init__(self):
        self.wood_color_profiles = {
            'top_panel': {
                'rgb_lower': np.array([169, 180, 176]),  # BGR
                'rgb_upper': np.array([225, 220, 210]),
                'name': 'Top Panel Wood'
            },
            'bottom_panel': {
                'rgb_lower': np.array([134, 105, 109]),  # BGR
                'rgb_upper': np.array([207, 176, 183]),
                'name': 'Bottom Panel Wood'
            }
        }

        # Detection parameters
        self.min_contour_area = 2000      # Increased for more reliable detection with tighter RGB ranges
        self.max_contour_area = 500000    # Slightly reduced for typical wood plank sizes
        self.min_aspect_ratio = 1.0       # Tightened for more rectangular wood shapes
        self.max_aspect_ratio = 10.0      # Reduced for more typical plank proportions
        self.contour_approximation = 0.025 # Slightly tighter for better shape approximation

        # Morphological operations
        self.morph_kernel_size = 11
        self.closing_iterations = 3
        self.opening_iterations = 2

        # Pixel to mm conversion parameters for width measurement
        self.pixel_per_mm_top = 2.96     # Placeholder: calibrate based on top camera distance (31cm)
        self.pixel_per_mm_bottom = 3.18  # Placeholder: calibrate based on bottom camera distance

    def calculate_width_mm(self, bbox_pixels: int, camera: str = 'top') -> float:
        """Calculate width in mm from bounding box dimension in pixels using pixel_per_mm factors"""
        if camera == 'top':
            return bbox_pixels / self.pixel_per_mm_top
        elif camera == 'bottom':
            return bbox_pixels / self.pixel_per_mm_bottom
        else:
            raise ValueError("Camera must be 'top' or 'bottom'")

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
        print(f"🎨 Dominant RGB in image: R={int(np.mean(r_values)):.0f}±{int(np.std(r_values)):.0f}, G={int(np.mean(g_values)):.0f}, B={int(np.mean(b_values)):.0f}")

        return analysis

    def detect_wood_by_color(self, image: np.ndarray, profile_names: list = None) -> tuple:
        """Detect wood using color profiles"""
        if profile_names is None:
            profile_names = list(self.wood_color_profiles.keys())

        # Apply histogram equalization on V channel for better lighting compensation
        hsv_temp = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv_temp)
        v = cv2.equalizeHist(v)
        hsv_temp = cv2.merge([h, s, v])
        rgb = cv2.cvtColor(hsv_temp, cv2.COLOR_HSV2BGR)

        combined_mask = np.zeros(rgb.shape[:2], dtype=np.uint8)

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

        pre_morph_pixels = cv2.countNonZero(combined_mask)
        pre_morph_percentage = (pre_morph_pixels / total_pixels) * 100
        print(f"🔧 Pre-morph combined mask: {pre_morph_pixels} pixels ({pre_morph_percentage:.1f}%)")

        # Clean up mask with morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (self.morph_kernel_size, self.morph_kernel_size))
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=self.closing_iterations)
        combined_mask = cv2.dilate(combined_mask, kernel, iterations=1)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel, iterations=self.opening_iterations)

        post_morph_pixels = cv2.countNonZero(combined_mask)
        post_morph_percentage = (post_morph_pixels / total_pixels) * 100
        print(f"🔧 Post-morph combined mask: {post_morph_pixels} pixels ({post_morph_percentage:.1f}%)")

        # Additional logging for dominant colors
        rgb_flat = rgb.reshape(-1, 3)
        r_values = rgb_flat[:, 0]
        g_values = rgb_flat[:, 1]
        b_values = rgb_flat[:, 2]
        print(f"🎨 Dominant RGB in image: R={int(np.mean(r_values)):.0f}±{int(np.std(r_values)):.0f}, G={int(np.mean(g_values)):.0f}, B={int(np.mean(b_values)):.0f}")

        return combined_mask, []

    def detect_rectangular_contours(self, mask: np.ndarray, camera: str = 'top') -> list:
        """Detect rectangular contours that could be wood planks"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        print(f"📐 Found {len(contours)} total contours")

        wood_candidates = []
        rejected_area = 0
        rejected_aspect = 0

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            # Filter by area
            if area < self.min_contour_area or area > self.max_contour_area:
                rejected_area += 1
                print(f"  ❌ Contour {i}: area {area:.0f} out of range [{self.min_contour_area}, {self.max_contour_area}]")
                continue

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

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

        print(f"📊 Contour filtering: {len(contours)} total, {rejected_area} rejected by area, {rejected_aspect} by aspect, {len(wood_candidates)} candidates")

        # Sort by confidence
        wood_candidates.sort(key=lambda x: x['confidence'], reverse=True)

        return wood_candidates

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

    def _detect_wood_by_texture(self, image: np.ndarray) -> float:
        """Detect wood using texture analysis (LBP features)"""
        try:
            # Convert to grayscale for texture analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Calculate texture features using Local Binary Patterns (LBP)
            # Simple texture measure: variance of Laplacian (focus/blur measure)
            laplacian_var = cv2.Laplacian(blurred, cv2.CV_64F).var()

            # Wood typically has moderate texture (not too smooth, not too rough)
            # Normalize to 0-1 confidence score
            if laplacian_var < 50:
                # Too smooth (might be painted surface)
                texture_confidence = 0.2
            elif laplacian_var < 200:
                # Good wood texture range
                texture_confidence = 0.8
            elif laplacian_var < 500:
                # Moderately textured
                texture_confidence = 0.6
            else:
                # Too rough (might be heavily damaged)
                texture_confidence = 0.3

            print(f"🔍 Texture analysis: Laplacian variance = {laplacian_var:.1f}, confidence = {texture_confidence:.2f}")

            return texture_confidence

        except Exception as e:
            print(f"❌ Error in texture analysis: {e}")
            return 0.5  # Neutral confidence on error

    def _detect_wood_by_shape(self, image: np.ndarray, camera: str = 'top') -> tuple:
        """Detect wood using shape analysis (contours and geometry)"""
        try:
            # Convert to grayscale and apply edge detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            print(f"🔺 Found {len(contours)} contours for shape analysis")

            wood_shapes = []
            for i, contour in enumerate(contours):
                area = cv2.contourArea(contour)

                # Filter by area
                if area < 1000:  # Smaller threshold for shape analysis
                    continue

                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)

                # Calculate shape properties
                aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 10
                extent = area / (w * h) if (w * h) > 0 else 0

                # Wood planks typically have rectangular shapes with good extent
                if 1.2 <= aspect_ratio <= 8.0 and extent > 0.6:
                    confidence = min(extent * 0.8 + (1.0 / aspect_ratio) * 0.2, 1.0)
                    wood_shapes.append({
                        'bbox': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'extent': extent,
                        'confidence': confidence
                    })
                    print(f"  ✅ Contour {i}: area={area:.0f}, aspect={aspect_ratio:.2f}, extent={extent:.2f}, conf={confidence:.2f}")

            return wood_shapes, edges

        except Exception as e:
            print(f"❌ Error in shape analysis: {e}")
            return [], None

    def visualize_detection(self, image: np.ndarray, detection_result: Dict, output_path: str = None) -> np.ndarray:
        """Create a visualization of the wood detection results"""
        vis_image = image.copy()

        if not detection_result.get('wood_detected', False):
            # No wood detected - add text overlay
            h, w = vis_image.shape[:2]
            cv2.putText(vis_image, "NO WOOD DETECTED", (w//2 - 150, h//2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            return vis_image

        # Draw wood detection results
        wood_candidates = detection_result.get('wood_candidates', [])
        for i, candidate in enumerate(wood_candidates):
            x, y, w, h = candidate['bbox']
            confidence = candidate['confidence']

            # Color based on confidence
            if confidence > 0.7:
                color = (0, 255, 0)  # Green for high confidence
            elif confidence > 0.5:
                color = (0, 255, 255)  # Yellow for medium confidence
            else:
                color = (0, 165, 255)  # Orange for low confidence

            # Draw bounding box
            cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 3)

            # Add label
            label = f"Wood {i+1}: {confidence:.2f}"
            cv2.putText(vis_image, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        # Add summary information
        h, w = vis_image.shape[:2]
        wood_count = detection_result.get('wood_count', 0)
        total_confidence = detection_result.get('confidence', 0.0)

        summary_text = f"Wood Detected: {wood_count} pieces (conf: {total_confidence:.2f})"
        cv2.putText(vis_image, summary_text, (10, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Save if output path provided
        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(vis_image, cv2.COLOR_RGB2BGR))
            print(f"💾 Visualization saved to: {output_path}")

        return vis_image

    def generate_auto_roi(self, wood_candidates: list, image_shape: tuple) -> tuple:
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

    def detect_wood_comprehensive(self, image: np.ndarray, profile_names: list = None, roi: tuple = None, camera: str = 'top') -> dict:
        """Comprehensive wood detection combining color and shape analysis"""

        print(f"🪵 Starting comprehensive wood detection on image shape: {image.shape}")

        # Step 1: Color-based detection with optional ROI
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

        print(f"✅ Detection complete: wood_detected={result['wood_detected']}, count={result['wood_count']}, confidence={result['confidence']:.2f}")

        return result


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wood Sorting Application")
        
        # Get screen dimensions for dynamic sizing
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Calculate window size (90% of screen size for windowed mode)
        window_width = int(screen_width * 0.9)
        window_height = int(screen_height * 0.9)
        
        # Center the window on screen
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # Set geometry with calculated dimensions
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Make window resizable
        self.resizable(True, True)
        
        # Set minimum size to prevent too small windows
        self.minsize(800, 600)
        
        # For Raspberry Pi - detect if running in fullscreen environment
        self.is_fullscreen = False
        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        
        # Auto-fullscreen for Raspberry Pi (you can enable this)
        # Uncomment the next line if you want automatic fullscreen on startup
        # self.after(100, self.auto_fullscreen_rpi)
        
        # Calculate responsive font sizes based on screen size
        base_font_size = max(8, min(12, int(screen_height / 80)))  # Reduced base size for better fit
        self.font_small = ("Helvetica", base_font_size - 1)
        self.font_normal = ("Helvetica", base_font_size)
        self.font_large = ("Helvetica", base_font_size + 2, "bold")
        self.font_button = ("Helvetica", base_font_size, "bold")  # Button font

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
        
        # Detection tracking variables
        self.detection_session_id = None
        self.piece_counter = 0
        self.current_piece_data = None
        
        # System mode tracking
        self.current_mode = "IDLE"  # Can be "IDLE", "TRIGGER", or "CONTINUOUS"
        
        # Automatic detection state (triggered by IR beam)
        self.live_detection_var = tk.BooleanVar(value=False) # For live inference mode
        self.auto_grade_var = tk.BooleanVar(value=False) # For auto grading in live mode
        self._last_auto_grade_time = 0
        self._in_active_inference = False  # Flag to prevent UI conflicts during inference

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

        # --- DeGirum Model and Camera Initialization ---
        # DeGirum Configuration
        self.inference_host_address = "@local"
        self.zoo_url = "/home/inspectura/Desktop/WoodSortingApplication/models/V2DefectCombined--640x640_quant_hailort_hailo8_1"
        self.model_name = "V2DefectCombined--640x640_quant_hailort_hailo8_1"
        
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
        
        # Initialize custom object trackers for each camera (optimized for fast movement)
        self.trackers = {
            "top": CustomObjectTracker(max_age=8, min_hits=1, iou_threshold=0.4),
            "bottom": CustomObjectTracker(max_age=8, min_hits=1, iou_threshold=0.4)
        }

        # Initialize detection deduplicator for low FPS scenarios
        self.deduplicator = DetectionDeduplicator(spatial_threshold_mm=15.0, temporal_threshold_sec=1.0)

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
        self.rgb_wood_detector = ColorWoodDetector()
        print("RGB Wood Detector initialized for dynamic ROI generation")

        # Initialize dynamic ROI storage
        self.dynamic_roi = None

        # Store wood detection results for visualization
        self.wood_detection_results = {"top": None, "bottom": None}

        # Live detection tracking
        self.live_detections = {"top": {}, "bottom": {}}
        self.live_grades = {"top": "No wood detected", "bottom": "No wood detected"}

        # ROI (Region of Interest) settings - Removed top ROI to avoid confusion
        self.roi_enabled = {"top": False, "bottom": False}  # Disable ROI for both cameras - use dynamic ROI instead
        self.roi_coordinates = {
            "top": {
                "x1": 0,    # Full frame for top camera
                "y1": 0,
                "x2": 1280,
                "y2": 720
            },
            "bottom": {
                "x1": 0,    # Full frame for bottom camera
                "y1": 0,
                "x2": 1280,
                "y2": 720
            }
        }

        # Main layout - Clean design based on the image
        main_frame = ttk.Frame(self, padding="5")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Configure grid weights for responsive layout
        main_frame.grid_columnconfigure(0, weight=1)  # Left camera
        main_frame.grid_columnconfigure(1, weight=1)  # Right camera  
        main_frame.grid_rowconfigure(0, weight=4)     # Camera feeds (most space)
        main_frame.grid_rowconfigure(1, weight=0)     # Controls section (compact)
        main_frame.grid_rowconfigure(2, weight=1)     # Bottom panel with grading & stats

        # --- Camera Feeds Section (Larger, cleaner design) ---
        cameras_container = ttk.Frame(main_frame)
        cameras_container.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=2, pady=2)
        cameras_container.grid_columnconfigure(0, weight=1)
        cameras_container.grid_columnconfigure(1, weight=1)
        cameras_container.grid_rowconfigure(0, weight=1)
        
        # Left Camera (Top Camera)
        left_camera_frame = ttk.LabelFrame(cameras_container, text="Top Camera View", padding="5")
        left_camera_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        left_camera_frame.grid_rowconfigure(0, weight=1)
        left_camera_frame.grid_columnconfigure(0, weight=1)
        
        # Top camera live feed - larger display area
        self.top_live_feed = ttk.Label(left_camera_frame, background="black", text="Initializing Camera...")
        self.top_live_feed.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Right Camera (Bottom Camera)
        right_camera_frame = ttk.LabelFrame(cameras_container, text="Bottom Camera View", padding="5")
        right_camera_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        right_camera_frame.grid_rowconfigure(0, weight=1)
        right_camera_frame.grid_columnconfigure(0, weight=1)
        
        # Bottom camera live feed - larger display area
        self.bottom_live_feed = ttk.Label(right_camera_frame, background="black", text="Initializing Camera...")
        self.bottom_live_feed.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # --- System Controls Section ---
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        controls_frame.grid_columnconfigure(0, weight=1)
        controls_frame.grid_columnconfigure(1, weight=1) 
        controls_frame.grid_columnconfigure(2, weight=1)
        controls_frame.grid_columnconfigure(3, weight=1)

        # System Status
        status_frame = ttk.LabelFrame(controls_frame, text="System Status", padding="5")
        status_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.status_label = ttk.Label(status_frame, text="Status: Initializing...", 
                                     font=self.font_normal, anchor="center", wraplength=150)
        self.status_label.pack(pady=5)

        # Conveyor Control
        control_frame = ttk.LabelFrame(controls_frame, text="Conveyor Control", padding="5")
        control_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        control_inner_frame = ttk.Frame(control_frame)
        control_inner_frame.pack(fill="both", expand=True)
        control_inner_frame.grid_columnconfigure(0, weight=1)
        control_inner_frame.grid_columnconfigure(1, weight=1)
        control_inner_frame.grid_columnconfigure(2, weight=1)

        ttk.Button(control_inner_frame, text="Continuous", 
                  command=self.set_continuous_mode).grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        ttk.Button(control_inner_frame, text="Trigger", 
                  command=self.set_trigger_mode).grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        ttk.Button(control_inner_frame, text="IDLE", 
                  command=self.set_idle_mode).grid(row=0, column=2, sticky="ew", padx=1, pady=1)

        # Detection Settings
        detection_frame = ttk.LabelFrame(controls_frame, text="Detection", padding="5")
        detection_frame.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)

        self.live_detection_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(detection_frame, text="Live Detect", variable=self.live_detection_var,
                       command=self.toggle_live_detection_mode).pack(anchor="w")
        self.live_detection_var.set(False)  # Ensure it's False at startup

        self.auto_grade_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(detection_frame, text="Auto Grade", variable=self.auto_grade_var).pack(anchor="w")

        # Reports
        reports_frame = ttk.LabelFrame(controls_frame, text="Reports", padding="5")
        reports_frame.grid(row=0, column=3, sticky="nsew", padx=2, pady=2)
        
        self.log_status_label = ttk.Label(reports_frame, text="Log: Ready", 
                                         foreground="green", font=self.font_small)
        self.log_status_label.pack()
        
        ttk.Button(reports_frame, text="Generate Report", 
                  command=self.manual_generate_report).pack(pady=2)
        
        self.show_report_notification = tk.BooleanVar(value=True)
        ttk.Checkbutton(reports_frame, text="Notifications", 
                       variable=self.show_report_notification).pack()
        
        self.last_report_label = ttk.Label(reports_frame, text="Last: None", 
                                          font=self.font_small, wraplength=100)
        self.last_report_label.pack()

        # --- Bottom Panel: Statistics (Full Width) ---
        bottom_panel = ttk.Frame(main_frame)
        bottom_panel.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        bottom_panel.grid_columnconfigure(0, weight=1)  # Statistics takes full width
        bottom_panel.grid_rowconfigure(0, weight=1)

        # Statistics Section - Full Width Tabbed Panel Design
        stats_frame = ttk.LabelFrame(bottom_panel, text="Statistics", padding="5")
        stats_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_rowconfigure(0, weight=1)

        # Create notebook for tabbed statistics
        self.stats_notebook = ttk.Notebook(stats_frame)
        self.stats_notebook.grid(row=0, column=0, sticky="nsew")

        # Tab 1: Grade Summary (Overview with Live Grading)
        grade_summary_tab = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(grade_summary_tab, text="Grade Summary")
        
        # Grade counts in a clean grid with better sizing and spacing
        grade_counts_frame = ttk.Frame(grade_summary_tab)
        grade_counts_frame.pack(fill="x", pady=10, padx=10)
        
        # Configure 4 columns for grade statistics with equal weight and minimum size
        for i in range(4):
            grade_counts_frame.grid_columnconfigure(i, weight=1, minsize=120)
        grade_counts_frame.grid_rowconfigure(0, weight=1, minsize=80)
        
        # Initialize stats labels with consistent spacing and fonts
        self.live_stats_labels = {}
        grade_info = [
            ("grade1", "Perfect\n(G2-0)", "dark green"),
            ("grade2", "Good\n(G2-1)", "green"),
            ("grade3", "Fair\n(G2-2)", "orange"),
            ("grade4", "Poor\n(G2-3)", "red"),
            ("grade5", "Reject\n(G2-4)", "dark red")
        ]
        
        for i, (grade_key, label_text, color) in enumerate(grade_info):
            grade_container = ttk.Frame(grade_counts_frame, relief="solid", borderwidth=2)
            grade_container.grid(row=0, column=i, sticky="nsew", padx=6, pady=5, ipadx=8, ipady=8)
            grade_container.grid_columnconfigure(0, weight=1)
            grade_container.grid_rowconfigure(0, weight=1)
            grade_container.grid_rowconfigure(1, weight=1)
            
            # Create a consistent inner frame for better control
            inner_frame = ttk.Frame(grade_container)
            inner_frame.grid(row=0, column=0, sticky="nsew", rowspan=2)
            
            # Title label with fixed font
            title_label = ttk.Label(inner_frame, text=label_text, font=("Arial", 9, "bold"), 
                                   justify="center")
            title_label.pack(expand=True, pady=(8, 2))
            
            # Count label with fixed font and consistent positioning
            self.live_stats_labels[grade_key] = ttk.Label(inner_frame, text="0", 
                                                         foreground=color, font=("Arial", 16, "bold"))
            self.live_stats_labels[grade_key].pack(expand=True, pady=(2, 8))

        # Live Grading Section (horizontal layout in Grade Summary tab)
        live_grading_frame = ttk.LabelFrame(grade_summary_tab, text="Live Grading Results", padding="10")
        live_grading_frame.pack(fill="x", pady=(10, 5), padx=10)
        live_grading_frame.grid_columnconfigure(0, weight=1)
        live_grading_frame.grid_columnconfigure(1, weight=1)
        live_grading_frame.grid_columnconfigure(2, weight=2)

        # Individual camera grades (horizontal layout)
        top_grade_container = ttk.Frame(live_grading_frame)
        top_grade_container.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        ttk.Label(top_grade_container, text="Top Camera:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.top_grade_label = ttk.Label(top_grade_container, text="No wood detected", 
                                        foreground="gray", font=self.font_small)
        self.top_grade_label.pack(anchor="w")

        bottom_grade_container = ttk.Frame(live_grading_frame)
        bottom_grade_container.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        ttk.Label(bottom_grade_container, text="Bottom Camera:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.bottom_grade_label = ttk.Label(bottom_grade_container, text="No wood detected", 
                                           foreground="gray", font=self.font_small)
        self.bottom_grade_label.pack(anchor="w")

        # Combined grade (prominent display, takes more space)
        combined_container = ttk.Frame(live_grading_frame)
        combined_container.grid(row=0, column=2, sticky="ew", padx=5, pady=2)
        ttk.Label(combined_container, text="Final Grade:", font=("Arial", 12, "bold")).pack(anchor="w")
        self.combined_grade_label = ttk.Label(combined_container, text="No wood detected",
                                             font=("Arial", 11, "bold"), foreground="gray")
        self.combined_grade_label.pack(anchor="w")

        # Add status indicator for grading state
        self.grading_status_label = ttk.Label(combined_container, text="",
                                             font=("Arial", 8), foreground="blue")
        self.grading_status_label.pack(anchor="w")

        # Tab 2: Defect Details
        defect_details_tab = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(defect_details_tab, text="Defect Details")
        
        # Defect details content
        self.defect_details_frame = ttk.Frame(defect_details_tab)
        self.defect_details_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab 3: Performance Metrics
        performance_tab = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(performance_tab, text="Performance")
        
        # Performance metrics content
        self.performance_frame = ttk.Frame(performance_tab)
        self.performance_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab 4: Recent Activity
        activity_tab = ttk.Frame(self.stats_notebook)
        self.stats_notebook.add(activity_tab, text="Recent Activity")
        
        # Main container with two sections
        activity_main_container = ttk.Frame(activity_tab)
        activity_main_container.pack(fill="both", expand=True, padx=5, pady=5)
        activity_main_container.grid_columnconfigure(0, weight=1)
        activity_main_container.grid_rowconfigure(0, weight=0)  # Summary section (fixed height)
        activity_main_container.grid_rowconfigure(1, weight=1)  # Log section (expandable)
        
        # Session Summary Section (wider, fixed height)
        self.session_summary_frame = ttk.LabelFrame(activity_main_container, text="Current Session Summary", padding="10")
        self.session_summary_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        # Processing Log Section (scrollable)
        log_container = ttk.LabelFrame(activity_main_container, text="Recent Processing Log", padding="5")
        log_container.grid(row=1, column=0, sticky="nsew")
        log_container.grid_columnconfigure(0, weight=1)
        log_container.grid_rowconfigure(0, weight=1)

        # Scrollable canvas for processing log
        log_canvas = tk.Canvas(log_container, height=200)  # Set minimum height
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=log_canvas.yview)
        self.processing_log_frame = ttk.Frame(log_canvas)
        
        self.processing_log_frame.bind(
            "<Configure>",
            lambda e: log_canvas.configure(scrollregion=log_canvas.bbox("all"))
        )
        
        def on_log_scroll(event):
            self._user_scrolling_log = True
            if hasattr(self, '_log_scroll_timer'):
                self.after_cancel(self._log_scroll_timer)
            self._log_scroll_timer = self.after(3000, lambda: setattr(self, '_user_scrolling_log', False))
        
        log_canvas.bind("<Button-4>", on_log_scroll)
        log_canvas.bind("<Button-5>", on_log_scroll)  
        log_canvas.bind("<MouseWheel>", on_log_scroll)
        log_scrollbar.bind("<ButtonPress-1>", lambda e: setattr(self, '_user_scrolling_log', True))
        
        log_canvas.create_window((0, 0), window=self.processing_log_frame, anchor="nw")
        log_canvas.configure(yscrollcommand=log_scrollbar.set)
        
        log_canvas.grid(row=0, column=0, sticky="nsew")
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Store canvas references for updates
        self.log_canvas = log_canvas
        self.activity_canvas = log_canvas  # Keep for compatibility
        
        # Initialize scroll state variables
        self._user_scrolling_log = False

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

        # --- Arduino Communication ---
        self.setup_arduino()

        # Start the video feed update loop
        self.update_feeds()
        
        # Start processing messages from background threads
        self.process_message_queue()

        # --- Inactivity and Reporting --- 
        self.check_inactivity()

        # Set the action for when the window is closed
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

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
            "knots with crack": "Unsound_Knot",
            "live knots": "Sound_Knot",
            "missing knots": "Unsound_Knot",
            # Variations and alternatives
            "dead_knots": "Dead_Knot",
            "knots_with_crack": "Unsound_Knot",
            "live_knots": "Sound_Knot",
            "missing_knots": "Unsound_Knot",
            # Legacy mappings for backward compatibility
            "sound_knots": "Sound_Knot",
            "dead_knots": "Dead_Knot",
            "unsound_knots": "Unsound_Knot",
            "sound knots": "Sound_Knot",
            "dead knots": "Dead_Knot",
            "unsound knots": "Unsound_Knot",
            "live_knot": "Sound_Knot",
            "dead_knot": "Dead_Knot",
            "missing_knot": "Unsound_Knot",
            "crack_knot": "Unsound_Knot",
            # Generic fallback
            "knot": "Unsound_Knot"
        }

        # Normalize the label (lowercase, remove extra spaces)
        normalized_label = model_label.lower().strip().replace('_', ' ')

        # Return mapped label or default to unsound knot
        return label_mapping.get(normalized_label, "Unsound_Knot")

    def calculate_defect_size(self, detection_box, camera_name="top"):
        """Calculate defect size in mm and percentage from detection bounding box"""
        try:
            # Extract bounding box coordinates
            x1, y1, x2, y2 = detection_box['bbox']

            # Calculate defect dimensions in pixels
            width_px = abs(x2 - x1)   # Horizontal dimension (across wood width)
            height_px = abs(y2 - y1) # Vertical dimension (along wood length)

            # For wood defects on vertically-oriented wood pieces, measure the height
            # (vertical dimension) as this represents the defect size perpendicular to grain
            # Based on rgb_wood_detector.py calibration approach
            defect_size_px = height_px

            # Use camera-specific conversion factor
            if camera_name == "top":
                pixel_to_mm = TOP_CAMERA_PIXEL_TO_MM
            else:  # bottom camera
                pixel_to_mm = BOTTOM_CAMERA_PIXEL_TO_MM

            # Convert to millimeters using division (pixels per mm factor)
            size_mm = defect_size_px / pixel_to_mm

            # Calculate percentage of actual wood pallet width
            percentage = (size_mm / WOOD_PALLET_WIDTH_MM) * 100

            # Debug logging to understand bounding box sizes
            print(f"DEBUG [{camera_name}]: bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) "
                  f"-> width_px={width_px:.1f}, height_px={height_px:.1f} "
                  f"-> defect_size_px={defect_size_px:.1f} -> size_mm={size_mm:.1f}")

            return size_mm, percentage

        except Exception as e:
            print(f"Error calculating defect size: {e}")
            # Return conservative values if calculation fails
            return 50.0, 35.0  # Assumes large defect for safety

    def get_individual_knot_grade(self, defect_type, defect_size_mm, wood_width_mm):
        """
        Determines the grade of a single knot based on SS-EN 1611-1 size limits.
        The formula is: Limit = (0.10 * width) + constant
        """
        # Define the constants from the standard table
        constants = GRADING_CONSTANTS.get(defect_type, {})

        # Grade order from best to worst
        grade_order = ["G2-0", "G2-1", "G2-2", "G2-3", "G2-4"]

        if defect_type not in constants:
            return "G2-4"  # Unknown types are worst grade

        # Check against limits for each grade
        for grade in grade_order:
            if grade == "G2-4":
                return "G2-4"  # If it hasn't passed any other grade, it's G2-4

            if grade not in constants:
                # This defect type is not permitted for this grade
                continue

            # Calculate the maximum allowed size for this grade
            limit = (0.10 * wood_width_mm) + constants[grade]

            if defect_size_mm <= limit:
                return grade  # This is the best possible grade for this knot

        return "G2-4"  # Should be unreachable, but as a fallback

    def determine_surface_grade(self, defect_measurements):
        """
        Determine overall surface grade based on worst knot size and knot count.
        defect_measurements: list of tuples [("Sound_Knot", size_mm), ...]
        """
        if not defect_measurements:
            return GRADE_G2_0

        # 1. Grade based on the size of the worst individual knot
        worst_grade_by_size = "G2-0"
        grade_order = ["G2-0", "G2-1", "G2-2", "G2-3", "G2-4"]

        dead_or_unsound_count = 0

        for defect_type, defect_size_mm, _ in defect_measurements:
            # Tally knots for count constraint
            if defect_type in ["Dead_Knot", "Unsound_Knot"]:
                dead_or_unsound_count += 1

            # Get individual knot grade
            knot_grade = self.get_individual_knot_grade(defect_type, defect_size_mm, WOOD_PALLET_WIDTH_MM)

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
            GRADE_G2_3: 2,    # Poor (G2-3) - Gate 2
            GRADE_G2_4: 3     # Reject (G2-4) - Gate 3
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
        
        widgets['wood_width_label'] = ttk.Label(calib_frame, 
                                              text=f"Wood Width: {WOOD_PALLET_WIDTH_MM}mm",
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
        
        wood_label = ttk.Label(calib_frame, text=f"Wood Width: {WOOD_PALLET_WIDTH_MM}mm", 
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
                tracker['surface_grade'] = self.determine_surface_grade(measurements)
        
        # Continue with the existing detailed logging logic (this is retained)
        if measurements and defect_dict:
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
            "wood_width_mm": WOOD_PALLET_WIDTH_MM
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
        from datetime import datetime
        
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
        from datetime import datetime
        
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
        self.update_single_feed(self.cap_top, self.top_live_feed, "top")
        self.update_single_feed(self.cap_bottom, self.bottom_live_feed, "bottom")
        
        # Reduce update frequency for non-critical components to prevent UI lag
        # Only update every 15th frame (~4.4 FPS for dashboard updates) to reduce load
        if not hasattr(self, '_frame_counter'):
            self._frame_counter = 0
        
        self._frame_counter += 1
        if self._frame_counter % 15 == 0:
            # Update detection status
            self.update_detection_status_display()
            
            # Only update details if not in active inference to prevent interference
            if not getattr(self, '_in_active_inference', False):
                self.ensure_detection_details_updated()
        
        # Optimize for constant detection - update every 10ms for ~100 FPS
        self.after(10, self.update_feeds)

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
            if self.auto_detection_active:
                total_detections = (len(self.detection_session_data["total_detections"]["top"]) + 
                                  len(self.detection_session_data["total_detections"]["bottom"]))
                self.status_label.config(
                    text=f"Status: AUTO (IR) DETECTION ACTIVE 🔍 ({total_detections} detections)", 
                    foreground="orange"
                )
            elif self.live_detection_var.get():
                self.status_label.config(
                    text=f"Status: {self.current_mode} MODE - Live Detection ACTIVE",
                    foreground="blue"
                )
            elif self.current_mode == "IDLE":
                self.status_label.config(
                    text="Status: IDLE MODE - System disabled, no operations",
                    foreground="gray"
                )
            elif self.current_mode == "TRIGGER":
                self.status_label.config(
                    text="Status: TRIGGER MODE - Waiting for IR beam trigger", 
                    foreground="green"
                )
            elif self.current_mode == "CONTINUOUS":
                self.status_label.config(
                    text="Status: CONTINUOUS MODE - Live detection enabled", 
                    foreground="blue"
                )
            else:
                # Fallback for unknown states
                self.status_label.config(
                    text=f"Status: {self.current_mode} MODE - Ready", 
                    foreground="green"
                )

    def toggle_live_detection_mode(self):
        """Handle toggling between IR trigger and live detection modes."""
        self.update_detection_status_display()

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

        # Get final active tracks from object trackers (these are already deduplicated)
        final_top_tracks = self.trackers["top"].get_tracks()
        final_bottom_tracks = self.trackers["bottom"].get_tracks()

        # Convert tracks to measurement format for grading
        all_measurements = []
        top_measurements = []
        bottom_measurements = []

        # Process top camera tracks
        for track in final_top_tracks:
            measurement = (track.defect_type, track.size_mm, 0.0)  # percentage not critical for grading
            top_measurements.append(measurement)
            all_measurements.append(measurement)

        # Process bottom camera tracks
        for track in final_bottom_tracks:
            measurement = (track.defect_type, track.size_mm, 0.0)  # percentage not critical for grading
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

        # Report defect detection results
        print("\nDEFECT DETECTION SUMMARY:")
        print("-" * 40)
        print(f"🎯 TOP CAMERA: {len(final_top_tracks)} defect(s) detected")
        for i, track in enumerate(final_top_tracks, 1):
            print(f"   {i}. {track.defect_type} - Size: {track.size_mm:.1f}mm (tracked for {track.hits} frames)")

        print(f"🎯 BOTTOM CAMERA: {len(final_bottom_tracks)} defect(s) detected")
        for i, track in enumerate(final_bottom_tracks, 1):
            print(f"   {i}. {track.defect_type} - Size: {track.size_mm:.1f}mm (tracked for {track.hits} frames)")

        # Determine final grades from tracked objects
        final_top_grade = self.determine_surface_grade(top_measurements)
        final_bottom_grade = self.determine_surface_grade(bottom_measurements)

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
        self.dynamic_roi = None

    def determine_final_grade_from_session(self, camera_name, detections_list):
        """Determine final grade from all detections collected during session"""
        if not detections_list:
            return GRADE_G2_0 # No defects found, perfect grade

        # Combine all defect counts from the session
        all_measurements = [m for d in detections_list for m in d.get("measurements", [])]

        # Use sophisticated grading if measurements available
        if all_measurements:
            return self.determine_surface_grade(all_measurements)
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
        cv2.putText(frame_copy, f"ROI - {camera_name.upper()}",
                   (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        return frame_copy

    def draw_wood_detection_overlay(self, frame, camera_name):
        """Draw wood detection results overlay on frame for visualization"""
        if not hasattr(self, 'wood_detection_results') or not self.wood_detection_results:
            return frame

        detection_result = self.wood_detection_results.get(camera_name)
        if not detection_result or not detection_result.get('wood_detected', False):
            return frame

        frame_copy = frame.copy()

        # Draw wood detection bounding boxes
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
                # Draw dynamic ROI (blue border)
                cv2.rectangle(frame_copy, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(frame_copy, "Dynamic ROI",
                           (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        # Add wood detection summary
        wood_count = detection_result.get('wood_count', 0)
        confidence = detection_result.get('confidence', 0.0)
        summary_text = f"Wood: {wood_count} detected (conf: {confidence:.2f})"
        cv2.putText(frame_copy, summary_text, (10, frame.shape[0] - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame_copy

    def update_single_feed(self, cap, label, camera_name):
        ret, frame = cap.read()
        if ret:
            # Skip detection processing if frame rate is too high
            if not hasattr(self, '_detection_frame_skip'):
                self._detection_frame_skip = {"top": 0, "bottom": 0}
            
            # Initialize memory management counter
            if not hasattr(self, '_memory_cleanup_counter'):
                self._memory_cleanup_counter = 0
            
            # Perform memory cleanup every 300 frames (~24 seconds at 125 FPS)
            self._memory_cleanup_counter += 1
            if self._memory_cleanup_counter % 300 == 0:
                import gc
                gc.collect()  # Force garbage collection
                
                # Clear cached dimensions periodically to handle window resizing
                if hasattr(self, '_label_dimensions'):
                    self._label_dimensions.clear()
                    
                print(f"Memory cleanup performed at frame {self._memory_cleanup_counter}")
            
            # Process detection based on automatic IR beam OR live detection toggle
            should_detect = self.auto_detection_active or self.live_detection_var.get()

            # During automatic detection, first do wood detection to establish dynamic ROI
            if self.auto_detection_active and should_detect:
                # STEP 2 & 3: WHEN BEAM is BROKEN use the rgb wood detection, and only proceed if wood detected
                try:
                    # Detect wood on current frame
                    wood_detection = self.rgb_wood_detector.detect_wood_comprehensive(frame, camera=camera_name)

                    # Check if wood is detected with sufficient confidence
                    wood_detected = wood_detection['wood_detected'] and wood_detection.get('confidence', 0) > 0.6

                    if wood_detected:
                        # Store dynamic ROI for defect detection
                        self.dynamic_roi[camera_name] = wood_detection.get('auto_roi')
                        self.wood_detection_results[camera_name] = wood_detection

                        # STEP 4: List wood detection details (only once per camera per detection session)
                        if not hasattr(self, '_wood_reported') or not self._wood_reported.get(camera_name, False):
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

            # Only proceed with defect detection if we have dynamic ROI (wood was detected)
            has_dynamic_roi = (hasattr(self, 'dynamic_roi') and self.dynamic_roi and
                             camera_name in self.dynamic_roi and self.dynamic_roi[camera_name] is not None)

            if should_detect and has_dynamic_roi:
                # STEP 3 CONTINUED: Use the generated Dynamic ROI for the Defect Detection
                # Convert ROI format from (x, y, w, h) to coordinates for apply_roi
                roi_coords = self.dynamic_roi[camera_name]
                roi_x, roi_y, roi_w, roi_h = roi_coords
                # Create ROI coordinates dict in the format expected by apply_roi
                dynamic_roi_coords = {
                    "x1": roi_x,
                    "y1": roi_y,
                    "x2": roi_x + roi_w,
                    "y2": roi_y + roi_h
                }
                detection_frame, roi_info = self.apply_roi(frame, camera_name, dynamic_roi_coords)
                print(f"🎯 Using dynamic ROI for {camera_name}: {dynamic_roi_coords}")
                
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
                        # Convert frame to RGB for saving
                        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                        self.detection_session_data["best_frames"][camera_name] = frame_rgb.copy()

                    # Store frame for potential PDF report
                    if len(self.detection_frames) < 50:  # Limit stored frames to prevent memory issues
                        frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                        self.detection_frames.append({
                            "camera": camera_name,
                            "timestamp": datetime.now().isoformat(),
                            "frame": frame_rgb.copy(),
                            "defects": defect_dict.copy()
                        })

                # Calculate grade for this camera using sophisticated grading
                if detections_for_grading:
                    surface_grade = self.determine_surface_grade(detections_for_grading)
                    grade_info = {
                        'grade': surface_grade,
                        'text': f'{surface_grade} - SS-EN 1611-1 ({camera_name.title()} Camera)',
                        'total_defects': len(detections_for_grading),
                        'color': self.get_grade_color(surface_grade)
                    }
                else:
                    grade_info = self.calculate_grade(defect_dict)  # Fallback to simple grading

                self.live_grades[camera_name] = grade_info

                # Update dashboard every 5th frame for smoother updates
                if self._detection_frame_skip[camera_name] % 5 == 0:
                    self.update_dashboard_display(camera_name, defect_dict, detections_for_grading)

                # Update the live grading display every 3rd frame
                if self._detection_frame_skip[camera_name] % 3 == 0:
                    self.update_live_grading_display()

                cv2image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            else:
                # No defect detection (either not should_detect or no dynamic ROI)
                # Just show raw feed without detection processing
                # Add ROI overlay to show the detection area even when not detecting
                frame_with_roi = self.draw_roi_overlay(frame, camera_name)
                # Add wood detection overlay if available
                frame_with_overlays = self.draw_wood_detection_overlay(frame_with_roi, camera_name)
                cv2image = cv2.cvtColor(frame_with_overlays, cv2.COLOR_BGR2RGB)

                # Reset detections only when automatic detection is not active
                if not self.auto_detection_active:
                    self.live_detections[camera_name] = {}
                    self.live_grades[camera_name] = "No wood detected"
                    if hasattr(self, 'live_measurements'):
                        self.live_measurements[camera_name] = []
                    # Update dashboard every 10th frame when no detection
                    if self._detection_frame_skip[camera_name] % 10 == 0:
                        self.update_dashboard_display(camera_name, {}, [])
                        self.update_live_grading_display()
            
            # Increment frame skip counter
            self._detection_frame_skip[camera_name] += 1
            
            # Convert to PIL Image and ensure consistent scaling
            img = Image.fromarray(cv2image)
            
            # Cache label dimensions to avoid repeated calculations
            if not hasattr(self, '_label_dimensions'):
                self._label_dimensions = {}
            
            cache_key = f"{camera_name}_dimensions"
            if cache_key not in self._label_dimensions:
                label.update_idletasks()
                self._label_dimensions[cache_key] = (label.winfo_width(), label.winfo_height())
            
            label_width, label_height = self._label_dimensions[cache_key]
            
            # Only resize if label has valid dimensions
            if label_width > 1 and label_height > 1:
                # Cache display dimensions calculation
                if f"{cache_key}_display" not in self._label_dimensions:
                    # Force consistent display size for both cameras (720p aspect ratio)
                    target_aspect_ratio = 16 / 9  # 1280x720 = 16:9
                    
                    # Use minimal margin
                    margin = 3
                    available_width = label_width - (2 * margin)
                    available_height = label_height - (2 * margin)
                    
                    # Calculate standardized size based on available space and 16:9 ratio
                    if available_width / available_height > target_aspect_ratio:
                        # Available space is wider than 16:9, constrain by height
                        display_height = available_height
                        display_width = int(display_height * target_aspect_ratio)
                    else:
                        # Available space is taller than 16:9, constrain by width
                        display_width = available_width
                        display_height = int(display_width / target_aspect_ratio)
                    
                    # Ensure dimensions don't exceed available space
                    display_width = min(display_width, available_width)
                    display_height = min(display_height, available_height)
                    
                    # Cache calculated dimensions and offsets
                    x_offset = (label_width - display_width) // 2
                    y_offset = (label_height - display_height) // 2
                    
                    self._label_dimensions[f"{cache_key}_display"] = {
                        'display_width': display_width,
                        'display_height': display_height,
                        'x_offset': x_offset,
                        'y_offset': y_offset
                    }
                
                # Use cached dimensions
                display_dims = self._label_dimensions[f"{cache_key}_display"]
                
                # Resize the camera image to exactly these dimensions (stretch if needed)
                # Use NEAREST for speed in real-time processing
                img = img.resize((display_dims['display_width'], display_dims['display_height']), Image.NEAREST)
                
                # Create a black background of the full label size
                final_img = Image.new('RGB', (label_width, label_height), 'black')
                
                # Paste the resized image
                final_img.paste(img, (display_dims['x_offset'], display_dims['y_offset']))
                img = final_img
            
            imgtk = ImageTk.PhotoImage(image=img)
            label.imgtk = imgtk
            label.configure(image=imgtk)

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
        # Update individual camera grades
        top_grade = self.live_grades["top"]
        bottom_grade = self.live_grades["bottom"]
        
        if isinstance(top_grade, dict):
            self.top_grade_label.config(text=top_grade['text'], foreground=top_grade['color'])
        else:
            self.top_grade_label.config(text=top_grade, foreground="gray")
        
        if isinstance(bottom_grade, dict):
            self.bottom_grade_label.config(text=bottom_grade['text'], foreground=bottom_grade['color'])
        else:
            self.bottom_grade_label.config(text=bottom_grade, foreground="gray")
        
        # Calculate combined grade using sophisticated method
        wood_detected = False
        top_surface_grade = None
        bottom_surface_grade = None
        
        # Get sophisticated grades from measurements if available
        if hasattr(self, 'live_measurements'):
            if self.live_measurements.get("top"):
                wood_detected = True
                top_surface_grade = self.determine_surface_grade(self.live_measurements["top"])
            
            if self.live_measurements.get("bottom"):
                wood_detected = True
                bottom_surface_grade = self.determine_surface_grade(self.live_measurements["bottom"])
        
        # Fallback to detection-based grading if measurements not available
        if not wood_detected:
            for camera_name in ["top", "bottom"]:
                if self.live_detections[camera_name]:
                    wood_detected = True
                    break
        
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
            
            self.combined_grade_label.config(text=combined_text, foreground=combined_color)
            
            # Auto-grade functionality - COMPLETELY DISABLED
            # Grading only happens when beam clears in TRIGGER mode
            # This ensures accurate grading based on complete defect tracking
            pass

        else:
            self.combined_grade_label.config(text="No wood detected", foreground="gray")

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
            details_text += f"Wood Width: {WOOD_PALLET_WIDTH_MM}mm | Defects: {total_defects}\n"
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
            
            details_text += f"Wood Width: {WOOD_PALLET_WIDTH_MM}mm\n"
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
            
            # Try multiple common serial ports for Arduino
            # Prioritize ACM ports for Arduino Uno R3/Leonardo with native USB
            # Include USB ports for Arduino Nano/Pro Mini with FTDI/CH340 chips
            # Include potential reassigned ports (ACM1, USB01, etc.)
            ports_to_try = [
                # ACM ports (Arduino Uno R3, Leonardo, Micro with native USB)
                '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2', '/dev/ttyACM3',
                # USB ports (Arduino Nano, Pro Mini with FTDI/CH340)
                '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3',
                # Reassigned ports (when disconnection occurs)
                '/dev/ttyUSB01', '/dev/ttyACM01',
                # Other Linux serial ports
                '/dev/ttyAMA0', '/dev/ttyAMA1', '/dev/ttyAMA10',
                # Windows COM ports
                'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10'
            ]
            
            for port in ports_to_try:
                try:
                    print(f"Trying to connect to Arduino on {port}...")
                    # More robust serial connection settings
                    self.ser = serial.Serial(
                        port=port, 
                        baudrate=9600, 
                        timeout=2,           # Increased timeout
                        write_timeout=2,     # Prevent hanging on write
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        xonxoff=False,       # Disable software flow control
                        rtscts=False,        # Disable hardware flow control
                        dsrdtr=False         # Disable DSR/DTR flow control
                    )
                    time.sleep(3)  # Extended time for Arduino to reset and stabilize
                    
                    # Clear any existing data in buffers
                    self.ser.reset_input_buffer()
                    self.ser.reset_output_buffer()
                    
                    # Test the connection with a gentle ping
                    self.ser.write(b'X')  # Send stop command as test
                    self.ser.flush()
                    time.sleep(0.5)
                    
                    print(f"✅ Arduino connected successfully on {port}")
                    break
                except (serial.SerialException, OSError) as e:
                    print(f"❌ Failed to connect on {port}: {e}")
                    continue
            else:
                # No port worked
                raise serial.SerialException("No Arduino found on any port")
            
            # Start Arduino listener thread if not already running and not shutting down
            if not (hasattr(self, '_shutting_down') and self._shutting_down):
                if not hasattr(self, 'arduino_thread') or not self.arduino_thread.is_alive():
                    self.arduino_thread = threading.Thread(target=self.listen_for_arduino, daemon=True)
                    self.arduino_thread.start()
            
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Status: Arduino connected. Ready for automatic detection.")
                # Start with auto detection ready status
                self.status_label.config(text="Status: Ready - Waiting for IR beam trigger", foreground="green")
            
        except serial.SerialException as e:
            self.ser = None
            print(f"Arduino connection failed: {e}")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Status: Arduino not found. Running in manual mode.")

    def process_message_queue(self):
        """Process messages from background threads safely in the main thread"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "arduino_message":
                    message = data

                    # --- IR BEAM HANDLING (Arduino sends "B" for beam broken) ---
                    if message == "B":
                        print("🔥 ARDUINO SENT 'B' - IR BEAM BROKEN DETECTED! 🔥")
                        # ONLY respond to IR triggers in TRIGGER mode
                        if self.current_mode == "TRIGGER":
                            if not self.auto_detection_active:
                                print("✅ TRIGGER MODE: Starting detection...")
                                print("🔧 Arduino should now set motorActiveForTrigger = true")
                                print("⚡ Stepper motor should start running NOW!")

                                if hasattr(self, 'status_label'):
                                    self.status_label.config(
                                        text="Status: IR TRIGGERED - Motor should be running!", foreground="orange"
                                    )
                                self.start_automatic_detection()
                                self.live_detection_var.set(True)
                                # Keep auto_grade_var False in TRIGGER mode - grading triggered by beam clear
                                print(f"After 'B': live_detection_var: {self.live_detection_var.get()}, auto_grade_var: {self.auto_grade_var.get()}")
                            else:
                                print("⚠️ IR beam broken but detection already active")
                        else:
                            # In IDLE or CONTINUOUS mode, just log the IR signal but don't act on it
                            print(f"❌ IR beam broken received but system is in {self.current_mode} mode - ignoring trigger")
                        continue  # skip other checks for this message

                    # --- LENGTH HANDLING (Arduino sends "L:duration" when beam clears) ---
                    if message.startswith("L:"):
                        try:
                            duration_ms = int(message.split(':')[1])
                            # Length calculation removed - only measuring defect width

                            # In TRIGGER mode, process grading if detection was active
                            if self.current_mode == "TRIGGER":
                                # Stop detection when beam clears, regardless of whether detection was active
                                self.live_detection_var.set(False)
                                self.auto_grade_var.set(False)
                                print("IR beam cleared – stopping detection")
                                print(f"After 'L': live_detection_var: {self.live_detection_var.get()}, auto_grade_var: {self.auto_grade_var.get()}")

                                if self.auto_detection_active:
                                    if hasattr(self, 'status_label'):
                                        self.status_label.config(
                                            text="Status: Processing results...", foreground="red"
                                        )
                                    self.stop_automatic_detection_and_grade()
                                    if hasattr(self, 'status_label'):
                                        self.status_label.config(
                                            text="Status: Ready - Waiting for IR beam trigger", foreground="green"
                                        )
                                else:
                                    print(f"Length signal received (duration: {duration_ms}ms) but no detection was active")
                            else:
                                print(f"Length signal received (duration: {duration_ms}ms) but system is in {self.current_mode} mode")
                        except (ValueError, IndexError):
                            print(f"Could not parse length message: {message}")
                        continue  # skip other checks for this message

                    # --- OTHER ARDUINO MESSAGES ---
                    else:
                        print(f"Arduino message received: '{message}'")
                        if hasattr(self, 'status_label'):
                            self.status_label.config(text=f"Status: Arduino: {message}")

                elif msg_type == "status_update":
                    if hasattr(self, 'status_label'):
                        self.status_label.config(text=f"Status: {data}")
                    
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
                        time.sleep(3)  # Increased wait time for Arduino to stabilize

                        # Try to reconnect with multiple attempts per reconnection cycle
                        reconnected = False
                        for attempt in range(3):  # Try 3 times per reconnection attempt
                            try:
                                self.setup_arduino()
                                if self.ser and self.ser.is_open:
                                    print(f"✅ Arduino reconnected successfully on {self.ser.port}")
                                    reconnect_attempts = 0
                                    reconnected = True
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
        
        # Add rate limiting to prevent overwhelming Arduino
        current_time = time.time()
        if hasattr(self, '_last_command_time'):
            time_since_last = current_time - self._last_command_time
            if time_since_last < 0.1:  # Minimum 100ms between commands
                time.sleep(0.1 - time_since_last)
        
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
                
                # Send command with error handling
                command_bytes = command.encode('utf-8')
                self.ser.write(command_bytes)
                self.ser.flush()  # Ensure data is sent immediately
                
                # Record timestamp for rate limiting
                self._last_command_time = time.time()
                
                print(f"✅ Sent command to Arduino: '{command}' (Port: {self.ser.port})")
            else:
                print("❌ Cannot send command: Arduino not connected.")
                if hasattr(self, 'status_label'):
                    self.status_label.config(text="Status: Arduino not connected.")
                    
        except (serial.SerialException, OSError, TypeError) as e:
            print(f"🔥 Error sending Arduino command '{command}': {e}")
            if hasattr(self, 'status_label'):
                self.status_label.config(text="Status: Arduino communication error - attempting reconnect...")
            
            # Try to reconnect only if not shutting down
            if not (hasattr(self, '_shutting_down') and self._shutting_down):
                print("🔄 Attempting Arduino reconnection...")
                self.ser = None
                time.sleep(1)  # Brief pause before reconnection attempt
                self.setup_arduino()

    def set_continuous_mode(self):
        """Sets the system to fully automatic continuous mode."""
        print("Setting Continuous (Live + Auto Grade) Mode")
        self.current_mode = "CONTINUOUS"
        self.send_arduino_command('C')  # Send command to Arduino
        self.live_detection_var.set(True)
        self.auto_grade_var.set(True)
        self.update_detection_status_display() # Update the status label

    def set_trigger_mode(self):
        """Sets the system to wait for an IR beam trigger."""
        print("Setting Trigger Mode")
        self.current_mode = "TRIGGER"
        print(f"Sending 'T' command to Arduino...")
        self.send_arduino_command('T')  # Send command to Arduino
        self.live_detection_var.set(False)
        self.auto_grade_var.set(False)
        self.update_detection_status_display() # Update the status label
        print(f"Trigger mode set - Python mode: {self.current_mode}")

    def set_idle_mode(self):
        """Disables all operations and stops the conveyor."""
        print("Setting IDLE Mode")
        self.current_mode = "IDLE"
        self.send_arduino_command('X')  # Send stop command to Arduino
        self.live_detection_var.set(False)
        self.auto_grade_var.set(False)
        self.auto_detection_active = False  # Ensure automatic detection is disabled
        self.status_label.config(text="Status: IDLE - Conveyor Stopped", foreground="gray")

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

        # 4. Send command to Arduino if it's connected
        if self.ser and self.ser.is_open:
            self.send_arduino_command(str(arduino_command))
        else:
            print("Arduino not connected. Command not sent.")

        # 5. Update status label and console
        status_text = f"Piece #{piece_number} Graded: {final_grade} (Cmd: {arduino_command})"
        print(f"✅ Grading Finalized - {status_text}")
        self.status_label.config(text=f"Status: {status_text}", foreground="darkgreen")
        self.log_action(f"Graded Piece #{piece_number} as {final_grade} -> Arduino Cmd: {arduino_command}")

        # Update grading status
        self.grading_status_label.config(text="✅ Grading completed", foreground="darkgreen")

    def _execute_manual_grade(self):
        """Execute manual grading based on current detections."""
        wood_detected = False
        top_surface_grade = None
        bottom_surface_grade = None
        
        all_measurements = self.live_measurements.get("top", []) + self.live_measurements.get("bottom", [])
        
        if all_measurements:
            wood_detected = True
            top_surface_grade = self.determine_surface_grade(self.live_measurements.get("top", []))
            bottom_surface_grade = self.determine_surface_grade(self.live_measurements.get("bottom", []))

        if wood_detected:
            final_grade = self.determine_final_grade(top_surface_grade, bottom_surface_grade)
            print(f"Manual grade trigger - SS-EN 1611-1 Final grade: {final_grade}")
            self.finalize_grading(final_grade, all_measurements)
        else:
            print("Manual grade trigger - No wood currently detected")
            self.status_label.config(text="Status: Manual grade - no wood detected")

    def analyze_frame(self, frame, camera_name="top", run_defect_model=True):
        """Analyze frame using DeGirum model with object tracking"""
        if self.model is None:
            return frame, {}, [], []

        try:
            # Run inference using DeGirum
            inference_result = self.model(frame)

            # Get annotated frame
            annotated_frame = inference_result.image_overlay

            # Process detections for object tracking
            current_detections = []
            for det in inference_result.results:
                model_label = det['label']
                bbox = det['bbox']
                confidence = det.get('confidence', 0.5)

                # Extract bounding box for size calculation
                bbox_info = {'bbox': bbox}

                # Calculate defect size in mm and percentage using camera-specific calibration
                size_mm, percentage = self.calculate_defect_size(bbox_info, camera_name)

                # Map to standard defect type
                standard_defect_type = self.map_model_output_to_standard(model_label)

                # Prepare detection for tracker (bbox, defect_type, size_mm, confidence)
                current_detections.append((bbox, standard_defect_type, size_mm, confidence))

            # Update object tracker with current detections
            if hasattr(self, 'trackers') and camera_name in self.trackers:
                active_tracks = self.trackers[camera_name].update(current_detections)
            else:
                active_tracks = []

            # Process active tracks for grading and display
            detections_for_grading = []
            final_defect_dict = {}

            for track in active_tracks:
                # Use track information for grading
                detections_for_grading.append((track.defect_type, track.size_mm, 0.0))  # percentage not needed for grading

                # Count by defect type for display
                if track.defect_type in final_defect_dict:
                    final_defect_dict[track.defect_type] += 1
                else:
                    final_defect_dict[track.defect_type] = 1

            # Use the model's default overlay annotations
            # The image_overlay from DeGirum already includes appropriate defect labels

            return annotated_frame, final_defect_dict, detections_for_grading

        except Exception as e:
            print(f"Error during DeGirum inference on {camera_name} camera: {e}")
            return frame, {}, []

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
            self.update_defect_details_tab()
            self.update_performance_tab()
            self.update_recent_activity_tab()
        except Exception as e:
            print(f"Error updating statistics tabs: {e}")
    
    def _safe_update_label(self, grade_key, count):
        """Safely update a label with error handling"""
        try:
            if (grade_key in self.live_stats_labels and 
                self.live_stats_labels[grade_key].winfo_exists()):
                self.live_stats_labels[grade_key].config(text=str(count))
        except Exception as e:
            print(f"Error updating label {grade_key}: {e}")

    def update_defect_details_tab(self):
        """Update the Defect Details tab with current defect information"""
        if not hasattr(self, 'defect_details_frame'):
            return
            
        # Clear existing content
        for widget in self.defect_details_frame.winfo_children():
            widget.destroy()
        
        # Current detection status
        current_frame = ttk.LabelFrame(self.defect_details_frame, text="Current Detection", padding="5")
        current_frame.pack(fill="x", pady=2)
        
        if hasattr(self, 'live_measurements') and any(self.live_measurements.values()):
            for camera_name in ["top", "bottom"]:
                measurements = self.live_measurements.get(camera_name, [])
                if measurements:
                    camera_text = f"{camera_name.title()} Camera: {len(measurements)} defects detected\n"
                    
                    # Group by defect type
                    defect_summary = {}
                    for defect_type, size_mm, percentage in measurements:
                        if defect_type not in defect_summary:
                            defect_summary[defect_type] = []
                        defect_summary[defect_type].append((size_mm, percentage))
                    
                    for defect_type, sizes in defect_summary.items():
                        avg_size = sum(s[0] for s in sizes) / len(sizes)
                        avg_percentage = sum(s[1] for s in sizes) / len(sizes)
                        camera_text += f"  • {defect_type.replace('_', ' ')}: {len(sizes)} defects, avg {avg_size:.1f}mm ({avg_percentage:.1f}%)\n"
                    
                    ttk.Label(current_frame, text=camera_text, font=self.font_small, justify="left").pack(anchor="w")
        else:
            ttk.Label(current_frame, text="No defects currently detected", font=self.font_small).pack(anchor="w")
        
        # Grading thresholds reference
        thresholds_frame = ttk.LabelFrame(self.defect_details_frame, text="SS-EN 1611-1 Grading Thresholds", padding="5")
        thresholds_frame.pack(fill="x", pady=2)
        
        threshold_text = "SS-EN 1611-1 Grading Thresholds (Limit = 0.10 * width + constant):\n\n"
        threshold_text += "Sound Knots:\n"
        threshold_text += "  G2-0: ≤21.5mm  |  G2-1: ≤31.5mm  |  G2-2: ≤46.5mm  |  G2-3: ≤61.5mm\n\n"
        threshold_text += "Dead Knots:\n"
        threshold_text += "  G2-0: ≤11.5mm  |  G2-1: ≤21.5mm  |  G2-2: ≤31.5mm  |  G2-3: ≤61.5mm\n\n"
        threshold_text += "Unsound Knots:\n"
        threshold_text += "  G2-2: ≤25.5mm  |  G2-3: ≤50.5mm\n\n"
        threshold_text += "Count Limits (Dead/Unsound per meter):\n"
        threshold_text += "  G2-0: 0  |  G2-1: 1  |  G2-2: 2  |  G2-3: 5"
        
        ttk.Label(thresholds_frame, text=threshold_text, font=self.font_small, justify="left").pack(anchor="w")

    def update_performance_tab(self):
        """Update the Performance Metrics tab"""
        if not hasattr(self, 'performance_frame'):
            return
            
        # Clear existing content
        for widget in self.performance_frame.winfo_children():
            widget.destroy()
        
        # System calibration info
        calibration_frame = ttk.LabelFrame(self.performance_frame, text="System Calibration", padding="5")
        calibration_frame.pack(fill="x", pady=2)
        
        calibration_text = f"Wood Pallet Width: {WOOD_PALLET_WIDTH_MM}mm\n"
        calibration_text += f"Top Camera: {TOP_CAMERA_DISTANCE_CM}cm distance, {TOP_CAMERA_PIXEL_TO_MM:.3f}mm/px\n"
        calibration_text += f"Bottom Camera: {BOTTOM_CAMERA_DISTANCE_CM}cm distance, {BOTTOM_CAMERA_PIXEL_TO_MM:.3f}mm/px\n"
        calibration_text += "Standard: SS-EN 1611-1 European Wood Grading"
        
        ttk.Label(calibration_frame, text=calibration_text, font=self.font_small, justify="left").pack(anchor="w")
        
        # Processing speed metrics
        speed_frame = ttk.LabelFrame(self.performance_frame, text="Processing Metrics", padding="5")
        speed_frame.pack(fill="x", pady=2)
        
        total_processed = getattr(self, 'total_pieces_processed', 0)
        session_start = getattr(self, 'session_start_time', time.time())
        elapsed = time.time() - session_start
        
        if elapsed > 0 and total_processed > 0:
            pieces_per_minute = (total_processed / elapsed) * 60
            avg_processing_time = elapsed / total_processed
            
            speed_text = f"Total Processing Time: {elapsed/60:.1f} minutes\n"
            speed_text += f"Processing Rate: {pieces_per_minute:.1f} pieces/minute\n"
            speed_text += f"Average Time per Piece: {avg_processing_time:.2f} seconds"
        else:
            speed_text = "No processing data available yet"
        
        ttk.Label(speed_frame, text=speed_text, font=self.font_small, justify="left").pack(anchor="w")
        
        # Grade distribution
        distribution_frame = ttk.LabelFrame(self.performance_frame, text="Grade Distribution", padding="5")
        distribution_frame.pack(fill="x", pady=2)
        
        if total_processed > 0:
            grade_counts = getattr(self, 'grade_counts', {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
            distribution_text = ""
            grade_names = {1: "Perfect (G2-0)", 2: "Good (G2-1)", 3: "Fair (G2-2)", 4: "Poor (G2-3)", 5: "Reject (G2-4)"}

            for grade, count in grade_counts.items():
                percentage = (count / total_processed) * 100 if total_processed > 0 else 0
                distribution_text += f"Grade {grade} ({grade_names.get(grade, 'Unknown')}): {count} pieces ({percentage:.1f}%)\n"
        else:
            distribution_text = "No processing data available yet"
        
        ttk.Label(distribution_frame, text=distribution_text, font=self.font_small, justify="left").pack(anchor="w")

    def update_recent_activity_tab(self):
        """Update the Recent Activity tab with widened summary and scrollable processing log"""
        # Don't update log if user is scrolling through it
        if getattr(self, '_user_scrolling_log', False):
            return
            
        # Generate content first to check if it changed
        new_stats_content = self._generate_stats_content()
        
        # Only update if content actually changed OR if this is the first update
        if (new_stats_content != self._last_stats_content or not self._last_stats_content):
            
            # Update Session Summary (wider display)
            for widget in self.session_summary_frame.winfo_children():
                widget.destroy()
            
            total_processed = getattr(self, 'total_pieces_processed', 0)
            session_start = getattr(self, 'session_start_time', time.time())
            session_duration = time.time() - session_start
            hours = int(session_duration // 3600)
            minutes = int((session_duration % 3600) // 60)
            
            # Create a wider summary display with better formatting
            summary_main_frame = ttk.Frame(self.session_summary_frame)
            summary_main_frame.pack(fill="x", expand=True)
            
            # Left column - Basic stats
            left_frame = ttk.Frame(summary_main_frame)
            left_frame.pack(side="left", fill="both", expand=True)
            
            basic_stats = f"Total Pieces Processed: {total_processed}\n"
            basic_stats += f"Session Duration: {hours}h {minutes}m\n"
            if total_processed > 0:
                avg_per_hour = (total_processed / session_duration) * 3600 if session_duration > 0 else 0
                basic_stats += f"Average Rate: {avg_per_hour:.1f} pieces/hour"
            
            ttk.Label(left_frame, text=basic_stats, font=self.font_small, justify="left").pack(anchor="w")
            
            # Right column - Grade distribution
            if total_processed > 0:
                right_frame = ttk.Frame(summary_main_frame)
                right_frame.pack(side="right", fill="both", expand=True)
                
                grade_counts = getattr(self, 'grade_counts', {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})
                grade_stats = "Grade Distribution:\n"
                grade_names = {1: "Perfect (G2-0)", 2: "Good (G2-1)", 3: "Fair (G2-2)", 4: "Poor (G2-3)", 5: "Reject (G2-4)"}

                for grade, count in grade_counts.items():
                    percentage = (count / total_processed) * 100 if total_processed > 0 else 0
                    grade_stats += f"{grade_names.get(grade, 'Unknown')}: {count} ({percentage:.1f}%)\n"
                
                ttk.Label(right_frame, text=grade_stats, font=self.font_small, justify="left").pack(anchor="w")
            
            # Update Processing Log (scrollable with many entries and detailed defect info)
            for widget in self.processing_log_frame.winfo_children():
                widget.destroy()
            
            if hasattr(self, 'session_log') and self.session_log:
                # Show all entries, not just last 10 (since it's now scrollable)
                recent_entries_copy = self.session_log.copy()
                recent_entries_copy.reverse()  # Show newest first
                
                for i, entry in enumerate(recent_entries_copy):
                    timestamp = entry.get('timestamp', 'Unknown')
                    piece_number = entry.get('piece_number', 'Unknown')
                    grade = entry.get('final_grade', 'Unknown')
                    defects = entry.get('defects', [])
                    
                    # Create a frame for each log entry for better formatting
                    entry_frame = ttk.Frame(self.processing_log_frame)
                    entry_frame.pack(fill="x", pady=2, padx=5)
                    
                    # Format defects info with specific details including sizes (single line)
                    if defects:
                        defects_details = []
                        for d in defects:
                            defect_type = d.get('type', 'Unknown')
                            count = d.get('count', 0)
                            sizes = d.get('sizes', '')
                            if sizes:
                                defects_details.append(f"{defect_type} (x{count}): {sizes}mm")
                            else:
                                defects_details.append(f"{defect_type} (x{count})")
                        
                        defects_info = " | ".join(defects_details)
                        log_text = f"[{timestamp}] Piece #{piece_number}: Grade {grade} - Defects: {defects_info}"
                    else:
                        log_text = f"[{timestamp}] Piece #{piece_number}: Grade {grade} - No defects detected"
                    
                    # Color code by grade
                    grade_colors = {
                        "G2-0": "dark green",
                        "G2-1": "green",
                        "G2-2": "orange",
                        "G2-3": "red",
                        "G2-4": "dark red"
                    }
                    text_color = grade_colors.get(grade, "black")
                    
                    log_label = ttk.Label(entry_frame, text=log_text, font=("Arial", 9), 
                                        justify="left", foreground=text_color)
                    log_label.pack(anchor="w", fill="x")
                    
                    # Add separator line (except for last entry)
                    if i < len(recent_entries_copy) - 1:
                        separator = ttk.Separator(self.processing_log_frame, orient="horizontal")
                        separator.pack(fill="x", pady=2)
            else:
                # Show message when no log entries exist
                no_data_label = ttk.Label(self.processing_log_frame, 
                                        text="No processing data yet...", 
                                        font=self.font_small, foreground="gray")
                no_data_label.pack(pady=20)
            
            # Cache the content
            self._last_stats_content = new_stats_content
            
            # Update scroll region for log
            if hasattr(self, 'log_canvas'):
                self.log_canvas.configure(scrollregion=self.log_canvas.bbox("all"))

    def update_detailed_statistics(self):
        """Legacy method - now redirects to update_recent_activity_tab for compatibility"""
        self.update_recent_activity_tab()

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


    def on_closing(self):
        print("Releasing resources...")
        
        # Set a flag to indicate shutdown is in progress
        self._shutting_down = True
        
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
        content += f"Grade G2-0 (Perfect): {self.grade_counts.get(1, 0)}\n"
        content += f"Grade G2-1 (Good): {self.grade_counts.get(2, 0)}\n"
        content += f"Grade G2-2 (Fair): {self.grade_counts.get(3, 0)}\n"
        content += f"Grade G2-3 (Poor): {self.grade_counts.get(4, 0)}\n"
        content += f"Grade G2-4 (Reject): {self.grade_counts.get(5, 0)}\n"
        
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
            messagebox.showerror("Report Error", f"Could not save TXT report: {e}")
            return

        # Append to main log file
        try:
            log_entry = f"{timestamp} | Pieces: {self.total_pieces_processed} | G2-0: {self.grade_counts.get(1, 0)} | G2-1: {self.grade_counts.get(2, 0)} | G2-2: {self.grade_counts.get(3, 0)} | G2-3: {self.grade_counts.get(4, 0)} | G2-4: {self.grade_counts.get(5, 0)}\n"
            with open(log_filename, 'a') as f:
                f.write(log_entry)
            print(f"Entry added to log file: {log_filename}")
            self.log_status_label.config(text="Log: Updated", foreground="blue")
        except Exception as e:
            print(f"Error updating log file: {e}")
            self.log_status_label.config(text="Log: Error", foreground="red")

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
            text.textLine(f"Grade G2-0 (Perfect): {self.grade_counts.get(1, 0)}")
            text.textLine(f"Grade G2-1 (Good): {self.grade_counts.get(2, 0)}")
            text.textLine(f"Grade G2-2 (Fair): {self.grade_counts.get(3, 0)}")
            text.textLine(f"Grade G2-3 (Poor): {self.grade_counts.get(4, 0)}")
            text.textLine(f"Grade G2-4 (Reject): {self.grade_counts.get(5, 0)}")
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
            self.last_report_label.config(text=f"Last Report: {os.path.basename(self.last_report_path)}")
            
            # Show notification only if toggle is enabled
            if self.show_report_notification.get():
                messagebox.showinfo("SS-EN 1611-1 Report", f"Reports saved as {txt_filename} and {pdf_filename}\nLog updated: {log_filename}")

        except Exception as e:
            print(f"Error generating PDF report: {e}")
            messagebox.showerror("Report Error", f"Could not save PDF report: {e}")
            
        # Reset the session log after generating the report
        self.session_log = []
        print("Session log has been cleared for the next report.")


    def manual_generate_report(self):
        """Manually generate a report"""
        self.generate_report()
        self.log_status_label.config(text="Log: Manual report generated", foreground="green")

    def simulate_ir_events(self):
        """Simulate IR beam events for testing TRIGGER mode"""
        print("Simulating IR beam events for testing...")

        # Simulate 'B' message (beam broken)
        print("Simulating 'B' message (beam broken)...")
        self.message_queue.put(("arduino_message", "B"))

        # Wait a moment then simulate 'L' message (beam clear with duration)
        self.after(2000, lambda: self.simulate_beam_clear())

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
    app.mainloop()
