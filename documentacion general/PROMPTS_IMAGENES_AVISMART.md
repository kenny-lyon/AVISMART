# Prompts de imágenes — Video institucional AviSmart (Higgsfield)

*Paso 1 de 2. Primero se generan **todas las imágenes** (cuadros clave); después, con el archivo `PROMPTS_VIDEOS_AVISMART.md`, cada imagen se anima y se convierte en video.*

Basado en `GUION_VIDEO_AVISMART.md`, con 4 actos, 18 tomas, unos 80 s, sin texto y solo música.

---

## Cómo usar este documento

| Paso | Qué hacer |
|---|---|
| 1 | Seguir las etapas **en orden**. La Etapa 0 (personajes) es la base de todas las tomas con personas |
| 2 | En cada toma, copiar el bloque **PROMPT**, que está en inglés porque así funcionan mejor los modelos, y pegarlo en Higgsfield → *Image* |
| 3 | Formato **16:9**, resolución **2K**, **4 variantes** por prompt. Elegir la mejor |
| 4 | Si la toma tiene personajes, subir su imagen de referencia de la Etapa 0 en *Reference / Image input* |
| 5 | Descargar la elegida, convertirla a `.webp` (ver la Etapa 6) y guardarla con el **nombre exacto** indicado |
| 6 | Marcar la casilla ✅ de la toma |

**Modelos recomendados en Higgsfield**

| Uso | Modelo |
|---|---|
| Escenas fotorrealistas (galpón, aves, personas) | **GPT Image** o **Seedream**. Si una toma sale "plástica", probar **Higgsfield Soul** |
| Pantallas del software, porque llevan texto | **GPT Image** (es el que mejor escribe texto) |
| Corregir una parte de una imagen (manos, pantalla) | La opción *Edit / Inpaint* con el mismo modelo |

### Bloques fijos (se pegan al final de cada prompt)

Para que todas las tomas parezcan del mismo video, cada prompt termina con uno de estos bloques.

**[ESTILO]**, para escenas reales:
```
photorealistic cinematic film still, shot on full-frame cinema camera, 35mm lens, warm golden hour light, color palette of warm golden yellow and deep forest green, natural skin tones, shallow depth of field, subtle film grain, high detail, 16:9, no text, no captions, no watermark, no logos
```

**[NEGATIVO]**, para el campo *Negative prompt* si el modelo lo tiene:
```
text, letters, watermark, logo, deformed chickens, extra legs, extra wings, deformed hands, extra fingers, blurry face, cartoon, 3d render, oversaturated, dirty sick birds, dead birds, gore
```

**[DISEÑO]**, para las pantallas del software:
```
modern SaaS web application UI for a poultry farm management software named "AviSmart", left sidebar in dark forest green (#102f25) with white line icons, warm off-white content background (#f7f5ef), golden yellow accent (#f1c84b) on primary buttons and highlights, white rounded cards with soft shadows, Manrope typeface, all labels in Spanish, clean professional data visualization, crisp sharp text, flat screenshot, no device frame
```

---

## Estructura de carpetas

```
video_ia/
├── 0_personajes/   (Etapa 0)
├── 1_pantallas/    (Etapa 1)
├── 2_acto1/        (Etapa 2)
├── 3_acto2/        (Etapa 3)
├── 4_acto3/        (Etapa 4)
└── 5_acto4/        (Etapa 5)
```

---

## ETAPA 0 — Personajes (base de identidad)

Se generan **antes que nada**. Estas imágenes se suben como referencia en cada toma donde aparece el personaje, para que tenga **la misma cara y la misma ropa** en todo el video.

### 0.1 Operario ☐
**Archivo:** `0_personajes/P_operario.webp`
```
full body character reference photo of a Peruvian Andean man in his early 30s, light brown skin, short black hair, clean shaven, friendly calm expression, wearing a dark green work coverall, black rubber boots and a dark green cap, standing straight facing camera, plain neutral light grey studio background, soft even lighting, photorealistic, sharp focus, no text
```
> Generar también una variante **de perfil** (agregar `side profile view`) y guardarla como `P_operario_perfil.webp`.

### 0.2 Veterinaria ☐
**Archivo:** `0_personajes/P_veterinaria.webp`
```
full body character reference photo of a Peruvian woman veterinarian in her mid 30s, light brown skin, dark hair tied back under a white hair cap, wearing a white disposable biosecurity coverall, white rubber boots, surgical face mask lowered on the chin, nitrile gloves, confident kind expression, standing facing camera, plain neutral light grey studio background, soft even lighting, photorealistic, sharp focus, no text
```
> Si se prefiere un veterinario hombre, cambiar `woman` por `man` y `hair tied back` por `short hair`. Hay que mantener la misma elección en todas las tomas.

