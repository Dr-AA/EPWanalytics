
# epw_io.py
import os
import pandas as pd
from config import REFERENCE_YEAR, LEAP_DAY_POLICY

COLUMN_RENAME = {
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
    27:"PrecipitableWater",
    28:"AerosolOpticalDepth",
    29:"SnowDepth",
    30:"DaysSinceLastSnowfall",
    31:"Albedo",
    32:"LiquidPrecipitationDepth",
    33:"LiquidPrecipitationQuantity",
}

def read_epw_like_aligned(path: str, label: str = None,
                           ref_year: int = REFERENCE_YEAR,
                           leap_policy: str = LEAP_DAY_POLICY) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=8, header=None, low_memory=False)
    df = df.rename(columns=COLUMN_RENAME)

    for c in ["Year", "Month", "Day", "Hour", "Minute"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in COLUMN_RENAME.values():
        if c not in ["Year", "Month", "Day", "Hour", "Minute"] and c in df.columns:
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

    meteo_cols = [c for c in COLUMN_RENAME.values()
                  if c not in ["Year", "Month", "Day", "Hour", "Minute"] and c in df.columns]
    out = df[meteo_cols].copy()
    out.insert(0, "datetime", dt)
    out["source"] = label if label else os.path.basename(path)
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
