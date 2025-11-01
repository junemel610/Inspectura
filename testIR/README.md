# Wood Sorting System - TestIR & Master Controller

## Overview

This directory contains the test implementation of the automated wood sorting system, featuring real-time IR beam trigger detection and AI-powered defect analysis. The system consists of two main components:

- **Master Controller** (Arduino): Handles IR beam sensing, conveyor control, and servo gate actuation
- **TestIR Application** (Python): Provides the GUI interface, AI defect detection, and grading logic

## System Architecture

```
IR Beam Sensor → Arduino Master Controller → Python Application → Servo Gates
     ↓                    ↓                        ↓              ↓
  Detects wood      Triggers detection      Analyzes defects   Sorts by grade
  presence/clearance   and controls motor     with AI model     (G2-0 to G2-4)
```

## Master Controller (Arduino)

### Hardware Requirements
- Arduino Uno R3 or compatible board
- IR beam sensor (connected to pin 11)
- 4 servo motors (connected to pins 2, 3, 4, 5)
- Stepper motor driver (connected to pins 8, 9, 10)
- Stepper motor for conveyor belt

### Pin Configuration
```cpp
const int IR_SENSOR_PIN = 11;      // IR beam sensor input
const int SERVO_1_PIN = 2;         // Gate 1 servo (G2-0)
const int SERVO_2_PIN = 3;         // Gate 2 servo (G2-1/2/3)
const int SERVO_3_PIN = 4;         // Gate 3 servo (G2-4)
const int SERVO_4_PIN = 5;         // Additional servo
const int STEPPER_ENA_PIN = 8;     // Stepper motor enable
const int STEPPER_DIR_PIN = 9;     // Stepper motor direction
const int STEPPER_STEP_PIN = 10;   // Stepper motor step
```

### Serial Commands

#### Commands Sent TO Python:
- `'B'`: IR beam broken (wood piece detected)
- `'L:[ms]'`: IR beam cleared with duration in milliseconds

#### Commands Received FROM Python:
- `'1'`: Move servos to 90° (Gate 1 - G2-0 Perfect)
- `'2'`: Move servos to 45° (Gate 2 - G2-1/2/3 Good/Fair/Poor)
- `'3'`: Move servos to 135° (Gate 3 - G2-4 Reject)
- `'C'`: Set CONTINUOUS mode (motor always on)
- `'T'`: Set TRIGGER mode (motor controlled by IR beam)
- `'X'`: Set IDLE mode (motor off)

### Operating Modes

1. **IDLE Mode**: System disabled, motor stopped
2. **CONTINUOUS Mode**: Motor runs continuously, detection always active
3. **TRIGGER Mode**: Motor runs continuously, detection triggered by IR beam

### Installation
1. Open `master_controller.ino` in Arduino IDE
2. Connect Arduino board
3. Upload the sketch
4. Note the serial port (e.g., `/dev/ttyACM0` or `COM3`)

## TestIR Application (Python)

### Features
- Real-time dual camera defect detection with synchronized wood detection
- SS-EN 1611-1 wood grading standard implementation
- IR beam trigger integration with automatic camera reconnection
- Comprehensive statistics and reporting
- Live grading display with detailed defect analysis
- Automatic autofocus disable on camera connection
- Bottom camera frame mirroring for consistent perspective

### Hardware Requirements
- 2 USB cameras (top and bottom views)
- Arduino Master Controller (connected via USB)
- Hailo AI accelerator (for defect detection model)
- Linux system with Python 3.8+

### Software Dependencies
```
tkinter              # GUI framework
opencv-python        # Camera handling
degirum              # AI model inference
Pillow               # Image processing
pyserial             # Arduino communication
reportlab            # PDF report generation
numpy                # Numerical operations
```

### Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Configure Arduino connection:**
   - Update the serial port in the application if needed
   - The app auto-detects common Arduino ports

3. **Set up AI model:**
   - Ensure Hailo AI model is available at the specified path
   - Model: `V2DefectCombined--640x640_quant_hailort_hailo8_1`

### Configuration

