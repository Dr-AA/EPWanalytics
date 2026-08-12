# config_weather_graph.py
from dash import html


DATA_ROOT = "data"

# VARIABLE_MAP : dictionnaire avec le noms de colonne unifiés (keys), et les noms de colonnes correspondant dans les formats suivants :
# 1) epw
# 2) csv - SIA4028 année 2023
# 3) csv - SIA2028 année 2035 et 2060
# 4) csv - SIA2028 contemporain (ancien jeu de données)
# 5) csv - Meteosuisse données mesurées

VARIABLE_MAP = {
    "Dry bulb (°C)": ["DryBulb", "temp", "tre200h0","tre200h0","tre200h0"],
    "Wet bulb (°C)": ["","wetbulb", "","wetbulb",""],
    "Dew point (°C)": ["DewPoint","dewpt", "","dewpt","tde200h0"],
    "Relative humidity (%)": ["RelativeHumidity","relhum", "ure200h0", "ure200h0","ure200h0"],
    "Mixing ratio (g/kg)" : ["", "mixratio","", "mixratio",""],
    "Enthalpy (kJ/kg)" : ["","enthalpy","","enthalpy",""],
    "Wind direction (°)": ["WindDirection","winddir", "dkl010h0", "dkl010h0","dkl010h0"],
    "Wind speed mean (m/s)": ["WindSpeed","windmean", "fkl010h0", "fkl010h0","fkl010h0"],
    "Wind speed max (m/s)" : ["","windmax", "fkl010h1", "fkl010h1","fkl010h1"],
    "Total sky cover (%)": ["TotalSkyCover","cloudcov", "skycover",""],
    "Global horizontal radiation (Wh/m²)": ["GlobalHorizontalRadiation","rad.global", "gls", "gls","gre000h0"],
    "Direct normal radiation (Wh/m²)": ["DirectNormalRadiation","rad.direct", "str.direkt", "str.direkt", ""],
    "Diffuse horizontal radiation (Wh/m²)": ["DiffuseHorizontalRadiation","rad.diffus", "str.diffus", "str.diffus","ods000h0"],
    "Horizontal infrared rad. intensity (Wh/m²)" : ["HorizontalInfraredRadiationIntensity","ir.horiz","","ir.horizontal", ""],
    "Air pressure (Pa)": ["StationPressure","airpres","", "prestahs", ""],
    "Vapor pressure (Pa)": ["","vappres","","","pva200h0"],
    "Snow Depth (cm)": ["SnowDepth","","","","htoauths"],
    "Albedo" : ["Albedo","albedo","","bodenalbedo"],
    "Ground emissivity (%)" : ["","emissivity","","bodenemissivitaet"],
    "Liquid precipitation depth (mm)": ["LiquidPrecipitationDepth","precip","","rre150h0","rre150h0"],
    "Liquid precipitation quantity (mm/h)": ["LiquidPrecipitationQuantity","","",""]
}

SIMPLE_VARIABLE_OPTIONS ={
"Dry bulb (°C)",
"Relative humidity (%)",
"Global horizontal radiation (Wh/m²)",
"Liquid precipitation depth (mm)"
}

