# index.py
from dash import html, dcc
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from app import app
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from navbar import create_navbar
from home import create_page_home
from page_epw import create_page_epw
from epw_io import load_weather_data_from_folder
from processing import compute_aggregated_df, filter_by_period
from config import YLABEL_MAP, REFERENCE_YEAR, FREQ_MAP, VARIABLE_MAP, FUNC_MAP, COLOR_MAP_BY_VAR, MANUAL_COLOR_MAP_OPTIONS
from windrose_dash import build_windrose_figure

PAD_RATIO = 0.05  # ajuste à 0.02..0.05 pour rapprocher visuellement 'Fixe' de 'Auto'

# >>> Chemin dossier à adapter
FOLDER = r"C:\Users\n.rey\PycharmProjects\EPWanalytics\data"

all_weather_data_df = load_weather_data_from_folder(FOLDER, files=None)
all_weather_data_df['datetime'] = pd.to_datetime(all_weather_data_df['datetime'], errors='coerce')
# Tu peux aussi passer ce DF via dcc.Store pour être "stateless":

nav = create_navbar()

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    nav,
    dcc.Store(id='y-fixed-store', data={"active": False, "var": None, "range": None}),
    dcc.Store(id='epw-store', data=None),   # on y mettra le DF sérialisé si besoin
    html.Div(id='page-content')
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])

def display_page(pathname):
    if pathname == '/epw':
        return create_page_epw()
    else:
        # page d’accueil par défaut
        return create_page_home()

#--------------------------------------------------------
#--------------------- Générique ---------------------------
#--------------------------------------------------------

# === Helper générique ===
def _mmdd_to_ref_dates(start_label: str, end_label: str, year: int = REFERENCE_YEAR):
    """'MM-JJ' -> (Timestamp start, Timestamp end) dans l'année de référence.
       Si parsing échoue, défaut 01-01 -> 12-31. Si end < start, on inverse."""
    def _parse(label, default):
        try:
            m, d = map(int, (label or '').split('-'))
            return pd.Timestamp(year=year, month=m, day=d)
        except Exception:
            return default
    s = _parse(start_label, pd.Timestamp(year=year, month=1, day=1))
    e = _parse(end_label, pd.Timestamp(year=year, month=12, day=31))
    if e < s:
        s, e = e, s
    return s, e


def _parse_mmdd(label: str, default=(1, 1)):
    """'MM-DD' -> (month, day) avec fallback."""
    try:
        m, d = map(int, (label or '').split('-'))
        return m, d
    except Exception:
        return default


@app.callback(
    [Output('common-sources', 'options'),
     Output('common-sources', 'value')],
    Input('url', 'pathname'),
    State('common-sources', 'value')
)
def populate_sources(pathname, current_value):
    if pathname != '/epw':
        raise PreventUpdate

    # 1) Construire la liste des options depuis le DF global
    sources = sorted(all_weather_data_df['source'].dropna().unique().tolist())
    options = [{'label': s, 'value': s} for s in sources]

    # 2) Déterminer la sélection (value)
    #    - on conserve les valeurs courantes valides si possible,
    #    - sinon on prend 1er élément par défaut (s’il existe),
    #    - on borne TOUJOURS à 4 éléments max.
    if current_value:
        valid = [v for v in current_value if v in sources]
        value = valid[:4]
        if not value and sources:
            value = sources[:1]
    else:
        value = sources[:1] if sources else []

    return options, value

@app.callback(
    Output('common-sources-warning', 'children'),
    Input('common-sources', 'value')
)
def warn_on_limit(selected):
    if not selected:
        return "Sélectionnez jusqu'à 4 fichiers."
    if len(selected) == 4:
        return "Limite atteinte : 4 fichiers maximum."
    return f"{len(selected)} fichier(s) sélectionné(s) — max 4."


