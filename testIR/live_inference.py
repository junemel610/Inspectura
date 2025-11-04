#!/usr/bin/env python3
"""
Live Inference Script for Wood Defect Detection
Uses the same model and camera configuration as testIR.py
"""

import cv2
import numpy as np
import degirum as dg
import time
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# ============================================================================
# CONFIGURATION (from rgb_wood_detector.py and testIR.py)
# ============================================================================

# Camera-specific calibration constants (from rgb_wood_detector.py)
TOP_CAMERA_DISTANCE_CM = 28      # Top camera distance from conveyor
BOTTOM_CAMERA_DISTANCE_CM = 27.5  # Bottom camera distance from conveyor
TOP_CAMERA_PIXEL_TO_MM = 2.915    # Top camera: 2.915 pixels per mm (calibrated at 31cm)
BOTTOM_CAMERA_PIXEL_TO_MM = 3.35  # Bottom camera: 3.35 pixels per mm
WOOD_PALLET_WIDTH_MM = 0          # Global variable for current detected wood width

# ROI Configuration (from testIR.py)
# Yellow ROI = Static camera detection zones
ROI_COORDINATES = {
    "top": {
        "x1": 345,  # Left boundary - exclude left equipment
        "y1": 0,    # Top boundary
        "x2": 880,  # Right boundary - exclude right equipment
        "y2": 720   # Bottom boundary - focus on wood area
    },
    "bottom": {
        "x1": 350,  # Left boundary for bottom camera
        "y1": 0,    # Top boundary
        "x2": 965,  # Right boundary
        "y2": 720   # Bottom boundary
    }
}

# Model Configuration
MODEL_NAME = "NonAugmentDefects--640x640_quant_hailort_hailo8_1"
MODEL_PATH = "/home/inspectura/Desktop/InspecturaGUI/models/NonAugmentDefects--640x640_quant_hailort_hailo8_1"
INFERENCE_HOST = "@local"

# Detection Thresholds
MIN_CONFIDENCE = 0.25  # Minimum confidence for defect detection

# Camera Configuration
CAMERA_INDEX_TOP = 0      # Change if needed
CAMERA_INDEX_BOTTOM = 2   # Change if needed
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

# Model expects 640x640 input
MODEL_INPUT_SIZE = 640

# Defect Colors (BGR format for OpenCV)
DEFECT_COLORS = {
    "Sound_Knot": (255, 200, 100),      # Light blue
    "Live_Knot": (255, 200, 100),       # Light blue
    "Dead_Knot": (0, 255, 255),         # Yellow
    "Missing_Knot": (0, 0, 255),        # Red
    "Crack_Knot": (0, 165, 255),        # Orange
    "Unsound_Knot": (0, 165, 255),      # Orange
    "knots_with_crack": (0, 165, 255),  # Orange
    "missing_knots": (0, 0, 255),       # Red
    "live_knots": (255, 200, 100),      # Light blue
    "dead_knots": (0, 255, 255),        # Yellow
}

# Defect Display Names
DEFECT_NAMES = {
    "Sound_Knot": "Sound Knot",
    "Live_Knot": "Live Knot",
    "Dead_Knot": "Dead Knot",
    "Missing_Knot": "Missing Knot",
    "Crack_Knot": "Crack Knot",
    "Unsound_Knot": "Unsound Knot",
    "knots_with_crack": "Knot w/ Crack",
    "missing_knots": "Missing Knot",
    "live_knots": "Live Knot",
    "dead_knots": "Dead Knot",
}

# ============================================================================
# RGB WOOD DETECTOR (from testIR.py ColorWoodDetector class)
# ============================================================================

