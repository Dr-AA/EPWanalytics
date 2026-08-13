
# data_processing.py
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import StringIO
from weather_graph.config_weather_graph import FREQ_MAP, FUNC_MAP

def build_master_df(store):
    if not store:
        print("store is empty")
        return pd.DataFrame()

    dfs = [
        pd.read_json(StringIO(p["df"]))
        for p in store.values()
    ]

    if not dfs:
        print("dfs is empty")
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)

def compute_aggregated_df(all_df: pd.DataFrame, period_label: str, func_label: str, var_col: str) -> pd.DataFrame:
    # Aggrège les données selon la période period_label et la fonction func_label, pour la variable var_col
    freq = FREQ_MAP[period_label]
    func = FUNC_MAP[func_label]

    if var_col not in all_df.columns:
        # Sécurité : renvoyer un DF vide si la variable n'existe pas
        return pd.DataFrame(columns=["source", "datetime", var_col])

    # 1) Agrégation par période
    base = (
        all_df.set_index("datetime")
        .groupby(["source","source_label"])[var_col]
        .resample(freq)
    )

    if func == "cumsum":
        # 1a) On somme par période (additive), quelle que soit la variable, puis on cumulera par source.
        aggregated = base.sum().reset_index()
        aggregated = aggregated.sort_values(["source", "datetime"])
        # 2) Cumul par source
        aggregated[var_col] = aggregated.groupby("source")[var_col].cumsum()

    elif func == "mean_min_max":
        mean_df = base.mean().reset_index()
        mean_df["stat"] = "mean"
        min_df = base.min().reset_index()
        min_df["stat"] = "min"
        max_df = base.max().reset_index()
        max_df["stat"] = "max"
        aggregated = pd.concat([mean_df, min_df, max_df],ignore_index=True)

    else:
        # Cas standard: func est un string ('mean','min',...) ou une fonction lambda (pour les quantiles)
        aggregated = base.agg(func).reset_index()

    return aggregated

def filter_by_period(df: pd.DataFrame, start_day: int, start_month: int,
                     end_day: int, end_month: int) -> pd.DataFrame:
    """
    Filtre [df] entre DD-MM -> DD-MM, en utilisant directement datetime.dt.dayofyear.
    S'il n'y a aucun datetime valide (tout NaT), la fonction renvoie df tel quel (pas de filtre).
    """
    out = df.copy()
    out['datetime'] = pd.to_datetime(out['datetime'], errors='coerce')

    # Si tout est NaT: ne pas filtrer
    if out['datetime'].isna().all():
        # print('[filter_by_period] datetime is all NaT -> skip filtering')
        return out

    doy = out['datetime'].dt.dayofyear

    start = pd.Timestamp(year=2001, month=start_month, day=start_day).day_of_year
    end   = pd.Timestamp(year=2001, month=end_month,  day=end_day).day_of_year

    if start <= end:
        mask = (doy >= start) & (doy <= end)
    else:
        # période chevauchante (ex. 11-01 → 02-28)
        mask = (doy >= start) | (doy <= end)

    # Fallback si mask est tout False (ex: erreur de typage atypique)
    if not mask.any():
        # print('[filter_by_period] mask empty -> return df unchanged')
        return out

    return out.loc[mask].copy()


#--------------------------------------------------------
#--------------------- Heat map, Wind rose---------------
#--------------------------------------------------------

def build_heatmap_matrix(df: pd.DataFrame, var_col: str) -> pd.DataFrame:
    """
    Crée la matrice Heatmap : index=heure (0..23), colonnes=jour de l'année (1..365/366),
    valeurs=mean(var) par (heure, DOY).
    """
    sub = df.copy()
    sub['datetime'] = pd.to_datetime(sub['datetime'], errors='coerce')
    sub = sub.dropna(subset=['datetime'])
    if sub.empty or var_col not in sub.columns:
        return pd.DataFrame()

    sub['doy'] = sub['datetime'].dt.dayofyear
    sub['hour'] = sub['datetime'].dt.hour
    mat = sub.pivot_table(index='hour', columns='doy', values=var_col, aggfunc='mean')
    # S'assurer que les axes sont complets (0..23 et 1..365/366)
    hours = list(range(0, 24))
    doys = sorted(mat.columns.unique().tolist())
    if not doys:  # aucun jour présent
        return pd.DataFrame()
    mat = mat.reindex(index=hours, columns=doys)
    return mat

