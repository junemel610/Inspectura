/*
  Master Controller for Automated Wood Sorting System
  Stable Scan Phase with Dynamic Last Segment
*/

#include <Servo.h>

// --- Pin Definitions ---
const int IR_SENSOR_PIN = 11;
const int SERVO_1_PIN = 2;
const int SERVO_2_PIN = 3;
const int SERVO_3_PIN = 4;
const int SERVO_4_PIN = 5;
const int STEPPER_ENA_PIN = 8;
const int STEPPER_DIR_PIN = 9;
const int STEPPER_STEP_PIN = 10;

// --- Servo Motors ---
Servo servo1, servo2, servo3, servo4;

// --- Modes ---
enum Mode { IDLE, CONTINUOUS, TRIGGER, SCAN_PHASE };
Mode currentMode = IDLE;
Mode previousMode = IDLE;  // Store previous mode for recovery

// --- Error Handling States ---
bool systemPaused = false;           // System paused due to critical errors
bool manualInspectionRequired = false; // Manual inspection required flag
bool errorRecoveryActive = false;    // Error recovery in progress
bool reconnectionRecovery = false;   // Flag indicating recovery from disconnection
unsigned long errorPauseStartTime = 0; // When error pause started
char lastErrorType[20] = "";         // Last error type received (increased from 12 to 20)

// --- Stepper Control ---
int minDelay = 3000;              // Starting delay for ramping
int maxDelay = 1100;              // Target delay after ramping
int rampDelay = 3000;             // Current delay (starts at minDelay)
bool rampFinished = false;        // Ramping state
unsigned long lastStepTime = 0;
bool stepState = false;

// --- IR Sensor ---
byte lastStableIrState = HIGH;       // byte instead of int (saves 1 byte)
byte lastFlickerIrState = HIGH;      // byte instead of int (saves 1 byte)
unsigned long lastStateChangeTime = 0;
const byte debounceDelay = 50;       // byte instead of long (saves 3 bytes)
unsigned long beamBrokenStartTime = 0;
bool beamIsBroken = false;

// --- Conveyor Parameters ---
const float CONVEYOR_SPEED_IN_PER_SEC = 1.160;   // physical conveyor speed (in/s)
const unsigned long STOP_DURATION_MS = 5000;      // 5-second pauses between scans
const float WOOD_TOTAL_LENGTH_INCH = 21.0;        // <-- change this for each wood length
const int NUM_SEGMENTS = 4;

// --- Dynamic Segment Distances ---
float SCAN_SEGMENTS[NUM_SEGMENTS];

// --- Scan State ---
byte currentSegment = 0;        // byte instead of int (saves 1 byte)
byte pauseCount = 0;            // byte instead of int (saves 1 byte)
bool scanInProgress = false;
bool scanActive = false;
bool waitingForPause = false;
bool waitingForBeam = false;
unsigned long moveStartTime = 0;
unsigned long pauseStartTime = 0;
unsigned long segmentDurationMs = 0;
bool stepStateScan = false;
unsigned long lastStepTimeScan = 0;

void setup() {
  Serial.begin(9600);

  pinMode(IR_SENSOR_PIN, INPUT_PULLUP);
  pinMode(STEPPER_ENA_PIN, OUTPUT);
  pinMode(STEPPER_DIR_PIN, OUTPUT);
  pinMode(STEPPER_STEP_PIN, OUTPUT);
  digitalWrite(STEPPER_DIR_PIN, HIGH);
  digitalWrite(STEPPER_ENA_PIN, HIGH);

  servo1.attach(SERVO_1_PIN);
  servo2.attach(SERVO_2_PIN);
  servo3.attach(SERVO_3_PIN);
  servo4.attach(SERVO_4_PIN);
  servo1.write(90);
  servo2.write(90);
  servo3.write(90);
  servo4.write(90);

  // --- Dynamic segment calculation ---
  SCAN_SEGMENTS[0] = 0.75;  // first short exposure
  SCAN_SEGMENTS[1] = 7.0;
  SCAN_SEGMENTS[2] = 7.0;
  SCAN_SEGMENTS[3] = WOOD_TOTAL_LENGTH_INCH - (SCAN_SEGMENTS[0] + SCAN_SEGMENTS[1] + SCAN_SEGMENTS[2]);
  if (SCAN_SEGMENTS[3] < 0) SCAN_SEGMENTS[3] = 0;

  Serial.println(F("Mode: IDLE"));
  
  // Send connection status to Python for recovery
  Serial.println(F("ARDUINO_READY"));
  delay(100);
  Serial.println(F("STATUS_REQUEST")); // Ask Python for current mode
}

