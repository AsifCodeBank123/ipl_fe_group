import streamlit as st
import plotly.express as px
import pandas as pd
import datetime
import pytz
import textwrap

from utils.data_loader import load_data, load_matches, load_captains
from utils.calculator import calculate_points
from utils.helpers import build_watchlist
from utils.ai_insights import generate_ai_insights_cached

# ----------------------------------------
# CONFIG
# ----------------------------------------
st.set_page_config(layout="wide", page_title="IPL Dashboard-FE Group")
TOTAL_MATCHES = 74

# ----------------------------------------
# LOAD CSS
# ----------------------------------------
with open("style/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if "refresh_trigger" not in st.session_state:
    st.session_state["refresh_trigger"] = False

# ----------------------------------------
# LOAD DATA
# ----------------------------------------
@st.cache_data
def load_all_data():
    df = load_data()
    matches_df = load_matches()
    cap_df = load_captains()
    return df, matches_df, cap_df

df, matches_df, cap_df = load_all_data()

# ----------------------------------------
# DAYS
# ----------------------------------------
day_cols = [c for c in df.columns if c.startswith("day")]
day_numbers = sorted([int(c.replace("day","")) for c in day_cols])

selected_day = st.sidebar.selectbox(
    "📅 Select Day",
    day_numbers,
    index=len(day_numbers)-1
)

# ----------------------------------------
# SIDEBAR (IMPROVED)
# ----------------------------------------
#st.sidebar.markdown("🏏 IPL Dashboard")

if st.sidebar.button("🔄 Refresh Data"):

    # Clear cache ONLY on click
    st.cache_data.clear()

    # Store IST time
    ist = pytz.timezone("Asia/Kolkata")
    st.session_state["last_refresh"] = datetime.datetime.now(ist)

    # Mark refresh trigger
    st.session_state["refresh_trigger"] = True

    st.rerun()

st.sidebar.markdown("---")

matches_left = TOTAL_MATCHES - selected_day + 1

st.sidebar.markdown(f"""
### 📌 Match Info
• Current Day: **{selected_day}**  
• Matches Left: **{matches_left}**
""")

st.sidebar.markdown("---")

st.sidebar.markdown("""
### 🧠 Rules
• Captain = 2×  
• Vice Captain = 1.5×  
• Max 2 changes allowed  
""")

st.sidebar.markdown("---")

st.sidebar.markdown("""
### 🔍 Tips
• Track captain impact  
• Focus on active franchises  
""")

effective_day = max(selected_day - 1, 1)

# ----------------------------------------
# CALCULATIONS
# ----------------------------------------
scored_df = calculate_points(df, cap_df, effective_day)
watch_map = build_watchlist(df, matches_df, cap_df, selected_day)

team_df = (
    scored_df.groupby("owner_name")["player_points"]
    .sum().reset_index()
    .rename(columns={"owner_name":"Owner","player_points":"Points"})
    .sort_values("Points", ascending=False)
)

team_df["Rank"] = range(1, len(team_df)+1)
team_df["Watchlist"] = team_df["Owner"].map(watch_map)



# ----------------------------------------
# MOVEMENT
# ----------------------------------------
if effective_day > 1:
    prev_df = calculate_points(df, cap_df, effective_day - 1)

    prev_team = (
        prev_df.groupby("owner_name")["player_points"]
        .sum().reset_index()
        .rename(columns={"owner_name": "Owner", "player_points": "Prev"})
    )

    prev_team["Prev Rank"] = prev_team["Prev"].rank(ascending=False)

    team_df = team_df.merge(prev_team, on="Owner", how="left")
    team_df["Movement"] = team_df["Prev Rank"] - team_df["Rank"]

else:
    team_df["Movement"] = 0

# ----------------------------------------
# 🔥 CORRECT DAILY GAINER (WITH C/VC MULTIPLIER)
# ----------------------------------------

# Current total (till selected day)
curr_points = (
    scored_df.groupby("owner_name")["player_points"]
    .sum()
)

# Previous total (till previous day)
if effective_day > 1:
    prev_scored = calculate_points(df, cap_df, effective_day - 1)

    prev_points = (
        prev_scored.groupby("owner_name")["player_points"]
        .sum()
    )

    day_points = curr_points - prev_points
else:
    day_points = curr_points

# Clean NaN (for day1 case)
day_points = day_points.fillna(curr_points)

max_points = day_points.max()

if max_points > 0:
    top_owners = day_points[day_points == max_points].index.tolist()
else:
    top_owners = []

#Movement Formatter

def format_movement(row):
    movement = row["Movement"]
    owner = row["Owner"]

    # Arrow logic
    if movement > 0:
        text = f"▲ +{int(movement)}"
    elif movement < 0:
        text = f"▼ {int(movement)}"
    else:
        text = "— 0"

    # Add 🔥 AFTER text
    if owner in top_owners:
        return f"{text} 🔥"

    return text

team_df["Movement"] = team_df.apply(format_movement, axis=1)

# ----------------------------------------
# DELTAS
# ----------------------------------------
scores = team_df["Points"].values

next_delta = [None] + [round(scores[i-1]-scores[i],1) for i in range(1,len(scores))]
first_delta = [None] + [round(scores[0]-s,1) for s in scores[1:]]

team_df["Next Rank"] = next_delta
team_df["1st Rank"] = first_delta

st.markdown("""
<style>
.top-counter {
    display:flex;
    justify-content:flex-end;
    align-items:center;
    margin-top:-10px;
    margin-bottom:8px;
}

.top-counter img {
    height:24px;
}

/* Mobile */
@media (max-width:768px) {
    .top-counter {
        justify-content:center;
        margin-top:0px;
    }
}
</style>

<div class="top-counter">
    <img src="https://hitscounter.dev/api/hit?url=https%3A%2F%2Fipl-dashboard-fe.streamlit.app%2F&label=Visits&icon=github&color=%230d6efd&message=&style=plastic&tz=UTC">
</div>
""", unsafe_allow_html=True)

# ----------------------------------------
# HEADER (NEW)
# ----------------------------------------
st.markdown(f"""
<div class="header">
    <div>
        <div class="title">🏏 IPL Fantasy Dashboard - FE Group</div>
        <div class="subtitle">Live standings till Day {selected_day - 1}</div>
    </div>
</div>
""", unsafe_allow_html=True)

if "last_refresh" in st.session_state:
    last = st.session_state["last_refresh"]
    st.caption(f"📡 Data synced at: {last.strftime('%d %b, %I:%M %p IST')}")
else:
    st.caption("📡 Data not refreshed yet")

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ----------------------------------------
# PROGRESS BAR
# ----------------------------------------

matches_completed = max(selected_day - 1, 0)
progress = matches_completed / TOTAL_MATCHES
percent = int(progress * 100)

st.markdown(f"""
<div style="font-size:0.9rem;color:#94a3b8;margin-bottom:4px;margin-top:10px">
📊 Season Progress: <b>{matches_completed}</b> / {TOTAL_MATCHES} matches ({percent}%)
</div>
""", unsafe_allow_html=True)

st.progress(progress)

# ----------------------------------------
# ✅ CORRECT HIGHEST & LOWEST GAINER (WITH C/VC)
# ----------------------------------------

# Current total (with C/VC)
curr_points = (
    scored_df.groupby("owner_name")["player_points"]
    .sum()
)

# Previous total (with C/VC)
if effective_day > 1:
    prev_scored = calculate_points(df, cap_df, effective_day - 1)

    prev_points = (
        prev_scored.groupby("owner_name")["player_points"]
        .sum()
    )

    day_points = curr_points - prev_points
else:
    day_points = curr_points

# Clean NaN
day_points = day_points.fillna(curr_points)

max_points = day_points.max()
min_points = day_points.min()

# Top & Low owner
top_owner = day_points.idxmax() if max_points > 0 else "—"
low_owner = day_points.idxmin() if max_points > 0 else "—"

# ----------------------------------------
# KPI (NEW)
# ----------------------------------------
k1, k2, k3, k4 = st.columns(4)

top_player = (
    scored_df.groupby("player_name")["player_points"]
    .sum().reset_index()
    .sort_values("player_points", ascending=False)
    .iloc[0]
)

k1.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(148,163,184,0.12), rgba(100,116,139,0.05));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(148,163,184,0.2);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        📊 Teams
    </div>
    <div style="font-size:22px; font-weight:700;">
        {len(team_df)}
    </div>
