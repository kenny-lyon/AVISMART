# Prompts de videos — Video institucional AviSmart (Higgsfield)

*Paso 2 de 2. Cada imagen generada con `PROMPTS_IMAGENES_AVISMART.md` se usa como **cuadro inicial** y se anima. Al final se montan todos los clips en el video de unos 80 s.*

Basado en `GUION_VIDEO_AVISMART.md`, con 4 actos, 18 tomas, sin texto y solo música.

---

## Cómo usar este documento

| Paso | Qué hacer |
|---|---|
| 1 | Higgsfield → *Video* → modo **Image to Video** |
| 2 | Subir la imagen indicada como **Start frame**. Si la toma pide **End frame**, subir también esa |
| 3 | Pegar el **PROMPT**. Solo describe **movimiento**, porque la escena ya está en la imagen |
| 4 | Elegir el **movimiento de cámara** indicado, si el modelo ofrece presets |
| 5 | Generar **2 variantes** y quedarse con la más estable |
| 6 | Guardar con el **nombre exacto** y marcar ✅ |

**Configuración fija para todas las tomas**

| Parámetro | Valor |
|---|---|
| Modelo | **Seedance** (recomendado). Si una toma sale mal, probar **Kling** o **Veo** |
| Resolución | **1080p** |
| Formato | **16:9** |
| Duración a generar | **5 s**. En la edición solo se usan 2–5 s, pero así sobra material para cortar |
| Audio | **Desactivado**. La música se pone al final |
| Movimiento | Lento y suave. El video debe sentirse calmo y profesional |

**Bloque fijo que va al final de cada prompt:**

**[MOV]**
```
smooth slow cinematic camera movement, stable, realistic natural motion, consistent lighting, no morphing, no text appearing, no flicker
```

> **Regla de oro:** si en una toma aparecen pollos que se deforman, manos que cambian o texto que se derrite, hay que **acortar el movimiento**. Se puede usar un preset más suave, quitar acciones del prompt o generar solo 3 s.

---

## Estructura de carpetas

```
video_ia/
├── 6_clips/
│   ├── acto1/
│   ├── acto2/
│   ├── acto3/
│   └── acto4/
└── 7_montaje/
```

---

## Mapa de tiempos (cuánto dura cada toma en el video final)

| Acto | Toma | Uso en el montaje | Tiempo acumulado |
|---|---|---|---|
| **1** | T01 Drone Cusco | 4,5 s | 0:00–0:04,5 |
| | T02 Camión | 3 s | –0:07,5 |
| | T03 Pollitos | 3,5 s | –0:11 |
| | T04 Operario y celular | 4 s | –0:15 |
| **2** | T05 Comedero | 3 s | –0:18 |
| | T06 Bebedero | 3 s | –0:21 |
| | T07 Pesaje | 3,5 s | –0:24,5 |
| | T08a Cámara en el galpón | 2,5 s | –0:27 |
| | T08b Vista de cámara con clima | 3 s | –0:30 |
| | T09 Panel en la laptop | 5 s | –0:35 |
| **3** | T10 Alerta en el celular | 4 s | –0:39 |
| | T11 Veterinaria entrando | 5 s | –0:44 |
| | T12 Vacuna ocular | 5 s | –0:49 |
| | T13 Dar conformidad | 6 s | –0:55 |
| **4** | T14 Pollos al atardecer | 4 s | –0:59 |
| | T15 Productor y reporte | 4 s | –1:03 |
| | T16 Conversación | 4 s | –1:07 |
| | T17a → b → c → d Cámaras | 2 + 2 + 2 + 3 s | –1:16 |
| | T18 Productor y análisis | 4 s | **–1:20** |

---

## ETAPA 1 — Acto 1 · El amanecer del lote

### 1.1 · T01 Drone de criaderos en Cusco ☐
- **Start frame:** `2_acto1/T01_drone_cusco.webp`
- **Cámara:** *Drone / FPV forward*, avance lento y alto
- **Archivo:** `6_clips/acto1/V01_drone.mp4`
```
slow aerial drone flight forward and slightly descending over the poultry farm toward the chicken houses, morning mist drifting gently in the valley, sunlight slowly spreading across the metal roofs, mountains stay still in the background, [MOV]
```

### 1.2 · T02 Camión llegando ☐
- **Start frame:** `2_acto1/T02_camion.webp`
- **Cámara:** *Static* o *Slow pan right*
- **Archivo:** `6_clips/acto1/V02_camion.mp4`
```
the truck slowly rolls forward and comes to a gentle stop at the chicken house entrance, a little dust rising from the dirt road behind the wheels, long morning shadows, camera slowly pans following the truck, [MOV]
```

