#include <Servo.h>

// ------------------- STEPPER PINS -------------------
const int stepPin = 10;
const int dirPin  = 9;
const int enPin   = 8;

// ------------------- STEPPER SPEED SETTINGS -------------------
int minDelay = 3000;
int maxDelay = 1100;
int rampDelay = minDelay;
bool rampFinished = false;
bool stepperEnabled = true;

// ------------------- SENSOR PIN -------------------
const int sensorPin = 11;

// ------------------- SERVOS -------------------
Servo servo1;
Servo servo2;
Servo servo3;
Servo servo4;

// ------------------- SERVO ANGLES -------------------
// Command 1
const int CMD1_SERVO1 = 90;
const int CMD1_SERVO2 = 108;
const int CMD1_SERVO34 = 25;

// Command 3
const int CMD3_SERVO1 = 90;
const int CMD3_SERVO2 = 100;
const int CMD3_SERVO34 = 155;

const int ANGLE_CENTER = 90;

// ------------------- SERVO DELAY -------------------
const unsigned long SERVO_GROUP_DELAY = 500; // ms

// ------------------- TIMING -------------------
unsigned long lastStepTime = 0;

void setup() {
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(enPin, OUTPUT);
  digitalWrite(enPin, LOW);
  digitalWrite(dirPin, HIGH);

  pinMode(sensorPin, INPUT);

  servo1.attach(2);
  servo2.attach(3);
  servo3.attach(4);
  servo4.attach(5);

  moveAllServos(ANGLE_CENTER);

  Serial.begin(9600);
  Serial.println("=== SYSTEM READY ===");
  Serial.println("1 = S1:90° S2:95° → then S3&4:25°");
  Serial.println("2 = All Servos -> 90°");
  Serial.println("3 = S1:85° S2:90° → then S3&4:155°");
  Serial.println("B = Stepper Start | S = Stepper Stop");
}

void loop() {
  runStepper();
  readSensor();
  handleSerial();
}

// ------------------- STEPPER FUNCTION -------------------
void runStepper() {
  if (!stepperEnabled) return;

  unsigned long now = micros();
  if (now - lastStepTime >= rampDelay) {
    lastStepTime = now;

    digitalWrite(stepPin, HIGH);
    delayMicroseconds(2);
    digitalWrite(stepPin, LOW);

    if (!rampFinished) {
      if (rampDelay > maxDelay) rampDelay -= 2;
      else rampFinished = true;
    }
  }
}

// ------------------- SENSOR FUNCTION -------------------
void readSensor() {
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint > 300) {
    lastPrint = millis();
    Serial.println(digitalRead(sensorPin) == LOW ? "Beam broken!" : "Beam intact");
  }
}

// ------------------- SERIAL HANDLER -------------------
void handleSerial() {
  if (Serial.available()) {
    char cmd = Serial.read();

    switch (cmd) {
      case '1':
        moveCommand1();
        Serial.println("Command 1 executed");
        break;

      case '2':
        moveAllServos(ANGLE_CENTER);
        Serial.println("All Servos -> 90°");
        break;

      case '3':
        moveCommand3();
        Serial.println("Command 3 executed");
        break;

      case 'B':
        stepperEnabled = true;
        Serial.println("Stepper STARTED");
        break;

      case 'S':
        stepperEnabled = false;
        Serial.println("Stepper STOPPED");
        break;
    }
  }
}

// ------------------- SERVO CONTROL -------------------
void moveCommand1() {
  // First group: Servo 1 & 2 (different angles)
  servo1.write(CMD1_SERVO1);
  servo2.write(CMD1_SERVO2);

  delay(SERVO_GROUP_DELAY);

  // Second group: Servo 3 & 4
  servo3.write(CMD1_SERVO34);
  servo4.write(CMD1_SERVO34);
}

void moveCommand3() {
  // First group: Servo 1 & 2 (different angles)
  servo1.write(CMD3_SERVO1);
  servo2.write(CMD3_SERVO2);

  delay(SERVO_GROUP_DELAY);

  // Second group: Servo 3 & 4
  servo3.write(CMD3_SERVO34);
  servo4.write(CMD3_SERVO34);
}

void moveAllServos(int angle) {
  servo1.write(angle);
  servo2.write(angle);
  servo3.write(angle);
  servo4.write(angle);
}
