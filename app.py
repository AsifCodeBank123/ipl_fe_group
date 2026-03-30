import streamlit as st
import plotly.express as px
import pandas as pd

from utils.data_loader import load_data, load_matches, load_captains
from utils.calculator import calculate_points
from utils.helpers import build_watchlist

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

selected_day = st.sidebar.selectbox(
    "📅 Select Day",
    day_numbers,
    index=len(day_numbers)-1
)

# ----------------------------------------
# SIDEBAR (IMPROVED)
# ----------------------------------------
#st.sidebar.markdown("🏏 IPL Dashboard")

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

def format_movement(x):
    if x > 0:
        return f"▲ +{int(x)}"
    if x < 0:
        return f"▼ {int(x)}"
    return "— 0"

team_df["Movement"] = team_df["Movement"].apply(format_movement)

# ----------------------------------------
# DELTAS
# ----------------------------------------
scores = team_df["Points"].values

next_delta = [None] + [round(scores[i-1]-scores[i],1) for i in range(1,len(scores))]
first_delta = [None] + [round(scores[0]-s,1) for s in scores[1:]]

team_df["Next Rank"] = next_delta
team_df["1st Rank"] = first_delta

# ----------------------------------------
# HEADER (NEW)
# ----------------------------------------
st.markdown(f"""
<div class="header">
    <div>
        <div class="title">🏏 IPL Fantasy Dashboard - FE Group</div>
        <div class="subtitle">Live standings till Day {selected_day}</div>
    </div>
</div>
""", unsafe_allow_html=True)

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
# TOP CAPTAIN & VC CARDS
# ----------------------------------------
cap_records = []
vc_records = []

for _, row in cap_df.iterrows():
    owner = row["owner_name"]
    start_day = row["from_day"]
    captain = row["captain"]
    vc = row["vice_captain"]

    for d in range(start_day, selected_day + 1):
        day_col = f"day{d}"
        if day_col not in df.columns:
            continue

        # Captain points
        c_row = df[
            (df["owner_name"] == owner) &
            (df["player_name"] == captain)
        ]
        if not c_row.empty:
            pts = pd.to_numeric(c_row.iloc[0].get(day_col, 0), errors="coerce")
            pts = 0 if pd.isna(pts) else pts
            cap_records.append((captain, pts * 2))

        # VC points
        vc_row = df[
            (df["owner_name"] == owner) &
            (df["player_name"] == vc)
        ]
        if not vc_row.empty:
            pts = pd.to_numeric(vc_row.iloc[0].get(day_col, 0), errors="coerce")
            pts = 0 if pd.isna(pts) else pts
            vc_records.append((vc, pts * 1.5))


# Aggregate
top_captain = (
    pd.DataFrame(cap_records, columns=["player", "points"])
    .groupby("player")["points"]
    .sum()
    .sort_values(ascending=False)
)

top_vc = (
    pd.DataFrame(vc_records, columns=["player", "points"])
    .groupby("player")["points"]
    .sum()
    .sort_values(ascending=False)
)

top_captain_name = top_captain.index[0] if not top_captain.empty else "—"
top_vc_name = top_vc.index[0] if not top_vc.empty else "—"

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

k1.markdown(f"<div class='card'><h4>Teams</h4><h2>{len(team_df)}</h2></div>", unsafe_allow_html=True)

k2.markdown(f"<div class='card highlight'><h4>Leader</h4><h2>{team_df.iloc[0]['Owner']}</h2></div>", unsafe_allow_html=True)

k3.markdown(f"""
<div class='card'>
<h4>Top Captain</h4>
<h2>🧢 {top_captain_name}</h2>
</div>
""", unsafe_allow_html=True)

k4.markdown(f"""
<div class='card'>
<h4>Top VC</h4>
<h2>🎖️ {top_vc_name}</h2>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ----------------------------------------
# TABS
# ----------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Rankings","👥 Players","📊 Insights"," 🎯 Squad Composition"])

#helper to compute captain and vc points for captain strategy table

def get_c_vc_points(owner, role="captain"):
    
    oc = cap_df[cap_df["owner_name"] == owner].sort_values("from_day")
    
    if oc.empty:
        return "—"
    
    player_points_list = []

    for d in range(1, selected_day + 1):
        day_col = f"day{d}"
        if day_col not in df.columns:
            continue

        cap_row = oc[oc["from_day"] <= d]
        if cap_row.empty:
            continue

        latest = cap_row.iloc[-1]
        player = latest["captain"] if role == "captain" else latest["vice_captain"]

        player_row = df[
            (df["owner_name"] == owner) &
            (df["player_name"] == player)
        ]

        if player_row.empty:
            continue

        points = pd.to_numeric(player_row.iloc[0].get(day_col, 0), errors="coerce")
        points = 0 if pd.isna(points) else points

        multiplier = 2.0 if role == "captain" else 1.5
        value = round(points * multiplier, 1)

        if value != 0:
            player_points_list.append(value)

    return "—" if not player_points_list else f"({', '.join(map(str, player_points_list))})"

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
    ].rename(columns={"Points": "Total Points",
                      "Watchlist": f"Watchlist (Day {selected_day})"})

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

    # CAPTAIN SECTION
    st.markdown("### 🧠 Captain Strategy")

    cap_df.columns = [c.lower() for c in cap_df.columns]

    rows = []

    for owner in df["owner_name"].unique():
        oc = cap_df[cap_df["owner_name"]==owner]

        if not oc.empty:
            latest = oc.iloc[-1]
            c = latest["captain"]
            vc = latest["vice_captain"]
        else:
            c, vc = "—","—"

        rows.append({
            "Owner":owner,
            "Captain":c,
            "Cap Points": get_c_vc_points(owner, "captain"),
            "Vice Captain":vc,
            "VC Points": get_c_vc_points(owner, "vc"),
            "Changes":len(oc)-1
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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

# ----------------------------------------
# FOOTER
# ----------------------------------------
st.markdown(
    "<div style='text-align:center;color:#94a3b8;margin-top:20px;'>Built for IPL 🚀</div>",
    unsafe_allow_html=True
)