VAR_NAME_EN_TO_FR = {
    "Dry bulb (°C)": "Température de bulbe sec (°C)",
    "Wet bulb (°C)": "Température de bulbe humide (°C)",
    "Dew point (°C)": "Température du point de rosée (°C)",
    "Relative humidity (%)": "Humidité relative (%)",
    "Mixing ratio (g/kg)" : "Mixing ratio (g/kg)" ,
    "Enthalpy (kJ/kg)" : "Enthalpie (kJ/kg)",
    "Wind speed mean (m/s)": "Vitesse moyenne du vent (m/s)",
    "Wind speed max (m/s)": "Vitesse max du vent (raffales) (m/s)",
    "Wind direction (°)": "Direction du vent (°)",
    "Total sky cover (%)": "Couverture nuageuse (%)",
    "Global horizontal radiation (Wh/m²)": "Rayonnement global horizontal (Wh/m²)",
    "Direct normal radiation (Wh/m²)": "Rayonnement direct normal (Wh/m²)",
    "Diffuse horizontal radiation (Wh/m²)": "Rayonnement diffus horizontal (Wh/m²)",
    "Horizontal infrared rad. intensity (Wh/m²)" : "Horizontal infrared rad. intensity (Wh/m²)",
    "Air pressure (Pa)": "Pression atmosphérique (Pa)",
    "Vapor pressure (Pa)":"Pression de vapeur d'eau (Pa)",
    "Snow Depth (cm)": "Hauteur de neige (cm)",
    "Albedo":"Albedo",
    "Ground emissivity (%)" : "Emissivité du sol (%)",
    "Liquid precipitation depth (mm)": "Hauteur de précipitations (mm)",
    "Liquid precipitation quantity (mm/h)": "Quantité de précipitations (mm/h)",
}


# --- Color maps pour la Heatmap ---
# Mapping par variable (colonne interne) vers un colorscale Plotly
# NB: 'RdBu_r' = bleu pour valeurs basses, rouge pour valeurs hautes (inverse de 'RdBu').
COLOR_MAP_BY_VAR = {
    "Dry bulb (°C)": "RdBu_r",                           # Température absolue : bleu → rouge
    "Wet bulb (°C)": "RdBu_r",                           # Même logique que dry bulb
    "Dew point (°C)": "RdBu_r",                          # Humidité/Température
    "Relative humidity (%)": "YlGnBu",                   # Humidité : jaune → vert → bleu
    "Mixing ratio (g/kg)": "YlGnBu",                     # Variable liée à la vapeur : palette humide
    "Enthalpy (kJ/kg)": "Inferno",                       # Énergie thermique : palette chaude
    "Wind direction (°)": "Phase",                       # Donnée angulaire (optionnel en heatmap)
    "Wind speed mean (m/s)": "Turbo",                    # Intensité physique → perceptuel équilibré
    "Wind speed max (m/s)": "Turbo",                     # Même logique que mean
    "Total sky cover (tenths)": "Greys",                 # Nébulosité : nuancier gris recommandé
    "Global horizontal radiation (Wh/m²)": "YlOrBr",     # Rayonnement solaire global
    "Direct normal radiation (Wh/m²)": "Inferno",        # Soleil direct → palette chaude
    "Diffuse horizontal radiation (Wh/m²)": "Cividis",   # Diffus → perceptuel neutre
    "Hor. infrared rad. intensity (Wh/m²)": "Magma",     # Infrarouge → palette sombre/thermique
    "Air pressure (Pa)": "Viridis",                      # Grandeur monotone, perceptuelle
    "Vapor pressure (Pa)": "Viridis",                    # Semblable à pression
    "Snow Depth (cm)": "Blues_r",                          # Neige → bleu/blanc
    "Albedo": "Purples_r",                                 # Ratio 0–1 → séquentielle
    "Ground emissivity (%)": "Purples",                  # Similaire à albedo, mais inversé physiquement
    "Liquid precipitation depth (mm)": "Blues",          # Pluie → bleu
    "Liquid precipitation quantity (mm/h)": "Blues"       # Intensité de pluie
}

