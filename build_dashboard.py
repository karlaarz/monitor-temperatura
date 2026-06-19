#!/usr/bin/env python3
"""Genera un dashboard HTML autónomo (offline) de temperatura/humedad por habitación.

Lee uno o más CSV de habitaciones, agrega los datos y escribe `dashboard.html`
con todo embebido (datos + Plotly.js). Se abre con doble clic, sin servidor.

Uso:
    python3 build_dashboard.py

Por ahora procesa una sola habitación ("Recámara"). Para agregar más, añade
entradas a la lista ROOMS.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

# --- Configuración -----------------------------------------------------------

BASE = Path(__file__).resolve().parent

# (nombre visible, ruta del CSV). Para agregar habitaciones, añade más tuplas.
# Si un CSV no existe todavía, se omite con un aviso (no es error).
ROOMS = [
    ("Recámara", BASE / "recamara _data.csv"),
    ("Cocina", BASE / "cocina_data.csv"),
    ("Exterior", BASE / "exterior_data.csv"),
]

OUTPUT = BASE / "index.html"
PLOTLY_LOCAL = BASE / "plotly.min.js"
PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

COL_TEMP = "Temperature_Celsius(℃)"
COL_RH = "Relative_Humidity(%)"
COL_DPT = "DPT(℃)"
COL_VPD = "VPD(kPa)"
COL_ABS = "Abs Humidity(g/m³)"
NUMERIC_COLS = [COL_TEMP, COL_RH, COL_DPT, COL_VPD, COL_ABS]


# --- Carga y limpieza --------------------------------------------------------

def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        sys.exit(f"ERROR: no se encontró el CSV: {path}")

    df = pd.read_csv(path)

    missing = [c for c in ["Date", *NUMERIC_COLS] if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: faltan columnas en {path.name}: {missing}")

    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    for c in NUMERIC_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["Date", COL_TEMP, COL_RH])
    dropped = before - len(df)
    if dropped:
        print(f"  {path.name}: {dropped} filas descartadas (fecha/valores inválidos)")

    df = df.sort_values("Date").reset_index(drop=True)
    return df


# --- Agregación --------------------------------------------------------------

def round_series(s: pd.Series, n: int) -> list:
    return [None if pd.isna(v) else round(float(v), n) for v in s]


MESES_ES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

FMT = "%d/%m/%Y %H:%M"


def extremes(g: pd.DataFrame) -> dict:
    """Extremos de temperatura y humedad de un grupo, con su fecha/hora."""
    it_max = g[COL_TEMP].idxmax()
    it_min = g[COL_TEMP].idxmin()
    ih_max = g[COL_RH].idxmax()
    ih_min = g[COL_RH].idxmin()
    return {
        "temp_max": round(float(g.loc[it_max, COL_TEMP]), 1),
        "temp_max_when": g.loc[it_max, "Date"].strftime(FMT),
        "temp_min": round(float(g.loc[it_min, COL_TEMP]), 1),
        "temp_min_when": g.loc[it_min, "Date"].strftime(FMT),
        "rh_max": int(g.loc[ih_max, COL_RH]),
        "rh_max_when": g.loc[ih_max, "Date"].strftime(FMT),
        "rh_min": int(g.loc[ih_min, COL_RH]),
        "rh_min_when": g.loc[ih_min, "Date"].strftime(FMT),
    }


def build_room_data(df: pd.DataFrame) -> dict:
    # Resumen global
    i_max = df[COL_TEMP].idxmax()
    i_min = df[COL_TEMP].idxmin()
    fmt = FMT
    summary = {
        "temp_max": round(float(df.loc[i_max, COL_TEMP]), 1),
        "temp_max_when": df.loc[i_max, "Date"].strftime(fmt),
        "temp_min": round(float(df.loc[i_min, COL_TEMP]), 1),
        "temp_min_when": df.loc[i_min, "Date"].strftime(fmt),
        "rh_max": int(df[COL_RH].max()),
        "rh_min": int(df[COL_RH].min()),
        "rh_avg": round(float(df[COL_RH].mean()), 1),
        "date_start": df["Date"].min().strftime("%d/%m/%Y"),
        "date_end": df["Date"].max().strftime("%d/%m/%Y"),
        "n": int(len(df)),
    }

    # Extremos por semana (lunes a domingo) y por mes
    weeks = []
    wp = df["Date"].dt.to_period("W-SUN")
    for per, g in df.groupby(wp):
        rec = extremes(g)
        rec["start"] = per.start_time.strftime("%d/%m/%Y")
        rec["end"] = per.end_time.strftime("%d/%m/%Y")
        rec["start_iso"] = per.start_time.strftime("%Y-%m-%d")
        rec["end_iso"] = per.end_time.strftime("%Y-%m-%d")
        rec["label"] = f"{rec['start']} – {rec['end']}"
        weeks.append(rec)

    months = []
    mp = df["Date"].dt.to_period("M")
    for per, g in df.groupby(mp):
        rec = extremes(g)
        rec["label"] = f"{MESES_ES[per.month]} {per.year}"
        months.append(rec)

    # Vista general por hora
    h = df.set_index("Date").resample("h")
    hourly_df = pd.DataFrame({
        "t": [d.strftime("%Y-%m-%dT%H:%M") for d in h[COL_TEMP].mean().index],
        "temp": h[COL_TEMP].mean().round(2).values,
        "temp_min": h[COL_TEMP].min().round(2).values,
        "temp_max": h[COL_TEMP].max().round(2).values,
        "rh": h[COL_RH].mean().round(1).values,
        "dpt": h[COL_DPT].mean().round(2).values,
        "vpd": h[COL_VPD].mean().round(3).values,
        "abs": h[COL_ABS].mean().round(2).values,
    }).dropna(subset=["temp"])

    hourly = {
        "t": hourly_df["t"].tolist(),
        "temp": round_series(hourly_df["temp"], 2),
        "temp_min": round_series(hourly_df["temp_min"], 2),
        "temp_max": round_series(hourly_df["temp_max"], 2),
        "rh": round_series(hourly_df["rh"], 1),
        "dpt": round_series(hourly_df["dpt"], 2),
        "vpd": round_series(hourly_df["vpd"], 3),
        "abs": round_series(hourly_df["abs"], 2),
    }

    # Detalle agrupado por día (submuestreo a 5 min para aligerar el HTML)
    DETAIL_STEP = 5  # minutos entre puntos del gráfico "Un día"
    df = df.assign(_day=df["Date"].dt.strftime("%Y-%m-%d"),
                   _hm=df["Date"].dt.strftime("%H:%M"))
    daily_detail = {}
    for day, g in df.groupby("_day"):
        g = g.iloc[::DETAIL_STEP]
        daily_detail[day] = {
            "hm": g["_hm"].tolist(),
            "temp": round_series(g[COL_TEMP], 1),
            "rh": round_series(g[COL_RH], 0),
            "dpt": round_series(g[COL_DPT], 1),
            "vpd": round_series(g[COL_VPD], 2),
            "abs": round_series(g[COL_ABS], 2),
        }

    # Heatmap: días (filas) x hora del día (columnas), temperatura promedio
    df = df.assign(_hour=df["Date"].dt.hour)
    pivot = df.pivot_table(index="_day", columns="_hour",
                           values=COL_TEMP, aggfunc="mean")
    pivot = pivot.reindex(columns=range(24))
    heatmap = {
        "days": list(pivot.index),
        "hours": [f"{h:02d}:00" for h in range(24)],
        "z": [[None if pd.isna(v) else round(float(v), 1) for v in row]
              for row in pivot.values],
    }

    # Heatmap mes x hora (temperatura promedio)
    df = df.assign(_month=df["Date"].dt.month)
    mpivot = df.pivot_table(index="_month", columns="_hour",
                            values=COL_TEMP, aggfunc="mean").reindex(columns=range(24))
    heatmap_month = {
        "months": [MESES_ES[m] for m in mpivot.index],
        "hours": [f"{h:02d}:00" for h in range(24)],
        "z": [[None if pd.isna(v) else round(float(v), 1) for v in row]
              for row in mpivot.values],
    }

    # Patrón día/noche: promedio por hora del día (0-23)
    by_hour = df.groupby("_hour")[[COL_TEMP, COL_RH]].mean().reindex(range(24))
    pattern = {
        "hours": [f"{h:02d}:00" for h in range(24)],
        "temp": round_series(by_hour[COL_TEMP], 2),
        "rh": round_series(by_hour[COL_RH], 1),
    }

    # Banda de confort: % del tiempo dentro de rango
    t_lo, t_hi, h_lo, h_hi = 18, 24, 40, 60
    n = len(df)
    in_temp = df[COL_TEMP].between(t_lo, t_hi)
    in_rh = df[COL_RH].between(h_lo, h_hi)
    comfort = {
        "t_lo": t_lo, "t_hi": t_hi, "h_lo": h_lo, "h_hi": h_hi,
        "temp_pct": round(float(in_temp.mean()) * 100, 1),
        "rh_pct": round(float(in_rh.mean()) * 100, 1),
        "both_pct": round(float((in_temp & in_rh).mean()) * 100, 1),
    }

    return {
        "summary": summary,
        "weeks": weeks,
        "months": months,
        "hourly": hourly,
        "daily_detail": daily_detail,
        "heatmap": heatmap,
        "heatmap_month": heatmap_month,
        "pattern": pattern,
        "comfort": comfort,
    }


# --- Plotly.js ---------------------------------------------------------------

def get_plotly_js() -> str:
    if PLOTLY_LOCAL.exists():
        return PLOTLY_LOCAL.read_text(encoding="utf-8")
    print(f"  Descargando Plotly desde {PLOTLY_CDN} ...")
    try:
        with urllib.request.urlopen(PLOTLY_CDN, timeout=30) as r:
            js = r.read().decode("utf-8")
        PLOTLY_LOCAL.write_text(js, encoding="utf-8")
        return js
    except Exception as e:
        sys.exit(f"ERROR: no se pudo obtener Plotly.js ({e}). "
                 f"Descárgalo manualmente a {PLOTLY_LOCAL}")


# --- HTML --------------------------------------------------------------------

def render_html(rooms: dict, plotly_js: str) -> str:
    data_json = json.dumps(rooms, ensure_ascii=False)
    template = (BASE / "template.html").read_text(encoding="utf-8")
    return (template
            .replace("/*__PLOTLY_JS__*/", plotly_js)
            .replace("/*__DATA_JSON__*/", data_json))


def main() -> None:
    print("Generando dashboard...")
    rooms = {}
    for name, path in ROOMS:
        if not path.exists():
            print(f"- Omitiendo {name}: no se encontró {path.name}")
            continue
        print(f"- Procesando {name} ({path.name})")
        df = load_csv(path)
        rooms[name] = build_room_data(df)

    if not rooms:
        sys.exit("ERROR: no se procesó ninguna habitación.")

    plotly_js = get_plotly_js()
    html = render_html(rooms, plotly_js)
    OUTPUT.write_text(html, encoding="utf-8")
    size_mb = OUTPUT.stat().st_size / 1e6
    print(f"OK -> {OUTPUT.name} ({size_mb:.1f} MB). Ábrelo con doble clic.")


if __name__ == "__main__":
    main()