</div>
""", unsafe_allow_html=True)


k2.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(251,191,36,0.18), rgba(245,158,11,0.08));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(251,191,36,0.3);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        🏆 Leader
    </div>
    <div style="font-size:22px; font-weight:700;">
        {team_df.iloc[0]['Owner']}
    </div>
</div>
""", unsafe_allow_html=True)

k3.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(16,185,129,0.08));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(34,197,94,0.25);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        🔥 Highest Gainer
    </div>
    <div style="font-size:22px; font-weight:700;">
        {top_owner}
    </div>
    <div style="font-size:13px; color:#22c55e;">
        {int(max_points)} pts
    </div>
</div>
""", unsafe_allow_html=True)


k4.markdown(f"""
<div style="
    background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(37,99,235,0.08));
    padding:16px;
    border-radius:16px;
    border:1px solid rgba(59,130,246,0.25);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    text-align:center;
">
    <div style="font-size:13px; color:#94a3b8; margin-bottom:6px;">
        🧊 Lowest Gainer
    </div>
    <div style="font-size:22px; font-weight:700;">
        {low_owner}
    </div>
    <div style="font-size:13px; color:#3b82f6;">
        {int(min_points)} pts
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ----------------------------------------
# TABS
# ----------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🏆 Rankings","👥 Players","📊 Insights"," 🎯 Squad Composition", "🤝 Replacement","📅 Match Points"])