### 0.3 Productor ☐
**Archivo:** `0_personajes/P_productor.webp`
```
full body character reference photo of a Peruvian Andean farm owner man in his late 40s, light brown skin, short greying black hair, short trimmed mustache, wearing a beige quilted vest over a blue plaid flannel shirt, dark work trousers and brown boots, confident warm expression, standing facing camera, plain neutral light grey studio background, soft even lighting, photorealistic, sharp focus, no text
```

**Antes de seguir, comprobar que:** las caras sean distintas entre sí, no haya texto ni logos en la ropa, las manos estén bien y la ropa se vea completa.

---

## ETAPA 1 — Pantallas del software (diseño completo inventado)

Según el guion, **no se usa el diseño actual**: se inventa un AviSmart completo. Estas pantallas se generan **planas**, sin dispositivo. Después sirven de dos formas:
- como referencia para las tomas de personas usando el celular, la tablet o la laptop;
- como inserto a pantalla completa en la edición.

> **Consejo:** si alguna palabra sale mal escrita, corregirla con *Edit / Inpaint* solo en esa zona. En pantalla, los números deben verse **creíbles**.

### 1.1 Abrir lote — celular (toma 4) ☐
**Archivo:** `1_pantallas/UI_abrir_lote_movil.webp` · **Formato: 9:16**
```
mobile app screen, form titled "Abrir lote" with fields: "Galpón: Galpón 2", "Línea: Cobb 500", "Proveedor: Incubadora Andina", "Pollitos recibidos: 5 000", "Descartados al llegar: 30", "Peso al llegar: 42 g", a large golden yellow button "Registrar recepción", small chick icon in header, [DISEÑO], vertical 9:16 mobile layout
```

### 1.2 Vista de cámara con clima — escritorio (toma 8) ☐
**Archivo:** `1_pantallas/UI_camara_clima.webp` · **Formato: 16:9**
```
security camera live view inside the AviSmart web app: large video frame showing the interior of a broiler chicken house with hundreds of white chickens under warm light, a small red "EN VIVO" badge in the corner, semi-transparent overlay cards on the video showing "Temperatura 26,4 °C", "Humedad 62 %", "CO₂ 1 450 ppm" with small green status dots, camera selector tabs "Galpón 1 · Galpón 2 · Galpón 3" above the video, [DISEÑO]
```

### 1.3 Panel del lote con curva de peso — escritorio (toma 9) ☐
**Archivo:** `1_pantallas/UI_panel_lote.webp` · **Formato: 16:9**
```
dashboard screen titled "Panel del lote · Galpón 2 · Día 28", top row of four KPI cards: "Aves vivas 4 912", "Mortalidad 1,8 %", "Conversión 1,52", "Eficiencia 368", below a large line chart "Curva de peso" with a smooth rising golden line for the real weight and a dashed grey line for the target curve, x axis days 1 to 42, y axis grams, right column with a small list "Próximas vacunas", [DISEÑO]
```

### 1.4 Notificación de alerta — celular (toma 10) ☐
**Archivo:** `1_pantallas/UI_notificacion.webp` · **Formato: 9:16**
```
smartphone lock screen with a dark blurred wallpaper of a chicken house, showing time "06:42", one notification banner from a messaging app with a small green and gold chick app icon, title "AviSmart — Alerta de salud", body "Galpón 2: mortalidad de hoy 0,9 % supera el umbral (0,5 %). Revisar lote.", clean modern mobile UI, crisp text, vertical 9:16, no brand logos
```

### 1.5 Vacunas — dar conformidad — tablet (toma 13) ☐
**Archivo:** `1_pantallas/UI_vacunas_conformidad.webp` · **Formato: 4:3**
```
tablet app screen titled "Sanidad · Vacunas", a table of vaccines with rows "Newcastle + Bronquitis · Día 7 · Aplicada", "Gumboro · Día 14 · Aplicada", "Newcastle refuerzo · Día 21 · Aplicada", the last row highlighted with a large golden yellow button "Dar conformidad" and a green check icon, side panel showing "Aplicada por: Operario · Vía ocular · 5 000 dosis", [DISEÑO], 4:3 tablet layout
```