@app.callback(
    [Output('epw-graph', 'style'),
     Output('epw-windrose', 'style'),
     Output('heat-map', 'style')],
    Input('epw-tabs', 'value')
)
def toggle_right_display(active_tab):
    base = {'height': '100%'}
    hidden = {'height': '100%', 'display': 'none'}
    if active_tab == 'tab-plot':
        return base, hidden, hidden
    elif active_tab == 'tab-wind':
        return hidden, base, hidden
    elif active_tab == 'tab-heat':
        return hidden, hidden, base
    return base, hidden, hidden


#--------------------------------------------------------
#--------------------- Graphe ---------------------------
#--------------------------------------------------------

# === Helpers padding & relayout ===
def pad_range(y0: float, y1: float, pad_ratio: float = PAD_RATIO, min_pad: float = 1e-6):
    """Élargit [y0, y1] de pad_ratio (±%) pour une marge visuelle uniforme."""
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

def _extract_range_from_relayout(relayout):
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


# === Calls back ===


@app.callback(
    Output('epw-graph', 'figure'),
    [
        Input('epw-tabs', 'value'),
        Input('common-sources', 'value'),
        Input('common-start', 'value'),
        Input('common-end', 'value'),
        Input('epw-var', 'value'),
        Input('epw-period', 'value'),
        Input('epw-func', 'value'),
        Input('y-mode', 'value'),
        Input('epw-graph', 'relayoutData'),
        Input('ymin', 'value'),
        Input('ymax', 'value'),
    ],
)
def update_epw_graph(active_tab, selected_sources, start_label, end_label,
                     var_col, period_label, func_label,
                     y_mode, relayout, ymin, ymax):
    if active_tab != 'tab-plot':
        raise PreventUpdate

    # 0) Sélection fichiers
    if not selected_sources:
        return go.Figure().update_layout(template='plotly_white', title="Aucun fichier sélectionné")

    df_sel = all_weather_data_df[all_weather_data_df['source'].isin(selected_sources)].copy()
    if df_sel.empty:
        return go.Figure().update_layout(template='plotly_white', title="Pas de données")

    # 1) Données agrégées
    plot_df = compute_aggregated_df(
        df_sel,
        period_label=period_label,
        func_label=func_label,
        var_col=var_col
    )

    # 2) Figure
    fig = go.Figure()
    # mode markers allégé si très dense
    mode = 'lines' if period_label in ('Heure', 'h', 'Hour') else 'lines+markers'
    for src, df_src in plot_df.groupby("source"):
        fig.add_trace(go.Scatter(
            x=df_src["datetime"], y=df_src[var_col],
            name=src, mode=mode,
            hovertemplate="%{x|%d-%m %H:%M}<br>%{y:.2f}"
        ))

    # 3) Layout de base
    fig.update_layout(
        template='plotly_white',
        title=f"{var_col} : {func_label} par {period_label}",
        xaxis_title=f"Calendrier {REFERENCE_YEAR} (1er janv. → 31 déc.)",
        yaxis_title=YLABEL_MAP.get(var_col, var_col),
        hovermode='x unified',
        legend=dict(
            x=0.99, y=0.99, xanchor='right', yanchor='top',
            bgcolor='rgba(255,255,255,0.4)', bordercolor='rgba(0,0,0,0.2)', borderwidth=1
        ),
        margin=dict(l=60, r=20, t=60, b=60),
    )

    # 4) Zoom X = période commune
    x0, x1 = _mmdd_to_ref_dates(start_label, end_label, REFERENCE_YEAR)
    fig.update_xaxes(range=[x0, x1])

    # 5) Axe Y : Auto / Manuel (inchangé)
    def pad_range(y0, y1, pad_ratio=0.05, min_pad=1e-6):
        if y0 is None or y1 is None:
            return None
        a, b = float(y0), float(y1)
        if a == b:
            pad = max(min_pad, abs(a) * pad_ratio)
            return [a - pad, b + pad]
        lo, hi = (a, b) if a < b else (b, a)
        span = hi - lo
        pad = max(min_pad, span * pad_ratio)
        return [lo - pad, hi + pad]

    def _extract_range_from_relayout(relayout):
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

    if y_mode == 'Auto':
        fig.update_yaxes(autorange=True)
        return fig

    manual_range = _extract_range_from_relayout(relayout) if relayout else None
    if manual_range is None:
        try:
            if ymin is not None and ymax is not None:
                y0f, y1f = sorted([float(ymin), float(ymax)])
                manual_range = [y0f, y1f]
        except Exception:
            manual_range = None

    if manual_range is None:
        if plot_df.empty:
            fig.update_yaxes(autorange=True)
            return fig
        dmin, dmax = float(plot_df[var_col].min()), float(plot_df[var_col].max())
        manual_range = pad_range(dmin, dmax) if dmin == dmax else [dmin, dmax]

    fig.update_yaxes(range=pad_range(*manual_range))
    return fig


