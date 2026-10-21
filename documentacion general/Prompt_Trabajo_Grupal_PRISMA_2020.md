# TRABAJO GRUPAL – BÚSQUEDA BIBLIOGRÁFICA PRISMA 2020

Estamos desarrollando la investigación titulada:

*Análisis longitudinal de la mortalidad en jaulas de trucha arcoíris del lago Titicaca y evaluación complementaria de modelos predictivos mediante datos abiertos de acuicultura.*

Estamos aplicando PRISMA 2020 y ya realizamos una primera recuperación bibliográfica en OpenAlex. Ahora necesitamos ampliar la búsqueda mediante **PubMed y Google Scholar**, manteniendo un procedimiento documentado y reproducible.

La revisión tiene dos líneas:

- **Línea A:** mortalidad, supervivencia y factores ambientales/productivos en trucha arcoíris y otros salmónidos cultivados.
- **Línea B:** modelos estadísticos, Machine Learning, predicción de mortalidad y modelación de variables ambientales relevantes, como temperatura y oxígeno disuelto.

## COMPAÑERO 1 – PUBMED (LÍNEA A)

Ingresar a: https://pubmed.ncbi.nlm.nih.gov/

Realizar la búsqueda:

```text
(
  "rainbow trout"[tiab] OR
  "Oncorhynchus mykiss"[tiab] OR
  salmonid*[tiab] OR
  "Atlantic salmon"[tiab] OR
  "Salmo salar"[tiab]
)
AND
(
  aquaculture[tiab] OR
  farming[tiab] OR
  farmed[tiab] OR
  "fish farm"[tiab]
)
AND
(
  mortality[tiab] OR
  survival[tiab]
)
```

Registrar la cantidad de resultados y exportar todos los registros recuperados en formato CSV y, preferentemente, también NBIB mediante `Send to → Citation Manager`.

Nombre sugerido: `PubMed_Linea_A`.

## COMPAÑERO 2 – PUBMED (LÍNEA B)

Utilizar la misma página de PubMed y ejecutar:

```text
(
  "rainbow trout"[tiab] OR
  "Oncorhynchus mykiss"[tiab] OR
  salmonid*[tiab] OR
  "Atlantic salmon"[tiab] OR
  "Salmo salar"[tiab]
)
AND
(
  aquaculture[tiab] OR
  farming[tiab] OR
  farmed[tiab] OR
  "fish farm"[tiab]
)
AND
(
  mortality[tiab] OR
  survival[tiab] OR
  "dissolved oxygen"[tiab] OR
  hypoxia[tiab] OR
  "water temperature"[tiab]
)
AND
(
  prediction[tiab] OR
  forecasting[tiab] OR
  "machine learning"[tiab] OR
  "time series"[tiab] OR
  regression[tiab] OR
  modeling[tiab] OR
  modelling[tiab]
)
```

Registrar los resultados y exportarlos en CSV y, preferentemente, NBIB.

Nombre sugerido: `PubMed_Linea_B`.

Si alguna búsqueda devuelve muy pocos resultados, no modificarla sin dejar constancia de la ecuación original y de la nueva versión.

## COMPAÑERO 3 – GOOGLE SCHOLAR

Ingresar a: https://scholar.google.com/

Realizar estas tres búsquedas por separado:

**GS1 – Mortalidad:**

```text
"rainbow trout" mortality aquaculture
```

**GS2 – Predicción:**

```text
"salmon" "mortality" prediction
```

**GS3 – Condiciones ambientales:**

```text
"aquaculture" "dissolved oxygen" prediction
```

Registrar por separado los resultados de cada búsqueda.

Revisar y documentar los primeros 100 resultados accesibles de cada consulta, o todos si aparecen menos. Si se elige otro alcance, informar exactamente cuántos se revisaron.

De los artículos pertinentes, recopilar los metadatos mediante la opción de cita del buscador, la página de la revista o el DOI. Preparar una hoja Excel con los artículos localizados. No utilizar herramientas de extracción masiva que incumplan las condiciones de Google Scholar.

## COLUMNAS OBLIGATORIAS PARA LOS ARCHIVOS

Necesitamos conservar, siempre que estén disponibles:

| Columna | Contenido |
|---|---|
| ID | Identificador del registro |
| Fuente | PubMed o Google Scholar |
| Búsqueda | A, B, GS1, GS2 o GS3 |
| Title | Título completo |
| Authors | Autores |
| Year | Año de publicación |
| DOI | Identificador DOI |
| PMID | Identificador PubMed, cuando corresponda |
| Journal | Revista o fuente |
| Abstract | Resumen del artículo |
| Keywords | Palabras clave |
| Publication type | Tipo de publicación |
| URL | Enlace directo al artículo |
| Open access | Acceso abierto, si se puede comprobar |
| Species | Especie estudiada, si se identifica |
| Target variable | Mortalidad, supervivencia, oxígeno, temperatura, etc., si se identifica |

Si una columna no está disponible, dejarla vacía. **No inventar valores ni utilizar información generada por IA como sustituto de los metadatos originales.**

## REGISTRO DE AUDITORÍA

Además de los artículos, cada compañero debe entregar una pequeña hoja denominada `Auditoria_Busqueda`, con:

1. Nombre del buscador.
2. Fecha de ejecución.
3. Ecuación exacta utilizada.
4. URL de la búsqueda, si está disponible.
5. Filtros aplicados (o indicar que no se aplicaron).
6. Cantidad total de resultados mostrados.
7. Cantidad de registros realmente exportados o revisados.
8. Formato y nombre del archivo.
9. Observaciones o dificultades.

Guardar una captura de pantalla de los resultados como respaldo adicional, sin incluir información privada de la cuenta.

## IMPORTANTE

No eliminar duplicados, no descartar artículos por cuenta propia y no limitar artificialmente los resultados a 30 o 250.

Tampoco debemos incluir únicamente estudios con resultados positivos: las investigaciones con resultados negativos o modelos de bajo desempeño pueden ser igualmente relevantes.

Cada compañero entregará su archivo original de exportación y su registro de auditoría. Posteriormente unificaremos todas las bases, detectaremos coincidencias y realizaremos el cribado conforme a PRISMA 2020.

**Entregables:** CSV/NBIB o Excel, registro de auditoría y capturas de respaldo.

El propósito no es juntar artículos al azar, sino construir una base bibliográfica trazable que permita justificar cada etapa de nuestra revisión sistemática.
