
# read_weather_file.py
import os
import pandas as pd
from weather_graph.config_weather_graph import VARIABLE_MAP

REFERENCE_YEAR = 2001
LEAP_DAY_POLICY = "drop"  # 'drop' | 'keep' | 'merge_to_28'

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

EPW_COLUMN_RENAME = {
    0:"Year", 1:"Month", 2:"Day", 3:"Hour", 4:"Minute",
    6:"DryBulb",
    7:"DewPoint",
    8:"RelativeHumidity",
    9:"StationPressure",
    10:"ExtraterrestrialHorizontalRadiation",
    11:"ExtraterrestrialDirectNormalRadiation",
    12:"HorizontalInfraredRadiationIntensity",
    13:"GlobalHorizontalRadiation",
    14:"DirectNormalRadiation",
    15:"DiffuseHorizontalRadiation",
    16:"GlobalHorizontalIlluminance",
    17:"DirectNormalIlluminance",
    18:"DiffuseHorizontalIlluminance",
    19:"ZenithLuminance",
    20:"WindDirection",
    21:"WindSpeed",
    22:"TotalSkyCover",
    23:"OpaqueSkyCover",
    24:"Visibility",
    25:"CeilingHeight",
    28:"PrecipitableWater",
    29:"AerosolOpticalDepth",
    30:"SnowDepth",
    31:"DaysSinceLastSnowfall",
    32:"Albedo",
    33:"LiquidPrecipitationDepth",
    34:"LiquidPrecipitationQuantity",
}

EPW_NAN_VALUE_MAP = {
    "DryBulb" : 99.9,
    "DewPoint" : 99.9,
    "RelativeHumidity" : 999,
    "StationPressure" : 999999,
    "ExtraterrestrialHorizontalRadiation" : 9999,
    "ExtraterrestrialDirectNormalRadiation" : 9999,
    "HorizontalInfraredRadiationIntensity" : 9999,
    "GlobalHorizontalRadiation" : 9999,
    "DirectNormalRadiation" : 9999,
    "DiffuseHorizontalRadiation" : 9999,
    "GlobalHorizontalIlluminance" : 999999,
    "DirectNormalIlluminance" : 999999,
    "DiffuseHorizontalIlluminance" : 999999,
    "ZenithLuminance" : 9999,
    "WindDirection" : 999,
    "WindSpeed" : 999,
    "TotalSkyCover" : 99,
    "OpaqueSkyCover" : 99,
    "Visibility" : 9999,
    "CeilingHeight" : 99999,
    "PrecipitableWater" : 999,
    "AerosolOpticalDepth" : .999,
    "SnowDepth" : 999,
    "DaysSinceLastSnowfall" : 99,
    "Albedo" : 999,
    "LiquidPrecipitationDepth" : 999,
    "LiquidPrecipitationQuantity" : 99,
}

SIA2028_2010_EXPECTED_COLUMNS = [
    "time.yy","time.mm","time.dd","time.hh",
    "tre200h0","prestahs","ure200h0","rre150h0",
    "fkl010h0","fkl010h1","dkl010h0",
    "tso100hs","nto000sw",
    "gls","str.diffus","str.direkt",
    "str.vert.E","str.vert.S","str.vert.W","str.vert.N",
    "bodenalbedo",
    "ir.horizontal","ir.vertikal.S",
    "bodenemissivitaet",
    "dewpt","enthalpy","mixratio","wetbulb"
]

SIA2028_2023_EXPECTED_COLUMNS = [
    "time.yy", "time.mm", "time.dd", "time.hh",
    "tre200h0", "ure200h0", "fkl010h0", "fkl010h1", "dkl010h0",
    "skycover",    "gls", "str.diffus", "str.direkt"
]

