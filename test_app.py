import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data_loader import load_data, load_matches, load_captains
from utils.calculator import calculate_points
from utils.helpers import build_watchlist

# ----------------------------------------
# CONFIG
# ----------------------------------------
st.set_page_config(layout="wide", page_title="IPL Dashboard")
TOTAL_MATCHES = 74  # change anytime

# ----------------------------------------
# LOAD CSS
# ----------------------------------------
with open("style/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ----------------------------------------
# LOAD DATA
# ----------------------------------------
df = load_data()
matches_df = load_matches()
cap_df = load_captains()

# ----------------------------------------
# DAYS
# ----------------------------------------
day_cols = [c for c in df.columns if c.startswith("day")]
day_numbers = sorted([int(c.replace("day","")) for c in day_cols])

selected_day = st.sidebar.selectbox("Select Day", day_numbers, index=len(day_numbers)-1)

# ----------------------------------------
# SIDEBAR INFO
# ----------------------------------------
st.sidebar.markdown("### 📌 Game Info")


matches_left = TOTAL_MATCHES - selected_day

st.sidebar.markdown(f"""
**Current Day:** {selected_day}  
**Matches Left:** {matches_left}  
""")

st.sidebar.markdown("---")

st.sidebar.markdown("### 🧠 Rules")
st.sidebar.write("• Captain = 2× points")
st.sidebar.write("• Vice Captain = 1.5× points")
st.sidebar.write("• Captain & VC changes allowed: 2")

st.sidebar.markdown("---")

st.sidebar.markdown("### 🔍 Tips")
st.sidebar.write("• Watch high-stacked franchises")
st.sidebar.write("• Track captain impact")

# ----------------------------------------
# CALCULATIONS
# ----------------------------------------
scored_df = calculate_points(df, cap_df, selected_day)
watch_map = build_watchlist(df, matches_df, cap_df, selected_day)

team_df = (
    scored_df.groupby("owner_name")["player_points"]
    .sum().reset_index()
    .rename(columns={"owner_name":"Owner","player_points":"Points"})
    .sort_values("Points", ascending=False)
)

team_df["Rank"] = range(1, len(team_df)+1)
team_df["Watchlist"] = team_df["Owner"].map(watch_map)

# --------------------------------------------------
# MOVEMENT CALCULATION
# --------------------------------------------------
if selected_day > 1:
    prev_df = calculate_points(df, cap_df, selected_day - 1)

    prev_team = (
        prev_df.groupby("owner_name")["player_points"]
        .sum().reset_index()
        .rename(columns={"owner_name": "Owner", "player_points": "Prev Points"})
    )

    prev_team["Prev Rank"] = prev_team["Prev Points"].rank(
        ascending=False, method="min"
    )

    team_df = team_df.merge(prev_team, on="Owner", how="left")
    team_df["Movement"] = team_df["Prev Rank"] - team_df["Rank"]

else:
    team_df["Movement"] = 0

def format_movement(x):
    if x > 0:
        return f"▲ +{int(x)}"
    elif x < 0:
        return f"▼ {int(x)}"
    return "— 0"

team_df["Movement"] = team_df["Movement"].apply(format_movement)

# --------------------------------------------------
# RANK DELTAS
# --------------------------------------------------
scores = team_df["Points"].values

def fmt(x):
    return round(x, 1) if pd.notna(x) else None

next_delta = [None]
for i in range(1, len(scores)):
    next_delta.append(fmt(scores[i-1] - scores[i]))

first_delta = [None] + [fmt(scores[0] - s) for s in scores[1:]]

team_df["Next Rank"] = next_delta
team_df["1st Rank"] = first_delta

# --------------------------------------------------
# OPTIONAL: SHORTEN WATCHLIST
# --------------------------------------------------
team_df["Watchlist"] = team_df["Watchlist"].apply(
    lambda x: x if len(x) < 50 else x[:50] + "..."
)

# --------------------------------------------------
# HERO
# --------------------------------------------------
st.markdown(f"""
<div class="hero">
<h2>🏏 IPL Fantasy Dashboard</h2>
<p>Live standings till Day {selected_day}</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# KPI
# --------------------------------------------------
# ----------------------------------------
# KPI
# ----------------------------------------
k1, k2, k3 = st.columns(3)

# Teams
k1.markdown(
    f"<div class='kpi'><h3>Total Teams</h3><p>{len(team_df)}</p></div>",
    unsafe_allow_html=True
)

# Leader
top_team = team_df.iloc[0]["Owner"]
k2.markdown(
    f"<div class='kpi'><h3>Leader</h3><p>{top_team}</p></div>",
    unsafe_allow_html=True
)

# Top Player
top_player = (
    scored_df.groupby("player_name")["player_points"]
    .sum().reset_index()
    .sort_values("player_points", ascending=False)
    .iloc[0]
)

k3.markdown(
    f"""
    <div class='kpi'>
        <h3>Top Player</h3>
        <p>{top_player['player_name']}</p>
        <span style="font-size:13px;color:#94a3b8;">
            {round(top_player['player_points'],1)} pts
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# TABS
# --------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Rankings","👥 Players","📊 Insights","📊 Squad Composition"])

# ==================================================
# TAB 1: RANKINGS
# ==================================================
with tab1:

    st.markdown("### 🏆 Team Rankings")

    display_df = team_df[
        ["Rank", "Owner", "Points", "Movement", "Next Rank", "1st Rank", "Watchlist"]
    ].rename(columns={"Points": "Total Points"})

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
    # CAPTAIN / VC STRATEGY TABLE
    # --------------------------------------------------

    st.markdown("### 🧠 Captain Strategy Overview")

    # Ensure lowercase columns
    cap_df.columns = [c.lower() for c in cap_df.columns]

    summary_rows = []

    for owner in df["owner_name"].unique():

        owner_caps = cap_df[cap_df["owner_name"] == owner].sort_values("from_day")

        # Current Captain / VC (latest change)
        if not owner_caps.empty:
            latest = owner_caps.iloc[-1]
            current_c = latest["captain"]
            current_vc = latest["vice_captain"]
        else:
            current_c = "—"
            current_vc = "—"

        # Count changes
        c_changes = owner_caps["captain"].nunique() - 1
        vc_changes = owner_caps["vice_captain"].nunique() - 1

        c_changes = max(c_changes, 0)
        vc_changes = max(vc_changes, 0)

        # Reserve players (released/injured = Y)
        reserves = (
            df[
                (df["owner_name"] == owner) &
                (df["released_injured"] == "Y")
            ]["player_name"]
            .tolist()
        )

        reserves_str = ", ".join(reserves) if reserves else "—"

        summary_rows.append({
            "Owner": owner,
            "Captain": current_c,
            "Vice Captain": current_vc,
            "Captain Changes": c_changes,
            "VC Changes": vc_changes,
            "Reserves": reserves_str
        })

    cap_summary_df = pd.DataFrame(summary_rows)

    styled_cap_df = (
        cap_summary_df
        .style
        .set_properties(**{"text-align": "center"})
        .set_table_styles([
            {"selector": "th", "props": [("text-align", "center")]}
        ])
    )

    st.dataframe(
        styled_cap_df,
        use_container_width=True,
        hide_index=True
    )

# ==================================================
# TAB 2: PLAYERS
# ==================================================
with tab2:

    st.markdown("### 👥 Player Breakdown")

    owner = st.selectbox("Select Owner", df["owner_name"].unique())

    owner_df = (
        scored_df[scored_df["owner_name"] == owner]
        .groupby(["player_name","franchise"])["player_points"]
        .sum().reset_index()
        .sort_values("player_points", ascending=False)
    )

    owner_df = owner_df.rename(columns={
        "player_name": "Player",
        "player_points": "Points",
        "franchise": "Franchise"
    })

    st.dataframe(
        owner_df.style.format({"Points": "{:.1f}"}),
        use_container_width=True,
        hide_index=True
    )

# ==================================================
# TAB 3: INSIGHTS
# ==================================================
with tab3:

    st.markdown("### 📊 Insights")

    col1, col2 = st.columns(2)

    # Team Points
    fig1 = px.bar(team_df, x="Owner", y="Points", text_auto=True)
    fig1.update_layout(template="plotly_dark")
    col1.plotly_chart(fig1, use_container_width=True)

    # Franchise Contribution
    franchise_df = (
        scored_df.groupby("franchise")["player_points"]
        .sum().reset_index()
    )

    fig2 = px.pie(franchise_df, names="franchise", values="player_points")
    fig2.update_layout(template="plotly_dark")
    col2.plotly_chart(fig2, use_container_width=True)

    # --------------------------------------------------
    # ROLE WISE DISTRIBUTION
    # --------------------------------------------------
    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    st.markdown("### 🧠 Role-wise Points Distribution")

    role_df = (
        scored_df.groupby("role")["player_points"]
        .sum()
        .reset_index()
    )

    fig_role = px.bar(
        role_df,
        x="role",
        y="player_points",
        text_auto=True,
        color="role"
    )

    fig_role.update_layout(
        template="plotly_dark",
        xaxis_title="Role",
        yaxis_title="Points"
    )

    st.plotly_chart(fig_role, use_container_width=True)

    def show_owner_insights(points_df):


        # ----------------------------------------
        # OWNER SELECT
        # ----------------------------------------
        st.markdown("### 🧠 Owner Breakdown")

        selected_owner = st.selectbox(
            "Select Owner",
            sorted(points_df["owner_name"].unique()),
            key="owner_insight"
        )

        owner_df = points_df[points_df["owner_name"] == selected_owner]

        col1, col2 = st.columns(2)

        # Franchise contribution
        teamwise = owner_df.groupby("franchise")["player_points"].sum().reset_index()

        fig1 = px.pie(
            teamwise,
            names="franchise",
            values="player_points",
            title="Points by Franchise"
        )

        fig1.update_layout(template="plotly_dark")

        col1.plotly_chart(fig1, use_container_width=True)

        # Role contribution
        rolewise = owner_df.groupby("role")["player_points"].sum().reset_index()

        fig2 = px.bar(
            rolewise,
            x="role",
            y="player_points",
            title="Points by Role"
        )

        fig2.update_layout(template="plotly_dark")

        col2.plotly_chart(fig2, use_container_width=True)

# ==================================================
# TAB 4: FRANCHISE DISTRIBUTION
# ==================================================
with tab4:

    # --------------------------------------------------
    # COUNT PLAYERS PER FRANCHISE PER OWNER
    # --------------------------------------------------
    squad_df = (
        df.groupby(["owner_name", "franchise"])["player_name"]
        .count()
        .reset_index()
        .rename(columns={
            "owner_name": "Owner",
            "player_name": "Count"
        })
    )

    # --------------------------------------------------
    # PIVOT TABLE (OWNER vs FRANCHISE)
    # --------------------------------------------------
    pivot_df = squad_df.pivot(
        index="Owner",
        columns="franchise",
        values="Count"
    ).fillna(0).astype(int)

    # --------------------------------------------------
    # DISPLAY TABLE
    # --------------------------------------------------
    st.markdown("#### 🧾 Squad Breakdown (Count of Players)")

    st.dataframe(
        pivot_df,
        use_container_width=True
    )

    # --------------------------------------------------
    # STACKED BAR CHART
    # --------------------------------------------------
    st.markdown("#### 📊 Franchise Composition (Visual)")

    fig = px.bar(
        squad_df,
        x="Owner",
        y="Count",
        color="franchise",
        text_auto=True,
    )

    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        xaxis_title="Owner",
        yaxis_title="Number of Players",
        legend_title="Franchise"
    )

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# FOOTER
# --------------------------------------------------
st.markdown(
    "<div style='text-align:center;margin-top:20px;color:#94a3b8;'>Built for IPL Analytics 🚀</div>",
    unsafe_allow_html=True
)