#helper to compute captain and vc points for captain strategy table

def get_c_vc_points(df,cap_df,owner,selected_day,role="captain"):

    oc = cap_df[cap_df["owner_name"] == owner].sort_values("from_day")
    if oc.empty:
        return "—"

    pts_list = []
    for d in range(1, selected_day + 1):
        day_col = f"day{d}"
        if day_col not in df.columns:
            continue

        cap_row = oc[oc["from_day"] <= d]
        if cap_row.empty:
            continue

        latest = cap_row.iloc[-1]
        player = latest["captain"] if role == "captain" else latest["vice_captain"]

        player_row = df[(df["owner_name"] == owner) & (df["player_name"] == player)]
        if player_row.empty:
            continue

        pts = pd.to_numeric(player_row.iloc[0].get(day_col, 0), errors="coerce")
        pts = 0 if pd.isna(pts) else pts

        mult = 2.0 if role == "captain" else 1.5
        val = round(pts * mult, 1)

        if val != 0:
            pts_list.append(val)

    return "—" if not pts_list else f"({', '.join(map(str, pts_list))})"

def get_current_c_vc(cap_df, owner, day):

    owner_changes = cap_df[
        (cap_df["owner_name"] == owner) &
        (cap_df["from_day"] <= day)
    ]

    if owner_changes.empty:
        return None, None

    latest = owner_changes.sort_values(
        "from_day"
    ).iloc[-1]

    return (
        latest["captain"],
        latest["vice_captain"]
    )

# ----------------------------------------
# PLAYER IMPACT SEGMENTATION
# ----------------------------------------

player_totals = (
    scored_df
    .groupby(["owner_name", "player_name"])["player_points"]
    .sum()
    .reset_index()
)

# Categorize
player_totals["category"] = player_totals["player_points"].apply(
    lambda x: "Dead (<10 points)" if x < 10 else "Active (≥10 points)"
)

# Count per owner per category
stack_df = (
    player_totals
    .groupby(["owner_name", "category"])["player_name"]
    .count()
    .reset_index(name="count")
)

