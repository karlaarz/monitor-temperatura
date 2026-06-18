# Termómetro Dashboard — Diseño

Fecha: 2026-06-18

## Objetivo

Generar un dashboard HTML interactivo, autónomo y offline que muestre, para una
habitación, la temperatura máxima y mínima y la humedad, con gráficas y opción de
"Ver más" para análisis en detalle. Diseñado para una sola habitación ahora
(`recamara`), pero estructurado para agregar más habitaciones después.

La interfaz de usuario está completamente en español.

## Datos de entrada

Archivo: `recamara _data.csv` (nota: el nombre contiene un espacio).

- ~217,000 filas, una por minuto, del 14/01/2026 al 14/06/2026.
- Columnas:
  - `Date` — formato día primero `dd/mm/yyyy HH:MM`
  - `Temperature_Celsius(℃)`
  - `Relative_Humidity(%)`
  - `DPT(℃)` — punto de rocío
  - `VPD(kPa)`
  - `Abs Humidity(g/m³)` — humedad absoluta

## Arquitectura

Dos piezas:

1. `build_dashboard.py` — script Python (pandas) que lee el CSV, agrega los datos y
   escribe `dashboard.html` con los datos embebidos. Se vuelve a ejecutar cuando los
   datos se actualizan.
2. `dashboard.html` — archivo único, autónomo, offline. Se abre con doble clic, sin
   servidor ni internet.

## Preparación de datos (build_dashboard.py)

- Parsear `Date` con día primero (`dayfirst=True`).
- Producir y embeber como JSON en el HTML:
  - **hourly** (vista general): por hora, min/max/promedio de temperatura y humedad
    relativa, más punto de rocío, VPD y humedad absoluta (promedio). ~3,600 puntos →
    gráfica fluida de todo el rango.
  - **daily_detail** (drill-down): datos por minuto agrupados por día (1440 pts/día).
    Guardados como arreglos compactos (no objetos) para reducir tamaño.
  - **summary**: estadísticas globales — temp máxima + fecha/hora, temp mínima +
    fecha/hora, humedad relativa máx / mín / promedio. Rango de fechas.
- Estructura keyed por nombre de habitación para permitir múltiples habitaciones
  después (por ahora solo `recamara`).

## Librería de gráficas

Plotly.js embebido inline en el HTML (offline). Provee zoom, pan, hover y
activar/desactivar series de forma nativa.

## Diseño de la página (de arriba a abajo, en español)

1. **Encabezado** — título "Recámara · Monitor de Temperatura" y rango de fechas.
2. **Tarjetas resumen**:
   - 🌡️ Temperatura máxima + fecha/hora
   - 🌡️ Temperatura mínima + fecha/hora
   - 💧 Humedad relativa: máxima / mínima / promedio
3. **Botón "Ver más"** — expande la sección de detalle (oculta al inicio).
4. **Sección de detalle**:
   - **Gráfica principal** — temperatura + humedad relativa (hourly) en todo el
     rango. Casillas para mostrar/ocultar: punto de rocío, VPD, humedad absoluta.
     Zoom y pan.
   - **Detalle por día** — selector de fecha; al elegir un día se muestra la curva
     por minuto de ese día.
   - **Tabla diaria** — min/max/promedio por día, ordenable.

## Extensibilidad a múltiples habitaciones

- Datos y render keyed por nombre de habitación.
- Agregar habitaciones después = iterar sobre varios CSV / varias claves; la
  estructura no cambia.

## Manejo de errores

- Si el CSV no existe o el nombre no coincide, el script falla con mensaje claro.
- Filas con valores faltantes o no numéricos se descartan al agregar (con conteo
  reportado en consola).

## Pruebas

- Verificar el parseo de fechas (día primero) con muestras conocidas.
- Verificar que summary (máx/min) coincide con cálculo directo sobre el CSV.
- Abrir `dashboard.html` y confirmar: tarjetas, gráfica, drill-down por día y tabla.
