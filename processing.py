
# processing.py
import pandas as pd
from config import FREQ_MAP, FUNC_MAP

def compute_aggregated_df(all_df: pd.DataFrame, period_label: str, func_label: str, var_col: str) -> pd.DataFrame:
    # Aggrège les données selon la période period_label et la fonction func_label, pour la variable var_col
    freq = FREQ_MAP[period_label]
    func = FUNC_MAP[func_label]

    if var_col not in all_df.columns:
        # Sécurité : renvoyer un DF vide si la variable n'existe pas
        return pd.DataFrame(columns=["source", "datetime", var_col])

    # 1) Agrégation par période
    base = (
        all_df.set_index("datetime")
        .groupby("source")[var_col]
        .resample(freq)
    )

    if func == "cumsum":
        # 1a) On somme par période (additive), quelle que soit la variable, puis on cumulera par source.
        aggregated = base.sum().reset_index()
        aggregated = aggregated.sort_values(["source", "datetime"])
        # 2) Cumul par source
        aggregated[var_col] = aggregated.groupby("source")[var_col].cumsum()
        return aggregated
    else:
        # Cas standard: func est un string ('mean','min',...) ou une fonction lambda (pour les quantiles)
        aggregated = base.agg(func).reset_index()
        return aggregated




def filter_by_period(df: pd.DataFrame, start_month: int, start_day: int,
                     end_month: int, end_day: int) -> pd.DataFrame:
    """
    Filtre [df] entre MM-DD -> MM-DD, en utilisant directement datetime.dt.dayofyear.
    S'il n'y a aucun datetime valide (tout NaT), la fonction renvoie df tel quel (pas de filtre).
    """
    out = df.copy()
    out['datetime'] = pd.to_datetime(out['datetime'], errors='coerce')

    # Si tout est NaT: ne pas filtrer
    if out['datetime'].isna().all():
        # print('[filter_by_period] datetime is all NaT -> skip filtering')
        return out

    doy = out['datetime'].dt.dayofyear

    start = pd.Timestamp(year=2001, month=start_month, day=start_day).day_of_year
    end   = pd.Timestamp(year=2001, month=end_month,  day=end_day).day_of_year

    if start <= end:
        mask = (doy >= start) & (doy <= end)
    else:
        # période chevauchante (ex. 11-01 → 02-28)
        mask = (doy >= start) | (doy <= end)

    # Fallback si mask est tout False (ex: erreur de typage atypique)
    if not mask.any():
        # print('[filter_by_period] mask empty -> return df unchanged')
        return out

    return out.loc[mask].copy()



def indicator_days_min_temp_above(df: pd.DataFrame, threshold: float,
                                  var_col: str = 'DryBulb') -> int:
    daily_min = (df.set_index('datetime')[var_col]
                   .resample('d')
                   .min())
    return int((daily_min >= threshold).sum())

def indicator_heating_degree_days(df: pd.DataFrame, base: float = 20.0,
                                  var_col: str = 'DryBulb', method: str = 'daily') -> float:
    s = df.set_index('datetime')[var_col]
    if method == 'hourly':
        hourly = s.resample('h').mean()
        hdd_hours = (base - hourly).clip(lower=0)
        return float(hdd_hours.sum() / 24.0)
    else:
        daily_mean = s.resample('d').mean()
        hdd_daily = (base - daily_mean).clip(lower=0)
        return float(hdd_daily.sum())