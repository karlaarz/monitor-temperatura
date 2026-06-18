# Monitor de Temperatura

Dashboard interactivo de temperatura y humedad por habitación, generado a partir de
un CSV de lecturas. La página `index.html` es autónoma (incluye datos y Plotly.js) y
se publica con GitHub Pages.

## Contenido

- `index.html` — dashboard listo para abrir o publicar.
- `build_dashboard.py` — genera `index.html` desde los CSV.
- `template.html` — estructura, estilos y lógica de la página.
- `recamara _data.csv` — datos de ejemplo (una habitación).

## Regenerar

Cuando actualices los datos:

```bash
python3 build_dashboard.py
git add index.html "recamara _data.csv"
git commit -m "Actualizar datos"
git push
```

`build_dashboard.py` descarga `plotly.min.js` la primera vez (queda en caché local) y
lo embebe en `index.html`.

## Agregar más habitaciones

Edita la lista `ROOMS` en `build_dashboard.py` con `(nombre, ruta_al_csv)`. Aparecen
pestañas automáticamente.
