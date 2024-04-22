#include <Arduino.h>
#include <LilyGo_AMOLED.h>
#include <TFT_eSPI.h>
#include <ArduinoJson.h> // Include ArduinoJson library

TFT_eSPI tft = TFT_eSPI();
TFT_eSprite spr = TFT_eSprite(&tft);
LilyGo_Class amoled;

#define WIDTH  amoled.width()
#define HEIGHT amoled.height()
#define BAR_WIDTH (WIDTH * 0.5 - 20) // Width of the bar with padding on both sides
#define BAR_HEIGHT 20          // Height of the bar
#define BAR_X_OFFSET 40        // X offset of the bar
#define CPU_BAR_Y_OFFSET (HEIGHT / 4) // Y offset of the CPU bar with increased vertical space
#define GPU_BAR_Y_OFFSET (HEIGHT / 2 + HEIGHT / 4) // Y offset of the GPU bar
#define MARKER_HEIGHT 0        // Height of the markers
#define TEXT_SIZE 3            // Text size for temperature display
#define MARKER_TEXT_SIZE 2.5   // Text size for marker text
#define TEXT_PADDING 15        // Padding between text and temperature values
#define MARKER_PADDING 30      // Padding between marker and text
#define FAN_RECT_WIDTH 70      // Width of the fan rectangles
#define FAN_RECT_HEIGHT 70     // Height of the fan rectangles
#define FAN_RPM_TEXT_SIZE 2.5 // Text size for fan RPM display
#define FAN_BLADES 7           // Number of fan blades
#define SEGMENT_PADDING 2      // Padding between segments of the bar

int lastCpuTemp = 0; // Last received CPU temperature
int lastGpuTemp = 0; // Last received GPU temperature
int lastGpuFanRPM = 0; // Last received GPU fan RPM
int cpuFanSpeed = 30; // Rotation speed of CPU fan blades (in degrees per frame)

bool serialActive = false; // Flag to indicate if serial connection is active or not

// Positioning variables
int cpuTempX, cpuTempY;
int gpuTempX, gpuTempY;
int cpuTempBarX, cpuTempBarY;
int gpuTempBarX, gpuTempBarY;
int cpuFanRectX, cpuFanRectY;
int gpuFanRectX, gpuFanRectY;
int cpuFanRpmX, cpuFanRpmY;
int gpuFanRpmX, gpuFanRpmY;

void setup() {
    Serial.begin(9600);

    if (!amoled.begin()) {
        while (1) {
            Serial.println("There is a problem with the device!~");
            delay(1000);
        }
    }

    spr.createSprite(WIDTH, HEIGHT);
    spr.setSwapBytes(1);

    // Set initial positions for components
    cpuTempX = 10;
    cpuTempY = CPU_BAR_Y_OFFSET + (BAR_HEIGHT / 2) + TEXT_PADDING;
    gpuTempX = 10;
    gpuTempY = GPU_BAR_Y_OFFSET + (BAR_HEIGHT / 2) + TEXT_PADDING;
    cpuTempBarX = BAR_X_OFFSET;
    cpuTempBarY = CPU_BAR_Y_OFFSET - (BAR_HEIGHT / 2);
    gpuTempBarX = BAR_X_OFFSET;
    gpuTempBarY = GPU_BAR_Y_OFFSET - (BAR_HEIGHT / 2);
    
    // Align components with the right side of the screen
    cpuFanRectX = WIDTH - (WIDTH * 0.25) + ((WIDTH * 0.25 - FAN_RECT_WIDTH) / 2);
    cpuFanRectY = 0; // Align with the top of the screen
    gpuFanRectX = WIDTH - (WIDTH * 0.25) + ((WIDTH * 0.25 - FAN_RECT_WIDTH) / 2);
    gpuFanRectY = HEIGHT - FAN_RECT_HEIGHT - TEXT_SIZE * 15; // Align with the bottom of the screen, leaving space for text
    cpuFanRpmX = cpuFanRectX + (FAN_RECT_WIDTH - 70) / 2;
    cpuFanRpmY = cpuFanRectY + FAN_RECT_HEIGHT + 5;
    gpuFanRpmX = gpuFanRectX + (FAN_RECT_WIDTH - 70) / 2;
    gpuFanRpmY = gpuFanRectY + FAN_RECT_HEIGHT + TEXT_PADDING;
}