void loop() {
  // CRITICAL: Process serial commands FIRST to handle CLEAR_ERROR immediately
  checkSerialCommands();
  
  // Check for system errors AFTER processing commands
  if (systemPaused && strlen(lastErrorType) > 0) {
    handleSystemPause();
    return; // Don't continue normal operations while paused
  }
  
  if (currentMode == SCAN_PHASE)
    handleScanPhase();
  else
    handleStepper();

  checkIrSensor();
}

// ---------------- Stepper Handler ----------------
void handleStepper() {
  if (currentMode == SCAN_PHASE) return;
  bool active = (currentMode == CONTINUOUS || currentMode == TRIGGER);
  digitalWrite(STEPPER_ENA_PIN, active ? LOW : HIGH);
  if (active) {
    unsigned long t = micros();
    if (t - lastStepTime >= rampDelay) {
      lastStepTime = t;
      digitalWrite(STEPPER_STEP_PIN, HIGH);
      delayMicroseconds(2);
      digitalWrite(STEPPER_STEP_PIN, LOW);
      
      // Ramp up speed
      if (!rampFinished && rampDelay > maxDelay) {
        rampDelay -= 2;
      } else {
        rampFinished = true;
      }
    }
  } else {
    // Reset ramping when stopped
    rampDelay = minDelay;
    rampFinished = false;
  }
}

// ---------------- Scan Phase ----------------
void handleScanPhase() {
  // Check for error conditions during scan phase
  if (systemPaused || manualInspectionRequired) {
    pauseScanPhaseForError();
    return;
  }
  
  digitalWrite(STEPPER_ENA_PIN, LOW);

  // Conveyor runs while waiting for beam
  if (waitingForBeam && !scanInProgress) {
    unsigned long t = micros();
    if (t - lastStepTimeScan >= maxDelay) {
      lastStepTimeScan = t;
      digitalWrite(STEPPER_STEP_PIN, HIGH);
      delayMicroseconds(2);
      digitalWrite(STEPPER_STEP_PIN, LOW);
    }
    return;
  }

  if (!scanInProgress) return;

  // Segmented scanning
  if (currentSegment < NUM_SEGMENTS) {
    if (!waitingForPause) {
      if (moveStartTime == 0) {
        segmentDurationMs = (SCAN_SEGMENTS[currentSegment] / CONVEYOR_SPEED_IN_PER_SEC) * 1000;
        moveStartTime = millis();
        // Segment debug info removed to save memory
      }

      unsigned long t = micros();
      if (t - lastStepTimeScan >= maxDelay) {
        lastStepTimeScan = t;
        digitalWrite(STEPPER_STEP_PIN, HIGH);
        delayMicroseconds(2);
        digitalWrite(STEPPER_STEP_PIN, LOW);
      }

      if (millis() - moveStartTime >= segmentDurationMs) {
        moveStartTime = 0;
        if (currentSegment < NUM_SEGMENTS - 1) {
          waitingForPause = true;
          pauseStartTime = millis();
          pauseCount++;
          // Wait 2 seconds before sending CAPTURE
          delay(2000);
          Serial.print("CAPTURE:");
          Serial.println(currentSegment + 1);
          Serial.print("P:");
          Serial.println(currentSegment + 1);
        } else {
          scanInProgress = false;
          clearTailAfterScan();
        }
      }
    } else if (millis() - pauseStartTime >= STOP_DURATION_MS) {
      waitingForPause = false;
      currentSegment++;
      Serial.println("RESUME_LIVE_FEED");
      Serial.print("Resuming segment ");
      Serial.println(currentSegment + 1);
    }
  }
}