# ==================================================
# TAB 1
# ==================================================
with tab1:

    st.markdown(f"""
    <span style="color:#94a3b8;font-size:0.85rem;">
    ℹ️ Rankings & movement are based on completed matches. Watchlist shows upcoming players for Day {selected_day}.
    </span>
    """, unsafe_allow_html=True)

    st.markdown("### 🏆 Team Rankings")

    display_df = team_df[
        ["Rank", "Owner", "Points", "Movement", "Next Rank", "1st Rank", "Watchlist"]
    ].rename(columns={
        "Points": "Total Points",
        "Watchlist": f"Watchlist (Day {selected_day})"
    })

    # 🔥 Highlight Top 3
    def highlight_top3(row):
        if row["Rank"] == 1:
            style = "background-color:#FFD700;color:black;font-weight:800"
        elif row["Rank"] == 2:
            style = "background-color:#C0C0C0;color:black;font-weight:700"
        elif row["Rank"] == 3:
            style = "background-color:#CD7F32;color:black;font-weight:700"
        else:
            style = ""
        return [style] * len(row)

    styled_df = (
        display_df
        .style
        .format({
            "Total Points": "{:.1f}",
            "Next Rank": "{:.1f}",
            "1st Rank": "{:.1f}"
        })
        .apply(highlight_top3, axis=1)
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": [("text-align", "center")]}])
    )

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # --------------------------------------------------
    # UPCOMING MATCH FORECASTS
    # --------------------------------------------------

    st.markdown("## 📈 Upcoming Match Forecasts")

    # --------------------------------------------------
    # NEXT 5 MATCHES
    # --------------------------------------------------
    future_matches = matches_df[
        matches_df["Day"] >= selected_day
    ].head(5).copy()

    if not future_matches.empty:

        # --------------------------------------------------
        # FORMAT MATCH LABEL
        # --------------------------------------------------
        def format_match_label(day, teams_str):

            teams = [
                t.strip()
                for t in teams_str.split(",")
            ]

            # DOUBLE HEADER
            if len(teams) == 4:

                return (
                    f"Day {day} - "
                    f"{teams[0]} vs {teams[1]} | "
                    f"{teams[2]} vs {teams[3]}"
                )

            # NORMAL MATCH
            elif len(teams) == 2:

                return (
                    f"Day {day} - "
                    f"{teams[0]} vs {teams[1]}"
                )

            return f"Day {day} - {teams_str}"

        # --------------------------------------------------
        # CREATE LABELS
        # --------------------------------------------------
        future_matches["match_label"] = future_matches.apply(
            lambda x: format_match_label(
                x["Day"],
                x["Teams"]
            ),
            axis=1
        )

        # --------------------------------------------------
        # BUILD FORECASTS
        # --------------------------------------------------
        all_match_forecasts = {}
        summary_rows = []

        for _, match in future_matches.iterrows():

            match_label = match["match_label"]

            teams = [
                t.strip()
                for t in match["Teams"].split(",")
            ]

            forecast_rows = []

            # ----------------------------------------
            # OWNER FORECAST
            # ----------------------------------------
            for owner, group in df.groupby("owner_name"):

                owner_players = group[
                    group["franchise"].isin(teams)
                ].copy()

                total = 0

                # current captain / VC for that match day
                captain, vice_captain = get_current_c_vc(
                    cap_df,
                    owner,
                    match["Day"]
                )

                # ----------------------------------------
                # PLAYER FORECAST
                # ----------------------------------------
                for _, r in owner_players.iterrows():

                    player = r["player_name"]

                    player_scores = []

                    for d in range(1, selected_day + 1):

                        day_col = f"day{d}"

                        pts = pd.to_numeric(
                            r.get(day_col, 0),
                            errors="coerce"
                        )

                        pts = 0 if pd.isna(pts) else pts

                        # ----------------------------------------
                        # APPLY FORECAST MULTIPLIER
                        # ----------------------------------------
                        if player == captain:
                            pts *= 2

                        elif player == vice_captain:
                            pts *= 1.5

                        if pts != 0:
                            player_scores.append(pts)

                    # ----------------------------------------
                    # PLAYER AVERAGE
                    # ----------------------------------------
                    avg_points = (
                        sum(player_scores) / len(player_scores)
                        if player_scores else 0
                    )

                    total += avg_points

                forecast_rows.append({
                    "Owner": owner,
                    "Predicted Points": round(total, 1)
                })

            # ----------------------------------------
            # FORECAST DF
            # ----------------------------------------
            forecast_df = pd.DataFrame(forecast_rows)

            forecast_df = forecast_df.sort_values(
                "Predicted Points",
                ascending=False
            )

            all_match_forecasts[match_label] = forecast_df

            # ----------------------------------------
            # SUMMARY ROW
            # ----------------------------------------
            top_row = forecast_df.iloc[0]

            summary_rows.append({
                "Match": match_label,
                "Top Owner": top_row["Owner"],
                "Best Forecast": round(top_row["Predicted Points"], 1)
            })

        # --------------------------------------------------
        # SUMMARY DF
        # --------------------------------------------------
        summary_df = pd.DataFrame(summary_rows)

    
        # --------------------------------------------------
        # MATCH FORECAST CARDS
        # --------------------------------------------------

        card_cols = st.columns(len(summary_df))

        for i, (_, row) in enumerate(summary_df.iterrows()):
            # Split the match string (assuming format "Day 45 • PBKS vs DC")
            day_part = row['Match'].split('-')[0].replace('Day', '').strip()
            team_part = row['Match'].split('-')[1].strip()

            # Use dedent to ensure no leading spaces trigger a "code block" look
            html = textwrap.dedent(f"""
                <div class="match-card">
                    <div class="match-top">
                        <div class="match-day">DAY {day_part}</div>
                        <div class="match-teams">{team_part}</div>
                    </div>
                    <div class="match-divider"></div>
                    <div class="match-label">🔥 Top Owner</div>
                    <div class="match-owner">{row['Top Owner']}</div>
                    <div class="match-points-label">Forecast</div>
                    <div class="match-points">{row['Best Forecast']} pts</div>
                </div>
            """)

            # Send to the specific column and use unsafe_allow_html
            if i < len(card_cols):
                card_cols[i].markdown(html, unsafe_allow_html=True)

        st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

        # --------------------------------------------------
        # MATCH SELECTOR
        # --------------------------------------------------
        selected_match = st.selectbox(
            "Select Match for Detailed Forecast",
            list(all_match_forecasts.keys())
        )

        selected_df = all_match_forecasts[selected_match]

        # --------------------------------------------------
        # TOP CARD
        # --------------------------------------------------
        top_owner = selected_df.iloc[0]

        st.markdown(f"""
        <div class="forecast-top-card">
            🔥 <b>{top_owner['Owner']}</b>
            projected to dominate
            <b>{selected_match}</b>
            with
            <b>{top_owner['Predicted Points']} pts</b>
        </div>
        """, unsafe_allow_html=True)

        # --------------------------------------------------
        # BAR CHART
        # --------------------------------------------------
        fig_forecast = px.bar(
            selected_df,
            x="Owner",
            y="Predicted Points",
            color="Predicted Points",
            text_auto=True
        )

        fig_forecast.update_layout(
            template="plotly_dark",
            height=420,
            xaxis_title=None,
            yaxis_title="Projected Match Points",
            coloraxis_showscale=False
        )

        st.plotly_chart(
            fig_forecast,
            use_container_width=True
        )

    else:
        st.info("No upcoming matches remaining.")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # --------------------------------------------------
    # FINAL TOURNAMENT FORECAST
    # --------------------------------------------------

    st.markdown("## 🏆 Final Tournament Forecast")

    # --------------------------------------------------
    # FORECAST FUNCTION
    # --------------------------------------------------

    def calculate_final_forecast(sim_day):

        future_matches_all = matches_df[
            matches_df["Day"] >= sim_day
        ].copy()

        forecast_rows = []

        for owner, group in df.groupby("owner_name"):

            # ----------------------------------------
            # CURRENT POINTS
            # ----------------------------------------
            current_points = team_df.loc[
                team_df["Owner"] == owner,
                "Points"
            ].values[0]

            future_projection = 0

            # ----------------------------------------
            # SIMULATE FUTURE MATCHES
            # ----------------------------------------
            for _, match in future_matches_all.iterrows():

                teams = [
                    t.strip()
                    for t in match["Teams"].split(",")
                ]

                owner_players = group[
                    group["franchise"].isin(teams)
                ].copy()

                captain, vice_captain = get_current_c_vc(
                    cap_df,
                    owner,
                    match["Day"]
                )

                match_projection = 0

                for _, r in owner_players.iterrows():

                    player = r["player_name"]

                    scores = []

                    for d in range(1, sim_day + 1):

                        pts = pd.to_numeric(
                            r.get(f"day{d}", 0),
                            errors="coerce"
                        )

                        pts = 0 if pd.isna(pts) else pts

                        # ----------------------------------------
                        # APPLY C / VC
                        # ----------------------------------------
                        if player == captain:
                            pts *= 2

                        elif player == vice_captain:
                            pts *= 1.5

                        if pts != 0:
                            scores.append(pts)

                    avg_points = (
                        sum(scores) / len(scores)
                        if scores else 0
                    )

                    match_projection += avg_points

                future_projection += match_projection

            predicted_final = (
                current_points +
                future_projection
            )

            forecast_rows.append({
                "Owner": owner,
                "Predicted Final": round(predicted_final, 1)
            })

        forecast_df = pd.DataFrame(forecast_rows)

        forecast_df = forecast_df.sort_values(
            "Predicted Final",
            ascending=False
        ).reset_index(drop=True)

        return forecast_df


    # --------------------------------------------------
    # CURRENT FORECAST
    # --------------------------------------------------

    forecast_df = calculate_final_forecast(
        selected_day
    )

    # --------------------------------------------------
    # PREVIOUS FORECAST
    # --------------------------------------------------

    previous_df = calculate_final_forecast(
        max(selected_day - 1, 1)
    )
    

    previous_map = dict(
        zip(
            previous_df["Owner"],
            previous_df["Predicted Final"]
        )
    )

    # --------------------------------------------------
    # FORECAST CARDS GRID
    # --------------------------------------------------

    forecast_list = forecast_df.to_dict("records")

    for row_start in range(0, len(forecast_list), 5):

        row_cards = forecast_list[row_start:row_start + 5]

        cols = st.columns(5)

        for i, row in enumerate(row_cards):

            owner = row["Owner"]

            current = row["Predicted Final"]

            old = previous_map.get(owner, current)

            delta = round(current - old, 1)

            trend = "➖"

            if delta > 0:
                trend = "🔼"

            elif delta < 0:
                trend = "🔽"


            html = textwrap.dedent(f"""
            <div class="final-forecast-card">
                <div class="forecast-rank">#{row_start + i + 1}</div>
                <div class="forecast-owner">{owner}</div>
                <div class="forecast-final-score">{current:,.0f}</div>
                <div class="forecast-trend"style="color:{'#22c55e' if delta > 0 else '#ef4444' if delta < 0 else '#94a3b8'};">{trend} {abs(delta):,.0f}</div>
            </div>""")

            cols[i].markdown(html,unsafe_allow_html=True)
            

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # ==================================================
    # 🧠 CAPTAIN STRATEGY (FINAL CLEAN VERSION)
    # ==================================================
    st.markdown("### 🧠 Captain Strategy")

    cap_df.columns = [c.lower() for c in cap_df.columns]

    # 🔧 Clean history + return changes count
    def format_history(series):
        if series.empty:
            return "—", 0

        cleaned = []
        prev = None

        for name in series.tolist():
            if name != prev:
                cleaned.append(name)
                prev = name

        history_str = cleaned[0] if len(cleaned) == 1 else " → ".join(cleaned)
        changes = max(len(cleaned) - 1, 0)

        return history_str, changes

    rows = []

    for owner in df["owner_name"].unique():

        oc = cap_df[
            cap_df["owner_name"] == owner
        ].sort_values("from_day")

        if not oc.empty:
            captain_history, cap_changes = format_history(oc["captain"])
            vc_history, vc_changes = format_history(oc["vice_captain"])
        else:
            captain_history, vc_history = "—", "—"
            cap_changes, vc_changes = 0, 0

        # ✅ Total changes (Captain + VC)
        total_changes = cap_changes + vc_changes

        rows.append({
            "Owner": owner,
            "Captain": captain_history,
            "Cap Points": get_c_vc_points(df,cap_df,owner,selected_day,role="captain"),
            "Vice Captain": vc_history,
            "VC Points": get_c_vc_points(df,cap_df,owner,selected_day,role="vice_captain"),
            "Changes": total_changes
        })

    cap_table = pd.DataFrame(rows)

    st.dataframe(cap_table,use_container_width=True,hide_index=True)

