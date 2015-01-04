// Copyright 2014 Julian Metzler

/*
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

// Pin configuration for UNO test board
/*#define PIN_ROW_A 2
#define PIN_ROW_B 3
#define PIN_ROW_C 7
#define PIN_ROW_D 4
#define PIN_ROW_E 8
#define PIN_ROW_F 11
#define PIN_ROW_G 12
#define PIN_ROW_H 13
#define PIN_OUTPUT_DISABLE 10
#define PIN_DATA 9
#define PIN_SRCLK 6
#define PIN_ORCLK 5
#define PIN_STOP_INDICATOR 14 // Analog In 0*/

// Pin configuration for NANO controller board
#define PIN_ROW_A 7
#define PIN_ROW_B 8
#define PIN_ROW_C 5
#define PIN_ROW_D 9
#define PIN_ROW_E 6
#define PIN_ROW_F 3
#define PIN_ROW_G 2
#define PIN_ROW_H 4
#define PIN_OUTPUT_DISABLE 10
#define PIN_DATA 13
#define PIN_SRCLK 11
#define PIN_ORCLK 12
#define PIN_STOP_INDICATOR 14 // Analog In 0*/

// The baudrate to use for the serial port
#define BAUDRATE 115200

// The number of LED matrix modules connected to the controller (= The number of columns divided by 8)
#define NUM_BLOCKS 15

// The maximum number of blocks that a message may consist of
#define MAX_BLOCK_COUNT 200

// The number of microseconds that should be waited for bitmap data until a timeout error is returned
#define BITMAP_READ_TIMEOUT 1000

enum displayModes {
  DISP_MODE_STATIC,
  DISP_MODE_SCROLL
};

enum scrollDirections {
  SCROLL_LEFT,
  SCROLL_RIGHT
};

enum scrollModes {
  SCROLL_MODE_REPEAT_ON_END,
  SCROLL_MODE_REPEAT_ON_DISAPPEARANCE,
  SCROLL_MODE_REPEAT_AFTER_GAP
};

byte curDispData[MAX_BLOCK_COUNT + NUM_BLOCKS][8]; // + NUM_BLOCKS as a backup space for scrollMode REPEAT_ON_DISAPPEARANCE

int curScrollPos = 0;
int curScrollFrame = 0;
int curBlinkFrame = 0;
int curDispDataBlockCount = NUM_BLOCKS;
int curDispMode = DISP_MODE_STATIC;
int curScrollDir = SCROLL_LEFT;
int curScrollSpeed = 1;
int curScrollMode = SCROLL_MODE_REPEAT_ON_DISAPPEARANCE;
int curScrollGap = 5;
int scrollWidth = NUM_BLOCKS;
int curBlinkFrequency = -1;
bool curBlinkState = true;
bool isOn = false;
bool wasOn = false;
bool stopIndicatorOn = false;

void clearDisplayData() {
  memset(curDispData, 0, sizeof curDispData);
}

void writeAllLow() {
  digitalWrite(PIN_ROW_A, LOW);
  digitalWrite(PIN_ROW_B, LOW);
  digitalWrite(PIN_ROW_C, LOW);
  digitalWrite(PIN_ROW_D, LOW);
  digitalWrite(PIN_ROW_E, LOW);
  digitalWrite(PIN_ROW_F, LOW);
  digitalWrite(PIN_ROW_G, LOW);
  digitalWrite(PIN_ROW_H, LOW);
  digitalWrite(PIN_OUTPUT_DISABLE, LOW);
  digitalWrite(PIN_DATA, LOW);
  digitalWrite(PIN_SRCLK, LOW);
  digitalWrite(PIN_ORCLK, LOW);
}

void setStopIndicator(bool state) {
  stopIndicatorOn = state;
  digitalWrite(PIN_STOP_INDICATOR, state);
}

int getPinForRow(int row) {
  if(row < 0) {
    row += 8;
  }
  row %= 8;
  switch(row) {
    case 0:
      return PIN_ROW_A;
    case 1:
      return PIN_ROW_B;
    case 2:
      return PIN_ROW_C;
    case 3:
      return PIN_ROW_D;
    case 4:
      return PIN_ROW_E;
    case 5:
      return PIN_ROW_F;
    case 6:
      return PIN_ROW_G;
    case 7:
      return PIN_ROW_H;
    default:
      return PIN_ROW_A;
  }
}

void modifyValue(int* variable, int value, int min, int max) {
  *variable += value;
  
  while(*variable < min) {
    *variable += (max - min);
  }
  
  while(*variable > max) {
    *variable -= (max - min);
  }
}