### 1.6 Reporte de cierre — laptop (toma 15) ☐
**Archivo:** `1_pantallas/UI_reporte_cierre.webp` · **Formato: 16:9**
```
PDF report document open on screen, titled "Reporte de cierre · Lote Galpón 2", sections with a weight curve line chart, a summary table "Aves vendidas 4 820", "Peso total 13 950 kg", "Conversión 1,58", "Eficiencia 372", and a highlighted golden box "Margen del lote S/ 52 850" with a small upward green arrow, AviSmart logo small at the top, clean printable document style on white paper with forest green headings
```

### 1.7 Cámaras con IA — detección y conteo (toma 17) ☐
**Archivo:** `1_pantallas/UI_camaras_ia.webp` · **Formato: 16:9**
```
AviSmart web app screen titled "Cámaras inteligentes", a 2x2 grid of live camera feeds of a broiler chicken house: top left normal color daylight view, top right black and white night infrared view, bottom left thermal camera view with iron-bow color palette (purple, orange, yellow) showing warm chickens, bottom right color view with thin golden bounding boxes around each chicken and one red bounding box labeled "Postura anómala", side panel with "Aves contadas 4 908", "Posibles bajas 2", "Alertas de postura 1", [DISEÑO]
```

### 1.8 Análisis estadístico — tablet/laptop (toma 18) ☐
**Archivo:** `1_pantallas/UI_analisis.webp` · **Formato: 16:9**
```
analytics screen titled "Análisis del lote", large status badge "Lote: va bien" in green, four small charts: "Temperatura (°C)" line chart, "CO₂ (ppm)" area chart, "Peso promedio (g)" rising line vs target, "Alimento diario (kg)" bar chart, a summary card "Clasificación: Excelente" with golden star, a small card "Predicción IA: el lote cerrará dentro de la meta", [DISEÑO]
```

**Antes de seguir, comprobar que:** todos los textos estén en español y bien escritos, los colores sean verde bosque y dorado, y las ocho pantallas parezcan del mismo software.

---

## ETAPA 2 — Acto 1 · El amanecer del lote (0–15 s)

### Toma 1 · Drone de criaderos en Cusco ☐
**Archivo:** `2_acto1/T01_drone_cusco.webp`
```
aerial drone photograph at sunrise of a poultry farm in an Andean valley near Cusco, Peru: several long white broiler chicken houses with metal roofs and yellow side curtains in parallel rows, surrounded by green fields and eucalyptus trees, high Andes mountains in the background, clear deep blue sky, first warm golden sunlight touching the roofs, light morning mist in the valley, [ESTILO]
```
> **Consejo:** buscar fotos reales de "granjas avícolas Cusco" y usar una como referencia de **composición**, nunca copiarla.

### Toma 2 · Camión llegando con pollitos ☐
**Archivo:** `2_acto1/T02_camion.webp`
```
a white delivery truck with ventilated cargo box arriving on a dirt road to the entrance of a broiler chicken house at early morning, stacked plastic chick transport boxes visible through the open rear door, Andean mountains behind, soft golden sunrise light and long shadows, wide shot, [ESTILO]
```

### Toma 3 · Manos sacando pollitos ☐
**Archivo:** `2_acto1/T03_pollitos.webp`
```
close-up of gentle hands of a worker in a dark green coverall tipping a plastic transport box and releasing dozens of fluffy yellow day-old chicks onto clean wood shavings bedding inside a warm chicken house, red brooder heat lamp glow, chicks tumbling softly, very shallow depth of field, [ESTILO]
```
*Referencia:* `P_operario.webp`, solo por la ropa.

### Toma 4 · Operario registrando la recepción ☐
**Archivo:** `2_acto1/T04_operario_celular.webp`
```
over-the-shoulder shot of the Peruvian worker in a dark green coverall and cap holding a smartphone, the phone screen clearly shows the reference app screen, in the blurred background yellow chicks on wood shavings under brooder lamps inside the chicken house, warm golden light, [ESTILO]
```
*Referencias:* `P_operario.webp` y `UI_abrir_lote_movil.webp`.
> Si la pantalla sale deformada, generar la toma con la **pantalla en verde** (`phone screen is solid bright green`) y pegar la UI en la edición.

---

## ETAPA 3 — Acto 2 · El día a día (15–35 s)

### Toma 5 · Comedero llenándose ☐
**Archivo:** `3_acto2/T05_comedero.webp`
```
close-up of golden feed pellets pouring from an automatic feeder pipe into a red round pan feeder inside a broiler chicken house, young white chickens around it starting to peck, dust particles glowing in warm side light, [ESTILO]
```

