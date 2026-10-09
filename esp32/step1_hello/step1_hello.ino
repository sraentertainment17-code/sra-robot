/*
  SRA Robot — Step 1: Hello from the ESP32-S3
  Verifies: USB serial works, board is alive.
  Open Serial Monitor at 115200 baud — you should see the counter climbing.
*/
void setup() {
  Serial.begin(115200);
  delay(1000); // let the USB-CDC port come up
  Serial.println("\n=== SRA Robot Brain Online ===");
  Serial.println("ESP32-S3 N16R8 | PSRAM check next step");
}
int i = 0;
void loop() {
  Serial.printf("alive %d\n", i++);
  delay(1000);
}