
# config.py
REFERENCE_YEAR = 2001
LEAP_DAY_POLICY = "drop"  # 'drop' | 'keep' | 'merge_to_28'



# VARIABLE_MAP : dictionnaire avec le noms de colonne unifiés (keys), et les noms de colonnes correspondant dans les formats suivants :
# 1) epw
# 2) csv - SIA4028 année 2023
# 3) csv - SIA2028 année 2035 et 2060
# 4) csv - SIA2028 contemporain (ancien jeu de données)
VARIABLE_MAP = {
    "Dry bulb (°C)": ["DryBulb", "temp", "tre200h0","tre200h0"],
    "Wet bulb (°C)": ["","wetbulb", "","wetbulb"],
    "Dew point (°C)": ["DewPoint","dewpt", "","dewpt"],
    "Relative humidity (%)": ["RelativeHumidity","relhum", "ure200h0", "ure200h0"],
    "Mixing ratio (g/kg)" : ["", "mixratio","", "mixratio"],
    "Enthalpy (kJ/kg)" : ["","enthalpy","","enthalpy"],
    "Wind direction (°)": ["WindDirection","winddir", "dkl010h0", "dkl010h0"],
    "Wind speed mean (m/s)": ["WindSpeed","windmean", "fkl010h0", "fkl010h0"],
    "Wind speed max (m/s)" : ["","windmax", "fkl010h1", "fkl010h1"],
    "Total sky cover (%)": ["TotalSkyCover","cloudcov", "skycover",""],
    "Global horizontal radiation (Wh/m²)": ["GlobalHorizontalRadiation","rad.global", "gls", "gls"],
    "Direct normal radiation (Wh/m²)": ["DirectNormalRadiation","rad.direct", "str.direkt", "str.direkt"],
    "Diffuse horizontal radiation (Wh/m²)": ["DiffuseHorizontalRadiation","rad.diffus", "str.diffus", "str.diffus"],
    "Horizontal infrared rad. intensity (Wh/m²)" : ["HorizontalInfraredRadiationIntensity","ir.horiz","","ir.horizontal"],
    "Air pressure (Pa)": ["StationPressure","airpres","", "prestahs"],
    "Vapor pressure (Pa)": ["","vappres","",""],
    "Snow Depth (cm)": ["SnowDepth","","",""],
    "Albedo" : ["Albedo","albedo","","bodenalbedo"],
    "Ground emissivity (%)" : ["","emissivity","","bodenemissivitaet"],
    "Liquid precipitation depth (mm)": ["LiquidPrecipitationDepth","precip","","rre150h0"],
    "Liquid precipitation quantity (mm/h)": ["LiquidPrecipitationQuantity","","",""]
}

VAR_NAME_EN_TO_FR = {
    "Dry bulb (°C)": "Température de bulbe sec (°C)",
    "Wet bulb (°C)": "Température de bulbe humide (°C)",
    "Dew point (°C)": "Température du point de rosée (°C)",
    "Relative humidity (%)": "Humidité relative (%)",
    "Wind speed mean (m/s)": "Vitesse moyenne du vent (m/s)",
    "Wind speed max (m/s)": "Vitesse max du vent (raffales) (m/s)",
    "Wind direction (°)": "Direction du vent (°)",
    "Total sky cover (tenths)": "Couverture nuageuse (dixièmes)",
    "Global horizontal radiation (Wh/m²)": "Rayonnement global horizontal (Wh/m²)",
    "Direct normal radiation (Wh/m²)": "Rayonnement direct normal (Wh/m²)",
    "Diffuse horizontal radiation (Wh/m²)": "Rayonnement diffus horizontal (Wh/m²)",
    "Air pressure (Pa)": "Pression atmosphérique (Pa)",
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

# Options proposées en mode Manuel (liste de colorscales Plotly)
MANUAL_COLOR_MAP_OPTIONS = [
    "Viridis", "Cividis", "Turbo",
    "RdBu_r", "YlGnBu", "YlOrBr",
    "Inferno", "Plasma", "Magma",
    "Earth", "Greens", "Blues", "Purples",
]


UNIT_CONVERSIONS = {
    "EPW": {
        "TotalSkyCover": 10.0,   # tenths → %
        "OpaqueSkyCover": 10.0,  # tenths → %
    },
    "SIA 4028": {
    },
    "SIA 2028:2023": {
        "Air pressure (Pa)": 100.0,         # hPa → Pa
        "Albedo": 1/100.0,                  # % → fraction
    },
    "SIA 2028:2010":{
    }
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

FUNC_MAP = {
    "Moyenne": "mean",
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