### 1.3 · T03 Pollitos llegando a la cama ☐
- **Start frame:** `2_acto1/T03_pollitos.webp`
- **Cámara:** *Static*, en **cámara lenta**
- **Archivo:** `6_clips/acto1/V03_pollitos.mp4`
```
slow motion, the hands gently tip the box and the fluffy yellow chicks slide softly onto the wood shavings, chicks start walking and chirping, feathers fluttering, warm lamp glow, [MOV]
```

### 1.4 · T04 Operario registrando en el celular ☐
- **Start frame:** `2_acto1/T04_operario_celular.webp`
- **Cámara:** *Slow push in* hacia la pantalla
- **Archivo:** `6_clips/acto1/V04_operario.mp4`
```
the worker's thumb taps the phone screen once, the phone stays steady, chicks moving softly in the blurred background, camera slowly pushes in over the shoulder toward the phone, the screen content remains sharp and unchanged, [MOV]
```
> Si la pantalla se deforma al animar, conviene usar la versión con **pantalla verde** y pegar `UI_abrir_lote_movil.webp` en la edición. Esto se ve en la Etapa 5.

---

## ETAPA 2 — Acto 2 · El día a día

### 2.1 · T05 Comedero llenándose ☐
- **Start frame:** `3_acto2/T05_comedero.webp`
- **Cámara:** *Static*, en **cámara lenta**
- **Archivo:** `6_clips/acto2/V05_comedero.mp4`
```
slow motion, golden feed pellets keep pouring into the pan feeder, chickens peck at the feed, dust particles floating in the light beams, [MOV]
```

### 2.2 · T06 Bebedero de niple ☐
- **Start frame:** `3_acto2/T06_bebedero.webp`
- **Cámara:** *Static macro*, en **cámara lenta**
- **Archivo:** `6_clips/acto2/V06_bebedero.mp4`
```
extreme slow motion, the water drop trembles and the chicken touches the nipple with its beak and drinks, the droplet catches the golden backlight, [MOV]
```

### 2.3 · T07 Pesaje de la muestra ☐
- **Start frame:** `3_acto2/T07_pesaje.webp`
- **Cámara:** *Slow orbit left*, un arco muy corto
- **Archivo:** `6_clips/acto2/V07_pesaje.mp4`
```
the hands gently lower the white chicken into the weighing bucket, the bucket sways slightly and settles, the chicken stays calm, camera makes a very small slow arc around the scale, [MOV]
```

### 2.4 · T08a Cámara en el galpón ☐
- **Start frame:** `3_acto2/T08a_camara_galpon.webp`
- **Cámara:** *Slow tilt up* hacia la cámara de seguridad
- **Archivo:** `6_clips/acto2/V08a_camara.mp4`
```
camera slowly tilts up from the chickens to the dome security camera on the beam, the small infrared LEDs blink softly once, warm light through the curtains, [MOV]
```

### 2.5 · T08b Vista de cámara con clima ☐
- **Start frame:** `1_pantallas/UI_camara_clima.webp`
- **Cámara:** *Slow zoom in*
- **Archivo:** `6_clips/acto2/V08b_vista_camara.mp4`
```
only the video area inside the interface moves: the chickens in the live camera feed walk and peck naturally, the rest of the interface, the overlay cards and all text remain perfectly still and sharp, very slow zoom in, [MOV]
```
> **Si el texto se derrite:** no se anima con IA. Se pone la imagen en CapCut con un *zoom lento* (keyframe del 100 % al 108 %) y encima, con una máscara, un trozo del clip **V05** o **V14** dentro del recuadro de video.

### 2.6 · T09 Panel del lote en la laptop ☐
- **Start frame:** `3_acto2/T09_panel_monitor.webp`
- **Cámara:** *Slow dolly in* hacia la pantalla
- **Archivo:** `6_clips/acto2/V09_panel.mp4`
```
camera slowly dollies in toward the laptop screen, steam rising gently from the coffee mug, soft light changes through the window, the screen content remains sharp and unchanged, [MOV]
```
> Lo de **"la curva de peso subiendo"** se hace en la edición: un inserto de `UI_panel_lote.webp` en el que se revela la línea de izquierda a derecha con una máscara animada. Así los números no se deforman.

---

## ETAPA 3 — Acto 3 · Cuidar a tiempo

### 3.1 · T10 Alerta en el celular ☐
- **Start frame:** `4_acto3/T10_alerta_celular.webp`
- **Cámara:** *Static*, con un leve *push in*
- **Archivo:** `6_clips/acto3/V10_alerta.mp4`
```
the smartphone vibrates on the wooden table, a tiny shake, the screen glows brighter, steam rising from the coffee cup, camera slowly pushes in, the notification text remains sharp and unchanged, [MOV]
```

