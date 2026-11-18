/*
  AviSmart: balanza automática del galpón para ESP32 + celda de carga + HX711.
  Las aves se suben solas a la plataforma. El programa detecta cada peso estable, lo guarda y cada minuto envía
  la tanda a AviSmart con la misma clave del sensor del galpón. AviSmart descarta las lecturas de un ave subiendo
  o de dos aves juntas, y calcula promedio, CV y uniformidad del día.
  Librería: "HX711" de Bogdan Necula (bogde). Más detalles en hardware/README.md.
*/
#include <WiFi.h>
#include <HTTPClient.h>
#include "HX711.h"

// ---------- Configuración: cambia estos datos ----------
const char* WIFI_NOMBRE = "NOMBRE_DEL_WIFI";
const char* WIFI_CLAVE  = "CLAVE_DEL_WIFI";
const char* AVISMART_URL = "http://192.168.1.10:8000/api/iot/pesos";
const char* SENSOR_CLAVE = "avs_PEGA_AQUI_LA_CLAVE";
const float FACTOR_CALIBRACION = 21.5;   // ver "Calibrar la balanza" en el README
// -------------------------------------------------------

const int PIN_DT = 16;
const int PIN_SCK = 17;
const float PESO_MINIMO_G = 30;          // por debajo, la plataforma está vacía
const float TOLERANCIA_G = 15;           // variación máxima para considerar el peso estable
const unsigned long ESTABLE_MS = 1500;   // tiempo que el peso debe mantenerse estable
const unsigned long ENVIO_MS = 60000;    // una tanda por minuto
const int MAX_PESOS = 300;

HX711 balanza;
float pesos[MAX_PESOS];
int cantidad = 0;
unsigned long ultimoEnvio = 0;

float leer() { return balanza.get_units(3); }

// Espera a que el peso se quede quieto. Devuelve 0 si el ave se bajó antes.
float pesoEstable() {
  float referencia = leer();
  unsigned long inicio = millis();
  while (millis() - inicio < ESTABLE_MS) {
    float ahora = leer();
    if (ahora < PESO_MINIMO_G) return 0;
    if (fabs(ahora - referencia) > TOLERANCIA_G) { referencia = ahora; inicio = millis(); }
  }
  return referencia;
}

void enviar() {
  if (cantidad == 0 || WiFi.status() != WL_CONNECTED) return;
  String cuerpo = "{\"pesos\":[";
  for (int i = 0; i < cantidad; i++) { if (i) cuerpo += ","; cuerpo += String(pesos[i], 0); }
  cuerpo += "]}";
  HTTPClient http;
  http.begin(AVISMART_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Sensor-Clave", SENSOR_CLAVE);
  int codigo = http.POST(cuerpo);
  Serial.printf("%d pesos -> %d\n", cantidad, codigo);
  http.end();
  if (codigo == 200) cantidad = 0;  // si falló, se reintenta en el próximo envío
}

void setup() {
  Serial.begin(115200);
  balanza.begin(PIN_DT, PIN_SCK);
  balanza.set_scale(FACTOR_CALIBRACION);
  balanza.tare();  // la plataforma debe estar vacía al encender
  WiFi.begin(WIFI_NOMBRE, WIFI_CLAVE);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) WiFi.reconnect();

  if (leer() >= PESO_MINIMO_G) {
    float peso = pesoEstable();
    if (peso > 0 && cantidad < MAX_PESOS) {
      pesos[cantidad++] = peso;
      Serial.printf("Ave: %.0f g\n", peso);
    }
    // No volver a pesar hasta que la plataforma quede vacía (la misma ave no cuenta dos veces).
    while (leer() >= PESO_MINIMO_G) delay(100);
  }

  if (millis() - ultimoEnvio >= ENVIO_MS) {
    enviar();
    ultimoEnvio = millis();
  }
}