#### Camera Settings
- **Resolution**: 1280x720
- **Frame Rate**: 30 FPS
- **Top Camera Distance**: 37cm
- **Bottom Camera Distance**: 29cm
- **Autofocus**: Automatically disabled on connection for consistent focus
- **Bottom Camera**: Frame mirrored horizontally for consistent perspective

#### Grading Parameters
- **Wood Width**: Measured dynamically from detected wood (typically 100-150mm)
- **Pixel-to-mm Factors**:
  - Top Camera: 2.96 pixels/mm
  - Bottom Camera: 3.18 pixels/mm

#### Grading Standards (SS-EN 161-1-1)
```
Limit = (0.10 × measured_wood_width) + constant

Where measured_wood_width is dynamically calculated from detected wood.

Example for 115mm wood:
Sound Knots:    G2-0: ≤21.5mm, G2-1: ≤31.5mm, G2-2: ≤46.5mm, G2-3: ≤61.5mm
Dead Knots:     G2-0: ≤11.5mm, G2-1: ≤21.5mm, G2-2: ≤31.5mm, G2-3: ≤61.5mm
Unsound Knots:  G2-2: ≤25.5mm, G2-3: ≤50.5mm
```

#### Confidence Thresholds
- **Minimum Confidence**: 25% (MIN_CONFIDENCE = 0.25)
- **Rejection Range**: 0-24.9% confidence (logged but not processed)
- **Low Confidence Alert**: 25-30% confidence (processed with warning)
- **Normal Confidence**: 30.1-100% confidence (processed normally)

#### Notification System

**Toast Notifications**: Non-blocking popup messages displayed in the center margin between cameras
- **Types**: Success (green), Warning (yellow), Error (red), Info (blue)
- **Size**: 450px × 100px
- **Duration**: Configurable (default 4-6 seconds)

**Low Confidence Detection (Test Case 3.1)**:
- Triggers when detections fall in 25-30% confidence range
- Indicates poor image quality or unclear defects
- Shows warning toast: "⚠️ Low Confidence Detection"
- Message: "{count} low confidence detection(s) on {camera} camera"
- Duration: 6 seconds for operator review
- Does NOT imply system failure - normal for challenging conditions

### Usage

#### Starting the Application
```bash
cd /path/to/testIR
python testIR.py
```

#### Operating Modes

1. **IDLE Mode**: System disabled, no operations
2. **TRIGGER Mode**: Waits for IR beam trigger, processes one piece at a time
3. **CONTINUOUS Mode**: Continuous detection and grading

#### GUI Controls

- **System Status**: Shows current mode and detection state
- **Camera Feeds**: Live video from top and bottom cameras
- **Detection Settings**:
  - Top ROI: Enable/disable region of interest for top camera
  - Live Detect: Toggle real-time detection
  - Auto Grade: Enable automatic grading
- **Statistics Tabs**:
  - Grade Summary: Live counts by grade
  - Defect Details: Detailed defect analysis
  - Performance: Processing metrics
  - Recent Activity: Processing log

#### IR Beam Trigger Sequence (TRIGGER Mode)

1. **Beam Cleared**: System waits for wood piece
2. **Beam Broken ('B')**: Detection starts, servo resets to 90°
3. **Detection Active**: AI analyzes defects in real-time
4. **Beam Clears ('L')**: Grading completes, servo moves to appropriate gate

### Grading Logic

#### Wood Detection
- Synchronized detection: Bottom camera only processes if top camera detects wood
- Dynamic ROI generation based on detected wood boundaries
- Color-based wood detection with morphological filtering

#### Individual Defect Grading
Each defect is graded using the formula: `Limit = (0.10 × wood_width) + constant`

#### Surface Grade Determination
1. **Size-based grading**: Worst individual defect grade
2. **Count-based grading**: Dead/Unsound knot limits per meter
3. **Final grade**: Worst of size and count criteria

#### Gate Mapping
- **G2-0** → Gate 1 (90°)
- **G2-1/2/3** → Gate 2 (45°)
- **G2-4** → Gate 3 (135°)

### File Structure

