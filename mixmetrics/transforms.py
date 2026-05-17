def resolve_name(steamid64, name_map, fallback):
    return name_map.get(str(steamid64), fallback)


def resolve_team(matchid, original_team, overrides):
    return overrides.get((int(matchid), original_team), original_team)


def add_player_display_names(df, name_map):
    df = df.copy()
    df["display_name"] = df.apply(
        lambda row: resolve_name(row["steamid64"], name_map, row["name"]),
        axis=1,
    )
    return df


def add_team_display_names(df, overrides):
    df = df.copy()
    df["team_display"] = df.apply(
        lambda row: resolve_team(row["matchid"], row["team"], overrides),
        axis=1,
    )
    return df


def add_basic_rates(df):
    df = df.copy()
    df["K-D"] = df["kills"] - df["deaths"]
    df["K/D"] = (df["kills"] / df["deaths"].replace(0, 1)).round(2)
    df["HS%"] = (
        (df["head_shot_kills"] / df["kills"].replace(0, 1)) * 100
    ).round(1)
    df["Accuracy%"] = (
        (df["shots_on_target_total"] / df["shots_fired_total"].replace(0, 1)) * 100
    ).round(1)
    df["Entry%"] = (
        (df["entry_wins"] / df["entry_count"].replace(0, 1)) * 100
    ).round(1)
    df["Clutches"] = df["v1_wins"] + df["v2_wins"]
    df["Clutch Attempts"] = df["v1_count"] + df["v2_count"]
    df["Clutch%"] = (
        (df["Clutches"] / df["Clutch Attempts"].replace(0, 1)) * 100
    ).round(1)
    df["Multi-kills"] = (
        df["enemy2ks"] + df["enemy3ks"] + df["enemy4ks"] + df["enemy5ks"]
    )
    return df


def add_aggregate_indicators(df):
    df = df.copy()
    if "maps" not in df.columns and "matches" in df.columns:
        df["maps"] = df["matches"]

    df["K-D"] = df["kills"] - df["deaths"]
    df["K/D"] = (df["kills"] / df["deaths"].replace(0, 1)).round(2)
    df["HS%"] = ((df["hs_kills"] / df["kills"].replace(0, 1)) * 100).round(1)
    df["DMG/map"] = (df["damage"] / df["maps"].replace(0, 1)).round(0).astype(int)
    df["Accuracy%"] = (
        (df["shots_on_target"] / df["shots_fired"].replace(0, 1)) * 100
    ).round(1)
    df["Entry%"] = (
        (df["entry_wins"] / df["entries"].replace(0, 1)) * 100
    ).round(1)
    df["Clutches"] = df["v1_wins"] + df["v2_wins"]
    df["Clutch Attempts"] = df["v1_count"] + df["v2_count"]
    df["Clutch%"] = (
        (df["Clutches"] / df["Clutch Attempts"].replace(0, 1)) * 100
    ).round(1)
    df["Util DMG/map"] = (
        df["utility_damage"] / df["maps"].replace(0, 1)
    ).round(0).astype(int)
    df["Flash Ast/map"] = (
        df["flash_successes"] / df["maps"].replace(0, 1)
    ).round(1)
    return df
