# index.py
from dash import html, dcc, callback_context
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from app import app
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np #
import os

from navbar import create_navbar
from home import create_page_home
from page_epw import create_page_epw
from read_weather_file import load_weather_data_from_folder
from processing import compute_aggregated_df, filter_by_period
from config import VAR_NAME_EN_TO_FR, REFERENCE_YEAR, FREQ_MAP, VARIABLE_MAP, FUNC_MAP, COLOR_MAP_BY_VAR, MANUAL_COLOR_MAP_OPTIONS
from windrose_dash import build_windrose_figure

PAD_RATIO = 0.05  # ajuste à 0.02..0.05 pour rapprocher visuellement les bornes de l'axe y en mode 'Fixe' et 'Auto'

# >>> Chemin dossier à adapter
FOLDER = r"C:\Users\n.rey\PycharmProjects\EPWanalytics\data"


#all_weather_data_df = load_weather_data_from_folder(FOLDER, files=None)
if os.environ.get("WERKZEUG_RUN_MAIN") == "true":                               #cette condition assure que les fichiers ne soient charger que après le reloader (Dash en mode debug), pour éviter qu'ils ne soient chargés deux fois
    all_weather_data_df = load_weather_data_from_folder(FOLDER, files=None)
else:
    all_weather_data_df = None



#all_weather_data_df['datetime'] = pd.to_datetime(all_weather_data_df['datetime'], errors='coerce')     #déjà fait dans "read_weather_file"

nav = create_navbar()

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    nav,
    dcc.Store(id='y-fixed-store', data={"active": False, "var": None, "range": None}),
    dcc.Store(id='epw-store', data=None),   # on y mettra le DF sérialisé si besoin
    dcc.Store(id='axes-store', data={'x': None, 'y': None}),
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


def _parse_mmdd(label: str, default=(1, 1)):
    """'DD.MM' -> (day, month) avec fallback."""
    try:
        d, m = map(int, (label or '').split('.'))
        return d, m
    except Exception:
        return default


@app.callback(
    [Output('common-sources', 'options'),
     Output('common-sources', 'value')],
    Input('url', 'pathname'),
    State('common-sources', 'value')
)
def populate_sources(pathname, current_value):
    # Crée la liste des weather files disponibles
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
    Output('station_files','value'),
    Input('station','value')
)
def populate_weather_file_list():

    return

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

#Gestion des limites d'axe et du zoom
def _extract_axis_ranges_or_auto(relayout):
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

