import pandas as pd

def get_current_c_vc(cap_df, owner, day):

    owner_caps = cap_df[
        (cap_df["owner_name"] == owner) &
        (cap_df["from_day"] <= day)
    ].sort_values("from_day")

    if owner_caps.empty:
        return None, None

    row = owner_caps.iloc[-1]
    return row["captain"], row["vice_captain"]


def calculate_points(df, cap_df, upto_day):

    temp = df.copy()
    temp["player_points"] = 0.0

    for d in range(1, upto_day + 1):

        day_col = f"day{d}"
        if day_col not in temp.columns:
            continue

        points = pd.to_numeric(temp[day_col], errors="coerce").fillna(0)
        multiplier = pd.Series(1.0, index=temp.index)

        for owner in temp["owner_name"].unique():
            c, vc = get_current_c_vc(cap_df, owner, d)

            mask = temp["owner_name"] == owner

            if c:
                multiplier.loc[mask & (temp["player_name"] == c)] = 2.0
            if vc:
                multiplier.loc[mask & (temp["player_name"] == vc)] = 1.5

        temp["player_points"] += points * multiplier

    return temp