// ---------------- Tail Clear ----------------
void clearTailAfterScan() {
  Serial.println("Last scan phase complete. Clearing tail...");

  float clearDistanceInches = 2.0;
  unsigned long clearDurationMs = (clearDistanceInches / CONVEYOR_SPEED_IN_PER_SEC) * 1000;
  unsigned long clearStart = millis();

  while (millis() - clearStart < clearDurationMs) {
    unsigned long t = micros();
    if (t - lastStepTimeScan >= maxDelay) {
      lastStepTimeScan = t;
      digitalWrite(STEPPER_STEP_PIN, HIGH);
      delayMicroseconds(2);
      digitalWrite(STEPPER_STEP_PIN, LOW);
    }
  }

  // digitalWrite(STEPPER_ENA_PIN, HIGH);
  Serial.println("Tail cleared. Waiting for next beam...");                                 

  currentSegment = 0;
  pauseCount = 0;
  scanInProgress = false;

  lastStableIrState = HIGH;
  lastFlickerIrState = HIGH;
  beamIsBroken = false;
  waitingForBeam = true;

  digitalWrite(STEPPER_ENA_PIN, LOW);
}

// ---------------- IR Sensor ----------------
void checkIrSensor() {
  int currentIrState = digitalRead(IR_SENSOR_PIN);
  if (currentIrState != lastFlickerIrState)
    lastStateChangeTime = millis();
  lastFlickerIrState = currentIrState;

  if ((millis() - lastStateChangeTime) > debounceDelay) {
    if (currentIrState != lastStableIrState) {
      if (currentIrState == LOW) {   // beam broken
        Serial.println("B");
        delay(50);
        activateAllServoGates(90);
        beamBrokenStartTime = millis();
        beamIsBroken = true;

        if (currentMode == SCAN_PHASE && waitingForBeam) {
          waitingForBeam = false;
          scanInProgress = true;
          currentSegment = 0;
          pauseCount = 0;
          Serial.println("Beam detected! Starting segmented scan...");
        }
      } else if (beamIsBroken) {     // beam cleared
        unsigned long rawDuration = millis() - beamBrokenStartTime;
        beamIsBroken = false;

        if (currentMode == SCAN_PHASE) {
          unsigned long totalPause = (NUM_SEGMENTS - 1) * STOP_DURATION_MS;
          unsigned long adjustedDuration = (rawDuration > totalPause)
                                            ? rawDuration - totalPause
                                            : rawDuration;
          float measuredLength = (adjustedDuration * CONVEYOR_SPEED_IN_PER_SEC) / 1000.0;
          Serial.print("L:");
          Serial.print(rawDuration);
          Serial.print(" ms (Adjusted: ");
          Serial.print(adjustedDuration);
          Serial.print(" ms) | Length: ");
          Serial.print(measuredLength, 2);
          Serial.println(" in (Scan Phase)");
        } else if (currentMode == CONTINUOUS) {
          float measuredLength = (rawDuration * CONVEYOR_SPEED_IN_PER_SEC) / 1000.0;
          Serial.print("L:");
          Serial.print(rawDuration);
          Serial.print(" ms | Length: ");
          Serial.print(measuredLength, 2);
          Serial.println(" in (Continuous)");
        }

        Serial.println("READY_FOR_NEXT_SCAN");
      }
      lastStableIrState = currentIrState;
    }
  }
}

// ---------------- Serial Commands ----------------
void checkSerialCommands() {
  // Process commands with rate limiting to prevent overflow
  static unsigned long lastCommandTime = 0;
  const unsigned long COMMAND_INTERVAL = 10; // Minimum 10ms between commands
  
  if (millis() - lastCommandTime < COMMAND_INTERVAL) {
    return; // Too soon, skip processing
  }
  
  // Process only one command per call to prevent blocking
  if (Serial.available() > 0) {
    char command[48]; // Reduced from 64 to 48 bytes to save memory
    int len = Serial.readBytesUntil('\n', command, sizeof(command) - 1);
    command[len] = '\0'; // Null terminate
    
    // Skip empty commands
    if (len == 0) return;
    
    // Trim whitespace manually
    while (len > 0 && (command[len-1] == ' ' || command[len-1] == '\r')) {
      command[--len] = '\0';
    }
    
    // Skip if command is now empty after trimming
    if (len == 0) return;
    
    // Process the command
    processCommand(command, len);
    lastCommandTime = millis();
    
    // Clear any remaining buffer to prevent overflow
    if (Serial.available() > 100) { // If buffer is getting too full
      while (Serial.available() > 0) {
        Serial.read(); // Clear excess data
      }
      Serial.println(F("BUFFER_CLEARED"));
    }
  }
}

