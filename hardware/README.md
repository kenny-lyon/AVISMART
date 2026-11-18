# Hardware del galpón (M7)

AviSmart ya recibe datos de equipos reales. Lo que hay aquí es el programa de ejemplo para el ESP32 y la ESP32-CAM.

> Estos programas todavía no se probaron en equipos físicos. El lado de AviSmart sí está probado con el simulador (`backend/app/simulador_iot.py`), que envía exactamente lo mismo.

## Materiales

| Módulo | Para qué | Obligatorio |
|---|---|---|
| ESP32 DevKit | Controlador con WiFi | Sí |
| DHT22 | Temperatura y humedad | Sí |
| Sensirion SCD30 | CO₂ (I2C) | No |
| MQ-137 | Amoníaco (analógico; requiere calibrar) | No |
| Medidor de agua de pulsos (por ejemplo YF-S201) | Litros consumidos | No |
| ESP32-CAM (AI-Thinker) | Fotos del galpón | No |
| Celda de carga de 10 kg + módulo HX711 + plataforma | Balanza automática (otro ESP32) | No |

## Conexiones del ESP32

| Módulo | Pin del módulo | Pin del ESP32 |
|---|---|---|
| DHT22 | DATA | GPIO 4 (resistencia de 10 kΩ a 3,3 V) |
| SCD30 | SDA / SCL | GPIO 21 / GPIO 22 |
| MQ-137 | AO | GPIO 34, **con divisor de voltaje**: el módulo da hasta 5 V y el ESP32 admite 3,3 V |
| Medidor de agua | Señal | GPIO 27, **con divisor de voltaje** si se alimenta a 5 V |

## Puesta en marcha

1. En AviSmart: **Granjas y galpones → Sensor → Activar sensor**. Copia la dirección y la clave.
2. Abre `esp32_sensor/esp32_sensor.ino` en el IDE de Arduino y cambia el WiFi, `AVISMART_URL` y `SENSOR_CLAVE`.
3. Pon en `1` los módulos que tengas (`USAR_CO2`, `USAR_NH3`, `USAR_AGUA`) y carga el programa.
4. En el Monitor Serie (115200) debe aparecer `-> 200` cada minuto, y en AviSmart el sensor pasa a **En línea**.
5. Para la cámara, haz lo mismo con `esp32_cam/esp32_cam.ino`, usando **la misma clave** del galpón. Las fotos aparecen en la pantalla **Cámara**.

El ESP32 y la PC deben estar en la misma red. Usa la IP de la PC, no `127.0.0.1`, y arranca la API escuchando en la red (`--host 0.0.0.0`).

## Contrato de datos

**Lectura** (como máximo una por minuto):

```
POST /api/iot/lecturas
X-Sensor-Clave: avs_...
Content-Type: application/json

{ "temperatura": 22.5, "humedad": 61, "co2_ppm": 1800, "nh3_ppm": 12.5, "agua_l": 1.3 }
```

`temperatura` y `humedad` son obligatorios. `agua_l` son los litros desde el envío anterior.

**Foto** (como máximo una por minuto, hasta 5 MB, JPG, PNG o WEBP):

```
POST /api/iot/fotos
X-Sensor-Clave: avs_...
Content-Type: multipart/form-data   (campo: archivo)
```

| Respuesta | Significado |
|---|---|
| 200 / 201 | Recibido |
| 401 | Clave no válida o sensor desactivado |
| 422 | Valor fuera de rango |
| 429 | Se envió antes de un minuto |

**Pesos de la balanza** (como máximo una tanda por minuto, hasta 300 pesos):

```
POST /api/iot/pesos
X-Sensor-Clave: avs_...
Content-Type: application/json

{ "pesos": [2450, 2380, 2512, 1210, 4870] }
```

AviSmart descarta los pesos menores al 60 % del esperado para la edad (un ave subiendo o bajando) y los mayores al 150 % (dos aves juntas). El esperado es la curva de la línea ajustada por el último pesaje del lote.

## Balanza automática

Una plataforma de unos 30 × 30 cm, a la altura de la cama, sobre una celda de carga de 10 kg. Las aves se suben solas.

| HX711 | ESP32 |
|---|---|
| DT | GPIO 16 |
| SCK | GPIO 17 |
| VCC / GND | 3,3 V / GND |

1. Instala la librería **HX711** de Bogdan Necula en el IDE de Arduino.
2. **Calibrar la balanza:**
   1. Carga el programa con `FACTOR_CALIBRACION = 1` y la plataforma vacía.
   2. Pon un peso conocido, por ejemplo 1 kg, y mira el valor en el Monitor Serie.
   3. Divide ese valor entre los gramos del peso: el resultado es el factor de calibración.
3. Abre `esp32_balanza/esp32_balanza.ino`. Cambia el WiFi, `AVISMART_URL` y `SENSOR_CLAVE` (la misma clave del galpón) y carga el programa con la plataforma **vacía**: al encender, la balanza descuenta el peso de la plataforma (hace la tara).
4. En el **Panel** aparece *Balanza automática · En línea*. En **Registro del día → Pesaje** aparece el modo **Balanza automática**.

Para que el promedio sea representativo, colócala en una zona de paso, lejos de comederos y bebederos, y cámbiala de lugar cada semana.

## Alertas automáticas

Además de los rangos de temperatura y humedad por edad, AviSmart avisa si el CO₂ supera **3000 ppm** o el amoníaco **25 ppm**.

## Probar sin hardware

Desde `backend`:

```
.venv\Scripts\python -m app.simulador_iot --clave avs_... --aire --foto ruta\a\foto.jpg
.venv\Scripts\python -m app.simulador_iot --clave avs_... --balanza 2450 --pesadas 30 --solo-balanza
```

`--balanza` es el peso promedio de las aves en gramos. El simulador incluye a propósito un 6 % de lecturas de un ave subiendo y un 4 % de dos aves juntas, para que se vea el filtro.