### Toma 6 · Bebedero de niple ☐
**Archivo:** `3_acto2/T06_bebedero.webp`
```
macro shot of a nipple drinker line with a clear water drop hanging from the nipple, a young white broiler chicken raising its beak to drink, soft golden backlight making the droplet sparkle, extremely shallow depth of field, [ESTILO]
```

### Toma 7 · Pesaje de la muestra ☐
**Archivo:** `3_acto2/T07_pesaje.webp`
```
close-up of the worker's hands in a dark green coverall placing a healthy white broiler chicken into a plastic weighing bucket hanging from a digital scale inside the chicken house, the scale display is blank and dark, other chickens blurred in the background, warm light, [ESTILO]
```
*Referencia:* `P_operario.webp`.
> El número de la balanza se deja **apagado** a propósito. Si la IA inventa números, salen raros.

### Toma 8a · Cámara en el galpón ☐
**Archivo:** `3_acto2/T08a_camara_galpon.webp`
```
a modern white dome security camera with small infrared LEDs mounted high on a metal beam inside a broiler chicken house, next to a small digital thermo-hygrometer sensor box on the wall, hundreds of white chickens blurred below, warm golden side light through curtains, low angle shot, [ESTILO]
```

### Toma 8b · Lo que ve la cámara (pantalla) ☐
Usa directamente `1_pantallas/UI_camara_clima.webp`. **No se genera nada nuevo.**

### Toma 9 · Panel del lote en un monitor ☐
**Archivo:** `3_acto2/T09_panel_monitor.webp`
```
a laptop on a wooden desk in a small farm office, the screen clearly shows the reference dashboard, through the window behind the laptop a chicken house is visible in soft morning light, coffee mug beside the laptop, shallow depth of field focused on the screen, [ESTILO]
```
*Referencia:* `UI_panel_lote.webp`.

---

## ETAPA 4 — Acto 3 · Cuidar a tiempo (35–55 s)

### Toma 10 · Celular con la alerta ☐
**Archivo:** `4_acto3/T10_alerta_celular.webp`
```
a smartphone lying face up on a rustic wooden table next to a cup of coffee and work gloves, the screen lit up showing the reference notification, early morning blue light from a window, close-up, shallow depth of field, [ESTILO]
```
*Referencia:* `UI_notificacion.webp`.

### Toma 11 · Veterinaria entrando (bioseguridad) ☐
**Archivo:** `4_acto3/T11_vet_entrada.webp`
```
the Peruvian woman veterinarian in a white biosecurity coverall, white boots, hair cap and surgical mask stepping into a footbath disinfection tray at the door of a broiler chicken house, holding a vaccine cooler box, doorway backlit by warm golden light, medium shot, [ESTILO]
```
*Referencia:* `P_veterinaria.webp`.

### Toma 12 · Vacuna ocular ☐
**Archivo:** `4_acto3/T12_vacuna_ocular.webp`
```
macro close-up of gloved hands of a veterinarian holding a fluffy yellow chick gently and applying a single eye-drop vaccine from a small dropper bottle into the chick's eye, the drop visible just before touching, soft warm backlight, extremely shallow depth of field, [ESTILO]
```
*Referencia:* `P_veterinaria.webp`, por los guantes y la manga.

### Toma 13 · Dar conformidad en la tablet ☐
**Archivo:** `4_acto3/T13_vet_tablet.webp`
```
over-the-shoulder shot of the Peruvian woman veterinarian in a white biosecurity coverall holding a tablet, her gloved finger about to tap the golden button on the screen, the screen clearly shows the reference vaccines screen, chickens blurred in the background inside the chicken house, warm light, [ESTILO]
```
*Referencias:* `P_veterinaria.webp` y `UI_vacunas_conformidad.webp`.

---

## ETAPA 5 — Acto 4 · El cierre (55–80 s)

### Toma 14 · Pollos grandes al atardecer ☐
**Archivo:** `5_acto4/T14_pollos_atardecer.webp`
```
wide low-angle shot inside a broiler chicken house at sunset, hundreds of large healthy white broiler chickens ready for market resting and walking on clean bedding, strong golden sunset backlight streaming through the side curtains creating rim light on the feathers, dust particles in the air, [ESTILO]
```