# ==================================================
# TAB 2
# ==================================================
with tab2:

    st.markdown("## 👥 Player Breakdown by Owner")

    owner_list = sorted(df["owner_name"].unique())
    selected_owner = st.selectbox("Select Owner", owner_list)

    # --------------------------------------------------
    # AGGREGATE TOTAL POINTS (SORTED DESC)
    # --------------------------------------------------
    owner_points_df = (
        scored_df
        .loc[scored_df["owner_name"] == selected_owner]
        .groupby(["player_name", "franchise"])["player_points"]
        .sum()
        .reset_index()
        .sort_values("player_points", ascending=False)
    )

    # --------------------------------------------------
    # GET CURRENT CAPTAIN / VC (DYNAMIC)
    # --------------------------------------------------
    cap_df.columns = [c.lower() for c in cap_df.columns]

    owner_caps = (
        cap_df[
            (cap_df["owner_name"] == selected_owner) &
            (cap_df["from_day"] <= selected_day)
        ]
        .sort_values("from_day")
    )

    if not owner_caps.empty:
        latest = owner_caps.iloc[-1]
        current_c = latest["captain"]
        current_vc = latest["vice_captain"]
    else:
        current_c = None
        current_vc = None

    # --------------------------------------------------
    # MATCH-WISE GAINS (NO ZERO, WITH MULTIPLIER)
    # --------------------------------------------------
    def get_player_daywise_gains(player_name):

        player_row = df[
            (df["owner_name"] == selected_owner) &
            (df["player_name"] == player_name)
        ]

        if player_row.empty:
            return "—"

        row = player_row.iloc[0]
        gains = []

        for d in range(1, selected_day + 1):

            day_col = f"day{d}"
            if day_col not in df.columns:
                continue

            points = pd.to_numeric(row.get(day_col, 0), errors="coerce")
            points = 0 if pd.isna(points) else points

            # --- dynamic captain lookup ---
            cap_row = owner_caps[owner_caps["from_day"] <= d]
            if not cap_row.empty:
                latest_cap = cap_row.iloc[-1]
                c = latest_cap["captain"]
                vc = latest_cap["vice_captain"]
            else:
                c, vc = None, None

            multiplier = 1.0

            if player_name == c:
                multiplier = 2.0
            elif player_name == vc:
                multiplier = 1.5

            value = round(points * multiplier, 1)

            if value != 0:
                gains.append(value)

        return "—" if not gains else f"({', '.join(map(str, gains))})"

    owner_points_df["Match-wise Gains"] = owner_points_df["player_name"].apply(
        get_player_daywise_gains
    )

    # --------------------------------------------------
    # CAPTAIN / VC LABEL
    # --------------------------------------------------
    def cv_label(player):
        if player == current_c:
            return "🧢 Captain"
        if player == current_vc:
            return "🎖️ Vice Captain"
        return ""

    owner_points_df["C / VC"] = owner_points_df["player_name"].apply(cv_label)

    # --------------------------------------------------
    # FINAL RENAME
    # --------------------------------------------------
    owner_points_df = owner_points_df.rename(columns={
        "player_name": "Player",
        "franchise": "Franchise",
        "player_points": "Points"
    })

    # --------------------------------------------------
    # STYLING
    # --------------------------------------------------
    def highlight_cv(row):

        if row["C / VC"] == "🧢 Captain":
            return [
                "background-color:rgba(251,191,36,0.15);"
                "border-left:4px solid #fbbf24;"
                "font-weight:600"
            ] * len(row)

        if row["C / VC"] == "🎖️ Vice Captain":
            return [
                "background-color:rgba(56,189,248,0.15);"
                "border-left:4px solid #38bdf8;"
                "font-weight:600"
            ] * len(row)

        return [""] * len(row)

    styled_owner_df = (
        owner_points_df
        .style
        .format({"Points": "{:.1f}"})
        .apply(highlight_cv, axis=1)
    )

    st.dataframe(
        styled_owner_df,
        use_container_width=True,
        hide_index=True
    )

