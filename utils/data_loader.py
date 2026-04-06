import pandas as pd
import streamlit as st
import os


#for google sheet
@st.cache_data
def load_data():

    sheet_id = "1saVEcqsG-AvFat-O8-X3V_6s1EySsnZC7KIWcyT537U"

    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    df = pd.read_csv(url)

    return df

# #local csv
# def load_data():
#     df = pd.read_csv("data/points.csv")
#     df.columns = df.columns.str.lower().str.strip().str.replace(" ", "", regex=False)
#     return df

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