void updateScrollWidth() {
  scrollWidth = curDispDataBlockCount;
  
  switch(curScrollMode) {
    case SCROLL_MODE_REPEAT_ON_END:
      scrollWidth = scrollWidth < NUM_BLOCKS ? NUM_BLOCKS : scrollWidth;
      break;
    
    case SCROLL_MODE_REPEAT_ON_DISAPPEARANCE:
      scrollWidth += NUM_BLOCKS;
      break;
    
    case SCROLL_MODE_REPEAT_AFTER_GAP:
      scrollWidth += curScrollGap;
      scrollWidth = scrollWidth < NUM_BLOCKS ? NUM_BLOCKS : scrollWidth;
      break;
  }
}

void clearSerialBuffer() {
  while(Serial.available() > 0) {
    Serial.read();
  }
}

void doSerialCommunication() {
  /*
  SERIAL PROTOCOL
  
  <0xFF> - Start byte
  
  <1 byte> - Type of message
    <0xA0> - Send a display bitmap
    <0xA1> - Set the display mode (Scrolling / Static)
    <0xA2> - Set the scroll speed (frame interval)
    <0xA3> - Set the scroll direction (left / right)
    <0xA4> - Set the scroll mode (repeat on visibility of end / repeat on disappearance / repeat after gap)
    <0xA5> - Set the scroll gap
    <0xA6> - Enable / disable display
    <0xA7> - Set blink frequency
    <0xA8> - Enable / disable stop indicator
  
  <0xCC> - Intermediate byte
  
  If sending a bitmap:
    <1 byte> - Block count of the following bitmap
    <0xCC> - Intermediate byte
    <data> - Bitmap data
  
  Otherwise:
    <1 byte> - Value of the selected option
  
  
  
  RESPONSE VALUES
  
  <0xE0> - Invalid action byte
  <0xE1> - Invalid intermediate byte #1
  <0xE2> - Invalid block count
  <0xE3> - Invalid intermediate byte #2
  <0xE4> - Timeout while receiving bitmap data
  <0xE5> - Invalid bitmap data
  <0xE6> - Invalid value for selected option
  <0xFF> - Serial communication successful
  */
  
  if(Serial.available() > 0) {
    // Check start byte
    int startByte = 0x00;
    while(Serial.available() > 0) {
      startByte = Serial.read();
      if(startByte == 0xFF) {
        break;
      }
    }
    
    if(startByte != 0xFF) {
      // No error, just discard
      return;
    }
    
    // Check action byte
    int actionByte = Serial.read();
    switch(actionByte) {
      case 0xA0:
        // Send bitmap data
        break;
      
      case 0xA1:
        // Set display mode
        break;
      
      case 0xA2:
        // Set scroll speed
        break;
      
      case 0xA3:
        // Set scroll direction
        break;
      
      case 0xA4:
        // Set scroll mode
        break;
      
      case 0xA5:
        // Set scroll gap
        break;
      
      case 0xA6:
        // Enable / disable display
        break;
      
      case 0xA7:
        // Set blink frequency
        break;
      
      case 0xA8:
        // Enable / disable stop indicator
        break;
      
      default:
        // Error 0: Invalid action byte
        clearSerialBuffer();
        Serial.write(0xE0);
        return;
    }
    
    // Check intermediate byte #1
    int intermediateByte = Serial.read();
    if(intermediateByte != 0xCC) {
      // Error 1: Invalid intermediate byte #1
      clearSerialBuffer();
      Serial.write(0xE1);
      return;
    }
    
    int blockCount;
    int columnCount;
    int valueByte;
    switch(actionByte) {
      case 0xA0:
        // Send bitmap data
        
        // Check block count
        blockCount = Serial.read();
        
        if(blockCount <= 0 || blockCount > MAX_BLOCK_COUNT) {
          // Error 2: Invalid block count
          clearSerialBuffer();
          Serial.write(0xE2);
          return;
        }
        
        // Check intermediate byte #2
        intermediateByte = Serial.read();
        if(intermediateByte != 0xCC) {
          // Error 3: Invalid intermediate byte #2
          clearSerialBuffer();
          Serial.write(0xE3);
          return;
        }
        
        // Clear the previous display data and receive the new data
        curDispDataBlockCount = blockCount;
        clearDisplayData();
        digitalWrite(PIN_OUTPUT_DISABLE, HIGH); // To prevent the high LED current from flowing through a single row for too long
        for(int block = 0; block < blockCount; block++) {
          for(int idx = 0; idx < 8; idx++) {
            // Wait for data in case the buffer is empty earlier than it should be
            // But prevent an endless loop by setting a timeout
            if(Serial.available() <= 0) {
              unsigned long bufEmptyStart = micros();
              bool timeoutHit = false;
              while(Serial.available() <= 0 && !timeoutHit) {
                // Idle as long as the timeout hasn't been hit and no data is in the buffer
                unsigned long timeElapsed = micros() - bufEmptyStart;
                timeoutHit = timeElapsed >= BITMAP_READ_TIMEOUT || timeElapsed < 0; // < 0 in case the micros rolled over to zero
              }
              
              if(timeoutHit) {
                // Error 4: Timeout while receiving bitmap data
                // Discard data that has already been received
                clearDisplayData();
                clearSerialBuffer();
                digitalWrite(PIN_OUTPUT_DISABLE, LOW);
                Serial.write(0xE4);
                return;
              }
            }
            
            // Read bitmap byte
            int curByte = Serial.read();
            if(curByte < 0x00 || curByte > 0xFF) {
              // Error 5: Invalid bitmap data
              // Discard data that has already been received
              clearDisplayData();
              clearSerialBuffer();
              digitalWrite(PIN_OUTPUT_DISABLE, LOW);
              Serial.write(0xE5);
              return;
            }
            curDispData[block][idx] = (byte) curByte;
          }
        }
        
        digitalWrite(PIN_OUTPUT_DISABLE, LOW);
        updateScrollWidth();
        break;
      
      case 0xA1:
        // Set display mode
        valueByte = Serial.read();
        switch(valueByte) {
          case 0x00:
            // Static
            curDispMode = DISP_MODE_STATIC;
            curScrollPos = 0;
            break;
          
          case 0x01:
            // Scrolling
            curDispMode = DISP_MODE_SCROLL;
            break;
          
          default:
            // Error 6: Invalid value for selected option
            clearSerialBuffer();
            Serial.write(0xE6);
            return;
        }
        break;
      
      case 0xA2:
        // Set scroll speed
        valueByte = Serial.read();
        // Check value
        if(valueByte < 0x01 || valueByte > 0xFF) {
          // Error 6: Invalid value for selected option
          clearSerialBuffer();
          Serial.write(0xE6);
          return;
        }
        curScrollSpeed = valueByte;
        break;
      
      case 0xA3:
        // Set scroll direction
        valueByte = Serial.read();
        switch(valueByte) {
          case 0x00:
            // Left
            curScrollDir = SCROLL_LEFT;
            break;
          
          case 0x01:
            // Right
            curScrollDir = SCROLL_RIGHT;
            break;
          
          default:
            // Error 6: Invalid value for selected option
            clearSerialBuffer();
            Serial.write(0xE6);
            return;
        }
        break;
      
      case 0xA4:
        // Set scroll mode
        valueByte = Serial.read();
        switch(valueByte) {
          case 0x00:
            // Repeat on visibility of end
            curScrollMode = SCROLL_MODE_REPEAT_ON_END;
            break;
          
          case 0x01:
            // Repeat on disappearance
            curScrollMode = SCROLL_MODE_REPEAT_ON_DISAPPEARANCE;
            break;
          
          case 0x02:
            // Repeat after a gap of a specified length
            curScrollMode = SCROLL_MODE_REPEAT_AFTER_GAP;
            break;
          
          default:
            // Error 6: Invalid value for selected option
            clearSerialBuffer();
            Serial.write(0xE6);
            return;
        }
        updateScrollWidth();
        break;
      
      case 0xA5:
        // Set scroll gap
        valueByte = Serial.read();
        // Check value
        if(valueByte < 0x00 || valueByte > NUM_BLOCKS) {
          // Error 6: Invalid value for selected option
          clearSerialBuffer();
          Serial.write(0xE6);
          return;
        }
        curScrollGap = valueByte;
        updateScrollWidth();
        break;
      
      case 0xA6:
        // Enable / disable display
        valueByte = Serial.read();
        switch(valueByte) {
          case 0x00:
            // Off
            isOn = false;
            break;
          
          case 0x01:
            // On
            isOn = true;
            break;
          
          default:
            // Error 6: Invalid value for selected option
            clearSerialBuffer();
            Serial.write(0xE6);
            return;
        }
        break;
      
      case 0xA7:
        // Set blink frequency
        valueByte = Serial.read();
        // Check value
        if(valueByte < 0x00 || valueByte > 0xFF) {
          // Error 6: Invalid value for selected option
          clearSerialBuffer();
          Serial.write(0xE6);
          return;
        }
        
        if(valueByte == 0x00) {
          curBlinkFrequency = -1;
          curBlinkState = true;
          curBlinkFrame = 0;
          digitalWrite(PIN_OUTPUT_DISABLE, LOW);
        } else {
          curBlinkFrequency = valueByte;
        }
        
        break;
      
      case 0xA8:
        // Enable / disable stop indicator
        valueByte = Serial.read();
        switch(valueByte) {
          case 0x00:
            // Off
            setStopIndicator(false);
            break;
          
          case 0x01:
            // On
            setStopIndicator(true);
            break;
          
          default:
            // Error 6: Invalid value for selected option
            clearSerialBuffer();
            Serial.write(0xE6);
            return;
        }
        break;
    }
    
    // Serial communication successful
    clearSerialBuffer();
    Serial.write(0xFF);
  }
}