void processCommand(char* command, int len) {
    // Handle single character commands (existing functionality)
    if (len == 1) {
      char cmd = command[0];
      switch (cmd) {
        case '1': activateAllServoGates(90); break;
        case '2':
          // Grouped servo movement - Command 1
            servo1.write(90);
            servo2.write(108);
            delay(250);
            servo3.write(25);
            servo4.write(25);
            break;
        case '3': 
          // Grouped servo movement - Command 3
          servo1.write(90);
          servo2.write(100);
          delay(250);
          servo3.write(155);
          servo4.write(155);
          break;
        case '0': activateAllServoGates(0); break;
        case 'C':
          if (!systemPaused) {
            currentMode = CONTINUOUS;
            digitalWrite(STEPPER_ENA_PIN, LOW);
            Serial.println(F("Mode: CONTINUOUS"));
          } else {
            Serial.println(F("ERROR: System paused"));
          }
          break;
        case 'T': 
          if (!systemPaused) {
            currentMode = TRIGGER; 
          } else {
            Serial.println(F("ERROR: System paused"));
          }
          break;
        case 'S':
          previousMode = currentMode; // Store previous mode
          if (!systemPaused) {
            currentMode = SCAN_PHASE;
            scanInProgress = false;
            waitingForBeam = true;
            currentSegment = 0;
            Serial.println(F("Mode: SCAN_PHASE"));
          } else {
            Serial.println(F("ERROR: System paused"));
          }
          break;
        case 'X':
          previousMode = currentMode; // Store previous mode
          currentMode = IDLE;
          systemPaused = false; // Allow IDLE to clear pause state
          manualInspectionRequired = false;
          errorRecoveryActive = false;
          activateAllServoGates(90);
          scanInProgress = false;
          waitingForBeam = false;
          digitalWrite(STEPPER_ENA_PIN, HIGH);
          Serial.println(F("Mode: IDLE"));
          break;
        case 'R': // Reject command for manual inspection
          if (manualInspectionRequired) {
            handleRejectAction();
          }
          break;
        case '?': // Status query command
          reportSystemStatus();
          break;
      }
    }
    // Handle multi-character error commands from Python
    else if (strncmp(command, "ERROR:", 6) == 0) {
      handleErrorCommand(command);
    }
    else if (strncmp(command, "CLEAR_ERROR:", 12) == 0) {
      handleClearErrorCommand(command);
    }
    else if (strcmp(command, "PAUSE_SYSTEM") == 0) {
      pauseSystemForError("Manual pause");
    }
    else if (strcmp(command, "RESUME_SYSTEM") == 0) {
      resumeSystemFromError();
    }
    else if (strcmp(command, "MANUAL_INSPECTION_COMPLETE") == 0) {
      handleManualInspectionComplete();
    }
    else if (strncmp(command, "RECOVER_MODE:", 13) == 0) {
      handleModeRecovery(command);
    }
    else if (strcmp(command, "STATUS_REQUEST") == 0) {
      reportSystemStatus();
    }
}

// ---------------- Error Handling Functions ----------------
void handleSystemPause() {
  // FIRST: Check if system is not actually paused anymore
  if (!systemPaused) {
    return; // Exit immediately if pause state has been cleared
  }
  
  // SECOND: Check if error type has been cleared (indicates cleared error)
  if (strlen(lastErrorType) == 0) {
    // Error has been cleared, force clear pause state
    systemPaused = false;
    manualInspectionRequired = false;
    errorRecoveryActive = false;
    Serial.println("STATUS_CLEARED: Error state cleared, resuming normal operations");
    return;
  }
  
  // Stop all motion during system pause
  digitalWrite(STEPPER_ENA_PIN, HIGH); // Disable stepper
  
  // Check if pause timeout exceeded (safety measure)
  if (millis() - errorPauseStartTime > 300000) { // 5 minutes
    Serial.println("ERROR_TIMEOUT: Automatic safety shutdown after 5 minutes");
    currentMode = IDLE;
    systemPaused = false;
    manualInspectionRequired = false;
    strncpy(lastErrorType, "", sizeof(lastErrorType) - 1);
    lastErrorType[0] = '\0'; // Clear error type
    return;
  }
  
  // Send periodic status updates (only if we still have an active error)
  static unsigned long lastStatusUpdate = 0;
  
  // CRITICAL FIX: Reset timer when error state changes
  static char lastReportedError[20] = "";
  if (strcmp(lastReportedError, lastErrorType) != 0) {
    // Error type changed, reset timer and update tracking
    strncpy(lastReportedError, lastErrorType, sizeof(lastReportedError) - 1);
    lastReportedError[sizeof(lastReportedError) - 1] = '\0';
    lastStatusUpdate = 0; // Reset timer for new error type
  }
  
  if (millis() - lastStatusUpdate > 10000) { // Every 10 seconds
    lastStatusUpdate = millis();
    Serial.print("STATUS_PAUSED: ");
    Serial.print(lastErrorType);
    if (manualInspectionRequired) {
      Serial.println(" - Manual inspection required");
    } else {
      Serial.println(" - Waiting for error resolution");
    }
  }
}

