/*
 *   Q0481 - Balança com HX711 (sem botão)
 *   Adaptado para leitura contínua em gramas
 */

// INCLUSÃO DE BIBLIOTECAS
#include <HX711.h>

// DEFINIÇÕES DE PINOS
#define pinDT  2
#define pinSCK 3

// DEFINIÇÕES
#define pesoMin 0.010    // 0,010 kg = 10 g
#define pesoMax 5.0      // 5,0 kg
#define escala -376600.0f  // fator de calibração encontrado

// INSTANCIANDO OBJETO
HX711 scale;

// DECLARAÇÃO DE VARIÁVEIS  
float medida = 0;

void setup() {
  Serial.begin(57600);

  scale.begin(pinDT, pinSCK);      // CONFIGURA PINOS DO HX711
  scale.set_scale(escala);         // INSERE FATOR DE ESCALA CALIBRADO

  delay(2000);
  scale.tare();                    // ZERA A BALANÇA
  Serial.println("Setup Finalizado!");
}

void loop() {
  scale.power_up();                // Liga o sensor

  medida = scale.get_units(5);     // Média de 5 leituras (em kg)

  if (medida <= pesoMin) {         // Se peso < 10 g → zera
    scale.tare();
    medida = 0;
    Serial.println("Tara Configurada!");
  } 
  else if (medida >= pesoMax) {    // Se peso > 5 kg → zera
    scale.tare();
    medida = 0;
    Serial.println("Tara Configurada!");
  } 
  else {
    // Converte para gramas
    float medida_g = medida * 1000.0;
    Serial.print("Peso: ");
    Serial.print(medida_g, 1);     // imprime com 1 casa decimal
    Serial.println(" g");
  }

  scale.power_down(); 
  delay(200);  // mede a cada 0,2 segundos
}