@app.callback(
    Output('axes-store', 'data'),
    [
        Input('epw-graph', 'relayoutData'),
        # Changement de contexte -> on repart à l'état par défaut
        Input('common-start', 'value'),
        Input('common-end', 'value'),
        Input('common-sources', 'value'),
        Input('epw-var', 'value'),
        Input('epw-period', 'value'),
        Input('epw-func', 'value'),
    ],
    State('axes-store', 'data')
)
def persist_axes(relayout, start_label, end_label, selected_sources,
                 var_col, period_label, func_label, store):
    store = (store or {'x': None, 'y': None}).copy()
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trig = ctx.triggered[0]['prop_id']

    # 1) Un évènement de zoom/pan/autoscale/double-clic vient du graphe
    if trig.startswith('epw-graph.relayoutData'):
        xr, yr = _extract_axis_ranges_or_auto(relayout)
        # on ne remplace que ce qui est spécifié
        if xr is not None:
            store['x'] = xr
        if yr is not None:
            store['y'] = yr
        return store

    # 2) Changement de période/sources/paramètres -> remettre l'état par défaut
    #    - X: None -> le callback de dessin appliquera la période
    #    - Y: None -> il appliquera Auto/Manuel selon les contrôles
    return {'x': None, 'y': None}



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
        Input('x-mode', 'value'),
        Input('y-mode', 'value'),
        Input('ymin', 'value'),
        Input('ymax', 'value'),
    ],
    State('axes-store', 'data')
)
def update_epw_graph(active_tab, selected_sources, start_label, end_label,var_col, period_label, func_label, x_mode,
                     y_mode, ymin, ymax,axes_store):

    if active_tab != 'tab-plot':
        raise PreventUpdate

    # 0) Sélection fichiers
    if not selected_sources:
        return go.Figure().update_layout(template='plotly_white', title="Aucun fichier sélectionné")

    df_sel = all_weather_data_df[all_weather_data_df['source'].isin(selected_sources)].copy()
    if df_sel.empty:
        return go.Figure().update_layout(template='plotly_white', title="Pas de données")

    # 1) Données avec agrégation temporelle + fonction appliquée
    plot_df = compute_aggregated_df(
        df_sel,
        period_label=period_label,
        func_label=func_label,
        var_col=var_col
    )

    fig = go.Figure()
    # 2) Construire les traces selon x_mode
    if x_mode == 'date':
        # Axe x : Mode temporel
        mode_line = 'lines' if period_label in ('Heure', 'h', 'Hour') else 'lines+markers'
        for src, df_src in plot_df.groupby("source"):
            fig.add_trace(go.Scatter(
                x=df_src["datetime"],
                y=df_src[var_col],
                name=src,
                mode=mode_line,
                hovertemplate="%{x|%d-%m %H:%M}<br>%{y:.2f}"
            ))
        x_title = f"Calendrier {REFERENCE_YEAR} (1er janv. → 31 déc.)"
        subtitle = func_label
    else:
        print('mode tri')
        # Axe x : Mode tri — faire le tri APRES agrégation
        isAscending = (x_mode == 'asc')
        for src, df_src in plot_df.groupby("source"):
            # Nettoyage NA, tri stable pour reproductibilité
            tmp = df_src[['datetime', var_col]].dropna(subset=[var_col]).copy()
            tmp = tmp.sort_values(by=var_col, ascending=isAscending, kind='mergesort')  # stable
            tmp['rank'] = range(1, len(tmp) + 1)  # 1..n pour cette source

            fig.add_trace(go.Scatter(
                x=tmp['rank'],
                y=tmp[var_col],
                name=src,
                mode='markers',
                hovertemplate="Rang %{x}<br>%{y:.2f}<br>%{customdata|%d-%m %H:%M}",
                customdata=tmp['datetime']  # afficher la date source dans le hover
            ))

        x_title = "Index (1..n)"
        subtitle = "Tri croissant" if isAscending else "Tri décroissant"

    # 3) Layout de base
    if func_label == "Somme cumulée" :
        title = f"{func_label} (cumul depuis 01.01)"
    else:
        title = f"{var_col} : {func_label} par {period_label}",

    fig.update_layout(
        template='plotly_white',
        title=f"{var_col} : {func_label} par {period_label}" + ("" if x_mode == 'date' else f" — {subtitle}") if func_label != "Somme cumulée" else f"{var_col} : {func_label} par {period_label}",
        xaxis_title=x_title,
        yaxis_title=VAR_NAME_EN_TO_FR.get(var_col, var_col),
        hovermode='x unified',
        legend=dict(
            x=0.99, y=0.99, xanchor='right', yanchor='top',
            bgcolor='rgba(255,255,255,0.4)', bordercolor='rgba(0,0,0,0.2)', borderwidth=1
        ),
        margin=dict(l=60, r=20, t=60, b=60),
    )

    # 4) Gestion de l'axe X (période / store / tri)
    axes_store = axes_store or {'x': None, 'y': None}
    if x_mode == 'date':
        # Respecter le store (zoom/auto) ou la période par défaut
        if axes_store.get('x') == 'auto':
            fig.update_xaxes(autorange=True)
        elif isinstance(axes_store.get('x'), (list, tuple)) and len(axes_store['x']) == 2:
            fig.update_xaxes(range=axes_store['x'])
        else:
            x0, x1 = _mmdd_to_ref_dates(start_label, end_label, REFERENCE_YEAR)
            fig.update_xaxes(range=[x0, x1])
    else:
        # En mode tri, X = 1..n => laisser autorange et ticks linéaires
        fig.update_xaxes(autorange=True, tickmode='auto', title_standoff=8)



    # 5) Axe Y : respecter un zoom manuel mémorisé, sinon logique Auto/Manuel
    if axes_store.get('y') == 'auto':
        fig.update_yaxes(autorange=True)
        return fig
    elif isinstance(axes_store.get('y'), (list, tuple)) and len(axes_store['y']) == 2:
        fig.update_yaxes(range=axes_store['y'])
        return fig

    # Pas de zoom manuel Y -> logique Auto/Manuel
    if y_mode == 'Auto':
        fig.update_yaxes(autorange=True)
        return fig

    # y_mode == 'Manuel'
    manual_range = None
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
        manual_range = [dmin, dmax] if dmin != dmax else pad_range(dmin, dmax)

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

# Afficher / masker la sélection manuelle de la colormap
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
    sd, sm = _parse_mmdd(start_label, (1, 1))
    ed, em = _parse_mmdd(end_label, (12, 31))

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
                        title=VAR_NAME_EN_TO_FR.get(var_col, var_col),
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
        title="Heatmap — " + VAR_NAME_EN_TO_FR.get(var_col, var_col),
        margin=dict(l=60, r=20, t=60, b=60),
    )
    return fig

if __name__ == '__main__':
    app.run(debug=True)
