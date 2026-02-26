#include <HX711.h>

// Pinos
#define pinDT  2
#define pinSCK 3

// Configurações
#define pesoMax 5000        // máximo de 5000 g (5 kg)
#define escala -376600.0f   // fator de calibração encontrado

// HX711
HX711 scale;

void setup() {
  Serial.begin(57600);
  scale.begin(pinDT, pinSCK);
  scale.set_scale(escala);
  delay(2000);
  scale.tare();   // Zera no início
}

void loop() {
  // ===== Leitura rápida do HX711 =====
  float medida = scale.get_units();         // em kg
  long medida_g = (long)(medida * 1000.0);  // converte para gramas

  // ===== Proteção contra valores fora da faixa =====
  if (medida_g > pesoMax) {
    medida_g = 0;
    scale.tare();
  }

  // ===== Tara manual via comando Serial =====
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 't' || c == 'T') {
      scale.tare();
      medida_g = 0;
    }
  }

  // ===== Saída para Serial Plotter =====
  Serial.println(medida_g);

  delay(100); // atualiza a cada 0,1 s
}