SIA4028_EXPECTED_COLUMNS = [
    "station","time.yy","time.mm","time.dd","time.hh",
    "temp", "relhum", "vappres", "dewpt", "mixratio", "wetbulb", "enthalpy", "precip", "airpres",
    "winddir", "windmean", "windmax",
    "rad.global", "rad.direct", "rad.diffus", "rad.vert.N", "rad.vert.E", "rad.vert.S", "rad.vert.W",
    "ir.horiz", "cloudcov", "albedo", "emissivity"
]

METEOSUISSE_EXPECTED_COLUMNS = [
    "station_abbr", "reference_timestamp", "tre200h0", "tre200hn", "tre200hx", "tre005h0", "tre005hn", "ure200h0",
    "pva200h0", "tde200h0", "prestah0", "pp0qffh0", "pp0qnhh0", "ppz700h0", "ppz850h0", "fkl010h1", "dkl010h0",
    "fkl010h0", "fu3010h0", "fu3010h1", "fkl010h3", "fu3010h3", "wcc006h0", "fve010h0", "rre150h0", "htoauths",
    "gre000h0", "oli000h0", "olo000h0", "osr000h0", "ods000h0", "sre000h0", "erefaoh0", "tso005hs", "tso010hs",
    "tso020hs"
]

SIA_TIME_COLUMN_RENAME = {
    "time.yy" : "Year",
    "time.mm" : "Month",
    "time.dd" : "Day",
    "time.hh" : "Hour",
}


def build_reverse_variable_map(variable_map):
    '''Exemple :
    Input :
    variable_map = {
        "Dry bulb (°C)": ["DryBulb", "temp"],
        "Dew point (°C)": ["DewPoint","dewpt"],
    }
    Output :
    reverse = {
        "DryBulb": "Dry bulb (°C)",
        "temp": "Dry bulb (°C)",
        "DewPoint": "Dew point (°C)",
        "dewpt": "Dew point (°C)",
        ...
    }
    '''
    reverse_map = {}
    for unified_name, variants in variable_map.items():
        for colname in variants:
            if colname:  # ignore strings vides
                reverse_map[colname] = unified_name
    return reverse_map


def rename_columns_to_unified(df, variable_map):
    #Utilise le reverse variable_map pour renommer les colonnes
    reverse_map = build_reverse_variable_map(variable_map)
    new_cols = {}

    for col in df.columns:
        if col in reverse_map:
            new_cols[col] = reverse_map[col]  # rename to unified name
    return df.rename(columns=new_cols)



