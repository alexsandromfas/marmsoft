#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// UUIDs do Serviço e Característica BLE
#define SERVICE_UUID "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "abcdef01-1234-5678-1234-56789abcdef0"

// Pinos dos FSR Sensors (4 sensores)
const int fsrPins[4] = {36, 39, 34, 35};

// Pinos dos Flex Sensors (8 sensores)
const int flexPins[8] = {32, 33, 25, 26, 27, 14, 12, 13};

// Pino do LED (GPIO2)
const int ledPin = 2;

BLECharacteristic *pCharacteristic;

// Callbacks para o servidor BLE
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *pServer) {
    Serial.println("Dispositivo conectado.");
  }

  void onDisconnect(BLEServer *pServer) {
    Serial.println("Dispositivo desconectado.");
    BLEDevice::startAdvertising(); // Reinicia a publicidade BLE
  }
};

void setup() {
  Serial.begin(115200);

  // Configurar LED como saída e acender
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);

  // Inicializa o BLE
  BLEDevice::init("ESP32 Sensors");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());

  // Cria o serviço BLE
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Cria a característica BLE
  pCharacteristic = pService->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);

  // Adiciona um descritor para notificações
  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  // Inicia a publicidade BLE
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->start();

  Serial.println("Servidor BLE iniciado.");
}

void loop() {
  String data = "";

  // Lê os valores dos FSR Sensors
  for (int i = 0; i < 4; i++) {
    int sensorValue = analogRead(fsrPins[i]); // Leitura ADC
    float voltage = (sensorValue / 4095.0) * 3.3; // Conversão para tensão
    data += "FSR" + String(i + 1) + "=" + String(voltage, 2) + "V, ";
  }

  // Lê os valores dos Flex Sensors
  for (int i = 0; i < 8; i++) {
    int sensorValue = analogRead(flexPins[i]); // Leitura ADC
    float voltage = (sensorValue / 4095.0) * 3.3; // Conversão para tensão
    data += "FLEX" + String(i + 1) + "=" + String(voltage, 2) + "V, ";
  }

  // Remove a vírgula final do buffer de dados BLE, se existir
  if (data.endsWith(", ")) {
    data = data.substring(0, data.length() - 2);
  }

  // Envia os dados via BLE
  pCharacteristic->setValue(data.c_str());
  pCharacteristic->notify();

  // Imprime no monitor serial
  Serial.println(data);

  delay(50); // Aguarda 50ms antes da próxima leitura
}