void drawFanBlades(int x, int y, int width, int height, float angle) {
    int cx = x + width / 2;
    int cy = y + height / 2;
    int radius = min(width, height) / 2 - 5;
    float angleStep = 2 * PI / FAN_BLADES;

    // Draw the circle in the middle
    spr.fillCircle(cx, cy, 5, TFT_WHITE);

    for (int i = 0; i < FAN_BLADES; i++) {
        float bladeAngle = angle + i * angleStep;
        float bladeTipX = cx + cos(bladeAngle) * (radius - 10); // Adjust the radius to bring tips closer
        float bladeTipY = cy + sin(bladeAngle) * (radius - 10); // Adjust the radius to bring tips closer
        float bladeBaseX = cx + cos(bladeAngle) * (radius - 30); // Adjust the base length as needed
        float bladeBaseY = cy + sin(bladeAngle) * (radius - 30); // Adjust the base length as needed

        // Calculate the points for the triangle
        float bladeTipX1 = bladeTipX - cos(bladeAngle + PI / 2) * 3; // Adjust triangle width as needed
        float bladeTipY1 = bladeTipY - sin(bladeAngle + PI / 2) * 3; // Adjust triangle width as needed
        float bladeTipX2 = bladeTipX + cos(bladeAngle + PI / 2) * 3; // Adjust triangle width as needed
        float bladeTipY2 = bladeTipY + sin(bladeAngle + PI / 2) * 3; // Adjust triangle width as needed

        // Draw the triangle
        spr.fillTriangle(bladeTipX1, bladeTipY1, bladeTipX2, bladeTipY2, bladeBaseX, bladeBaseY, TFT_WHITE);
    }
}

uint16_t getTemperatureColor(int temp) {
    if (temp <= 0) return TFT_BLACK;
    if (temp >= 100) return TFT_RED;
    int red = map(temp, 0, 100, 0, 255);
    int green = map(temp, 0, 100, 255, 0);
    return tft.color565(red, green, 0);
}

void drawTemperatureBar(int x, int y, int width, int height, int temperature, int padding) {
    uint16_t color = getTemperatureColor(temperature);
    int segmentWidth = (width - (9 * padding)) / 10; // 10 segments with 9 paddings between them
    for (int i = 0; i < 10; i++) {
        int xPos = x + i * (segmentWidth + padding);
        if (temperature >= (i + 1) * 10) { // Draw only if temperature is within this segment
            spr.fillRect(xPos, y, segmentWidth, height, color);
        }
    }
    spr.drawRect(x, y, width, height, TFT_WHITE);
}

