import pandas as pd
import os

def load_data():
    df = pd.read_csv("data/points.csv")
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "", regex=False)
    return df

def load_matches():
    if os.path.exists("data/matches_by_day.csv"):
        return pd.read_csv("data/matches_by_day.csv")
    return pd.DataFrame(columns=["Day", "Teams"])

def load_captains():
    if os.path.exists("data/captain_changes.csv"):
        df = pd.read_csv("data/captain_changes.csv")
        df.columns = df.columns.str.lower().str.strip()
        return df
    return pd.DataFrame(columns=["owner_name","from_day","captain","vice_captain"])