# ==================================================
# TAB 3
# ==================================================
with tab3:

    st.markdown("### 📊 Insights")

    col1, col2 = st.columns(2)

    fig1 = px.bar(team_df, x="Owner", y="Points")
    fig1.update_layout(template="plotly_dark")
    col1.plotly_chart(fig1, use_container_width=True)

    franchise_df = scored_df.groupby("franchise")["player_points"].sum().reset_index()

    fig2 = px.pie(franchise_df, names="franchise", values="player_points")
    fig2.update_layout(template="plotly_dark")
    col2.plotly_chart(fig2, use_container_width=True)

    fig = px.bar(
        stack_df,
        x="owner_name",
        y="count",
        color="category",
        text_auto=True,
        barmode="stack",
        color_discrete_map={
            "Dead (<10 points)": "#ef4444",     # red
            "Active (≥10 points)": "#22c55e"    # green
        }
    )

    fig.update_layout(
        template="plotly_dark",
        title="📊 Squad Quality (Dead vs Active Players)",
        xaxis_title="Owner",
        yaxis_title="No. of Players",
        legend_title=""
    )

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB 4
# ==================================================
with tab4:

    squad_df = df.groupby(["owner_name", "franchise"]).size().reset_index(name="player_count")

    fig = px.bar(
        squad_df,
        x="owner_name",
        y="player_count",
        color="franchise",
        text_auto=True
    )

    fig.update_layout(barmode="stack", template="plotly_dark")

    st.plotly_chart(fig, use_container_width=True)