class ColorWoodDetector:
    """RGB-based wood detection using color segmentation"""
    
    def __init__(self):
        # Wood color profiles (RGB ranges)
        self.wood_color_profiles = {
            'top_panel': {
                'rgb_lower': np.array([160, 160, 160]),
                'rgb_upper': np.array([225, 220, 210])
            },
            'bottom_panel': {
                'rgb_lower': np.array([70, 70, 85]),
                'rgb_upper': np.array([225, 220, 210])
            }
        }
        
        # Detection parameters (from rgb_wood_detector.py)
        self.min_contour_area = 1000
        self.max_contour_area = 500000    # From rgb_wood_detector.py (reduced from 2000000)
        self.min_aspect_ratio = 1.0       # From rgb_wood_detector.py (tightened from 1.5)
        self.max_aspect_ratio = 10.0
        self.contour_approximation = 0.025  # From rgb_wood_detector.py (tightened from 0.02)
        
        # Morphological operation settings (from rgb_wood_detector.py)
        self.morph_kernel_size = 11       # From rgb_wood_detector.py (increased from 5)
        self.closing_iterations = 3
        self.opening_iterations = 2
        
        # Pixel-to-mm conversion factors (from rgb_wood_detector.py)
        self.pixel_per_mm_top = 2.96     # Calibrated at 31cm distance
        self.pixel_per_mm_bottom = 3.5   # Calibrated for bottom camera
        
        # Storage for detection results
        self.wood_detection_results = {}
        self.dynamic_roi = {}
        self.detected_wood_width_mm = {}
    
    def calculate_width_mm(self, width_px: float, camera_name: str = 'top') -> float:
        """Convert pixel width to millimeters"""
        if camera_name == 'top':
            return width_px / self.pixel_per_mm_top
        else:
            return width_px / self.pixel_per_mm_bottom
    
    def detect_wood_by_color(self, image: np.ndarray, profile_names: List[str] = None) -> Tuple[np.ndarray, List[Dict]]:
        """Detect wood using color-first approach with edge enhancement (from rgb_wood_detector.py)"""
        try:
            if image is None or image.size == 0:
                print("❌ Error: Invalid input image for color detection")
                return np.zeros((100, 100), dtype=np.uint8), []
            
            if profile_names is None:
                profile_names = list(self.wood_color_profiles.keys())
            
            # Step 1: Apply histogram equalization on V channel for better lighting compensation
            hsv_temp = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv_temp)
            v = cv2.equalizeHist(v)
            hsv_temp = cv2.merge([h, s, v])
            rgb = cv2.cvtColor(hsv_temp, cv2.COLOR_HSV2BGR)
            
            combined_mask = np.zeros(rgb.shape[:2], dtype=np.uint8)
            detections = []
            
            print(f"🎨 Using profiles: {profile_names}")
            
            # Combine masks from selected profiles (using BGR format like rgb_wood_detector.py)
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
            color_mask_blurred = cv2.GaussianBlur(combined_mask, (5, 5), 0)
            color_edges = cv2.Canny(color_mask_blurred, 100, 200)
            
            # Dilate the edges to make them more visible
            kernel_edge = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            color_edges_dilated = cv2.dilate(color_edges, kernel_edge, iterations=1)
            
            # Combine the original color mask with edge information
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
            
            # Additional logging for dominant colors (from rgb_wood_detector.py)
            rgb_flat = rgb.reshape(-1, 3)
            r_values = rgb_flat[:, 0]
            g_values = rgb_flat[:, 1]
            b_values = rgb_flat[:, 2]
            print(f"🎨 Dominant RGB in image: R={int(np.mean(r_values))}±{int(np.std(r_values))}, G={int(np.mean(g_values))}, B={int(np.mean(b_values))}")
            
            return enhanced_mask, detections
            
        except Exception as e:
            print(f"❌ Error in color detection: {e}")
            return np.zeros(image.shape[:2], dtype=np.uint8), []
    
    def detect_rectangular_contours(self, mask: np.ndarray, camera: str = 'top') -> List[Dict]:
        """Detect rectangular contours that could be wood planks - focusing on center area (from rgb_wood_detector.py)"""
        try:
            if mask is None or mask.size == 0:
                print("❌ Error: Invalid mask for contour detection")
                return []
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"📐 Found {len(contours)} total contours")

            # Get mask dimensions for center focus
            mask_height, mask_width = mask.shape
            center_margin_x = int(mask_width * 0.2)
            center_margin_y = int(mask_height * 0.2)
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
                    
                    # Filter by minimum size
                    min_height = 266 if camera == 'top' else 286
                    min_width = 100
                    
                    if h < min_height or w < min_width:
                        rejected_area += 1
                        print(f"  ❌ Contour {i}: size {w}x{h} too small for {camera} camera (min {min_width}x{min_height})")
                        continue
                    
                    aspect_ratio = max(w, h) / min(w, h)
                    
                    # Filter by aspect ratio
                    if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
                        rejected_aspect += 1
                        print(f"  ❌ Contour {i}: aspect {aspect_ratio:.2f} out of range [{self.min_aspect_ratio}, {self.max_aspect_ratio}]")
                        continue
                    
                    # Calculate additional metrics
                    hull = cv2.convexHull(contour)
                    hull_area = cv2.contourArea(hull)
                    solidity = area / hull_area if hull_area > 0 else 0
                    
                    # Approximate contour to polygon
                    epsilon = self.contour_approximation * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    confidence = self._calculate_wood_confidence(area, aspect_ratio, solidity, len(approx))
                    
                    wood_candidate = {
                        'contour': contour,
                        'approx_points': approx,
                        'bbox': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'solidity': solidity,
                        'vertices': len(approx),
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
        
        # Area score
        if 10000 <= area <= 100000:
            confidence += 0.3
        elif area > 5000:
            confidence += 0.2
        
        # Aspect ratio score
        if 2.0 <= aspect_ratio <= 6.0:
            confidence += 0.3
        elif 1.5 <= aspect_ratio <= 8.0:
            confidence += 0.2
        
        # Solidity score
        if solidity > 0.7:
            confidence += 0.2
        elif solidity > 0.5:
            confidence += 0.1
        
        # Vertex count score
        if vertices == 4:
            confidence += 0.2
        elif 4 <= vertices <= 6:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def generate_auto_roi(self, wood_candidates: List[Dict], image_shape: Tuple) -> Optional[Tuple[int, int, int, int]]:
        """Generate automatic ROI based on detected wood"""
        if not wood_candidates:
            return None
        
        # Use the highest confidence detection
        best_candidate = wood_candidates[0]
        x, y, w, h = best_candidate['bbox']
        
        # Add some padding around the detected wood
        padding_x = int(w * 0.1)
        padding_y = int(h * 0.1)
        
        roi_x1 = max(0, x - padding_x)
        roi_y1 = max(0, y - padding_y)
        roi_x2 = min(image_shape[1], x + w + padding_x)
        roi_y2 = min(image_shape[0], y + h + padding_y)
        
        return (roi_x1, roi_y1, roi_x2 - roi_x1, roi_y2 - roi_y1)
    
    def detect_wood_comprehensive(self, image: np.ndarray, profile_names: List[str] = None, 
                                  roi: Tuple[int, int, int, int] = None, camera: str = 'top') -> Dict:
        """Comprehensive wood detection combining color and shape analysis"""
        try:
            if image is None or image.size == 0:
                print("❌ Error: Invalid input image for comprehensive detection")
                return {
                    'wood_detected': False,
                    'wood_count': 0,
                    'wood_candidates': [],
                    'auto_roi': None,
                    'color_mask': np.zeros((100, 100), dtype=np.uint8),
                    'confidence': 0.0,
                    'error': 'Invalid input image'
                }
            
            print(f"🪵 Starting comprehensive wood detection on image shape: {image.shape}")
            
            # Use camera-specific profile if none specified
            if profile_names is None:
                profile_names = ['top_panel'] if camera == 'top' else ['bottom_panel']
            
            # Color-based detection
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
            
            # Find rectangular contours
            wood_candidates = self.detect_rectangular_contours(color_mask, camera)
            print(f"📐 Found {len(wood_candidates)} wood candidates")
            
            # Generate automatic ROI
            auto_roi = self.generate_auto_roi(wood_candidates, image.shape)
            
            # Update wood width if detected
            if wood_candidates:
                best_candidate = wood_candidates[0]
                x, y, w, h = best_candidate['bbox']
                detected_width_mm = self.calculate_width_mm(h, camera)
                self.detected_wood_width_mm[camera] = detected_width_mm
                print(f"🎯 Detected wood width: {detected_width_mm:.1f}mm (camera: {camera})")
            
            result = {
                'wood_detected': len(wood_candidates) > 0,
                'wood_count': len(wood_candidates),
                'wood_candidates': wood_candidates,
                'auto_roi': auto_roi,
                'color_mask': color_mask,
                'confidence': wood_candidates[0]['confidence'] if wood_candidates else 0.0
            }
            
            # Store results
            self.wood_detection_results[camera] = result
            self.dynamic_roi[camera] = auto_roi
            
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
                'error': str(e)
            }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def draw_roi_overlay(frame, camera_name, roi_enabled=True):
    """
    Draw static Yellow ROI rectangle overlay on frame for visualization
    This shows the detection area where wood detection runs
    """
    if not roi_enabled:
        return frame
    
    roi_coords = ROI_COORDINATES.get(camera_name, {})
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
    
    # Draw ROI rectangle (yellow border) - thicker line for visibility
    cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 255), 3)
    
    # Add ROI label at top
    cv2.putText(frame_copy, f"Yellow ROI - {camera_name.upper()}", 
               (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    
    return frame_copy

def get_defect_color(defect_type):
    """Get color for defect type"""
    return DEFECT_COLORS.get(defect_type, (0, 255, 0))  # Default green

def get_defect_name(defect_type):
    """Get display name for defect type"""
    return DEFECT_NAMES.get(defect_type, defect_type)

def bbox_inside_roi(bbox, roi, overlap_threshold=0.7):
    """
    Check if a bounding box has significant overlap with ROI (>70% by default)
    This allows large defects near wood edges to be detected
    
    Args:
        bbox: Detection bounding box [x1, y1, x2, y2]
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
    
    # Unpack detection bbox
    det_x1, det_y1, det_x2, det_y2 = bbox
    
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

def filter_overlapping_detections(detections, overlap_threshold=0.3):
    """
    Filter overlapping detections using Non-Maximum Suppression (NMS)
    Keeps only the most confident detection per overlapping area
    
    Args:
        detections: List of detection dictionaries with 'bbox' and 'confidence'
        overlap_threshold: IoU threshold for considering detections as overlapping
        
    Returns:
        List of filtered detections
    """
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
    sorted_detections = sorted(detections, key=lambda x: x.get('confidence', 0.0), reverse=True)
    
    filtered_detections = []
    
    for detection in sorted_detections:
        bbox = detection['bbox']
        
        # Check if this detection overlaps significantly with any already selected detection
        is_overlapping = False
        for selected_detection in filtered_detections:
            selected_bbox = selected_detection['bbox']
            iou = calculate_iou(bbox, selected_bbox)
            
            if iou > overlap_threshold:
                is_overlapping = True
                break
        
        # Only add if it doesn't overlap significantly with existing detections
        if not is_overlapping:
            filtered_detections.append(detection)
    
    return filtered_detections

def resize_to_640(frame):
    """
    Resize frame to 640x640 WITH PADDING to maintain aspect ratio
    This prevents distortion of defects
    
    Returns:
        resized_frame: 640x640 image with padding
        scale: uniform scale factor used
        pad_x: left padding pixels
        pad_y: top padding pixels
    """
    h, w = frame.shape[:2]
    
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

def draw_detections(frame, detections, scale_x=1.0, scale_y=1.0):
    """
    Draw bounding boxes and labels on frame
    
    Args:
        frame: Original frame to draw on
        detections: List of detection dicts with ALREADY ADJUSTED coordinates
        scale_x: Legacy parameter (not used with new coordinate system)
        scale_y: Legacy parameter (not used with new coordinate system)
    """
    annotated = frame.copy()
    
    for det in detections:
        label = det['label']
        bbox = det['bbox']
        confidence = det.get('confidence', 0.0)
        
        # Coordinates are already adjusted to original frame size
        x1 = int(bbox[0])
        y1 = int(bbox[1])
        x2 = int(bbox[2])
        y2 = int(bbox[3])
        
        # Get color and name
        color = get_defect_color(label)
        display_name = get_defect_name(label)
        
        # Draw bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        
        # Prepare label text
        label_text = f"{display_name} ({confidence:.2f})"
        
        # Calculate text size for background
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(
            label_text, font, font_scale, thickness
        )
        
        # Position text above bounding box
        text_x = x1
        text_y = y1 - 10
        
        # Adjust if text goes outside frame
        if text_y < text_height + baseline:
            text_y = y2 + text_height + baseline + 10
        
        # Draw background rectangle for text
        bg_x1 = max(0, text_x)
        bg_y1 = max(0, text_y - text_height - baseline)
        bg_x2 = min(annotated.shape[1], text_x + text_width)
        bg_y2 = min(annotated.shape[0], text_y + baseline)
        
        cv2.rectangle(annotated, (bg_x1, bg_y1), (bg_x2, bg_y2), color, -1)
        
        # Draw text (black for contrast)
        cv2.putText(annotated, label_text, (text_x, text_y),
                   font, font_scale, (0, 0, 0), thickness)
    
    return annotated

def add_info_overlay(frame, fps, detection_count, camera_name="Camera"):
    """Add FPS and detection info overlay"""
    overlay = frame.copy()
    
    # Semi-transparent background
    cv2.rectangle(overlay, (10, 10), (300, 80), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.5, frame, 0.5, 0)
    
    # Add text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, f"{camera_name}", (20, 35),
               font, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (20, 60),
               font, 0.6, (0, 255, 0), 2)
    cv2.putText(frame, f"Defects: {detection_count}", (150, 60),
               font, 0.6, (0, 255, 255), 2)
    
    return frame

# ============================================================================
# MAIN INFERENCE CLASS
# ============================================================================

class LiveInference:
    def __init__(self, use_top=True, use_bottom=True, enable_wood_detection=True):
        """
        Initialize live inference
        
        Args:
            use_top: Use top camera
            use_bottom: Use bottom camera
            enable_wood_detection: Enable RGB wood detection before defect detection
        """
        self.use_top = use_top
        self.use_bottom = use_bottom
        self.enable_wood_detection = enable_wood_detection
        
        print("="*60)
        print("Live Wood Defect Detection Inference")
        print("="*60)
        
        # Initialize wood detector if enabled
        if self.enable_wood_detection:
            print("\n🪵 Initializing RGB wood detector...")
            self.wood_detector = ColorWoodDetector()
            print("✅ Wood detector initialized!")
        else:
            self.wood_detector = None
        
        # Load model
        print(f"\n📦 Loading model: {MODEL_NAME}")
        print(f"   Path: {MODEL_PATH}")
        try:
            self.model = dg.load_model(
                model_name=MODEL_NAME,
                inference_host_address=INFERENCE_HOST,
                zoo_url=MODEL_PATH
            )
            print("✅ Model loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            sys.exit(1)
        
        # Initialize cameras
        self.cap_top = None
        self.cap_bottom = None
        
        if self.use_top:
            print(f"\n📹 Opening top camera (index {CAMERA_INDEX_TOP})...")
            self.cap_top = cv2.VideoCapture(CAMERA_INDEX_TOP)
            self.cap_top.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.cap_top.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            
            if self.cap_top.isOpened():
                print("✅ Top camera opened successfully!")
            else:
                print("❌ Failed to open top camera")
                self.use_top = False
        
        if self.use_bottom:
            print(f"\n📹 Opening bottom camera (index {CAMERA_INDEX_BOTTOM})...")
            self.cap_bottom = cv2.VideoCapture(CAMERA_INDEX_BOTTOM)
            self.cap_bottom.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.cap_bottom.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            
            if self.cap_bottom.isOpened():
                print("✅ Bottom camera opened successfully!")
            else:
                print("❌ Failed to open bottom camera")
                self.use_bottom = False
        
        if not self.use_top and not self.use_bottom:
            print("\n❌ No cameras available. Exiting...")
            sys.exit(1)
        
        # FPS tracking
        self.fps_top = 0
        self.fps_bottom = 0
        self.frame_count_top = 0
        self.frame_count_bottom = 0
        self.start_time = time.time()
        
        print("\n" + "="*60)
        print("🚀 Starting live inference...")
        print("Press 'q' to quit")
        print("Press 's' to save annotated frame")
        print("Press 'd' to save debug frames (original)")
        print("="*60 + "\n")
    
    def process_frame(self, frame, camera_name="top", enable_roi=True):
        """
        Process a single frame through wood detection and defect detection
        Following testIR.py ROI workflow:
        1. Wood detection runs within Yellow ROI (static camera zone)
        2. Defect detection runs on full 640x640 frame
        3. Visualizations show both Yellow ROI and detected wood boxes
        
        Args:
            frame: Input frame (1280x720)
            camera_name: Camera identifier ("top" or "bottom")
            enable_roi: Enable ROI filtering
            
        Returns:
            annotated_frame: Frame with all visualizations
            detection_count: Number of defect detections
        """
        # Get original dimensions
        original_h, original_w = frame.shape[:2]
        
        # STEP 1: Wood Detection within Yellow ROI (if enabled)
        wood_detected = False
        wood_result = None
        
        if self.wood_detector is not None and enable_roi:
            # Get ROI coordinates for this camera
            roi_coords = ROI_COORDINATES.get(camera_name, {})
            if roi_coords:
                x1, y1 = roi_coords["x1"], roi_coords["y1"]
                x2, y2 = roi_coords["x2"], roi_coords["y2"]
                
                # Crop frame to Yellow ROI for wood detection
                yellow_roi_frame = frame[y1:y2, x1:x2]
                print(f"🟨 Running wood detection on Yellow ROI: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
                
                # Run wood detection on cropped ROI
                wood_result = self.wood_detector.detect_wood_comprehensive(
                    yellow_roi_frame, camera=camera_name
                )
                wood_detected = wood_result['wood_detected']
                
                # Adjust bounding boxes back to full frame coordinates
                if wood_detected:
                    for candidate in wood_result['wood_candidates']:
                        bbox_x, bbox_y, bbox_w, bbox_h = candidate['bbox']
                        candidate['bbox'] = (bbox_x + x1, bbox_y + y1, bbox_w, bbox_h)
                    
                    if wood_result.get('auto_roi'):
                        roi_x, roi_y, roi_w, roi_h = wood_result['auto_roi']
                        wood_result['auto_roi'] = (roi_x + x1, roi_y + y1, roi_w, roi_h)
                    
                    print(f"✅ Wood detected on {camera_name} (confidence: {wood_result['confidence']:.2f})")
                else:
                    print(f"⚠️  No wood detected on {camera_name}")
            else:
                print(f"❌ No Yellow ROI defined for {camera_name}")
        elif self.wood_detector is not None and not enable_roi:
            # Run wood detection on full frame if ROI disabled
            wood_result = self.wood_detector.detect_wood_comprehensive(
                frame, camera=camera_name
            )
            wood_detected = wood_result['wood_detected']
        
        # STEP 2: Defect Detection on Full Frame (640x640 with padding)
        # Always run on full frame - model was trained on full camera feeds
        frame_640, scale, pad_x, pad_y = resize_to_640(frame)
        
        # Run inference
        results = self.model(frame_640)
        
        # Debug: Print all raw detections
        print(f"📊 RAW DETECTIONS (total: {len(results.results)}):")
        for i, det in enumerate(results.results):
            label = det.get('label', 'unknown')
            confidence = det.get('confidence', 0.0)
            bbox = det.get('bbox', [0, 0, 0, 0])
            print(f"   #{i+1}: {label} @ {confidence:.3f} | bbox: [{bbox[0]:.0f}, {bbox[1]:.0f}, {bbox[2]:.0f}, {bbox[3]:.0f}]")
        
        # Get Dynamic Wood ROI for filtering
        dynamic_wood_roi = wood_result.get('auto_roi') if wood_result else None
        
        # Filter detections by confidence and adjust coordinates
        filtered_detections = []
        rejected_by_roi = 0
        rejected_by_confidence = 0
        
        for det in results.results:
            confidence = det.get('confidence', 0.0)
            label = det.get('label', 'unknown')
            
            # WORKAROUND: Accept 0.000 confidence (Hailo-8 quantization bug - these ARE valid detections)
            # For non-zero confidence, apply threshold filtering
            # Reject detections with low confidence (0 < confidence < MIN_CONFIDENCE)
            if confidence != 0.0 and confidence < MIN_CONFIDENCE:
                rejected_by_confidence += 1
                print(f"   ❌ Rejected (low confidence): {label} @ {confidence:.3f}")
                continue
            
            # Adjust bounding box coordinates to account for padding and scaling
            bbox = det.get('bbox', [0, 0, 0, 0])
            
            # Remove padding offset
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
                print(f"   ⚠️  Skipping detection in padding area: {label}")
                continue
            
            # NEW: Filter by Dynamic Wood ROI (only keep detections inside wood area)
            adjusted_bbox = [x1, y1, x2, y2]
            if bbox_inside_roi(adjusted_bbox, dynamic_wood_roi):
                adjusted_det = det.copy()
                adjusted_det['bbox'] = adjusted_bbox
                filtered_detections.append(adjusted_det)
            else:
                rejected_by_roi += 1
                print(f"   🚫 Rejected (outside Wood ROI): {label} @ [{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")
        
        print(f"🔍 Filtered detections: {len(filtered_detections)} (0.000 always accepted, others >= {MIN_CONFIDENCE})")
        if rejected_by_confidence > 0:
            print(f"   ❌ Rejected by confidence filter: {rejected_by_confidence} detection(s)")
        if rejected_by_roi > 0:
            print(f"   🚫 Rejected by Wood ROI filter: {rejected_by_roi} detection(s)")
        
        # Apply Non-Maximum Suppression (NMS) to remove overlapping detections
        print(f"🔄 Before overlap filter: {len(filtered_detections)} detection(s)")
        final_detections = filter_overlapping_detections(filtered_detections, overlap_threshold=0.3)
        if len(final_detections) < len(filtered_detections):
            removed = len(filtered_detections) - len(final_detections)
            print(f"   ⚠️  Overlap filter removed {removed} detection(s) (IoU > 0.3)")
        
        # STEP 3: Build Visualization Layers
        # Start with original frame
        annotated = frame.copy()
        
        # Layer 1: Draw Yellow ROI (static detection zone)
        if enable_roi:
            annotated = draw_roi_overlay(annotated, camera_name, roi_enabled=True)
        
        # Layer 2: Draw best wood detection only (green box)
        if wood_detected and wood_result is not None:
            # Only use the best candidate (highest confidence)
            best_candidate = wood_result['wood_candidates'][0]
            x, y, w, h = best_candidate['bbox']
            conf = best_candidate['confidence']
            
            # Green box for best wood detection
            color = (0, 255, 0)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            
            # Add label
            label = f"Wood: {conf:.2f}"
            cv2.putText(annotated, label, (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Draw dynamic wood ROI (auto-generated from wood detection)
            if wood_result.get('auto_roi'):
                roi_x, roi_y, roi_w, roi_h = wood_result['auto_roi']
                # Use dashed effect by drawing multiple small segments
                dash_length = 10
                gap_length = 5
                # Top edge
                for i in range(roi_x, roi_x + roi_w, dash_length + gap_length):
                    cv2.line(annotated, (i, roi_y), (min(i + dash_length, roi_x + roi_w), roi_y), (255, 255, 0), 2)
                # Bottom edge
                for i in range(roi_x, roi_x + roi_w, dash_length + gap_length):
                    cv2.line(annotated, (i, roi_y + roi_h), (min(i + dash_length, roi_x + roi_w), roi_y + roi_h), (255, 255, 0), 2)
                # Left edge
                for i in range(roi_y, roi_y + roi_h, dash_length + gap_length):
                    cv2.line(annotated, (roi_x, i), (roi_x, min(i + dash_length, roi_y + roi_h)), (255, 255, 0), 2)
                # Right edge
                for i in range(roi_y, roi_y + roi_h, dash_length + gap_length):
                    cv2.line(annotated, (roi_x + roi_w, i), (roi_x + roi_w, min(i + dash_length, roi_y + roi_h)), (255, 255, 0), 2)
                
                cv2.putText(annotated, "Dynamic Wood ROI", (roi_x, roi_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Layer 3: Draw defect detections (color-coded)
        # Note: Coordinates already adjusted in process_frame, no scaling needed
        annotated = draw_detections(annotated, final_detections)
        
        return annotated, len(final_detections)
    
    def run(self):
        """Main inference loop"""
        # Get ROI setting (set in main)
        enable_roi = getattr(self, 'enable_roi', True)
        
        try:
            while True:
                current_time = time.time()
                
                # Process top camera
                if self.use_top and self.cap_top is not None:
                    ret_top, frame_top = self.cap_top.read()
                    if ret_top:
                        # Process frame with ROI setting
                        annotated_top, count_top = self.process_frame(
                            frame_top, "top", enable_roi=enable_roi
                        )
                        
                        # Update FPS
                        self.frame_count_top += 1
                        elapsed = current_time - self.start_time
                        if elapsed > 1.0:
                            self.fps_top = self.frame_count_top / elapsed
                        
                        # Add overlay
                        display_top = add_info_overlay(
                            annotated_top, self.fps_top, count_top, "Top Camera"
                        )
                        
                        # Resize to 360p for display (640x360)
                        display_top = cv2.resize(display_top, (640, 360), interpolation=cv2.INTER_LINEAR)
                        
                        # Show frame
                        cv2.imshow("Top Camera - Defect Detection", display_top)
                
                # Process bottom camera
                if self.use_bottom and self.cap_bottom is not None:
                    ret_bottom, frame_bottom = self.cap_bottom.read()
                    if ret_bottom:
                        # Flip bottom camera horizontally (matching testIR.py)
                        frame_bottom = cv2.flip(frame_bottom, 1)
                        
                        # Process frame with ROI setting
                        annotated_bottom, count_bottom = self.process_frame(
                            frame_bottom, "bottom", enable_roi=enable_roi
                        )
                        
                        # Update FPS
                        self.frame_count_bottom += 1
                        elapsed = current_time - self.start_time
                        if elapsed > 1.0:
                            self.fps_bottom = self.frame_count_bottom / elapsed
                        
                        # Add overlay
                        display_bottom = add_info_overlay(
                            annotated_bottom, self.fps_bottom, count_bottom, "Bottom Camera"
                        )
                        
                        # Resize to 360p for display (640x360)
                        display_bottom = cv2.resize(display_bottom, (640, 360), interpolation=cv2.INTER_LINEAR)
                        
                        # Show frame
                        cv2.imshow("Bottom Camera - Defect Detection", display_bottom)
                
                # Reset FPS counter every second
                if current_time - self.start_time > 1.0:
                    self.start_time = current_time
                    self.frame_count_top = 0
                    self.frame_count_bottom = 0
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\n👋 Quitting...")
                    break
                elif key == ord('s'):
                    # Save current frames
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    if self.use_top and ret_top:
                        filename = f"top_camera_{timestamp}.jpg"
                        cv2.imwrite(filename, display_top)
                        print(f"💾 Saved: {filename}")
                    if self.use_bottom and ret_bottom:
                        filename = f"bottom_camera_{timestamp}.jpg"
                        cv2.imwrite(filename, display_bottom)
                        print(f"💾 Saved: {filename}")
                elif key == ord('d'):
                    # Save debug frames (original + what model sees)
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    if self.use_top and ret_top:
                        cv2.imwrite(f"debug_original_top_{timestamp}.jpg", frame_top)
                        print(f"💾 Debug: Saved original top frame")
                    if self.use_bottom and ret_bottom:
                        cv2.imwrite(f"debug_original_bottom_{timestamp}.jpg", frame_bottom)
                        print(f"💾 Debug: Saved original bottom frame")
        
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Release resources"""
        print("\n🧹 Cleaning up...")
        
        if self.cap_top is not None:
            self.cap_top.release()
            print("✅ Top camera released")
        
        if self.cap_bottom is not None:
            self.cap_bottom.release()
            print("✅ Bottom camera released")
        
        cv2.destroyAllWindows()
        print("✅ Windows closed")
        print("\n👋 Goodbye!\n")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Live inference for wood defect detection"
    )
    parser.add_argument(
        "--camera",
        choices=["top", "bottom", "both"],
        default="both",
        help="Which camera(s) to use (default: both)"
    )
    parser.add_argument(
        "--top-index",
        type=int,
        default=CAMERA_INDEX_TOP,
        help=f"Top camera index (default: {CAMERA_INDEX_TOP})"
    )
    parser.add_argument(
        "--bottom-index",
        type=int,
        default=CAMERA_INDEX_BOTTOM,
        help=f"Bottom camera index (default: {CAMERA_INDEX_BOTTOM})"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=MIN_CONFIDENCE,
        help=f"Minimum confidence threshold (default: {MIN_CONFIDENCE})"
    )
    parser.add_argument(
        "--no-wood-detection",
        action="store_true",
        help="Disable RGB wood detection (only run defect detection)"
    )
    parser.add_argument(
        "--no-roi",
        action="store_true",
        help="Disable Yellow ROI filtering (run detection on full frame)"
    )
    
    args = parser.parse_args()
    
    # Update configurations from arguments
    CAMERA_INDEX_TOP = args.top_index
    CAMERA_INDEX_BOTTOM = args.bottom_index
    MIN_CONFIDENCE = args.confidence
    
    # Determine which cameras to use
    use_top = args.camera in ["top", "both"]
    use_bottom = args.camera in ["bottom", "both"]
    
    # Wood detection enabled by default
    enable_wood_detection = not args.no_wood_detection
    enable_roi = not args.no_roi
    
    # Print configuration
    print("\n" + "="*60)
    print("CONFIGURATION")
    print("="*60)
    if enable_wood_detection:
        print("🪵 RGB Wood Detection: ENABLED")
    else:
        print("⚠️  RGB Wood Detection: DISABLED")
    
    if enable_roi:
        print("🟨 Yellow ROI: ENABLED")
        print(f"   Top camera ROI: {ROI_COORDINATES['top']}")
        print(f"   Bottom camera ROI: {ROI_COORDINATES['bottom']}")
    else:
        print("⚠️  Yellow ROI: DISABLED (full frame detection)")
    
    print(f"🎯 Confidence Threshold: {MIN_CONFIDENCE}")
    print("="*60 + "\n")
    
    # Run inference
    inference = LiveInference(
        use_top=use_top, 
        use_bottom=use_bottom,
        enable_wood_detection=enable_wood_detection
    )
    # Store ROI setting for use in process_frame
    inference.enable_roi = enable_roi
    inference.run()

