/*
  AviSmart: cámara del galpón para ESP32-CAM (AI-Thinker).
  Toma una foto cada cierto tiempo y la envía a AviSmart con la misma clave del sensor del galpón.
  Estas fotos se ven en la pantalla Cámara y quedan guardadas para entrenar los modelos de imagen.
  En el IDE de Arduino: placa "AI Thinker ESP32-CAM". Más detalles en hardware/README.md.
*/
#include <WiFi.h>
#include <WiFiClient.h>
#include "esp_camera.h"

// ---------- Configuración: cambia estos datos ----------
const char* WIFI_NOMBRE = "NOMBRE_DEL_WIFI";
const char* WIFI_CLAVE  = "CLAVE_DEL_WIFI";
const char* AVISMART_HOST = "192.168.1.10";
const int   AVISMART_PUERTO = 8000;
const char* SENSOR_CLAVE = "avs_PEGA_AQUI_LA_CLAVE";
const unsigned long INTERVALO_MS = 300000;  // cada 5 minutos
// -------------------------------------------------------

bool iniciarCamara() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = 5;  c.pin_d1 = 18; c.pin_d2 = 19; c.pin_d3 = 21;
  c.pin_d4 = 36; c.pin_d5 = 39; c.pin_d6 = 34; c.pin_d7 = 35;
  c.pin_xclk = 0; c.pin_pclk = 22; c.pin_vsync = 25; c.pin_href = 23;
  c.pin_sccb_sda = 26; c.pin_sccb_scl = 27;
  c.pin_pwdn = 32; c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = FRAMESIZE_SVGA;  // 800x600
  c.jpeg_quality = 12;
  c.fb_count = 1;
  return esp_camera_init(&c) == ESP_OK;
}

void enviarFoto() {
  camera_fb_t* foto = esp_camera_fb_get();
  if (!foto) { Serial.println("No se pudo tomar la foto"); return; }

  WiFiClient cliente;
  if (!cliente.connect(AVISMART_HOST, AVISMART_PUERTO)) {
    Serial.println("Sin conexión con AviSmart");
    esp_camera_fb_return(foto);
    return;
  }
  String limite = "AviSmartLimite";
  String inicio = "--" + limite + "\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\"galpon.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
  String fin = "\r\n--" + limite + "--\r\n";

  cliente.printf("POST /api/iot/fotos HTTP/1.1\r\nHost: %s\r\nX-Sensor-Clave: %s\r\n", AVISMART_HOST, SENSOR_CLAVE);
  cliente.printf("Content-Type: multipart/form-data; boundary=%s\r\nContent-Length: %u\r\nConnection: close\r\n\r\n",
                 limite.c_str(), (unsigned)(inicio.length() + foto->len + fin.length()));
  cliente.print(inicio);
  for (size_t i = 0; i < foto->len; i += 1024) cliente.write(foto->buf + i, min((size_t)1024, foto->len - i));
  cliente.print(fin);
  esp_camera_fb_return(foto);

  unsigned long espera = millis();
  while (cliente.connected() && !cliente.available() && millis() - espera < 10000) delay(10);
  Serial.println(cliente.readStringUntil('\n'));  // "HTTP/1.1 201 Created" si llegó bien
  cliente.stop();
}

void setup() {
  Serial.begin(115200);
  if (!iniciarCamara()) Serial.println("La cámara no inició");
  WiFi.begin(WIFI_NOMBRE, WIFI_CLAVE);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    delay(5000);
    return;
  }
  enviarFoto();
  delay(INTERVALO_MS);
}