void pauseScanPhaseForError() {
  // Immediately stop conveyor motion
  digitalWrite(STEPPER_ENA_PIN, HIGH);
  
  // Send pause notification
  Serial.println("SCAN_PAUSED: Error detected during scan phase");
  
  // Save current scan state for potential resume
  if (scanInProgress) {
    Serial.print("SCAN_STATE: Segment ");
    Serial.print(currentSegment + 1);
    Serial.print(" of ");
    Serial.println(NUM_SEGMENTS);
  }
}

void pauseSystemForError(const char* errorType) {
  systemPaused = true;
  errorPauseStartTime = millis();
  strncpy(lastErrorType, errorType, sizeof(lastErrorType) - 1);
  lastErrorType[sizeof(lastErrorType) - 1] = '\0'; // Ensure null termination
  
  // Stop all motion immediately
  digitalWrite(STEPPER_ENA_PIN, HIGH);
  
  Serial.print("SYSTEM_PAUSED: ");
  Serial.println(errorType);
}

void resumeSystemFromError() {
  // Force clear all error states when explicitly requested
  systemPaused = false;
  manualInspectionRequired = false;
  errorRecoveryActive = false;
  
  // Clear the last error type
  strncpy(lastErrorType, "", sizeof(lastErrorType) - 1);
  lastErrorType[0] = '\0'; // Ensure empty string
  
  Serial.println("SYSTEM_RESUMED: All errors cleared, resuming operations");
  
  // Resume scan phase if it was in progress
  if (currentMode == SCAN_PHASE && scanInProgress) {
    Serial.println("SCAN_RESUMED: Continuing scan phase");
    digitalWrite(STEPPER_ENA_PIN, LOW);
  }
  else if (currentMode == CONTINUOUS || currentMode == TRIGGER) {
    // Re-enable stepper for active modes
    digitalWrite(STEPPER_ENA_PIN, LOW);
    Serial.println("STEPPER_RESUMED: Motor re-enabled for active mode");
  }
}

void handleErrorCommand(const char* command) {
  // Parse error command: "ERROR:ERROR_TYPE:Description"
  const char* firstColon = strchr(command + 6, ':'); // After "ERROR:"
  if (firstColon != NULL) {
    int errorTypeLen = firstColon - (command + 6);
    char errorType[20];  // Increased from 16 to 20
    strncpy(errorType, command + 6, min(errorTypeLen, 19));
    errorType[min(errorTypeLen, 19)] = '\0';
    
    // Extract description but limit its length to prevent truncation
    const char* description = firstColon + 1;
    
    Serial.print(F("ERROR_RECEIVED: "));
    Serial.print(errorType);
    Serial.print(F(" - "));
    
    // Limit description to prevent serial buffer overflow
    char shortDesc[30];
    strncpy(shortDesc, description, 29);
    shortDesc[29] = '\0';
    Serial.println(shortDesc);
    
    // Handle different error types
    if (strcmp(errorType, "CAMERA_DISCONNECTED") == 0 || 
        strcmp(errorType, "ARDUINO_DISCONNECTED") == 0 ||
        strcmp(errorType, "RESOURCE_EXHAUSTION") == 0 ||
        strcmp(errorType, "MODEL_LOADING_FAILED") == 0) {
      pauseSystemForError(errorType);
    }
    else if (strcmp(errorType, "NO_WOOD_DETECTED") == 0 ||
             strcmp(errorType, "LOW_CONFIDENCE_DETECTION") == 0 ||
             strcmp(errorType, "PLANK_MISALIGNMENT") == 0) {
      // These might not require immediate pause, but log them
      Serial.print(F("WARNING: "));
      Serial.println(errorType);
    }
    else if (strcmp(errorType, "MANUAL_INSPECTION_REQUIRED") == 0) {
      manualInspectionRequired = true;
      pauseSystemForError(errorType);
      Serial.println(F("MANUAL_INSPECTION: Operator intervention required"));
    }
  }
}

