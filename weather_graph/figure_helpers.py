import pandas as pd

def add_events_to_figure(fig, events_df):
    print(f"Adding {len(events_df)} events")

    events_df = events_df.copy()
    events_df["start_datetime"] = pd.to_datetime(events_df["start_datetime"])
    events_df["end_datetime"] = pd.to_datetime(events_df["end_datetime"])

    for _, event in events_df.iterrows():
        print(f"Adding event from {event["start_datetime"]} to {event["end_datetime"]}")
        half_period = get_half_period(event["period_label"])
        fig.add_vrect(
            x0=event["start_datetime"]-half_period,
            x1=event["end_datetime"]+half_period,
            fillcolor="red",
            opacity=0.15,
            line_width=0,
        )
    return fig

def get_half_period(period_label):
    if period_label == "Heure":
        return pd.Timedelta(hours=0.5)
    elif period_label == "Jour":
        return pd.Timedelta(days=0.5)
    elif period_label == "Semaine":
        return pd.Timedelta(days=3.5)
    elif period_label == "Mois":
        # approximation
        return pd.Timedelta(days=15)
    elif period_label == "Année":
        # approximation
        return pd.Timedelta(days=182)

    return pd.Timedelta(days=0)