# ==================================================
# TAB 5 - REPLACEMENT
# ==================================================
with tab5:

    st.subheader("🔁 Player Replacement")

    # -------------------------------
    # 🔹 Dynamic Day Columns
    # -------------------------------
    import re

    day_cols = sorted(
        [col for col in df.columns if col.startswith("day")],
        key=lambda x: int(re.findall(r'\d+', x)[0])
    )

    df[day_cols] = df[day_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["total_points"] = df[day_cols].sum(axis=1)

    # -------------------------------
    # 🔹 Owner Selection
    # -------------------------------
    owners = sorted(df["owner_name"].unique())

    selected_owner = st.selectbox(
        "Select Owner",
        owners,
        key="tab5_owner"
    )

    # -------------------------------
    # 🔹 Player Selection
    # -------------------------------
    owner_players = df[df["owner_name"] == selected_owner]

    selected_player = st.selectbox(
        "Select Player to Replace",
        owner_players["player_name"],
        key="tab5_player"
    )

    # -------------------------------
    # 🔹 Selected Player Details
    # -------------------------------
    player_data = owner_players[
        owner_players["player_name"] == selected_player
    ].iloc[0]

    bid_price = player_data["bid_price"]
    player_points = player_data["total_points"]

    st.markdown(f"""
    **Selected Player:** {selected_player}  
    💰 Price: {bid_price}  
    📊 Total Points: {player_points}
    """)

    # -------------------------------
    # 🔹 Eligibility Check
    # -------------------------------
    if bid_price < 350:
        st.error("❌ Not eligible for replacement (Price < $350)")
        eligible_players = None
    else:
        st.success("✅ Eligible for replacement")

        # Show allowed price range
        st.caption(f"Allowed price: ≤ {int(bid_price + 50)}")

        # -------------------------------
        # 🔹 Eligible Players Filter
        # -------------------------------
        eligible_players = df[
            (df["player_name"] != selected_player) &
            (df["owner_name"] != selected_owner) &
            (df["bid_price"] <= bid_price + 50) &          # ✅ upper limit only
            (df["total_points"] <= player_points + 50)     # ✅ upper limit only
        ].copy()

        # -------------------------------
        # 🔹 Display Results
        # -------------------------------
        if eligible_players is not None:

            if eligible_players.empty:
                st.warning("No eligible replacement players found.")
            else:
                eligible_players = eligible_players[
                    ["player_name", "owner_name", "bid_price", "total_points"]
                ].sort_values(by="total_points", ascending=False)

                # Add point difference
                eligible_players["point_diff"] = (
                    eligible_players["total_points"] - player_points
                )

                # Highlight better players
                def highlight(row):
                    if row["point_diff"] > 0:
                        return ["background-color: rgba(34,197,94,0.2)"] * len(row)
                    return [""] * len(row)

                # ✅ Apply format (NO decimals)
                st.dataframe(
                    eligible_players.style
                        .format({
                            "bid_price": "{:.0f}",
                            "total_points": "{:.0f}",
                            "point_diff": "{:.0f}"
                        })
                        .apply(highlight, axis=1),
                    use_container_width=True,
                    hide_index=True
                )

            # -------------------------------
            # 🔹 Divider
            # -------------------------------
            st.markdown("---")

            # -------------------------------
            # 🔹 Rules
            # -------------------------------
            st.info("""
            📌 **Replacement Rules**

            1. Player price must be ≥ $350  
            2. The replacement player should be priced at most at $50 higher than the ruled out player
            3. The replacement players fantasy XI points should be equal to or max 50 points higher the ruled out player 
            4. Points count from next match only  
            5. If player is already C/VC in another team, cannot assign C/VC again  
            """)
    
    with tab6:

        st.subheader("📅 Match-wise Points")

        # -------------------------------
        # 🔹 Day Selection
        # -------------------------------
        day_list = sorted(matches_df["Day"].unique())

        selected_day_mp = st.selectbox(
            "Select Day",
            day_list,
            key="mp_day"
        )

        # -------------------------------
        # 🔹 Get Matches
        # -------------------------------
        rows = matches_df[matches_df["Day"] == selected_day_mp]

        teams = []
        for _, r in rows.iterrows():
            teams.extend([t.strip() for t in r["Teams"].split(",")])

        # Create match pairs
        matches = [
            (teams[i], teams[i+1])
            for i in range(0, len(teams), 2)
            if i + 1 < len(teams)
        ]

        if not matches:
            st.warning("No matches found for this day.")
            st.stop()

        # -------------------------------
        # 🔹 Match Selection
        # -------------------------------
        match_options = list(range(1, len(matches) + 1))

        selected_match_no = st.selectbox(
            "Select Match",
            match_options,
            key="mp_match"
        )

        team1, team2 = matches[selected_match_no - 1]

        st.markdown(f"### 🏏 {team1} vs {team2}")

        # -------------------------------
        # 🔹 Points Extraction
        # -------------------------------
        day_col = f"day{selected_day_mp}"

        if day_col not in df.columns:
            st.warning("No points data available for this day.")
            st.stop()

        match_df = df[
            df["franchise"].isin([team1, team2])
        ].copy()

        match_df[day_col] = pd.to_numeric(
            match_df[day_col],
            errors="coerce"
        ).fillna(0)

        # -------------------------------
        # 🔹 Prepare Table
        # -------------------------------
        display_df = match_df[
            ["owner_name", "player_name", "franchise", day_col]
        ].rename(columns={
            "owner_name": "Owner",
            "player_name": "Player",
            "franchise": "Team",
            day_col: "Points"
        }).sort_values("Points", ascending=False)

        if display_df.empty:
            st.warning("No player data available for this match.")
            st.stop()

        # -------------------------------
        # 🔥 Highlight Top Performer
        # -------------------------------
        max_pts = display_df["Points"].max()

        def highlight(row):
            if row["Points"] == max_pts and max_pts > 0:
                return ["background-color: rgba(34,197,94,0.3)"] * len(row)
            return [""] * len(row)

        st.dataframe(
            display_df.style
                .format({"Points": "{:.0f}"})
                .apply(highlight, axis=1),
            use_container_width=True,
            hide_index=True
        )

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# --------------------------------------------------
# AI INSIGHTS SECTION
# --------------------------------------------------

with st.spinner("🧠 Thinking..."):
    insights = generate_ai_insights_cached(team_df, selected_day)

# -------------------------
# CLEAN + SPLIT
# -------------------------
import re

def format_numbers(text):
    def repl(match):
        num = int(match.group())
        return f"{num:,}"
    return re.sub(r"\b\d{3,}\b", repl, text)

lines = insights.replace("*", "").replace("-", "").split("\n")
clean_lines = [l.strip() for l in lines if l.strip()]

rising = clean_lines[0] if len(clean_lines) > 0 else ""
falling = clean_lines[1] if len(clean_lines) > 1 else ""
battle = clean_lines[2] if len(clean_lines) > 2 else ""
extra = clean_lines[3] if len(clean_lines) > 3 else ""

# format numbers
rising = format_numbers(rising)
falling = format_numbers(falling)
battle = format_numbers(battle)
extra = format_numbers(extra)

# -------------------------
# CARD LAYOUT
# -------------------------
c1, c2, c3, c4 = st.columns(4)

c1.markdown(f"""
<div class="ai-card rise">
    <div class="ai-title">🔼 Rising</div>
    <div class="ai-text">{rising}</div>
</div>
""", unsafe_allow_html=True)

c2.markdown(f"""
<div class="ai-card fall">
    <div class="ai-title">🔽 Falling</div>
    <div class="ai-text">{falling}</div>
</div>
""", unsafe_allow_html=True)

c3.markdown(f"""
<div class="ai-card battle">
    <div class="ai-title">⚖️ Key Battle</div>
    <div class="ai-text">{battle}</div>
</div>
""", unsafe_allow_html=True)

c4.markdown(f"""
<div class="ai-card insight">
    <div class="ai-title">💡Bonus Insight</div>
    <div class="ai-text">{extra}</div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


# ----------------------------------------
# FOOTER
# ----------------------------------------
st.markdown(
    "<div style='text-align:center;color:#94a3b8;margin-top:20px;'>Built for IPL 🚀</div>",
    unsafe_allow_html=True
)