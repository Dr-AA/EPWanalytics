
# epw_io.py
import os
import pandas as pd
from config import REFERENCE_YEAR, LEAP_DAY_POLICY

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

SIA4028_EXPECTED_COLUMNS = [
    "station","time.yy","time.mm","time.dd","time.hh",
    "temp", "relhum", "vappres", "dewpt", "mixratio", "wetbulb", "enthalpy", "precip", "airpres",
    "winddir", "windmean", "windmax",
    "rad.global", "rad.direct", "rad.diffus", "rad.vert.N", "rad.vert.E", "rad.vert.S", "rad.vert.W",
    "ir.horiz", "cloudcov", "albedo", "emissivity"
]

SIA4028_COLUMN_RENAME = {
    "time.yy" : "Year",
    "time.mm" : "Month",
    "time.dd" : "Day",
    "time.hh" : "Hour",
}

def read_epw_like_aligned(path: str, label: str = None,
                           ref_year: int = REFERENCE_YEAR,
                           leap_policy: str = LEAP_DAY_POLICY) -> pd.DataFrame:
    if os.path.splitext(path)[1].lower() == ".epw":
        print("Reading epw file")
        df = pd.read_csv(path, skiprows=8, header=None, low_memory=False)
        df = df.rename(columns=EPW_COLUMN_RENAME)
    elif os.path.splitext(path)[1].lower() == ".csv":
        print("Reading csv file")
        df = pd.read_csv(path, skiprows=0, low_memory=False)
        if list(df.columns) != SIA4028_EXPECTED_COLUMNS:
            print("Error reading .csv file : unexpected column names.")
            return
        df = df.rename(columns=SIA4028_COLUMN_RENAME)
        df["Minute"] = 60
    else :
        print("Error reading weather file : the file format is unknown.")
        return

    for c in ["Year", "Month", "Day", "Hour", "Minute"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    #for c in EPW_COLUMN_RENAME.values():
    for c in df.columns:
        if c not in ["Year", "Month", "Day", "Hour", "Minute"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if leap_policy != "keep":
        is_feb29 = (df["Month"] == 2) & (df["Day"] == 29)
        if leap_policy == "drop":
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

    meteo_cols = [c for c in EPW_COLUMN_RENAME.values()
                  if c not in ["Year", "Month", "Day", "Hour", "Minute"] and c in df.columns]
    out = df[meteo_cols].copy()
    out.insert(0, "datetime", dt)
    out["source"] = label if label else os.path.basename(path)


    # ✅ Remplacer les valeurs sentinelles par NaN
    for var, nan_val in EPW_NAN_VALUE_MAP.items():
        if var in out.columns:
            out[var] = out[var].mask(out[var] >= nan_val)

    return out

def load_weather_data_from_folder(folder: str, files=None, exts=(".epw", ".csv"),
                                  ref_year: int = REFERENCE_YEAR,
                                  leap_policy: str = LEAP_DAY_POLICY) -> pd.DataFrame:
    if files is None:
        files = [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in exts]
    series = []
    for fname in files:
        path = os.path.join(folder, fname)
        if not os.path.isfile(path):
            print(f"[WARN] Missing file: {path}")
            continue
        try:
            series.append(read_epw_like_aligned(path, label=os.path.splitext(fname)[0],
                                                ref_year=ref_year, leap_policy=leap_policy))
        except Exception as e:
            print(f"[WARN] Failed reading {fname}: {e}")
    if not series:
        raise RuntimeError("No valid EPW/CSV files loaded.")
    all_df = pd.concat(series, ignore_index=True).sort_values("datetime")

    return all_df