WEATHER_STATIONS = {
    "Aadorf / Tänikon (TAE)" : "TAE",
    "Acquarossa / Comprovasco (COM)" : "COM",
    "Adelboden (ABO)" : "ABO",
    "Aigle (AIG)" : "AIG",
    "Altdorf (ALT)" : "ALT",
    "Basel / Binningen (BAS)" : "BAS",
    "Basel centre-ville (BASSTA)" : "BASSTA",
    "Bern / Zollikofen (BER)" : "BER",
    "Bern centre-ville (BERSTA)" : "BERSTA",
    "Buchs / Aarau (BUS)" : "BUS",
    "Bullet / La Frétaz (FRE)" : "FRE",
    "Chur (CHU)" : "CHU",
    "Cimetta (CIM)" : "CIM",
    "Davos (DAV)" : "DAV",
    "Disentis (DIS)" : "DIS",
    "Engelberg (ENG)" : "ENG",
    "Evolène / Villa (EVO)" : "EVO",
    "Fahy (FAH)" : "FAH",
    "Genève / Cointrin (GVE)" : "GVE",
    "Genève centre-ville (GVESTA)" : "GVESTA",
    "Glarus (GLA)" : "GLA",
    "Güttingen (GUT)" : "GUT",
    "Hörnli (HOE)" : "HOE",
    "Interlaken (INT)" : "INT",
    "La Chaux-de-Fonds (CDF)" : "CDF",
    "Lausanne centre-ville (LAUSTA)" : "LAUSTA",
    "Locarno / Monti (OTL)" : "OTL",
    "Lugano (LUG)" : "LUG",
    "Luzern (LUZ)" : "LUZ",
    "Luzern centre-ville (LUZSTA)" : "LUZSTA",
    "Magadino / Cadenazzo (MAG)" : "MAG",
    "Montana (MVE)" : "MVE",
    "Napf (NAP)" : "NAP",
    "Neuchâtel (NEU)" : "NEU",
    "Nyon / Changins (CGI)" : "CGI",
    "Payerne (PAY)" : "PAY",
    "Piotta (PIO)" : "PIO",
    "Plaffeien (PLF)" : "PLF",
    "Poschiavo / Robbia (ROB)" : "ROB",
    "Pully (PUY)" : "PUY",
    "Robièi (ROE)" : "ROE",
    "Rünenberg (RUE)" : "RUE",
    "S. Bernardino (SBE)" : "SBE",
    "Samedan (SAM)" : "SAM",
    "Schaffhausen (SHA)" : "SHA",
    "Scuol (SCU)" : "SCU",
    "Sion (SIO)" : "SIO",
    "St. Gallen (STG)" : "STG",
    "Stabio (SBO)" : "SBO",
    "Ulrichen (ULR)" : "ULR",
    "Vaduz (VAD)" : "VAD",
    "Visp (VIS)" : "VIS",
    "Wädenswil (WAE)" : "WAE",
    "Winterthur centre-ville (WINSTA)" : "WINSTA",
    "Wynau (WYN)" : "WYN",
    "Zermatt (ZER)" : "ZER",
    "Zürich / Affoltern (REH)" : "REH",
    "Zürich centre-ville (ZUESTA)" : "ZUESTA",
    "Zürich / Fluntern (SMA)" : "SMA",
    "Zürich / Kloten (KLO)" : "KLO",
}

FREQ_MAP = {
    "Heure": "h",
    "Jour": "d",
    "Semaine": "W-MON",
    "Mois": "ME",
    "Année" : "YE"
}
FREQ_LABELS = {
    "Heure": {"singular": "heure","plural": "heures"},
    "Jour": {"singular": "jour","plural": "jours"},
    "Semaine": {"singular": "semaine","plural": "semaines"},
    "Mois": {"singular": "mois","plural": "mois"},
    "Année": {"singular": "année","plural": "années"}
}

FUNC_MAP = {
    "Moyenne": "mean",
    "Moyenne et enveloppe min/max": "mean_min_max",
    "Min": "min",
    "Max": "max",
    "Médiane": "median",
    "Quartile 25%" : lambda s: s.quantile(0.25),
    "Quartile 75%" : lambda s: s.quantile(0.75),
    "Ecart-type" : "std",
    "Somme": "sum",
    "Somme cumulée": "cumsum",
    # 'Somme cumulée' est un mot-clé traité par compute_aggregated_df
    # qui fera une agrégation par 'sum' puis un cumsum (par source).
}


#--------------------------
#---Affichage--------------
#--------------------------