@app.callback(
    Output('y-range-container', 'style'),
    [Input('y-mode', 'value')]
)
def toggle_y_range_inputs(y_mode):
    if y_mode == 'Manuel':
        return {'marginTop': '10px'}
    # Masquer sinon
    return {'display': 'none'}

@app.callback(
    [Output('ymin', 'value'), Output('ymax', 'value')],
    [Input('y-mode', 'value')],
    [State('epw-var', 'value'),
     State('epw-period', 'value'),
     State('epw-func', 'value')]
)
def prefill_manual_range(y_mode, var_col, period_label, func_label):
    if y_mode != 'Manuel':
        raise PreventUpdate
    # Déduire des données affichées
    plot_df = compute_aggregated_df(all_weather_data_df, period_label, func_label, var_col)
    if plot_df.empty:
        raise PreventUpdate
    dmin, dmax = float(plot_df[var_col].min()), float(plot_df[var_col].max())
    # Si constants, ajouter un peu de marge
    if dmin == dmax:
        rng = pad_range(dmin, dmax)
        dmin, dmax = rng[0], rng[1]
    return round(dmin, 0), round(dmax, 0)   # Arrondir



#--------------------------------------------------------
#--------------------- Wind Rose-------------------------
#--------------------------------------------------------

def _polar_ticks_and_labels(n_dir_bins: int):
    """Retourne (dir_centers_deg, cardinal_labels) pour n secteurs."""
    bin_width = 360.0 / float(n_dir_bins)
    dir_centers_deg = (np.arange(n_dir_bins) * bin_width) % 360.0
    if n_dir_bins == 16:
        cardinal = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
                    "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    elif n_dir_bins == 8:
        cardinal = ["N","NE","E","SE","S","SW","W","NW"]
    elif n_dir_bins == 4:
        cardinal = ["N","E","S","W"]
    else:
        cardinal = [f"{int(e)}°" for e in dir_centers_deg]
    return dir_centers_deg, cardinal