### 3.2 · T11 Veterinaria entrando ☐
- **Start frame:** `4_acto3/T11_vet_entrada.webp`
- **Cámara:** *Tracking / follow*, seguimiento suave
- **Archivo:** `6_clips/acto3/V11_vet_entrada.mp4`
```
the veterinarian steps through the disinfection footbath and walks into the chicken house carrying the cooler box, water rippling in the footbath, camera follows her smoothly from behind, golden backlight in the doorway, [MOV]
```

### 3.3 · T12 Vacuna ocular ☐
- **Start frame:** `4_acto3/T12_vacuna_ocular.webp`
- **Cámara:** *Static macro*, en **cámara lenta**
- **Archivo:** `6_clips/acto3/V12_vacuna.mp4`
```
extreme slow motion, a single vaccine drop falls from the dropper into the chick's eye, the chick blinks calmly, gloved hands hold it gently and steady, [MOV]
```

### 3.4 · T13 Dar conformidad en la tablet ☐
- **Start frame:** `4_acto3/T13_vet_tablet.webp`
- **Cámara:** *Slow push in* hacia la tablet
- **Archivo:** `6_clips/acto3/V13_conformidad.mp4`
```
the veterinarian's gloved finger taps the golden button on the tablet, a soft green check confirmation appears on the button, she lowers the tablet slightly, chickens moving in the blurred background, the rest of the screen remains sharp and unchanged, [MOV]
```
> **Opcional, para un toque más limpio:** generar un **End frame** con la misma imagen y el botón ya en verde, editado con *Inpaint*: `the golden button turned into a green button with a white check mark`. Así el modelo hace la transición sin inventar.

---

## ETAPA 4 — Acto 4 · El cierre

### 4.1 · T14 Pollos grandes al atardecer ☐
- **Start frame:** `5_acto4/T14_pollos_atardecer.webp`
- **Cámara:** *Slow dolly forward*, a la altura del ave
- **Archivo:** `6_clips/acto4/V14_atardecer.mp4`
```
camera glides slowly forward at chicken eye level between the large healthy chickens, chickens walking calmly, golden sunset backlight with dust particles floating, [MOV]
```

### 4.2 · T15 Productor revisando el reporte ☐
- **Start frame:** `5_acto4/T15_productor_reporte.webp`
- **Cámara:** *Slow pan right*
- **Archivo:** `6_clips/acto4/V15_reporte.mp4`
```
the farm owner scrolls the laptop touchpad slowly, nods slightly and smiles with satisfaction, sunset light shifting softly on his face, camera slowly pans, the screen content remains sharp, [MOV]
```

### 4.3 · T16 Productor y operario conversando ☐
- **Start frame:** `5_acto4/T16_conversacion.webp`
- **Cámara:** *Slow orbit right*, un arco corto en contrapicado
- **Archivo:** `6_clips/acto4/V16_conversacion.mp4`
```
the farm owner and the worker talk and laugh naturally, the owner pats the worker's shoulder, subtle hand gestures, golden sunset flare behind them, camera makes a slow small arc around them, faces stay consistent, [MOV]
```

### 4.4 · T17 Cámaras día → noche → térmica → IA (4 clips)
Estos clips se **funden entre sí** en la edición, así que la cámara debe moverse **igual** en los cuatro: *Static* con un *zoom in* muy lento.

**17a · Visual de día** ☐ — Start: `T17a_rgb_dia.webp` → `6_clips/acto4/V17a_dia.mp4`
```
static security camera view, chickens walking and pecking naturally, daylight steady, very slow zoom in, [MOV]
```

**17b · Infrarroja de noche** ☐ — Start: `T17b_ir_noche.webp` → `6_clips/acto4/V17b_noche.mp4`
```
static night vision security camera view, chickens resting and breathing, small subtle movements, slight infrared noise, very slow zoom in, [MOV]
```

**17c · Térmica** ☐ — Start: `T17c_termica.webp` → `6_clips/acto4/V17c_termica.mp4`
```
static thermal camera view, warm glowing chickens moving slowly, heat colors shifting subtly as they move, the cold blue zone near the curtain stays, very slow zoom in, [MOV]
```

**17d · IA detectando** ☐ — Start: `1_pantallas/UI_camaras_ia.webp` → `6_clips/acto4/V17d_ia.mp4`
```
inside each of the four camera feeds the chickens move slightly, the golden bounding boxes follow the chickens, the red box pulses softly once, all interface text and numbers remain perfectly still and sharp, very slow zoom in, [MOV]
```
> **Si el texto se deforma en la 17d:** usar la imagen fija con un zoom lento en CapCut.