MODES = {
    "simple": {
        "show_date_interval" : False,
        "var_options": ["Dry bulb (°C)","Relative humidity (%)","Global horizontal radiation (Wh/m²)","Liquid precipitation depth (mm)"],
        "func_options": ["Moyenne","Min","Max","Moyenne et enveloppe min/max"],
        "x_options": [
            {'label': 'Date', 'value': 'date'},
            {'label': 'Tri décroissant', 'value': 'desc'},
        ],
        "show_y_axis_scaling_options" : False,
        "show_events": False,
        "show_windrose_normalisation": False,
    },

    "advanced": {
        "show_date_interval" : True,
        "var_options": list(VARIABLE_MAP.keys()),
        "func_options": list(FUNC_MAP.keys()),
        "x_options": [
            {'label': 'Date', 'value': 'date'},
            {'label': 'Tri décroissant', 'value': 'desc'},
            {'label': 'Tri croissant', 'value': 'asc'},
        ],
        "show_y_axis_scaling_options" : True,
        "show_events": True,
        "show_windrose_normalisation": True,
    }
}

LINE_COLORS = [
    "#163aa5",  # bleu
    "#66c9fd",  # bleu clair
    "#b2612a",  # orange
    "#f0a052",  # orange clair
    "#549c72",  # vert
    "#9bd5a9",  # vert clair
    "#9f59b7",  # violet
    "#f1a3f7",  # violet clair
    "#000000",  # noir
    "#7F7F7F",  # noir clair (gris)
]

LINE_COLORS = [
    # Bleu
    "#163aa5",  # bleu
    "#66c9fd",  # bleu clair
    "#b8e8ff",  # bleu pastel
    # Orange
    "#b2612a",  # orange
    "#f0a052",  # orange clair
    "#f8d1ae",  # orange pastel
    # Vert
    "#549c72",  # vert
    "#9bd5a9",  # vert clair
    "#d4efd9",  # vert pastel
    # Violet
    "#9f59b7",  # violet
    "#f1a3f7",  # violet clair
    "#f7d6fa",  # violet pastel
    # Noir / Gris
    "#000000",  # noir
    "#7f7f7f",  # gris
    "#d9d9d9",  # gris clair
]

LINE_STYLES = [
    {"symbol": "━", "plotly": "solid"},
    {"symbol": "╌╌", "plotly": "dash"},
    {"symbol": "···", "plotly": "dot"},
    {"symbol": "−·−", "plotly": "dashdot"},
]

# Heat Map : Options proposées en mode Manuel (liste de colorscales Plotly)
MANUAL_COLOR_MAP_OPTIONS = [
    "Viridis", "Cividis", "Turbo",
    "RdBu_r", "YlGnBu", "YlOrBr",
    "Inferno", "Plasma", "Magma",
    "Earth", "Greens", "Blues", "Purples",
]

TOOLTIPS_ENABLED = True

TOOLTIPS = {
"advanced-mode" : "Le mode avancé permet d'accéder à des options supplémentaires",
"station-dropdown" : "Sélection de la station météo",
"dataset-dropdown" : [
    "RCP : Scenarios d'émissions de gaz à effet de serre. RCP 2.6 est très optimiste; RCP 8.5 correspond au 'business as usual'",
    html.Br(),
    "DRY : scenario représentatif de la période (Design Reference Year)",
    html.Br(),
    "1-in-10 : scenario représentatif d'un été chaud survenant environ 1 année sur 10",
    ],
"date-interval-container" : "Ce filtre s'applique au graphe (également avec l'axe X en mode tri), aux roses des vents et heatmaps",
"Agregation-container" : "Les données brutes sont au pas de temps horaire. La combinaison d'un pas de temps et d'une fonction permet d'afficher, par exemple, des moyennes mensuelles ou des maxima journaliers.",
"x-mode" : "Le mode Tri permet de classer les valeurs pour rapidement voir leur distribution.",
}