@app.callback(
    Output('epw-windrose', 'figure'),
    [
        Input('epw-tabs', 'value'),
        Input('common-sources', 'value'),
        Input('common-start', 'value'),
        Input('common-end', 'value'),
        Input('wr-nbins', 'value'),
        Input('wr-norm', 'value'),
    ]
)
def update_windrose(active_tab, selected_sources, start_label, end_label, n_dir_bins, normalize):
    if active_tab != 'tab-wind':
        raise PreventUpdate

    if not selected_sources:
        return go.Figure().update_layout(template='plotly_white', title="Aucun fichier sélectionné")

    # Limiter à 4
    sources = list(selected_sources)[:4]

    n = len(sources)
    if n == 1:
        # Cas simple : on renvoie la figure telle quelle
        src = sources[0]
        df_src = all_weather_data_df[all_weather_data_df['source'] == src]
        fig = build_windrose_figure(df_src, start_label or "01-01", end_label or "12-31",
                                    int(n_dir_bins or 16), normalize or "None")
        fig.update_layout(title=f"Rose des vents — {src}")
        return fig

    # Définir la grille
    if n == 2:
        rows, cols, height = 1, 2, 700
    else:
        rows, cols, height = 2, 2, 900  # pour 3 ou 4

    specs = [[{'type': 'polar'} for _ in range(cols)] for _ in range(rows)]
    subplot_titles = [s for s in sources] + ([''] * (rows*cols - n))  # titres par sous-plot

    fig = make_subplots(rows=rows, cols=cols, specs=specs, subplot_titles=subplot_titles)

    # Ajouter les traces de chaque source dans le bon sous-plot
    r = c = 1
    for i, src in enumerate(sources):
        df_src = all_weather_data_df[all_weather_data_df['source'] == src]
        f_i = build_windrose_figure(df_src, start_label or "01-01", end_label or "12-31",
                                    int(n_dir_bins or 16), normalize or "None")
        # Première subplot avec légende, les autres sans
        for j, tr in enumerate(f_i.data):
            tr.showlegend = (i == 0)  # légende seulement pour le premier
            fig.add_trace(tr, row=r, col=c)

        # Prochaine case
        c += 1
        if c > cols:
            c = 1
            r += 1

    # Appliquer le layout polaire sur tous les domaines (polar, polar2, polar3, polar4)
    dir_centers_deg, cardinal = _polar_ticks_and_labels(int(n_dir_bins or 16))
    polar_layout = dict(
        angularaxis=dict(
            direction="clockwise",
            rotation=90,  # 0° = Nord en haut
            tickmode='array',
            tickvals=dir_centers_deg,
            ticktext=cardinal
        ),
        radialaxis=dict(
            ticks='outside',
            showline=True,
            gridcolor='rgba(0,0,0,0.2)'
        )
    )

    fig.update_layout(polar=polar_layout) # Premier domaine
    # Domaines supplémentaires selon n
    if n >= 2: fig.update_layout(polar2=polar_layout)
    if n >= 3: fig.update_layout(polar3=polar_layout)
    if n >= 4: fig.update_layout(polar4=polar_layout)

    # décale le titre (source) de 15 px ; ajuste entre 30..60 selon ton thème/zoom
    for ann in fig.layout.annotations:
        ann.update(yshift=15)

    # Harmoniser le layout (polar axes) sur tous les sous-plots
    fig.update_layout(
        template='plotly_white',
        height=height,
        margin=dict(l=60, r=20, t=80, b=60),
        legend=dict(
            x=0.99, y=0.99, xanchor='right', yanchor='top',
            bgcolor='rgba(255,255,255,0.6)', bordercolor='rgba(0,0,0,0.2)', borderwidth=1
        ),
        title_text="Roses des vents (multi-fichiers)",
    )
    return fig


#--------------------------------------------------------
#--------------------- Heat Map -------------------------
#--------------------------------------------------------

def _build_heatmap_matrix(df: pd.DataFrame, var_col: str) -> pd.DataFrame:
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

# Afficher / masker la sélection mannuelle de la colormap
@app.callback(
    Output('heatmap-colormap-choice-container', 'style'),
    Input('heatmap-colormap', 'value')
)
def toggle_heatmap_palette_choice(mode):
    if mode == 'Manuel':
        return {'display': 'block'}
    return {'display': 'none'}

