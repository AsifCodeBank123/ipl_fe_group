from openai import OpenAI
import streamlit as st


# -----------------------------
# NVIDIA CLIENT
# -----------------------------
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=st.secrets["NVIDIA_API_KEY"]  # we will set this later
)


# -----------------------------
# BUILD INPUT DATA
# -----------------------------
def build_ai_input(team_df):

    summary = []

    # detect correct column names safely
    points_col = None
    projection_col = None

    for col in team_df.columns:
        if "point" in col.lower():
            points_col = col
        if "projection" in col.lower():
            projection_col = col

    for _, row in team_df.iterrows():
        summary.append({
            "owner": row.get("Owner"),
            "rank": int(row.get("Rank", 0)),
            "points": float(row.get(points_col, 0)),
            "projection": float(row.get(projection_col, 0))
        })

    return summary


# -----------------------------
# GENERATE INSIGHTS
# -----------------------------
def generate_ai_insights(team_df):

    data = build_ai_input(team_df)

    prompt = f"""
        You are a fantasy cricket expert.

        Based on standings:
        {data}

        Return output in EXACT format:

        Rising:
        <Name> (Rank X)
        <short line>

        Falling:
        <Name> (Rank X)
        <short line>

        Key Battle:
        <Name vs Name>
        <short line with points difference>

        Bonus Insight:
        <one additional smart observation>

        Rules:
        - Keep each line short
        - Use numbers like 1188 (no commas, formatting handled later)
        - No markdown, no symbols (*, -)
        """

    response = client.chat.completions.create(
        model="mistralai/mistral-large-3-675b-instruct-2512",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )

    return response.choices[0].message.content


# -----------------------------
# CACHE (IMPORTANT)
# -----------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def generate_ai_insights_cached(team_df, day):
    return generate_ai_insights(team_df)