void writeArrayStatic(byte array[][8]) {
  for(int row = 0; row < 8; row++) {
    for(int block = NUM_BLOCKS - 1; block >= 0; block--) {
      for(byte mask = 1; mask > 0; mask <<= 1) {
        digitalWrite(PIN_DATA, array[block][row] & mask);
        digitalWrite(PIN_SRCLK, HIGH);
        digitalWrite(PIN_SRCLK, LOW);
      }
    }
    
    digitalWrite(getPinForRow(row - 1), LOW);
    
    digitalWrite(PIN_ORCLK, HIGH);
    digitalWrite(PIN_ORCLK, LOW);
    
    doSerialCommunication();
    
    digitalWrite(getPinForRow(row), HIGH);
  }
  
  if(curBlinkFrequency > 0) {
    curBlinkFrame++;
    if(curBlinkFrame >= curBlinkFrequency) {
      curBlinkFrame = 0;
      curBlinkState = !curBlinkState;
      digitalWrite(PIN_OUTPUT_DISABLE, curBlinkState);
    }
  }
}

void writeArrayScrolling(byte array[][8], int interval = 1, int scrollDirection = SCROLL_LEFT) {
  // interval is the number of times a frame should be written until it is scrolled
   
  for(int row = 0; row < 8; row++) {
    for(int block = NUM_BLOCKS - 1; block >= 0; block--) {
      int blockOffset = curScrollPos / 8;
      int maskOffset = curScrollPos % 8;
      int blockOffsetOffset = 0;
      for(int maskPos = 0; maskPos < 8; maskPos++) {
        byte mask = 1;
        int actualMaskPos = maskPos + maskOffset;
        if(actualMaskPos >= 8) {
          actualMaskPos -= 8;
          blockOffsetOffset = 1;
        } else {
          blockOffsetOffset = 0;
        }
        mask <<= actualMaskPos;
        int blockPos = block - blockOffset - blockOffsetOffset;
        digitalWrite(PIN_DATA, array[blockPos < 0 ? blockPos + scrollWidth : blockPos][row] & mask);
        digitalWrite(PIN_SRCLK, HIGH);
        digitalWrite(PIN_SRCLK, LOW);
      }
    }
    
    digitalWrite(getPinForRow(row - 1), LOW);
    
    digitalWrite(PIN_ORCLK, HIGH);
    digitalWrite(PIN_ORCLK, LOW);
    
    doSerialCommunication();
    
    digitalWrite(getPinForRow(row), HIGH);
  }
  
  curScrollFrame++;
  if(curScrollFrame >= interval) {
    curScrollFrame = 0;
    
    if(scrollDirection == SCROLL_RIGHT) {
      modifyValue(&curScrollPos, 1, 0, scrollWidth * 8);
    } else if(scrollDirection == SCROLL_LEFT) {
      modifyValue(&curScrollPos, -1, 0, scrollWidth * 8);
    }
  }
  
  if(curBlinkFrequency > 0) {
    curBlinkFrame++;
    if(curBlinkFrame >= curBlinkFrequency) {
      curBlinkFrame = 0;
      curBlinkState = !curBlinkState;
      digitalWrite(PIN_OUTPUT_DISABLE, curBlinkState);
    }
  }
}