void loop() {
    static String jsonBuffer = "";
    
    while (Serial.available() > 0) {
        char incomingByte = Serial.read();
        
        // Accumulate bytes until the end of JSON data
        if (incomingByte == '}') {
            jsonBuffer += incomingByte;
            
            // Parse JSON data
            DynamicJsonDocument doc(1024);
            deserializeJson(doc, jsonBuffer);
            
            // Extract values based on keys
            int newCpuTemp = doc["cpu_temp"];
            int newGpuTemp = doc["gpu_temp"];
            int newGpuFanRPM = doc["gpu_fan_rpm"];

            // Update last values
            lastCpuTemp = newCpuTemp;
            lastGpuTemp = newGpuTemp;
            lastGpuFanRPM = newGpuFanRPM;

            // Reset the JSON buffer
            jsonBuffer = "";

            serialActive = true;
        } else {
            // Append byte to the JSON buffer
            jsonBuffer += incomingByte;
        }
    }

    if (!serialActive) {
        // If serial connection is not active, display initial text
        spr.fillScreen(TFT_BLACK);
        spr.setTextSize(3);
        spr.setTextColor(TFT_YELLOW);
        spr.setTextDatum(MC_DATUM); // Center text horizontally and vertically
        spr.drawString("CATAPULTCASE", WIDTH / 2, HEIGHT / 2 - 20);
        amoled.pushColors(0, 0, WIDTH, HEIGHT, (uint16_t *)spr.getPointer());
        delay(100); // Delay for screen refresh
        return; // Exit loop early
    }

    // Clear the screen
    spr.fillSprite(TFT_BLACK);

    // Draw CPU and GPU temperature bars with padding
    drawTemperatureBar(BAR_X_OFFSET, CPU_BAR_Y_OFFSET - (BAR_HEIGHT / 2), BAR_WIDTH, BAR_HEIGHT, lastCpuTemp, SEGMENT_PADDING);
    drawTemperatureBar(BAR_X_OFFSET, GPU_BAR_Y_OFFSET - (BAR_HEIGHT / 2), BAR_WIDTH, BAR_HEIGHT, lastGpuTemp, SEGMENT_PADDING);

    // Draw temperature levels above the graphs
    for (int i = 0; i <= 100; i += 25) {
        int xPos = BAR_X_OFFSET + (i * BAR_WIDTH) / 100;
        spr.drawFastVLine(xPos, CPU_BAR_Y_OFFSET - MARKER_HEIGHT, MARKER_HEIGHT, TFT_WHITE);
        spr.drawFastVLine(xPos, GPU_BAR_Y_OFFSET - MARKER_HEIGHT, MARKER_HEIGHT, TFT_WHITE);
        spr.setTextSize(MARKER_TEXT_SIZE); // Set the text size for marker text
        spr.setCursor(xPos - 10, CPU_BAR_Y_OFFSET - MARKER_HEIGHT - MARKER_PADDING);
        spr.print(i);
        spr.print("C");
        spr.setCursor(xPos - 10, GPU_BAR_Y_OFFSET - MARKER_HEIGHT - MARKER_PADDING);
        spr.print(i);
        spr.print("C");
    }

    // Draw CPU Temperature Text
    spr.setTextSize(TEXT_SIZE);
    spr.setTextColor(TFT_WHITE);
    spr.setCursor(cpuTempX, cpuTempY);
    spr.print("CPU Temp: ");
    spr.print(lastCpuTemp);
    spr.print("C");

    // Draw GPU Temperature Text
    spr.setCursor(gpuTempX, gpuTempY);
    spr.print("GPU Temp: ");
    spr.print(lastGpuTemp);
    spr.print("C");

    // Draw CPU fan rectangle
    spr.drawRect(cpuFanRectX - 60, cpuFanRectY, FAN_RECT_WIDTH, FAN_RECT_HEIGHT, TFT_WHITE);

    // Draw GPU fan rectangle
    spr.drawRect(gpuFanRectX - 60, gpuFanRectY, FAN_RECT_WIDTH, FAN_RECT_HEIGHT, TFT_WHITE);

    // Draw fan blades with rotation
    float cpuFanAngle = millis() * (cpuFanSpeed / 1000.0);
    drawFanBlades(cpuFanRectX - 60, cpuFanRectY, FAN_RECT_WIDTH, FAN_RECT_HEIGHT, cpuFanAngle);
    float gpuFanAngle = millis() * (cpuFanSpeed / 1000.0);
    drawFanBlades(gpuFanRectX - 60, gpuFanRectY, FAN_RECT_WIDTH, FAN_RECT_HEIGHT, gpuFanAngle);

    // Draw "CPU RPM" text
    spr.setTextSize(FAN_RPM_TEXT_SIZE);
    spr.setTextColor(TFT_WHITE);
    spr.setCursor(cpuFanRpmX - 60, cpuFanRpmY);
    spr.print("CPU RPM: ");
    spr.print("N/A"); // Replace "SomeValue" with the actual value

    // Draw "GPU RPM" text beneath the GPU fan rectangle
    spr.setCursor(gpuFanRpmX - 60, gpuFanRpmY);
    spr.print("GPU RPM: ");
    spr.print(lastGpuFanRPM);

    // Push to display
    amoled.pushColors(0, 0, WIDTH, HEIGHT, (uint16_t *)spr.getPointer());

    // Delay for screen refresh
    delay(500);
}
