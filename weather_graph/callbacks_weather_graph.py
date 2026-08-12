# callbacks_weather_graph.py
from dash import html, callback_context
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State, ALL
from app import app
from io import StringIO
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import os

from generic_helpers import hex_to_rgba, pad_y_axis_range, ddmm_to_ref_dates, parse_ddmm, extract_axis_ranges_or_auto, extract_range_from_relayout

from weather_graph.read_weather_file import read_weather_file, REFERENCE_YEAR
from weather_graph.data_processing import build_master_df, compute_aggregated_df, filter_by_period, build_heatmap_matrix, build_windrose_figure, detect_events
from weather_graph.figure_helpers import add_events_to_figure
import weather_graph.config_weather_graph as cfg

def callbacks_weather_graph(app):

    #--------------------------------------------------------
    #--------------------- Gestion de l'affichage------------
    #--------------------------------------------------------

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
    #--------------------- Gestion des fichiers--------------
    #--------------------------------------------------------

    @app.callback(
        Output("dataset-dropdown", "options"),
        Input("station-dropdown", "value")
    )
    def update_dataset_list(station_code):
        if not station_code:
            return []

        station_dir = os.path.join("data", station_code)
        if not os.path.isdir(station_dir):
            print("absolute =", os.path.abspath(station_dir))
            print(f"Folder{station_dir} not found")
            return []

        options = []
        for subfolder in os.listdir(station_dir):
            fullpath = os.path.join(station_dir, subfolder)

            if os.path.isdir(fullpath):
                # Ajouter TOUS les fichiers .epw ou .csv du sous-dossier
                for f in os.listdir(fullpath):
                    if f.lower().endswith((".epw", ".csv")):
                        filepath = os.path.join(fullpath, f)
                        #label = f"{subfolder} / {f}"
                        options.append({"label": f, "value": filepath})

        return options

    @app.callback(
        Output("load-file-btn", "disabled"),
        Output("load-file-btn", "style"),
        Input("station-dropdown", "value"),
        Input("dataset-dropdown", "value"),
        Input("loaded-files-store", "data"),
    )
    def update_load_button(station, dataset, loaded_files):
        loaded_files = loaded_files or {}
        enabled = (
                station is not None
                and dataset is not None
                and dataset not in loaded_files
        )

        if enabled:
            return False, {
                "marginTop": "6px",
                "backgroundColor": "#1f388b",
                "color": "white",
                "border": "1px solid #1f388b",
                "borderRadius": "4px",
                "padding": "6px 12px",
                "cursor": "pointer",
            }
        else:
            return True, {
                "marginTop": "6px",
                "backgroundColor": "#f9f9f9",
                "color": "#6c757d",
                "border": "1px solid #ced4da",
                "borderRadius": "4px",
                "padding": "6px 12px",
                "cursor": "not-allowed",
            }

    @app.callback(
        Output("loaded-files-store", "data", allow_duplicate=True),
        Output("display-settings-store", "data", allow_duplicate=True),
        Input("load-file-btn", "n_clicks"),
        State("dataset-dropdown", "value"),
        State("dataset-dropdown", "label"),
        State("loaded-files-store", "data"),
        State("display-settings-store", "data"),
        prevent_initial_call=True
    )
    def load_weather_file(n_clicks, filepath, label, loaded_store, display_store):
        """ Appelée lorsque le bouton "charger fichier" est clické; appelle read_weather_file() pour lire les données .epw ou .csv;
        stock les données dans loaded-file-store; stock les infos d'affichage dans "display-settings-store" """

        if not filepath:
            raise PreventUpdate

        # Charger le fichier
        df = read_weather_file(filepath, label)
        if df is None:
            raise PreventUpdate

        # Serialiser en JSON
        df_json = df.to_json(date_format="iso")

        # Ajouter au store (clé = chemin complet)
        loaded_store = loaded_store or {}
        display_store = display_store or {}

        loaded_store[filepath] = {
            "df": df_json
        }

        display_store[filepath] = {
            "visible": True,
            "color": cfg.LINE_COLORS[len(display_store) % len(cfg.LINE_COLORS)],
            "line_style": 0,
        }

        return loaded_store, display_store

    @app.callback(
        Output("loaded-sources-container", "children"),
        Input("loaded-files-store", "data"),
        Input("display-settings-store", "data"),

    )
    def render_loaded_sources(loaded_store, display_store):
        if not loaded_store:
            return html.Div("Aucun fichier chargé.", style = {"color":"#6c757d"}),

        rows = []

        for path in loaded_store:
            payload = display_store[path]

            rows.append(
                html.Div(
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "space-between",
                        "marginBottom": "4px",
                    },
                    children=[

                        #Partie gauche
                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "8px","flexGrow": 1},
                            children=[

                                #Carré de couleur, click pour faire défiler les couleurs (version simple)
                                html.Div(
                                    id={"type": "source-color", "path": path},
                                    n_clicks=0,
                                    style={
                                        "width": "14px",
                                        "height": "14px",
                                        "backgroundColor": payload["color"],
                                        "border": "1px solid #666",
                                        "cursor": "pointer",
                                    }
                                ),

                                # -- icône type de ligne
                                html.Div(
                                    cfg.LINE_STYLES[payload["line_style"]]["symbol"],
                                    id={"type": "source-line-style", "path": path},
                                    n_clicks=0,
                                    style={
                                        "cursor": "pointer",
                                        "width": "35px",
                                        "textAlign": "center",
                                        #"marginLeft": "5px",
                                        #"marginRight": "5px",
                                        "fontWeight": "bold",
                                    }
                                ),

                                # Label
                                html.Span(
                                    os.path.basename(path),
                                    #style={"color": payload["color"]}  #Activer cette ligne pour afficher le nom du fichier dans la couleur de la courbe
                                ),
                            ]
                        ),

                        # Partie droite

                        html.Div(
                            style={"display": "flex", "alignItems": "center", "gap": "12px", "marginLeft": "10px"},
                            children=[
                                # 👁️ Icône visibilité
                                html.I(
                                    className=(
                                        "bi bi-eye-fill"
                                        if payload.get("visible", True)
                                        else "bi bi-eye-slash-fill"
                                    ),
                                    id={"type": "source-visibility", "path": path},
                                    n_clicks=0,
                                    style={
                                        "cursor": "pointer",
                                        "fontSize": "18px",
                                        "color": "#0d6efd" if payload.get("visible", True) else "#999",
                                    },
                                ),

                                # ❌ suppression
                                html.Button(
                                    "✕",
                                    id={"type": "source-delete", "path": path},
                                    n_clicks=0,
                                    style={
                                        "border": "none",
                                        "background": "transparent",
                                        "color": "#cc0000",
                                        "fontSize": "16px",
                                        "cursor": "pointer",
                                    },
                                ),
                            ],
                        ),#fin de la partie droite


                    ],
                ) #fin du div principal
            )

        return rows


    @app.callback(
        Output("display-settings-store", "data", allow_duplicate=True),
        Input({"type": "source-visibility", "path": ALL}, "n_clicks"),
        State("display-settings-store", "data"),
        prevent_initial_call=True
    )
    def toggle_source_visibility(n_clicks_list, display_store):
        print("-- Call to toggle_source_visibility --")

        if not callback_context.triggered:
            print("WARN : callback_context.triggered is False")
            raise PreventUpdate

        trigger = callback_context.triggered_id
        path = trigger["path"]

        # 🔐 Le fichier a peut-être été supprimé entre-temps
        if path not in display_store:
            print("WARN : path is not in store")
            raise PreventUpdate

        # 🔒 Identifier l'index correct
        paths = list(display_store.keys())
        try:
            idx = paths.index(path)
        except ValueError:
            print("WARN : could not get idx")
            raise PreventUpdate

        clicks = n_clicks_list[idx]

        # 🔒 Pas un vrai clic utilisateur
        if clicks == 0:
            #print("WARN : clicks = 0")
            raise PreventUpdate

        # ✅ EVEN clicks → SOLO mode
        if clicks % 2 == 0:
            for p in display_store:
                display_store[p]["visible"] = (p == path)
        else:
            # ✅ Toggle réel demandé
            display_store[path]["visible"] = not display_store[path].get("visible", True)
        print("Visibility for", path, "=", display_store[path]["visible"])
        return display_store

    @app.callback(
        Output("display-settings-store", "data", allow_duplicate=True),
        Input({"type": "source-color", "path": ALL}, "n_clicks"),
        State("display-settings-store", "data"),
        prevent_initial_call=True
    )
    def cycle_color(n_clicks_list, display_store):
        """ Appelé lors d'un click sur le carré de couleur; modifie la couleur du dataset dans display-settings-store"""

        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        path = ctx.triggered_id["path"]
        if path not in display_store:
            raise PreventUpdate
        idx = list(display_store.keys()).index(path)
        if n_clicks_list[idx] == 0:
            raise PreventUpdate
        current_color = display_store[path]["color"]
        try:
            current_idx = cfg.LINE_COLORS.index(current_color)
        except ValueError:
            current_idx = 0
        next_idx = (current_idx + 1) % len(cfg.LINE_COLORS)
        display_store[path]["color"] = cfg.LINE_COLORS[next_idx]

        return display_store

    @app.callback(
        Output("display-settings-store", "data", allow_duplicate=True),
        Input({"type": "source-line-style", "path": ALL}, "n_clicks"),
        State("display-settings-store", "data"),
        prevent_initial_call=True,
    )
    def cycle_line_style(n_clicks_list, display_store):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        path = ctx.triggered_id["path"]
        if path not in display_store:
            raise PreventUpdate
        idx = list(display_store.keys()).index(path)
        if n_clicks_list[idx] == 0:
            raise PreventUpdate
        display_store[path]["line_style"] = (display_store[path]["line_style"] + 1) % len(cfg.LINE_STYLES)
        return display_store


    @app.callback(
        Output("loaded-files-store", "data", allow_duplicate=True),
        Output("display-settings-store", "data", allow_duplicate=True),
        Input({"type": "source-delete", "path": ALL}, "n_clicks"),
        State("loaded-files-store", "data"),
        State("display-settings-store", "data"),
        prevent_initial_call=True
    )
    def delete_source(n_clicks_list, loaded_store, display_store):
        print("-- Call to delete-source --")
        ctx = callback_context
        if not ctx.triggered:
            print("WARN - not ctx.triggered")
            raise PreventUpdate

        trigger = ctx.triggered_id
        path = trigger["path"]

        # 🔐 bouton créé ou re-rendu → n_clicks == 0 → IGNORER
        idx = [i for i, p in enumerate(loaded_store.keys()) if p == path]
        if not idx:
            print("WARN - not idx")
            raise PreventUpdate

        index = idx[0]
        if n_clicks_list[index] == 0:
            #print("WARN - n_clicks = 0")
            raise PreventUpdate

        # ✅ vrai clic utilisateur
        loaded_store.pop(path, None)
        display_store.pop(path, None)
        return loaded_store, display_store

    #--------------------------------------------------------
    #--------------------- Graphe ---------------------------
    #--------------------------------------------------------



    # === Calls back axes ===

    @app.callback(
        Output('axes-store', 'data'),
        [
            Input('epw-graph', 'relayoutData'),
            # Changement de contexte -> on repart à l'état par défaut
            Input('date-start', 'value'),
            Input('date-end', 'value'),
            Input('epw-var', 'value'),
            Input('epw-period', 'value'),
            Input('epw-func', 'value'),
        ],
        State('axes-store', 'data')
    )
    def persist_axes(relayout, start_label, end_label,
                     var_col, period_label, func_label, store):
        store = (store or {'x': None, 'y': None}).copy()
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        trig = ctx.triggered[0]['prop_id']

        # 1) Un évènement de zoom/pan/autoscale/double-clic vient du graphe
        if trig.startswith('epw-graph.relayoutData'):
            xr, yr = extract_axis_ranges_or_auto(relayout)
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
        Output('y-range-container', 'style'),
        [Input('y-mode', 'value')]
    )
    def toggle_y_range_inputs(y_mode):
        if y_mode == 'Manuel':
            return {'marginTop': '10px'}
        # Masquer sinon
        return {'display': 'none'}

    @app.callback(
        [Output('ymin', 'value'),
         Output('ymax', 'value')],
        [Input('y-mode', 'value')],
        [State('epw-var', 'value'),
         State('epw-period', 'value'),
         State('epw-func', 'value'),
         State("loaded-files-store", "data")]
    )
    def prefill_manual_range(y_mode, var_col, period_label, func_label, loaded_files):
        if y_mode != 'Manuel':
            raise PreventUpdate
        # Déduire des données affichées
        df_master = build_master_df(loaded_files)
        plot_df = compute_aggregated_df(df_master, period_label, func_label, var_col)
        if plot_df.empty:
            raise PreventUpdate
        dmin, dmax = float(plot_df[var_col].min()), float(plot_df[var_col].max())
        # Si constants, ajouter un peu de marge
        if dmin == dmax:
            rng = pad_y_axis_range(dmin, dmax)
            dmin, dmax = rng[0], rng[1]
        return round(dmin, 0), round(dmax, 0)   # Arrondir



    # === Calls back to plot the graph ===

    @app.callback(
        Output("aggregated-data-store", "data"),
        Input("loaded-files-store", "data"),
        Input("epw-var", "value"),
        Input("epw-period", "value"),
        Input("epw-func", "value"),
    )
    def compute_plot_data(loaded_files, var_col, period_label, func_label):

        df_master = build_master_df(loaded_files)
        if df_master.empty:
            return

        plot_df = compute_aggregated_df(df_master, period_label, func_label, var_col)

        return plot_df.to_json(date_format="iso")

    @app.callback(
        Output('epw-graph', 'figure'),
        [
            Input('epw-tabs', 'value'),
            Input('date-start', 'value'),
            Input('date-end', 'value'),
            Input('epw-var', 'value'),
            Input('epw-period', 'value'),
            Input('epw-func', 'value'),
            Input('x-mode', 'value'),
            Input('y-mode', 'value'),
            Input('ymin', 'value'),
            Input('ymax', 'value'),
            Input("aggregated-data-store", "data"),
            Input("display-settings-store", "data"),
            #Inputs évènements :
            Input("event-enabled", "value"),
            Input("event-data-store", "data"),
        ],
        State('axes-store', 'data'),
        prevent_initial_call=True
    )
    def update_weather_graph(active_tab, start_label, end_label, var_col, period_label, func_label, x_mode,
                             y_mode, ymin, ymax, plot_df_json, display_store,
                             event_enabled, events_json,
                             axes_store,):
        print("-- Call to update_weather_graph --")
        if active_tab != 'tab-plot':
            raise PreventUpdate

        if plot_df_json is None:
            return go.Figure().update_layout(template='plotly_white', title="Aucun fichier sélectionné")
            #raise PreventUpdate

        plot_df = pd.read_json(
            StringIO(plot_df_json)
        )

        fig = go.Figure()

        # 2) Construire les traces selon x_mode
        #sources = df_master["source"].unique()
        #color_map = build_color_map(sources)
        if x_mode == 'date':

            # Axe x : Mode temporel
            if period_label == "Année": # -> Bar chart
                print("Bar chart")
                for src, df_src in plot_df.groupby("source"):
                    payload = display_store[src]
                    if not payload["visible"]:
                        continue

                    fig.add_trace(
                        go.Bar(
                            x=df_src["datetime"],
                            y=df_src[var_col],
                            name=df_src["source_label"].iloc[0],
                            marker_color=payload["color"],
                        )
                    )
                x_title = f"Valeur annuelle"
                fig.update_xaxes(showticklabels=False)

            else: #-> line plot
                mode_line = 'lines' if period_label in ('Heure', 'h', 'Hour') else 'lines' #'lines+markers'

                show_band = func_label == "Moyenne et enveloppe min/max"

                for src, df_src in plot_df.groupby("source"):
                    payload = display_store[src]
                    if not payload["visible"]:
                        continue

                    if show_band :
                        df_min = df_src[df_src["stat"] == "min"]
                        df_mean = df_src[df_src["stat"] == "mean"]
                        df_max = df_src[df_src["stat"] == "max"]

                        df_min = df_min.sort_values("datetime")
                        df_max = df_max.sort_values("datetime")
                        print(len(df_min))
                        print(len(df_mean))
                        print(len(df_max))
                        print(df_min["datetime"].is_monotonic_increasing)
                        print(df_max["datetime"].is_monotonic_increasing)
                        print(df_min["datetime"].equals(df_max["datetime"]))
                        print(df_min["datetime"].equals(df_mean["datetime"]))


                        fig.add_trace(
                            go.Scatter(
                                x=list(df_max["datetime"]) +
                                  list(df_min["datetime"][::-1]),
                                y=list(df_max[var_col]) +
                                  list(df_min[var_col][::-1]),
                                fill="toself",
                                fillcolor=hex_to_rgba(payload["color"], 0.20),
                                line=dict(color="rgba(0,0,0,0)"),
                                hoverinfo="skip",
                                showlegend=False,
                            )
                        )

                        fig.add_trace(
                            go.Scatter(
                                x=df_mean["datetime"],
                                y=df_src[var_col],
                                name=df_src["source_label"].iloc[0],
                                mode=mode_line,
                                line=dict(
                                    color=payload["color"],
                                    dash=cfg.LINE_STYLES[payload["line_style"]]["plotly"],
                                    width=2,
                                ),
                                hovertemplate="%{x|%d-%m %H:%M}<br>%{y:.2f}",
                            )
                        )
                    else:
                        fig.add_trace(
                            go.Scatter(
                                x=df_src["datetime"],
                                y=df_src[var_col],
                                name=df_src["source_label"].iloc[0],
                                mode=mode_line,
                                line=dict(
                                    color=payload["color"],
                                    dash=cfg.LINE_STYLES[payload["line_style"]]["plotly"],
                                    width=2,
                                ),
                                hovertemplate="%{x|%d-%m %H:%M}<br>%{y:.2f}",
                            )
                        )

                x_title = ""
                # ticks de l'axe temporel x : ne pas afficher l'année
                fig.update_xaxes(
                    tickformatstops=[
                        dict(dtickrange=[None, 86400000], value="%d %b %H:%M"),
                        dict(dtickrange=[86400000, None], value="%d %b"),
                    ]
                )
            subtitle = func_label
        else:
            print('mode tri')
            # Axe x : Mode tri — faire le tri APRES agrégation
            isAscending = (x_mode == 'asc')
            for src, df_src in plot_df.groupby("source"):
                # Nettoyage NA, tri stable pour reproductibilité
                tmp = df_src[['datetime', var_col]].dropna(subset=[var_col]).copy()
                sd, sm = parse_ddmm(start_label, (1, 1))
                ed, em = parse_ddmm(end_label, (31,12))
                tmp = filter_by_period(tmp,sd,sm,ed,em)
                tmp = tmp.sort_values(by=var_col, ascending=isAscending, kind='mergesort')  # stable
                tmp['rank'] = range(1, len(tmp) + 1)  # 1..n pour cette source

                payload = display_store[src]
                if not payload["visible"]:
                    continue

                fig.add_trace(go.Scatter(
                    x=tmp['rank'],
                    y=tmp[var_col],
                    name=df_src["source_label"].iloc[0],
                    marker_color=payload["color"],
                    #dash=LINE_STYLES[payload["line_style"]]["plotly"],
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
            title=f"{cfg.VAR_NAME_EN_TO_FR.get(var_col, var_col)} : {func_label} par {period_label}" + ("" if x_mode == 'date' else f" — {subtitle}") if func_label != "Somme cumulée" else f"{cfg.VAR_NAME_EN_TO_FR.get(var_col, var_col)} : {func_label} par {period_label}",
            xaxis_title=x_title,
            yaxis_title=cfg.VAR_NAME_EN_TO_FR.get(var_col, var_col),
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
                if period_label == "Année":
                    fig.update_xaxes(type="category")
                else:
                    x0, x1 = ddmm_to_ref_dates(start_label, end_label, REFERENCE_YEAR)
                    fig.update_xaxes(range=[x0, x1])
        else:
            # En mode tri, X = 1..n => laisser autorange et ticks linéaires
            fig.update_xaxes(autorange=True, tickmode='auto', title_standoff=8)

        #5) Evènements
        if "enabled" in event_enabled and events_json:
            events_df = pd.read_json(StringIO(events_json))
            fig = add_events_to_figure(fig,events_df)

        #6) Axe Y : respecter un zoom manuel mémorisé, sinon logique Auto/Manuel
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
            manual_range = [dmin, dmax] if dmin != dmax else pad_y_axis_range(dmin, dmax)

        fig.update_yaxes(range=pad_y_axis_range(*manual_range))

        return fig


    @app.callback(
        Output("event-data-store", "data"),
        Input("loaded-files-store", "data"),
        Input("event-var", "value"),
        Input("event-func", "value"),
        Input("event-period", "value"),
        Input("event-threshold-min", "value"),
        Input("event-threshold-max", "value"),
        Input("event-duration-min", "value"),
        prevent_initial_call=True
    )
    def compute_event_data(loaded_files, variable, func_label, period_label, threshold_min, threshold_max, duration_min):
        print("-- Call to compute_event_data --")
        df_master = build_master_df(loaded_files)

        events_df = detect_events(
            df_master,
            variable=variable,
            period_label=period_label,
            func_label=func_label,
            threshold_min=threshold_min,
            threshold_max=threshold_max,
            duration_min=duration_min
        )

        return events_df.to_json(date_format="iso")

    @app.callback(
        Output("event-period-text", "children"),
        Input("event-period", "value"),
        Input("event-duration-min", "value"),
    )
    def update_event_period_text(period_label, duration):
        duration = duration or 1
        if duration == 1:
            return " " + cfg.FREQ_LABELS[period_label]["singular"] + "."
        else:
            return " " + cfg.FREQ_LABELS[period_label]["plural"] + "."

    @app.callback(
        Output("event-result-text", "children"),
        Input("event-data-store","data"),
        prevent_initial_call = True
    )
    def update_event_result_text(events_json):
        if events_json :
            events_df = pd.read_json(StringIO(events_json))
            nb_events = len(events_df)
            if nb_events == 0 :
                return "Aucun évènement trouvé."
            elif nb_events <= 30 :
                return f"Nombre d'évènements trouvés : {nb_events}"
            elif nb_events > 30 :
                return f"Attention, les évènements détectés ne sont pas affichés car leur nombre ({nb_events}) dépasse le nombre maximal (30). Veuillez modifier les critères ou réduire le nombre de datasets."







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
            Input('date-start', 'value'),
            Input('date-end', 'value'),
            Input('wr-nbins', 'value'),
            Input('wr-norm', 'value'),
            Input("loaded-files-store", "data"),
            Input("display-settings-store", "data"),
        ],
    )
    def update_windrose(active_tab, start_label, end_label, n_dir_bins, normalize,loaded_files, display_store):
        if active_tab != 'tab-wind':
            raise PreventUpdate

        df = build_master_df(loaded_files)

        if "source_label" in df.keys():
            visible_sources = [src for src, cfg in display_store.items() if cfg["visible"]]
            df = df[df["source"].isin(visible_sources)]
            selected_sources = df["source_label"].unique()
            sources = list(selected_sources)[:4]    # Limiter à 4
        else :
            return go.Figure().update_layout(template='plotly_white', title="Aucun fichier sélectionné")

        n = len(sources)
        if n == 1:
            # Cas simple : on renvoie la figure telle quelle
            src = sources[0]
            df_src = df[df['source_label'] == src]
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
            df_src = df[df['source_label'] == src]
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
            title_text="Roses des vents",
        )
        return fig


    #--------------------------------------------------------
    #--------------------- Heat Map -------------------------
    #--------------------------------------------------------



    # Afficher / masquer la sélection manuelle de la colormap
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
            Input('date-start', 'value'),
            Input('date-end', 'value'),
            Input('heatmap-var', 'value'),          # variable
            Input('heatmap-colormap', 'value'),     # 'Auto' ou 'Manuel'
            Input('heatmap-colormap-choice', 'value'),  # palette manuelle
            Input("loaded-files-store", "data"),
            Input("display-settings-store", "data"),
        ],
    )
    def update_heatmap(active_tab, start_label, end_label,
                       var_col, cm_mode, manual_choice, loaded_files, display_store):
        if active_tab != 'tab-heat':
            raise PreventUpdate

        df = build_master_df(loaded_files)

        # Sélection & garde-fous
        if "source_label" in df.keys():
            #Conserver uniquement les datasets visibles
            visible_sources = [src for src, cfg in display_store.items() if cfg["visible"]]
            df = df[df["source"].isin(visible_sources)]
            selected_sources = df["source_label"].unique()
            sources = list(selected_sources)[:4]
        else:
            return go.Figure().update_layout(template='plotly_white', title="Aucun fichier sélectionné")

        # Parse période MM-JJ -> ints
        sd, sm = parse_ddmm(start_label, (1, 1))
        ed, em = parse_ddmm(end_label, (31, 12))

        # Construire les matrices pour chaque source
        mats = []
        titles = []
        for src in sources:
            df_src = df[df['source_label'] == src]
            df_filt = filter_by_period(df_src, sd, sm, ed, em)
            mat = build_heatmap_matrix(df_filt, var_col)
            mats.append(mat)
            titles.append(src)

        # Vérifier qu'au moins une matrice est non vide
        if all((m.empty for m in mats)):
            print("Toutes les matrices sont vides")
            return go.Figure().update_layout(
                template='plotly_white',
                title="Aucune donnée valide pour la période/variable choisies"
            )

        # Déterminer la grille
        n = len(sources)
        print(f"len(sources) = {n}")
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
        if cm_mode == 'Manuel' and manual_choice in cfg.MANUAL_COLOR_MAP_OPTIONS:
            colorscale = manual_choice
        else:
            colorscale = cfg.COLOR_MAP_BY_VAR.get(var_col, 'Viridis')

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
                        z=z, x=x, y=y,
                        colorscale=colorscale,
                        zmin=zmin_final, zmax=zmax_final,
                        colorbar=dict(
                            title=cfg.VAR_NAME_EN_TO_FR.get(var_col, var_col),
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
            title="Heatmap — " + cfg.VAR_NAME_EN_TO_FR.get(var_col, var_col),
            margin=dict(l=60, r=20, t=60, b=60),
        )
        return fig

    #--------------------------------------------------------
    #--------------------- Mode simplifié -------------------
    #--------------------------------------------------------

    @app.callback(
        Output("date-interval-container","style"),
        Output("epw-var", "options"),
        Output("epw-func", "options"),
        Output("x-mode", "options"),
        Output("y-axis-container", "style"),
        Output("date-start", "value"),
        Output("date-end", "value"),
        Output("events-container","style"),
        Output("event-enabled","value"),
        Output("wind-rose-normalisation-container","style"),
        Input("advanced-mode", "value")
    )
    def switch_mode(mode_selection):
        advanced = "advanced" in (mode_selection or [])

        selected_mode = (
            cfg.MODES["advanced"] if advanced else cfg.MODES["simple"]
        )

        events_style = (
            {} if selected_mode["show_date_interval"] else {"display": "none"}
        )

        var_options = [
            {"label": cfg.VAR_NAME_EN_TO_FR[var],"value": var} for var in selected_mode["var_options"]
        ]

        func_options = [
            {"label": func,"value": func} for func in selected_mode["func_options"]
        ]

        x_options = selected_mode["x_options"]

        y_axis_container_style = (
            {} if selected_mode["show_y_axis_scaling_options"] else {"display": "none"}
        )

        events_style = (
            {} if selected_mode["show_events"] else {"display": "none"}
        )



        windrose_normalisation_container_style = (
            {} if selected_mode["show_windrose_normalisation"] else {"display": "none"}
        )

        #Remettre aux valeurs par défaut les variables qui ne sont plus accessibles
        date_start ='01.01'
        date_end = '31.12'
        event_enabled = []

        return [
            events_style,
            var_options,
            func_options,
            x_options,
            y_axis_container_style,
            date_start,
            date_end,
            events_style,
            event_enabled,
            windrose_normalisation_container_style
        ]