void handleClearErrorCommand(const char* command) {
  // Parse clear error command: "CLEAR_ERROR:ERROR_TYPE"
  const char* errorType = command + 12; // After "CLEAR_ERROR:"
  
  Serial.print(F("ERROR_CLEARED: "));
  Serial.println(errorType);
  
  // IMMEDIATELY clear ALL error states - no conditions
  systemPaused = false;
  manualInspectionRequired = false;
  errorRecoveryActive = false;
  
  // Clear the last error type completely
  strncpy(lastErrorType, "", sizeof(lastErrorType) - 1);
  lastErrorType[0] = '\0'; // Ensure empty string
  
  // Send immediate confirmation that system is resumed
  Serial.println(F("STATUS_RESUMED: Error cleared, operations continuing"));
  
  // Re-enable stepper if we're in an active mode
  if (currentMode == CONTINUOUS || currentMode == TRIGGER) {
    digitalWrite(STEPPER_ENA_PIN, LOW);
    Serial.println(F("STEPPER_RESUMED: Motor re-enabled"));
  }
  else if (currentMode == SCAN_PHASE && scanInProgress) {
    digitalWrite(STEPPER_ENA_PIN, LOW);
    Serial.println(F("SCAN_RESUMED: Continuing scan phase"));
  }
}

void handleManualInspectionComplete() {
  manualInspectionRequired = false;
  
  if (!systemPaused) {
    Serial.println("MANUAL_INSPECTION_COMPLETE: Resuming operations");
    
    // Resume scan if it was in progress
    if (currentMode == SCAN_PHASE && scanInProgress) {
      digitalWrite(STEPPER_ENA_PIN, LOW);
      Serial.println("SCAN_RESUMED: Manual inspection complete");
    }
  } else {
    Serial.println("MANUAL_INSPECTION_COMPLETE: System still paused for other errors");
  }
}

void handleModeRecovery(const char* command) {
  // This function is now simplified - no auto-recovery to SCAN mode
  // Extract mode from RECOVER_MODE:mode format
  const char* colonPtr = strchr(command, ':');
  if (colonPtr != NULL) {
    const char* mode = colonPtr + 1;
    
    // Only allow setting to IDLE mode for cleanup purposes
    if (strcmp(mode, "IDLE") == 0) {
      currentMode = IDLE;
      scanActive = false;
      reconnectionRecovery = false;
      Serial.println(F("RECOVERY:MODE_SET_TO_IDLE"));
      Serial.println(F("STATUS:IDLE_MODE"));
    }
    else {
      // Don't automatically recover to SCAN - let user restart manually
      Serial.println(F("RECOVERY:MANUAL_RESTART_RECOMMENDED"));
      Serial.println(F("STATUS:RECONNECTED_AWAITING_USER_INPUT"));
    }
  }
}

void reportSystemStatus() {
  // Report current system state to Python
  Serial.print("SYSTEM_STATUS:");
  Serial.print("mode=");
  Serial.print(currentMode);
  Serial.print(",scan=");
  Serial.print(scanActive ? "true" : "false");
  Serial.print(",paused=");
  Serial.print(systemPaused ? "true" : "false");
  Serial.print(",previous=");
  Serial.print(previousMode);
  Serial.print(",recovery=");
  Serial.println(reconnectionRecovery ? "true" : "false");
}

void handleRejectAction() {
  // Handle reject action during manual inspection
  Serial.println("REJECT_ACTION: Wood piece rejected by operator");
  
  // Route to reject bin (adjust servo angles as needed for your setup)
  activateAllServoGates(135); // Redirect to reject
  delay(2000); // Give time for wood to be routed
  activateAllServoGates(90);  // Return to normal position
  
  // Complete manual inspection
  manualInspectionRequired = false;
  
  // Clear scan state and prepare for next piece
  scanInProgress = false;
  waitingForBeam = true;
  currentSegment = 0;
  
  Serial.println("REJECT_COMPLETE: Ready for next wood piece");
}

// ---------------- Servo Control ----------------
void activateAllServoGates(int angle) {
  servo1.write(angle);
  servo2.write(angle);
  servo3.write(angle);
  servo4.write(angle);
}