def read_weather_file(path: str, label: str = None,
                      ref_year: int = REFERENCE_YEAR,
                      leap_policy: str = LEAP_DAY_POLICY) -> pd.DataFrame:

    #Load dataframe according to file extension
    file_ext = os.path.splitext(path)[1].lower()
    if file_ext == ".epw":
        df = pd.read_csv(path, skiprows=8, header=None, low_memory=False)
    elif file_ext == ".csv":
        with open(path, "r", encoding="utf-8") as f:
            first_line = f.readline()
        sep = ";" if first_line.count(";") > first_line.count(",") else ","
        df = pd.read_csv(path, sep=sep, skiprows=0, low_memory=False)
    else:
        print("[WARN] Error reading weather file : the file format is unknown.")
        return

    #Determine data format and rename columns accordingly
    if file_ext == ".epw":
        data_format = "EPW"
        df = df.rename(columns=EPW_COLUMN_RENAME)  # Colonnes sans noms -> noms de variables EPW
    elif list(df.columns) == SIA4028_EXPECTED_COLUMNS:
        data_format = "SIA 4028"
        df = df.rename(columns=SIA_TIME_COLUMN_RENAME) #Colonnes temporelles SIA -> colonnes temporelles unifiées
        df["Minute"] = 60
    elif list(df.columns) == SIA2028_2023_EXPECTED_COLUMNS:
        data_format = "SIA 2028:2023"
        df = df.rename(columns=SIA_TIME_COLUMN_RENAME) #Colonnes temporelles SIA -> colonnes temporelles unifiées
        df["Minute"] = 60
    elif list(df.columns) == SIA2028_2010_EXPECTED_COLUMNS:
        data_format = "SIA 2028:2010"
        df = df.rename(columns=SIA_TIME_COLUMN_RENAME) #Colonnes temporelles SIA -> colonnes temporelles unifiées
        df["Minute"] = 60
    elif list(df.columns) == METEOSUISSE_EXPECTED_COLUMNS:
        data_format = "MeteoSuisse valeurs mesurées"
        print("Reading .csv file with Meteosuisse (measured values) column names.")
        df["reference_timestamp"] = pd.to_datetime(df["reference_timestamp"],format="%d.%m.%Y %H:%M")
        df["Year"] = df["reference_timestamp"].dt.year
        df["Month"] = df["reference_timestamp"].dt.month
        df["Day"] = df["reference_timestamp"].dt.day
        df["Hour"] = df["reference_timestamp"].dt.hour
        df["Minute"] = 60
    else:
        print("[WARN] Reading .csv file with unknown column names - skipping this file.")
        col_names = ";".join(df.columns)
        print(f"Nombre de colonnes : {len(df.columns)}")
        print(col_names)
        return
    print(f"-- Reading file with data format : {data_format}--")

    #Convert to numeric
    for c in df.columns:
        if c not in ["Year", "Month", "Day", "Hour", "Minute"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    #Handle date format : convert ref_year, month, day, minute to datetime
    if leap_policy != "keep":
        is_feb29 = (df["Month"] == 2) & (df["Day"] == 29)
        if leap_policy == "drop":
            print(f"Applying drop policy (is_feb29 : {is_feb29.sum()})")
            df = df.loc[~is_feb29].copy()
        elif leap_policy == "merge_to_28":
            df.loc[is_feb29, "Day"] = 28

    base_date = pd.to_datetime(
        (pd.Series([ref_year] * len(df)).astype(str) + "-" +
         df["Month"].astype(str).str.zfill(2) + "-" +
         df["Day"].astype(str).str.zfill(2)),
        errors="coerce"
    )
    hour = df["Hour"].astype(int)
    minute = df["Minute"].astype(int)
    minutes_since_midnight = (hour - 1) * 60 + minute
    minutes_since_midnight = minutes_since_midnight.where(minute != 60, hour * 60)
    dt = base_date + pd.to_timedelta(minutes_since_midnight, unit="m")

    #Unit conversion
    if data_format in UNIT_CONVERSIONS:
        for col, factor in UNIT_CONVERSIONS[data_format].items():
            if col in df.columns:
                df[col] *= factor

    #Column names conversion
    df = rename_columns_to_unified(df, VARIABLE_MAP)

    df.insert(0, "datetime", dt)
    df["source"] = path
    df["source_label"] = os.path.basename(path)

    # ✅ Remplacer les valeurs sentinelles par NaN
    for var, nan_val in EPW_NAN_VALUE_MAP.items():
        if var in df.columns:
            df[var] = df[var].mask(df[var] >= nan_val)
    return df

def load_weather_data_from_folder(folder: str, files=None, exts=(".epw", ".csv"),
                                  ref_year: int = REFERENCE_YEAR,
                                  leap_policy: str = LEAP_DAY_POLICY) -> pd.DataFrame:
    print("Loading weather files...")
    if files is None:
        files = [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]
    series = []
    for fname in files:
        path = os.path.join(folder, fname)
        if not os.path.isfile(path):
            print(f"[WARN] Missing file: {path}")
            continue
        try:
            series.append(read_weather_file(path, label=os.path.splitext(fname)[0],
                                            ref_year=ref_year, leap_policy=leap_policy))
        except Exception as e:
            print(f"[WARN] Failed reading {fname}: {e}")
    if not series:
        raise RuntimeError("No valid EPW/CSV files loaded.")
    all_df = pd.concat(series, ignore_index=True).sort_values("datetime")

    #print(all_df.columns)

    return all_df
