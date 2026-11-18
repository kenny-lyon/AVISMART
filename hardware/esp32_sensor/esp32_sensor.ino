/*
  AviSmart: sensor del galpón para ESP32.
  Envía temperatura y humedad cada minuto a AviSmart. CO2, amoníaco y medidor de agua son opcionales:
  activa solo los módulos que tengas conectados. Conexiones y pruebas: ver hardware/README.md.

  Librerías (Gestor de librerías del IDE de Arduino):
    - DHT sensor library (Adafruit)
    - SparkFun SCD30 Arduino Library (solo con USAR_CO2)
*/
#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ---------- Configuración: cambia estos datos ----------
const char* WIFI_NOMBRE = "NOMBRE_DEL_WIFI";
const char* WIFI_CLAVE  = "CLAVE_DEL_WIFI";
// La dirección y la clave las muestra AviSmart en Granjas y galpones > Sensor.
const char* AVISMART_URL = "http://192.168.1.10:8000/api/iot/lecturas";
const char* SENSOR_CLAVE = "avs_PEGA_AQUI_LA_CLAVE";

#define USAR_CO2  0   // 1 si hay un SCD30 conectado por I2C
#define USAR_NH3  0   // 1 si hay un MQ-137 en PIN_NH3 (requiere calibrar R0)
#define USAR_AGUA 0   // 1 si hay un medidor de agua de pulsos en PIN_AGUA

const int PIN_DHT  = 4;
const int PIN_NH3  = 34;
const int PIN_AGUA = 27;
const unsigned long INTERVALO_MS = 60000;  // AviSmart acepta una lectura por minuto
const float PULSOS_POR_LITRO = 450.0;      // revisa la hoja de datos de tu medidor
const float NH3_R0 = 10.0;                 // resistencia en aire limpio: se obtiene al calibrar
// -------------------------------------------------------

DHT dht(PIN_DHT, DHT22);

#if USAR_CO2
#include <Wire.h>
#include <SparkFun_SCD30_Arduino_Library.h>
SCD30 co2;
#endif

#if USAR_AGUA
volatile unsigned long pulsos = 0;
void IRAM_ATTR contarPulso() { pulsos++; }
#endif

void conectarWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.begin(WIFI_NOMBRE, WIFI_CLAVE);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(500);
  Serial.println(WiFi.status() == WL_CONNECTED ? "WiFi conectado" : "Sin WiFi");
}

#if USAR_NH3
// Curva aproximada del MQ-137: calibrar con un medidor de referencia antes de confiar en el valor.
float leerNh3() {
  float voltaje = analogRead(PIN_NH3) * 3.3 / 4095.0;
  if (voltaje < 0.01) return 0;
  float rs = (3.3 - voltaje) / voltaje * 10.0;
  return pow(10, (log10(rs / NH3_R0) - 0.323) / -0.243);
}
#endif

void setup() {
  Serial.begin(115200);
  dht.begin();
#if USAR_CO2
  Wire.begin();
  if (!co2.begin()) Serial.println("No se detecta el SCD30");
#endif
#if USAR_AGUA
  pinMode(PIN_AGUA, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_AGUA), contarPulso, FALLING);
#endif
  conectarWifi();
}

void loop() {
  conectarWifi();
  float temperatura = dht.readTemperature();
  float humedad = dht.readHumidity();

  if (isnan(temperatura) || isnan(humedad)) {
    Serial.println("Falla al leer el DHT22");
  } else if (WiFi.status() == WL_CONNECTED) {
    String json = "{\"temperatura\":" + String(temperatura, 1) + ",\"humedad\":" + String(humedad, 0);
#if USAR_CO2
    if (co2.dataAvailable()) json += ",\"co2_ppm\":" + String(co2.getCO2());
#endif
#if USAR_NH3
    json += ",\"nh3_ppm\":" + String(leerNh3(), 1);
#endif
#if USAR_AGUA
    noInterrupts();
    unsigned long contados = pulsos;
    interrupts();
    json += ",\"agua_l\":" + String(contados / PULSOS_POR_LITRO, 2);
#endif
    json += "}";

    HTTPClient http;
    http.begin(AVISMART_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Sensor-Clave", SENSOR_CLAVE);
    int codigo = http.POST(json);
    Serial.printf("%s -> %d\n", json.c_str(), codigo);
    http.end();
#if USAR_AGUA
    // Solo se descuenta lo que AviSmart recibió: si falló, esos litros van en el siguiente envío.
    if (codigo == 200) {
      noInterrupts();
      pulsos -= contados;
      interrupts();
    }
#endif
  }
  delay(INTERVALO_MS);
}
