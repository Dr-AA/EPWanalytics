
# config.py
REFERENCE_YEAR = 2001
LEAP_DAY_POLICY = "drop"  # 'drop' | 'keep' | 'merge_to_28'

FREQ_MAP = {
    "Heure": "h",
    "Jour": "d",
    "Semaine": "W-MON",
    "Mois": "ME",
    "Année" : "y"
}

FUNC_MAP = {
    "Moyenne": "mean",
    "Min": "min",
    "Max": "max",
}

VARIABLE_MAP = {
    "Dry bulb (°C)": "DryBulb",
    "Dew point (°C)": "DewPoint",
    "Relative humidity (%)": "RelativeHumidity",
    "Wind speed (m/s)": "WindSpeed",
    "Wind direction (°)": "WindDirection",
    "Global horizontal radiation (Wh/m²)": "GlobalHorizontalRadiation",
    "Direct normal radiation (Wh/m²)": "DirectNormalRadiation",
    "Diffuse horizontal radiation (Wh/m²)": "DiffuseHorizontalRadiation",
    "Station pressure (Pa)": "StationPressure",
    "Precipitable water (mm)": "PrecipitableWater",
    "Liquid precipitation depth (mm)": "LiquidPrecipitationDepth",
    "Liquid precipitation quantity (mm/h)": "LiquidPrecipitationQuantity",
}

YLABEL_MAP = {
    "DryBulb": "Température de bulbe sec (°C)",
    "DewPoint": "Température du point de rosée (°C)",
    "RelativeHumidity": "Humidité relative (%)",
    "WindSpeed": "Vitesse du vent (m/s)",
    "WindDirection": "Direction du vent (°)",
    "GlobalHorizontalRadiation": "Rayonnement global horizontal (Wh/m²)",
    "DirectNormalRadiation": "Rayonnement direct normal (Wh/m²)",
    "DiffuseHorizontalRadiation": "Rayonnement diffus horizontal (Wh/m²)",
    "StationPressure": "Pression atmosphérique (Pa)",
    "PrecipitableWater": "Eau précipitable (mm)",
    "LiquidPrecipitationDepth": "Hauteur de précipitations (mm)",
    "LiquidPrecipitationQuantity": "Quantité de précipitations (mm/h)",
}


# --- Color maps pour la Heatmap ---
# Mapping par variable (colonne interne) vers un colorscale Plotly
# NB: 'RdBu_r' = bleu pour valeurs basses, rouge pour valeurs hautes (inverse de 'RdBu').
COLOR_MAP_BY_VAR = {
    "DryBulb": "RdBu_r",                 # Température : bleu -> rouge
    "DewPoint": "RdBu_r",                # Point de rosée
    "RelativeHumidity": "YlGnBu",        # Humidité : jaune -> vert -> bleu
    "WindSpeed": "Turbo",                # Vitesse du vent : multi (perceptuel)
    "WindDirection": "Phase",            # Direction (optionnel), mais Heatmap peu pertinente pour la direction
    "GlobalHorizontalRadiation": "YlOrBr",   # Rayonnement : jaune/orange/brun
    "DirectNormalRadiation": "Inferno",      # Rayonnement direct : palette chaude
    "DiffuseHorizontalRadiation": "Cividis", # Diffus : perceptuel, contrasté
    "StationPressure": "Viridis",            # Pression : perceptuel, neutre
    "LiquidPrecipitationDepth": "Blues",     # Précipitations : bleu
    # Fallbacks pour variables non mappées explicitement :
    # "PrecipitableWater": "PuBuGn",
    # "LiquidPrecipitationQuantity": "Blues",
}

# Options proposées en mode Manuel (liste de colorscales Plotly)
MANUAL_COLOR_MAP_OPTIONS = [
    "Viridis", "Cividis", "Turbo",
    "RdBu_r", "YlGnBu", "YlOrBr",
    "Inferno", "Plasma", "Magma",
    "Earth", "Greens", "Blues", "Purples",
]