def build_windrose_figure(df_src, start_label, end_label, n_dir_bins, normalize):
    """
    Construit une rose des vents (Barpolar Plotly) en empilant les classes de vitesse.
    - Bins directionnels: n_dir_bins secteurs (4/8/16).
    - Bins vitesse fixes (km/h): [0–2, 2–5, 5–10, 10–20, 20–30, 30–40, 40–50, ≥50].
    - Normalisation: None/"None" (comptes), "total" (% du total), "dir" (% par secteur).
    """

    # 1) Période
    try:
        sd, sm = map(int, start_label.split('.'))
        ed, em = map(int, end_label.split('.'))
    except Exception:
        print("EXCEPT DATE")
        sm, sd, em, ed = 1, 1, 12, 31
    print(f"Start : {sd}.{sm} | End : {ed}.{em}")
    sub = filter_by_period(df_src, sd, sm, ed, em)

    # 2) Colonnes vent: m/s → km/h + nettoyage (sentinelles)
    dfw = sub[['Wind direction (°)', 'Wind speed mean (m/s)']].copy()


    spd = dfw['Wind speed mean (m/s)'].astype(float) * 3.6            # m/s → km/h

    ang = dfw['Wind direction (°)'].astype(float)
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
    if normalize in (None, "heures"):
        values = M
        r_label = "Nombre d'heures"
        radial_ticksuffix = "h"
    elif normalize == "total":
        values = (M / M_sum) * 100.0
        r_label = "% du total"
        radial_ticksuffix = "%"
    elif normalize == "dir":
        row_sum = M.sum(axis=1, keepdims=True)
        row_sum[row_sum == 0] = np.nan
        values = (M / row_sum) * 100.0
        values = np.nan_to_num(values)
        r_label = "% par secteur"
        radial_ticksuffix = "%"
    else:
        values = M
        r_label = "Nombre d'heures"

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
                ticksuffix=radial_ticksuffix,
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


def detect_events(
    df: pd.DataFrame,
    variable: str,
    period_label: str,
    func_label: str,
    threshold_min: float | None = None,
    threshold_max: float | None = None,
    duration_min: int = 1,
) -> pd.DataFrame:

    if threshold_min is None and threshold_max is None:
        return pd.DataFrame()
    if duration_min is None or duration_min < 1:
        return pd.DataFrame()

    agg = compute_aggregated_df(df, period_label, func_label, variable)

    events = []
    for source, df_src in agg.groupby("source"):
        df_src = df_src.sort_values("datetime").copy()

        #Appliquer seuils min et max
        condition = pd.Series(True, index=df_src.index)
        if threshold_min is not None:
            condition &= df_src[variable] >= threshold_min
        if threshold_max is not None:
            condition &= df_src[variable] <= threshold_max

        #Assigner chaque ligne à un évènement
        groups = (
            condition                   #pour chaque ligne : True or False selon que les conditions sont respectées ou non
            .ne(condition.shift())      # "ne" signifie "not equal", condition.shift() déplace de une ligne -> on check si la ligne est différente de la ligne suivante
            .cumsum()                   #incrémente
        )

        for _, episode in df_src.groupby(groups):

            #Si ce groupe correspond à un épisode où la condition n'est pas satisfaite, on l'ignore.
            idx0 = episode.index[0]
            if not condition.loc[idx0]:
                continue

            duration = len(episode)

            if duration < duration_min:
                continue

            events.append({
                "source": source,
                "start_datetime": episode["datetime"].iloc[0],
                "end_datetime": episode["datetime"].iloc[-1],
                "n_periods": duration,
                "variable": variable,
                "function": func_label,
                "period_label": period_label,
                "threshold_min": threshold_min,
                "threshold_max": threshold_max,
                "value_min": episode[variable].min(),
                "value_mean": episode[variable].mean(),
                "value_max": episode[variable].max(),
            })

    return pd.DataFrame(events)