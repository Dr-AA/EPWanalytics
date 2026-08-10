
# page_weather_graph.py
import os
from dash import html, dcc
import dash_bootstrap_components as dbc
from weather_graph.config_weather_graph import VARIABLE_MAP, FREQ_MAP, FUNC_MAP, MANUAL_COLOR_MAP_OPTIONS, WEATHER_STATIONS, DATA_ROOT

def list_available_stations():
    """Retourne les stations pour lesquelles au moins un fichier météo existe."""
    available = []

    for long_name, code in WEATHER_STATIONS.items():
        station_dir = os.path.join(DATA_ROOT, code)
        if not os.path.isdir(station_dir):
            continue

        # Cherche dans les sous-dossiers
        has_data = False
        for sub in os.listdir(station_dir):
            subpath = os.path.join(station_dir, sub)
            if not os.path.isdir(subpath):
                continue

            # Vérifie si ce sous-dossier contient au moins un fichier CSV ou EPW
            for f in os.listdir(subpath):
                if f.lower().endswith((".csv", ".epw")):
                    has_data = True
                    break
            if has_data:
                break
        if has_data:
            available.append({"label": long_name, "value": code})
    return available

def create_page_weather_graph():
    """
    Colonne gauche : paramètres communs + onglets (réglages spécifiques).
    Colonne droite : zone d'affichage (graph / windrose / heatmap).
    """

    # ---- Paramètres communs (sans CardHeader) ----
    common_params = dbc.Card(
        dbc.CardBody([
            #0 Stores
            dcc.Store(id="loaded-files-store", data={}),
            dcc.Store(id="display-settings-store", data={}),
            dcc.Store(id="aggregated-data-store", data=None),
            dcc.Store(id="event-data-store", data=None),

            #0 Mode simplifié / avancé
            dcc.Checklist(
                id="advanced-mode",
                options=[{"label": " Options avancées","value": "advanced"}],
                value=[]
            ),

            #1 Choix de la station
            html.Label("Station", style={'fontWeight': 'bold', "marginTop": "10px"}),
            dcc.Dropdown(
                id='station-dropdown',
                options=list_available_stations(),
                value=None,
                placeholder="Choisir une station",
                clearable=False
            ),

            #2 Choix du fichier
            html.Label("Fichier", style={'fontWeight': 'bold', "marginTop": "10px"}),
            dcc.Dropdown(
                id='dataset-dropdown',
                options=[],
                value=None,
                placeholder="Choisir un fichier",
                clearable=False
            ),

            #3 Nom du fichier + bouton
            html.Button("Charger ce fichier", id="load-file-btn", style={"marginTop": "6px"}),

            #4 Liste des fichiers chargés
            html.Label("Données chargées", style={'fontWeight': 'bold', "display": "block", "marginTop": "10px"}),

            html.Div(
                id="loaded-sources-container",
                style={
                    "border": "1px solid #eee",
                    "borderRadius": "6px",
                    "padding": "6px",
                    "maxHeight": "200px",
                    "overflowY": "auto",
                }
            ),

            #5 Choix de la Période
            html.Div([
                html.Label("Période (DD.MM → DD.MM)", style={'fontWeight': 'bold', 'marginTop': '12px'}),
                html.Div([
                    dcc.Input(
                        id='date-start', type='text', value='01.01',
                        placeholder='DD.MM', style={'width': '45%', 'marginRight': '10px'}
                    ),
                    dcc.Input(
                        id='date-end', type='text', value='31.12',
                        placeholder='DD.MM', style={'width': '45%'}
                    ),
                ], style={'marginBottom': '10px'}),
            ],
            id="date-interval-container"
            ),
        ]),
        className='mb-3'
    )

    # ---- Onglets gauche : Tabs avec contrôles spécifiques ----
    tabs_left = dcc.Tabs(
        id='epw-tabs',
        value='tab-plot',
        style={'marginTop': '0px'},
        children=[

            # --- Tab Graphe ---
            dcc.Tab(
                label='Graphe',
                value='tab-plot',
                style={'padding': '6px 6px', 'fontSize': '13px', 'marginTop': '0px'},
                selected_style={'padding': '6px 6px', 'fontSize': '13px', 'fontWeight': '600'},
                children=[
                    dbc.Card(
                        dbc.CardBody([
                            html.Label("Variable", style={'fontWeight': 'bold'}),
                            dcc.Dropdown(
                                id='epw-var',
                                options=[
                                    {'label': var, 'value': var}
                                    for var in VARIABLE_MAP.keys()
                                ],
                                value=list(VARIABLE_MAP.keys())[0],
                                clearable=False
                            ),

                            html.Label("Agrégations", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                            dcc.Dropdown(
                                id='epw-period',
                                options=[{'label': label, 'value': label} for label in FREQ_MAP.keys()],
                                value='Jour',
                                clearable=False
                            ),

                            html.Label("Fonction", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                            dcc.Dropdown(
                                id='epw-func',
                                options=[{'label': label, 'value': label} for label in FUNC_MAP.keys()],
                                value='Moyenne',
                                clearable=False
                            ),

                            html.Label("Axe X", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                            dcc.RadioItems(
                                id='x-mode',
                                options=[],
                                value='date',
                                inputStyle={"margin-right": "8px"},
                                labelStyle={'display': 'inline-block', 'margin-right': '16px'}
                            ),

                            html.Label("Axe Y", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                            dcc.RadioItems(
                                id='y-mode',
                                options=[
                                    {'label': 'Auto', 'value': 'Auto'},
                                    {'label': 'Manuel', 'value': 'Manuel'},
                                ],
                                value='Auto',
                                inputStyle={"margin-right": "8px"},
                                labelStyle={'display': 'inline-block', 'margin-right': '16px'}
                            ),

                            html.Div(
                                [
                                    html.Label("Y min", style={'marginRight': '10px'}),
                                    dcc.Input(
                                        id='ymin', type='number', placeholder='Ymin',
                                        debounce=True, style={'width': '45%'}
                                    ),
                                    html.Label(
                                        "Y max", style={'marginLeft': '10px', 'marginRight': '10px'}
                                    ),
                                    dcc.Input(
                                        id='ymax', type='number', placeholder='Ymax',
                                        debounce=True, style={'width': '45%'}
                                    ),
                                ],
                                id='y-range-container',
                                style={'marginTop': '10px'}
                            ),


                            #--- Evènements ---
                            html.Div(
                                [

                                    html.Label("Evènements", style={'fontWeight': 'bold','marginTop': '10px'}),
                                    dcc.Checklist(
                                        id="event-enabled", value=[], style={"marginTop": "5px"},
                                        options=[
                                            {"label": " Mettre en surbrillance les périodes où :","value": "enabled"}
                                        ],
                                    ),
                                    dcc.Dropdown(
                                        id='event-var',
                                        options=[
                                            {'label': var, 'value': var}
                                            for var in VARIABLE_MAP.keys()
                                        ],
                                        value='Dry bulb (°C)', clearable=False, style={"marginTop": "3px"}
                                    ),
                                    dcc.Dropdown(
                                        id='event-func',
                                        options=[{'label': label, 'value': label} for label in FUNC_MAP.keys()],
                                        value='Moyenne', clearable=False, style={"marginTop": "3px"}
                                    ),
                                    dcc.Dropdown(
                                        id='event-period',
                                        options=[{'label': label, 'value': label} for label in FREQ_MAP.keys()],
                                        value='Jour', clearable=False, style={"marginTop": "3px"}
                                    ),
                                    html.Div(
                                        [
                                            html.Span("Est inférieur ou égal à", style={'margin': '0 10px'}),
                                            dcc.Input(
                                                id='event-threshold-max',
                                                type='number', placeholder='Seuil inférieur',
                                                debounce=True, style={'width': '130px'}
                                            ),
                                        ],
                                        style={"marginTop": "3px"}
                                    ),
                                    html.Div(
                                        [
                                            html.Span("ET supérieur ou égal à", style={'margin': '0 10px'}),
                                            dcc.Input(
                                                id='event-threshold-min',
                                                type='number', placeholder='Seuil supérieur',
                                                debounce=True, style={'width': '130px'}
                                            ),
                                        ],
                                        style={"marginTop": "3px"}
                                    ),
                                    html.Div(
                                        [
                                            html.Span("Pour une période min. de", style={'margin': '0 10px'}),
                                            dcc.Input(
                                                id='event-duration-min',
                                                type='number', placeholder='', min=1, step=1, value=1,
                                                debounce=True, style={'width': '50px'}
                                            ),
                                            html.Span("", id = 'event-period-text'),
                                        ],
                                        style={"marginTop": "3px"}
                                    ),
                                    html.Label("", id='event-result-text', style={'marginTop': '10px'}),
                                ],
                                id="advanced-events-container"
                            )
                        ]),
                        className='mt-2'
                    )
                ]
            ),

            # --- Tab Rose des vents ---
            dcc.Tab(
                label='Rose des vents',
                value='tab-wind',
                style={'padding': '6px 6px', 'fontSize': '13px', 'marginTop': '0px'},
                selected_style={'padding': '6px 6px', 'fontSize': '13px', 'fontWeight': '600'},
                children=[
                    dbc.Card(
                        dbc.CardBody([
                            html.Label("Nombre de secteurs", style={'fontWeight': 'bold'}),
                            dcc.Dropdown(
                                id='wr-nbins',
                                options=[{'label': s, 'value': int(s)} for s in ['4', '8', '16']],
                                value=16, clearable=False
                            ),

                            html.Label("Normalisation", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                            dcc.RadioItems(
                                id='wr-norm',
                                options=[
                                    {'label': 'Nb de valeurs', 'value': 'None'},
                                    {'label': '% du total', 'value': 'total'},
                                    {'label': '% par secteur', 'value': 'dir'},
                                ],
                                value='None',
                                inputStyle={"margin-right": "8px"},
                                labelStyle={'display': 'inline-block', 'margin-right': '16px'}
                            ),
                        ]),
                        className='mt-2'
                    )
                ]
            ),

            # --- Tab Heatmap ---
            dcc.Tab(
                label='Heatmap',
                value='tab-heat',
                style={'padding': '6px 6px', 'fontSize': '13px', 'marginTop': '0px'},
                selected_style={'padding': '6px 6px', 'fontSize': '13px', 'fontWeight': '600'},
                children=[
                    dbc.Card(
                        dbc.CardBody([
                            html.Label("Variable", style={'fontWeight': 'bold'}),
                            dcc.Dropdown(
                                id='heatmap-var',
                                options=[
                                    {'label': label, 'value': label}
                                    for label in VARIABLE_MAP.keys()
                                ],
                                value=list(VARIABLE_MAP.keys())[0],
                                clearable=False
                            ),

                            html.Label("Colormap", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                            dcc.RadioItems(
                                id='heatmap-colormap',
                                options=[
                                    {'label': 'Auto', 'value': 'Auto'},
                                    {'label': 'Manuel', 'value': 'Manuel'},
                                ],
                                value='Auto',
                                inputStyle={"margin-right": "8px"},
                                labelStyle={'display': 'inline-block', 'margin-right': '16px'}
                            ),

                            html.Div([
                                html.Label("Sélection de la colormap", style={'fontWeight': 'bold', 'marginTop': '10px'}),
                                dcc.Dropdown(
                                    id='heatmap-colormap-choice',
                                    options=[{'label': name, 'value': name} for name in MANUAL_COLOR_MAP_OPTIONS],
                                    value='Viridis',
                                    clearable=False
                                )
                                ],
                                id='heatmap-colormap-choice-container',
                                style={'display': 'none'}
                            ),
                        ]),
                        className='mt-2'
                    )
                ]
            ),
        ]
    )

    # ---- Colonne droite : zone d'affichage (les 3 Graphs) ----
    right_display = html.Div(
        [
            dcc.Graph(id='epw-graph', style={'height': '100%'}, config={'displayModeBar': True}),
            dcc.Graph(id='epw-windrose', style={'height': '100%', 'display': 'none'}),
            dcc.Graph(id='heat-map', style={'height': '100%', 'display': 'none'}),
        ],
        id='right-display',
        className='right-display'
    )

    # ---- Grille : gauche (contrôles) / droite (affichage) ----
    layout = html.Div(
        [
            html.Div(id='tabs-resize-trigger', style={'display': 'none'}),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div([common_params, tabs_left], className='left-panel'),
                        width=3,
                        className='left-col'
                    ),
                    dbc.Col(
                        right_display,
                        width=9,
                        className='right-col'
                    ),
                ],
                className='g-2 page-grid'
            )
        ],
        className='page-root'
    )

    return layout
