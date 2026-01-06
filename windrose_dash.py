
# windrose_dash.py
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from processing import filter_by_period  # MM-JJ → MM-JJ

def build_windrose_figure(df_src, start_label, end_label, n_dir_bins, normalize):
    """
    Construit une rose des vents (Barpolar Plotly) en empilant les classes de vitesse.
    - Bins directionnels: n_dir_bins secteurs (4/8/16).
    - Bins vitesse fixes (km/h): [0–2, 2–5, 5–10, 10–20, 20–30, 30–40, 40–50, ≥50].
    - Normalisation: None/"None" (comptes), "total" (% du total), "dir" (% par secteur).
    """

    # 1) Période
    try:
        sm, sd = map(int, start_label.split('-'))
        em, ed = map(int, end_label.split('-'))
    except Exception:
        sm, sd, em, ed = 1, 1, 12, 31
    sub = filter_by_period(df_src, sm, sd, em, ed)

    # 2) Colonnes vent: m/s → km/h + nettoyage (sentinelles)
    dfw = sub[['WindDirection', 'WindSpeed']].copy()


    spd = dfw['WindSpeed'].astype(float) * 3.6            # m/s → km/h

    ang = dfw['WindDirection'].astype(float)
    # EPW sentinelles/aberrantes (ex. 999) → ignore
    spd = spd.mask((spd < 0) | (spd > 200))
    ang = ang.mask((ang < 0) | (ang >= 360))
    valid = spd.notna() & ang.notna()
    spd = spd[valid].to_numpy()
    ang = ang[valid].to_numpy()

    if spd.size == 0:
        return go.Figure().update_layout(
            template="plotly_white",
            title="Aucune donnée valide pour la période choisie",
            height=400
        )

    # 3) Bins directionnels (indices Numpy, sans pd.cut)
    bin_width = 360.0 / float(n_dir_bins)
    # Décalage + modulo pour que "N" couvre les valeurs autour de 0° (wrap 360↔0)
    ang_shift = (ang + bin_width / 2.0) % 360.0
    dir_idx = np.floor(ang_shift / bin_width).astype(int)  # 0..n_dir_bins-1

    # Centres (affichage) + labels
    dir_centers_deg = (np.arange(n_dir_bins) * bin_width) % 360.0
    if n_dir_bins == 16:
        cardinal = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    elif n_dir_bins == 8:
        cardinal = ["N","NE","E","SE","S","SW","W","NW"]
    elif n_dir_bins == 4:
        cardinal = ["N","E","S","W"]
    else:
        cardinal = [f"{int(e)}°" for e in dir_centers_deg]

    # 4) Bins vitesse fixes (overflow toujours présent)
    # edges: 0,2,5,10,20,30,40,50, +inf → 8 classes
    edges = np.array([0, 2, 5, 10, 20, 30, 40, 50, np.inf], dtype=float)
    spd_bin = np.digitize(spd, edges, right=False) - 1  # → 0..7 (8 classes)

    # 5) Matrice de comptes M (dir x vitesse)
    n_spd_bins = len(edges) - 1  # 8
    M = np.zeros((n_dir_bins, n_spd_bins), dtype=float)
    for k in range(n_spd_bins):
        sel = (spd_bin == k)
        if np.any(sel):
            counts = np.bincount(dir_idx[sel], minlength=n_dir_bins).astype(float)
            M[:, k] = counts

    M_sum = M.sum()

    if M_sum == 0:
        return go.Figure().update_layout(
            template="plotly_white",
            title="Aucune donnée valide pour la période choisie",
            height=400
        )

    # 6) Normalisation
    if normalize in (None, "None"):
        values = M
        r_label = "Comptes"
    elif normalize == "total":
        values = (M / M_sum) * 100.0
        r_label = "% du total"
    elif normalize == "dir":
        row_sum = M.sum(axis=1, keepdims=True)
        row_sum[row_sum == 0] = np.nan
        values = (M / row_sum) * 100.0
        values = np.nan_to_num(values)
        r_label = "% par secteur"
    else:
        values = M
        r_label = "Comptes"

    # 7) Libellés + couleurs
    speed_labels = ["< 2", "2–5", "5–10", "10–20", "20–30", "30–40", "40–50", "≥ 50"]
    base_colors = ["#E6FFE6","#BFFFBF","#99FF99","#66FF66","#33CC66","#33B266","#2EA64E","#FFD84D"]

    # 8) Figure barpolar (stack)
    bar_width_deg = bin_width * 0.92
    fig = go.Figure()
    for j in range(values.shape[1]):
        fig.add_trace(go.Barpolar(
            r=values[:, j],
            theta=dir_centers_deg,
            name=f"{speed_labels[j]} km/h",
            marker_color=base_colors[j],
            width=np.full(n_dir_bins, bar_width_deg),
            hovertemplate="%{theta}°<br>Classe: " + speed_labels[j] + " km/h<br>" + r_label + ": %{r:.2f}"
        ))

    fig.update_layout(
        template='plotly_white',
        title=f"Rose des vents ({r_label})",
        polar=dict(
            angularaxis=dict(
                direction="clockwise",
                rotation=90,   # 0° = Nord
                tickmode='array',
                tickvals=dir_centers_deg,
                ticktext=cardinal
            ),
            radialaxis=dict(
                ticks='outside',
                showline=True,
                gridcolor='rgba(0,0,0,0.2)'
            )
        ),
        legend=dict(
            x=0.99, y=0.99, xanchor='right', yanchor='top',
            bgcolor='rgba(255,255,255,0.6)', bordercolor='rgba(0,0,0,0.2)', borderwidth=1
        ),
        margin=dict(l=60, r=20, t=60, b=60),
        height=700,
        barmode='stack'
    )
    return fig