**Plan B de la 17 (transición día → noche en un solo clip):** Start frame `T17a_rgb_dia.webp` y End frame `T17b_ir_noche.webp`, con este prompt:
```
the security camera view smoothly transitions from daylight color to night infrared black and white as night falls, same framing, [MOV]
```

### 4.5 · T18 Productor revisando el análisis ☐
- **Start frame:** `5_acto4/T18_productor_analisis.webp`
- **Cámara:** *Slow pull out*, se aleja despacio. Es el **cierre** del video
- **Archivo:** `6_clips/acto4/V18_analisis.mp4`
```
the farm owner swipes the tablet once with his finger and looks up toward the chicken house with a calm confident expression, camera slowly pulls back revealing more of the chicken house entrance at sunset, the screen content remains sharp, [MOV]
```

---

## ETAPA 5 — Montaje (CapCut o DaVinci Resolve)

### 5.1 Preparar el proyecto ☐
- Proyecto en **1920 × 1080, 30 fps**.
- Importar las carpetas `6_clips/acto1` a `acto4`, además de `1_pantallas/` para los insertos.

### 5.2 Música primero ☐
- Pista instrumental cálida (*acoustic*, *corporate inspiring*, *indie folk*) de **unos 80 s**, con licencia libre o pagada (biblioteca de audio de YouTube, Pixabay Music, Artlist).
- Poner **marcadores** en cada golpe fuerte de la música.
- Hacer coincidir los **cambios de acto** con los cambios de la música: 0:15, 0:35 y 0:55.

### 5.3 Armar la línea de tiempo ☐
- Colocar los clips en el orden del **Mapa de tiempos**.
- Cortar cada clip en su **mejor tramo**: el centro suele ser el más estable.
- **Cortar en los marcadores** de la música.
- Si un clip de 5 s es muy bueno, dividirlo en 2 cortes de unos 2 s con otra toma en medio. Así se logra el ritmo de 1,5–3 s que pide el guion.

### 5.4 Pantallas e insertos ☐
- **Pantallas verdes** (T04, T13 u otras si se usaron): aplicar *Chroma key*, poner la UI debajo y ajustar las 4 esquinas con *Corner pin* o *Máscara*.
- **T09, curva de peso:** inserto a pantalla completa de `UI_panel_lote.webp` y revelar la línea dorada con una máscara que avanza de izquierda a derecha en unos 2 s.
- **T08b y T17d:** si no se animaron con IA, usar la imagen fija con un zoom lento del 100 % al 108 %.

### 5.5 Transiciones ☐
- Por regla general, **corte directo**.
- **Fundido cruzado de 0,5 s** solo en:
  - T17a → T17b → T17c → T17d (día → noche → térmica → IA);
  - el último plano (T18), que termina con **fundido a negro** de 1 s.

### 5.6 Color ☐
- Aplicar un **mismo ajuste** a todos los clips: temperatura un poco cálida, verdes algo más profundos y negros suaves.
- **No** aplicarlo a las tomas 17b y 17c. La infrarroja y la térmica deben verse "técnicas".

### 5.7 Revisión ☐
- [ ] Sin ningún texto agregado (el guion pide video **sin texto**). Solo se ven los textos propios de las pantallas.
- [ ] Las caras de los personajes son coherentes entre tomas.
- [ ] Ningún pollo deforme ni mano extraña. Si hay alguno, recortar ese tramo.
- [ ] Duración total entre 60 y 80 s.
- [ ] La música termina junto con el fundido final.

### 5.8 Exportar ☐
| Parámetro | Valor |
|---|---|
| Formato | `.mp4`, H.264 |
| Resolución | 1920 × 1080 |
| Cuadros | 30 fps |
| Calidad | Alta (unos 12–16 Mbps) |
| Audio | AAC 320 kbps (música) |
| Archivo | `7_montaje/AviSmart_institucional.mp4` |

**Portada:** exportar un cuadro bonito (por ejemplo, de T14 o T16) como `7_montaje/AviSmart_institucional_portada.webp`.

---

## Control final de clips

| Etapa | Clips | ☐ |
|---|---|---|
| 1 · Acto 1 | V01–V04 (4) | ☐ |
| 2 · Acto 2 | V05–V09 (6) | ☐ |
| 3 · Acto 3 | V10–V13 (4) | ☐ |
| 4 · Acto 4 | V14–V18 (8) | ☐ |
| 5 · Montaje | `AviSmart_institucional.mp4` | ☐ |

**Recomendación de créditos en Higgsfield:** generar primero **una toma de cada acto** (T01, T05, T12 y T14) para validar que el estilo se mantiene. Recién después se generan todas las demás.
