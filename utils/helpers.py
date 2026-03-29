def build_watchlist(df, matches_df, cap_df, selected_day):

    playing = set()

    row = matches_df[matches_df["Day"] == selected_day]
    if not row.empty:
        playing = set(row.iloc[0]["Teams"].split(","))

    watch = {}

    for owner, grp in df.groupby("owner_name"):

        eligible = grp[
            (grp["franchise"].isin(playing)) &
            (grp["released_injured"].fillna("").str.upper() != "Y")
        ]

        owner_caps = cap_df[
            (cap_df["owner_name"] == owner) &
            (cap_df["from_day"] <= selected_day)
        ].sort_values("from_day")

        c = vc = None
        if not owner_caps.empty:
            last = owner_caps.iloc[-1]
            c = last["captain"]
            vc = last["vice_captain"]

        players = []
        for _, r in eligible.iterrows():
            name = r["player_name"]
            if name == c:
                name = f"🧢 {name}"
            elif name == vc:
                name = f"🎖️ {name}"
            players.append(name)

        watch[owner] = ", ".join(players) if players else "—"

    return watch