### Toma 15 · Productor con el reporte de cierre ☐
**Archivo:** `5_acto4/T15_productor_reporte.webp`
```
medium shot of the Peruvian farm owner in a beige quilted vest sitting at a wooden desk in a farm office, looking at a laptop with a satisfied subtle smile, the laptop screen clearly shows the reference closing report, warm sunset light from the window, [ESTILO]
```
*Referencias:* `P_productor.webp` y `UI_reporte_cierre.webp`.

### Toma 16 · Productor y operario conversando ☐
**Archivo:** `5_acto4/T16_conversacion.webp`
```
slightly low-angle medium shot of the Peruvian farm owner in a beige vest and the Peruvian worker in a dark green coverall talking and smiling at the open door of a chicken house, the owner resting a hand on the worker's shoulder, golden sunset behind them, Andean mountains in the distance, [ESTILO]
```
*Referencias:* `P_productor.webp` y `P_operario.webp`.

### Toma 17 · Cámaras día y noche en sus formatos (4 imágenes)
Las cuatro imágenes tienen **el mismo encuadre del galpón**, para luego fundirlas entre sí. Primero se genera la 17a y **se usa como referencia** en la 17b, la 17c y la 17d.

**17a · Visual (RGB), de día** ☐ — `5_acto4/T17a_rgb_dia.webp`
```
high-angle security camera view from a ceiling corner of a broiler chicken house during the day, hundreds of white chickens, feeder and drinker lines in perspective, natural daylight, realistic CCTV wide angle lens look, slight fisheye, no text, no timestamp
```

**17b · Infrarroja, de noche** ☐ — `5_acto4/T17b_ir_noche.webp`
```
same exact framing as the reference image, but at night seen through an infrared night vision security camera: monochrome black and white image, chickens resting and glowing pale grey, dark background, slight IR noise, realistic CCTV night vision look, no text, no timestamp
```

**17c · Térmica** ☐ — `5_acto4/T17c_termica.webp`
```
same exact framing as the reference image, but seen through a thermal imaging camera with iron-bow color palette: chickens glowing bright yellow and orange, floor in purple and dark blue, one colder blue zone near a side curtain, realistic thermal camera look, no text, no scale bar
```

**17d · IA detectando** ☐ — usa `1_pantallas/UI_camaras_ia.webp`. **No se genera nada nuevo.**

### Toma 18 · Productor revisando el análisis ☐
**Archivo:** `5_acto4/T18_productor_analisis.webp`
```
over-the-shoulder shot of the Peruvian farm owner in a beige quilted vest standing at the entrance of a chicken house holding a tablet, the tablet screen clearly shows the reference analytics screen, chickens and warm sunset light blurred in the background, [ESTILO]
```
*Referencias:* `P_productor.webp` y `UI_analisis.webp`.

---

## ETAPA 6 — Exportar a .webp

Higgsfield descarga las imágenes en PNG o JPG. Hay que convertirlas a `.webp` con **calidad 90**, que pesa poco y no se nota la pérdida.

**Opción fácil:** [squoosh.app](https://squoosh.app). Se arrastra la imagen, se elige *WebP* con calidad 90 y se descarga.

**Opción por lotes**, con ffmpeg instalado. En PowerShell, dentro de cada carpeta:
```powershell
Get-ChildItem *.png, *.jpg | ForEach-Object { ffmpeg -y -i $_.FullName -c:v libwebp -quality 90 ($_.BaseName + ".webp") }
```

> **Importante:** hay que guardar también el **PNG original** de cada imagen elegida. Si al animar Higgsfield no acepta el `.webp`, se sube el PNG.

---

## Control final de imágenes

| Etapa | Imágenes | ☐ |
|---|---|---|
| 0 · Personajes | 3 (+1 perfil) | ☐ |
| 1 · Pantallas | 8 | ☐ |
| 2 · Acto 1 | 4 | ☐ |
| 3 · Acto 2 | 5 (la 8b es pantalla) | ☐ |
| 4 · Acto 3 | 4 | ☐ |
| 5 · Acto 4 | 7 (la 17d es pantalla) | ☐ |

**Revisión antes de pasar a videos:**
- [ ] Las caras de los personajes son las mismas en todas las tomas.
- [ ] No hay pollos deformes (patas, alas o picos de más).
- [ ] No hay texto inventado fuera de las pantallas.
- [ ] Todas comparten la luz cálida y la paleta dorado/verde.
- [ ] Todas están en 16:9, salvo las pantallas de celular y tablet, que son insertos.

➡️ **Siguiente:** `PROMPTS_VIDEOS_AVISMART.md`