# Afficher la ou les heatmap
@app.callback(
    Output('heat-map', 'figure'),
    [
        Input('epw-tabs', 'value'),             # ne dessiner que si l'onglet Heatmap est actif
        Input('common-sources', 'value'),       # 1..4 fichiers sélectionnés
        Input('common-start', 'value'),
        Input('common-end', 'value'),
        Input('heatmap-var', 'value'),          # variable
        Input('heatmap-colormap', 'value'),     # 'Auto' ou 'Manuel'
        Input('heatmap-colormap-choice', 'value'),  # palette manuelle
    ],
)
def update_heatmap(active_tab, selected_sources, start_label, end_label,
                   var_col, cm_mode, manual_choice):
    if active_tab != 'tab-heat':
        raise PreventUpdate

    # Sélection & garde-fous
    if not selected_sources:
        return go.Figure().update_layout(template='plotly_white', title="Aucun fichier sélectionné")
    sources = list(selected_sources)[:4]

    # Parse période MM-JJ -> ints
    sm, sd = _parse_mmdd(start_label, (1, 1))
    em, ed = _parse_mmdd(end_label, (12, 31))

    # Construire les matrices pour chaque source
    mats = []
    titles = []
    for src in sources:
        df_src = all_weather_data_df[all_weather_data_df['source'] == src]
        df_filt = filter_by_period(df_src, sm, sd, em, ed)
        mat = _build_heatmap_matrix(df_filt, var_col)
        mats.append(mat)
        titles.append(src)

    # Vérifier qu'au moins une matrice est non vide
    if all((m.empty for m in mats)):
        return go.Figure().update_layout(
            template='plotly_white',
            title="Aucune donnée valide pour la période/variable choisies"
        )

    # Déterminer la grille
    n = len(sources)
    if n == 1:
        rows, cols = 1, 1
    elif n == 2:
        rows, cols = 1, 2
    else:
        rows, cols = 2, 2

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=titles + ([''] * (rows * cols - n)),
        horizontal_spacing=0.07, vertical_spacing=0.08
    )

    # Colorscale
    if cm_mode == 'Manuel' and manual_choice in MANUAL_COLOR_MAP_OPTIONS:
        colorscale = manual_choice
    else:
        colorscale = COLOR_MAP_BY_VAR.get(var_col, 'Viridis')

    # zmin/zmax communs pour comparabilité (sur toutes les matrices valides)
    z_global_min = None
    z_global_max = None
    for mat in mats:
        if mat.empty:
            continue
        z = mat.values.astype(float)
        zmin = np.nanmin(z) if np.isfinite(z).any() else None
        zmax = np.nanmax(z) if np.isfinite(z).any() else None
        if zmin is not None and zmax is not None:
            if z_global_min is None or zmin < z_global_min:
                z_global_min = zmin
            if z_global_max is None or zmax > z_global_max:
                z_global_max = zmax

    # Padding léger sur la plage
    if z_global_min is not None and z_global_max is not None and z_global_min != z_global_max:
        span = z_global_max - z_global_min
        pad = max(1e-9, 0.02 * span)
        zmin_final = z_global_min - pad
        zmax_final = z_global_max + pad
    else:
        zmin_final = None
        zmax_final = None

    # Ajouter les Heatmaps
    r = c = 1
    for i, mat in enumerate(mats):
        # Matrice vide -> placeholder
        if mat.empty:
            # Créer un subplot vide avec titre "Pas de données"
            fig.add_trace(go.Scatter(x=[], y=[]), row=r, col=c)
            fig.update_xaxes(title_text="Jour de l'année", row=r, col=c)
            fig.update_yaxes(title_text="Heure", row=r, col=c)
        else:
            z = mat.values
            x = mat.columns.tolist()  # DOY
            y = mat.index.tolist()    # Heure

            fig.add_trace(
                go.Heatmap(
                    z=z,
                    x=x,
                    y=y,
                    colorscale=colorscale,
                    zmin=zmin_final, zmax=zmax_final,
                    colorbar=dict(
                        title=YLABEL_MAP.get(var_col, var_col),
                        thickness=12,
                        len=0.8
                    ) if i == 0 else None,   # colorbar uniquement sur le 1er subplot
                    showscale=(i == 0),
                    hovertemplate="Jour %{x}<br>Heure %{y}:00<br>%{z:.2f}"
                ),
                row=r, col=c
            )
            # Titres axes par subplot
            fig.update_xaxes(title_text="Jour de l'année", row=r, col=c)
            fig.update_yaxes(title_text="Heure", row=r, col=c)

        # Prochaine case
        c += 1
        if c > cols:
            c = 1
            r += 1

    # Layout global
    fig.update_layout(
        template='plotly_white',
        title="Heatmap — " + YLABEL_MAP.get(var_col, var_col),
        margin=dict(l=60, r=20, t=60, b=60),
    )
    return fig



if __name__ == '__main__':
    app.run(debug=True)
