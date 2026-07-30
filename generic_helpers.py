# generic_helpers.py
import pandas as pd

#--------------------------------------------------------
#--------------------- Affichage -------------------------
#--------------------------------------------------------

def hex_to_rgba(hex_color, alpha):

    hex_color = hex_color.lstrip('#')

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f"rgba({r},{g},{b},{alpha})"

def pad_y_axis_range(y0: float, y1: float, min_pad: float = 1e-6):
    """Élargit [y0, y1] de pad_ratio (±%) pour une marge visuelle uniforme."""
    pad_ratio = 0.05  # ajuste à 0.02..0.05 pour rapprocher visuellement les bornes de l'axe y en mode 'Fixe' et 'Auto'

    if y0 is None or y1 is None:
        return None
    a, b = (float(y0), float(y1))
    if a == b:
        pad = max(min_pad, abs(a) * pad_ratio)
        return [a - pad, b + pad]
    lo, hi = (a, b) if a < b else (b, a)
    span = hi - lo
    pad = max(min_pad, span * pad_ratio)
    return [lo - pad, hi + pad]

#--------------------------------------------------------
#--------------------- Handling dates--------------------
#--------------------------------------------------------

def mmdd_to_ref_dates(start_label: str, end_label: str, year: int):
    """'DD.MM' -> (Timestamp start, Timestamp end) dans l'année de référence.
       Si parsing échoue, défaut 01.01 -> 31.12. Si end < start, on inverse."""
    def _parse(label, default):
        try:
            d, m = map(int, (label or '').split('.'))
            return pd.Timestamp(year=year, month=m, day=d)
        except Exception:
            return default
    s = _parse(start_label, pd.Timestamp(year=year, month=1, day=1))
    e = _parse(end_label, pd.Timestamp(year=year, month=12, day=31))
    if e < s:
        s, e = e, s
    return s, e


def parse_mmdd(label: str, default=(1, 1)):
    """'DD.MM' -> (day, month) avec fallback."""
    try:
        d, m = map(int, (label or '').split('.'))
        return d, m
    except Exception:
        return default


#--------------------------------------------------------
#--------------------- Axes range with relayout----------
#--------------------------------------------------------

def extract_range_from_relayout(relayout):
    """Extrait une plage [y0, y1] depuis relayoutData (Zoom/Pan Plotly), si présent."""
    if not relayout:
        return None
    if 'yaxis.range' in relayout and isinstance(relayout['yaxis.range'], (list, tuple)) and len(relayout['yaxis.range']) == 2:
        y0, y1 = relayout['yaxis.range']
        return [float(y0), float(y1)]
    y0 = relayout.get('yaxis.range[0]')
    y1 = relayout.get('yaxis.range[1]')
    if y0 is not None and y1 is not None:
        return [float(y0), float(y1)]
    return None


#Gestion des limites d'axe et du zoom
def extract_axis_ranges_or_auto(relayout):
    """
    Analyse relayoutData pour extraire:
      - xrange (liste [x0, x1]) OU 'auto' si autoscale demandé, sinon None
      - yrange (liste [y0, y1]) OU 'auto' si autoscale demandé, sinon None
    """
    xr = yr = None

    if not relayout:
        return None, None

    # --- X ---
    # cas autoscale/double-clic
    if relayout.get('xaxis.autorange') is True:
        xr = 'auto'
    # cas range explicite
    elif 'xaxis.range' in relayout and isinstance(relayout['xaxis.range'], (list, tuple)) and len(relayout['xaxis.range']) == 2:
        xr = [pd.to_datetime(relayout['xaxis.range'][0]), pd.to_datetime(relayout['xaxis.range'][1])]
    else:
        x0 = relayout.get('xaxis.range[0]')
        x1 = relayout.get('xaxis.range[1]')
        if x0 is not None and x1 is not None:
            xr = [pd.to_datetime(x0), pd.to_datetime(x1)]

    # --- Y ---
    if relayout.get('yaxis.autorange') is True:
        yr = 'auto'
    elif 'yaxis.range' in relayout and isinstance(relayout['yaxis.range'], (list, tuple)) and len(relayout['yaxis.range']) == 2:
        y0, y1 = relayout['yaxis.range']
        yr = [float(y0), float(y1)]
    else:
        y0 = relayout.get('yaxis.range[0]')
        y1 = relayout.get('yaxis.range[1]')
        if y0 is not None and y1 is not None:
            yr = [float(y0), float(y1)]

    return xr, yr