```
testIR/
├── master_controller/
│   └── master_controller.ino    # Arduino firmware
├── testIR.py                   # Main Python application
├── README.md                   # This documentation
├── detection_logs/             # JSON logs of detections
├── *.pdf                       # Generated reports
├── *.txt                       # Text reports
└── wood_sorting_*.txt          # Activity and sorting logs
```

### Troubleshooting

#### Arduino Connection Issues
- Check serial port permissions: `sudo chmod 666 /dev/ttyACM0`
- Verify Arduino is properly connected and powered
- Check baud rate (9600) matches between Arduino and Python

#### Camera Issues
- Ensure cameras are connected and not used by other applications
- Check camera device paths using `v4l2-ctl --list-devices`
- Verify camera resolutions are supported
- Cameras automatically reconnect on disconnection with retry logic
- Autofocus is disabled automatically on connection
- Bottom camera frames are mirrored for consistent perspective

#### AI Model Issues
- Ensure Hailo driver is installed and running
- Check model path exists and is accessible
- Verify model file integrity

#### IR Beam Problems
- Adjust IR sensor sensitivity if needed
- Check debounce delay (currently 100ms)
- Verify stable power supply to IR sensor

### Testing

#### Test Case 3.1: System Robustness Under Abnormal Conditions

**Objective**: Verify system handles poor image quality and unclear defects gracefully

**Test Procedure**:
1. Use planks with poor image quality (blur, low lighting, unclear defects)
2. Present planks with defects at edges or partial visibility
3. Simulate challenging detection conditions

**Expected Behavior**:
- Detections with 0-24.9% confidence: Rejected and logged (console only)
- Detections with 25-30% confidence: Accepted with warning toast notification
- Detections with 30%+ confidence: Processed normally without warnings
- Operator receives clear warning without implying system failure
- System continues operation without interruption

**Validation**:
- Toast notification appears: "⚠️ Low Confidence Detection"
- Console logs show: "⚠️ UNCERTAIN detection (Test Case 3.1): {defect} @ {confidence}"
- Detections are still processed and graded
- No false system error states triggered

#### Simulation Mode
Run with test flag to simulate IR events:
```bash
python testIR.py test
```

#### Manual Testing
- Use Arduino IDE Serial Monitor to send commands
- Check Python console output for debugging information
- Monitor detection logs for detailed analysis

### Performance Metrics

- **Processing Rate**: ~10-15 pieces/minute (depending on wood size)
- **Detection Accuracy**: >95% for major defects
- **Response Time**: <500ms for IR trigger to grading completion
- **Memory Usage**: ~200-300MB during operation
- **Camera Reconnection**: Automatic with 3-attempt retry logic
- **Wood Detection**: Synchronized across cameras for consistency

### Logs and Reports

#### Automatic Reports
- Generated after 30 seconds of inactivity
- Includes session summary and individual piece details
- Available in both PDF and text formats

#### Log Files
- `wood_sorting_activity_log.txt`: General activity log
- `wood_sorting_log.txt`: Session summaries
- `detection_logs/*.json`: Detailed detection data
- `logs/*.log`: System and error logs

### Safety Considerations

- Ensure proper ventilation for electronics
- Use appropriate power supplies for motors and servos
- Implement emergency stop mechanisms
- Regular maintenance of mechanical components

### Recent Updates

- **v4.2**: Implemented Test Case 3.1 - Low Confidence Detection System
  - Added low confidence detection alerts (25-30% confidence range)
  - Toast notification system for operator warnings
  - Enhanced robustness testing for poor image quality and unclear defects
  - Professional warning messages without implying system failure
- **v4.1**: Added synchronized wood detection (bottom camera follows top)
- **v4.0**: Implemented automatic camera reconnection with retry logic
- **v3.9**: Added autofocus disable on camera connection
- **v3.8**: Fixed v4l2-ctl parsing for device detection
- **v3.7**: Added bottom camera frame mirroring from start

### Future Enhancements

- Multi-piece batch processing
- Advanced defect classification
- Real-time performance optimization
- Web-based monitoring interface
- Integration with ERP systems

---

For technical support or questions, refer to the main project documentation or contact the development team.