void setup() {
  clearDisplayData();
  
  pinMode(PIN_ROW_A, OUTPUT);
  pinMode(PIN_ROW_B, OUTPUT);
  pinMode(PIN_ROW_C, OUTPUT);
  pinMode(PIN_ROW_D, OUTPUT);
  pinMode(PIN_ROW_E, OUTPUT);
  pinMode(PIN_ROW_F, OUTPUT);
  pinMode(PIN_ROW_G, OUTPUT);
  pinMode(PIN_ROW_H, OUTPUT);
  pinMode(PIN_OUTPUT_DISABLE, OUTPUT);
  pinMode(PIN_DATA, OUTPUT);
  pinMode(PIN_SRCLK, OUTPUT);
  pinMode(PIN_ORCLK, OUTPUT);
  pinMode(PIN_STOP_INDICATOR, OUTPUT);
  
  writeAllLow();
  setStopIndicator(stopIndicatorOn);
  
  Serial.begin(BAUDRATE);
}

void loop() {
  if(!wasOn && isOn) {
    wasOn = isOn;
  } else if(wasOn && !isOn) {
    writeAllLow();
    wasOn = isOn;
  }
  
  if(isOn) {
    if(curDispMode == DISP_MODE_STATIC) {
      writeArrayStatic(curDispData);
    } else if(curDispMode == DISP_MODE_SCROLL) {
      writeArrayScrolling(curDispData, curScrollSpeed, curScrollDir);
    }
  } else {
    doSerialCommunication();
    delay(25);
  }
}
