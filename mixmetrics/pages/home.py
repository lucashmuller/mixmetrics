import streamlit as st

from mixmetrics.data import (
    clear_match_days_cache,
    clear_map_scores_cache,
    clear_players_cache,
    clear_stats_cache,
    clear_team_overrides_cache,
    load_match_days,
    load_map_scores,
    load_players,
    load_stats,
    load_team_overrides,
)
from mixmetrics.transforms import (
    add_aggregate_indicators,
    add_basic_rates,
    add_player_display_names,
)
from mixmetrics.ui import dataframe, default_column_config, page_header, section_title, stat_card


def render_home():
    page_header(
        "MixMetrics Overview",
        "A competitive snapshot of maps, leaders, roles, and recent match performance.",
        "Analytics",
    )

    df_home = load_stats()
    name_map_home = load_players()
    match_days = load_match_days()
    map_scores = load_map_scores()

    if df_home.empty:
        st.info("No data yet. Ask an admin to upload the first match CSV.")
        return

    df_home = add_player_display_names(df_home, name_map_home)
    df_home = add_basic_rates(df_home)

    lb = (
        df_home.groupby("display_name")
        .agg(
            matches=("matchid", "nunique"),
            kills=("kills", "sum"),
            deaths=("deaths", "sum"),
            damage=("damage", "sum"),
            hs_kills=("head_shot_kills", "sum"),
            assists=("assists", "sum"),
            shots_fired=("shots_fired_total", "sum"),
            shots_on_target=("shots_on_target_total", "sum"),
            entries=("entry_count", "sum"),
            entry_wins=("entry_wins", "sum"),
            v1_count=("v1_count", "sum"),
            v1_wins=("v1_wins", "sum"),
            v2_count=("v2_count", "sum"),
            v2_wins=("v2_wins", "sum"),
            flash_successes=("flash_successes", "sum"),
            utility_damage=("utility_damage", "sum"),
        )
        .reset_index()
    )
    lb = add_aggregate_indicators(lb)

    kd_leader = lb.sort_values(["K-D", "kills"], ascending=False).iloc[0]
    damage_leader = lb.sort_values(["DMG/map", "kills"], ascending=False).iloc[0]
    entry_leader = lb[lb["entries"] > 0].sort_values(
        ["Entry%", "entry_wins"], ascending=False
    )
    support_leader = lb.assign(
        support_score=lb["flash_successes"] + (lb["utility_damage"] / 100)
    ).sort_values(["support_score", "flash_successes"], ascending=False).iloc[0]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    stat_card(c1, "Maps", df_home["matchid"].nunique())
    stat_card(c2, "Players", df_home["steamid64"].nunique())
    stat_card(c3, "Best K-D", kd_leader["display_name"], f"{kd_leader['K-D']:+}")
    stat_card(
        c4,
        "Top DMG/map",
        damage_leader["display_name"],
        f"{damage_leader['DMG/map']}",
    )
    if entry_leader.empty:
        stat_card(c5, "Top Entry", "No entries", "0.0%")
    else:
        top_entry = entry_leader.iloc[0]
        stat_card(c5, "Top Entry", top_entry["display_name"], f"{top_entry['Entry%']:.1f}%")
    stat_card(
        c6,
        "Top Support",
        support_leader["display_name"],
        f"{support_leader['Flash Ast/map']:.1f} flash/map",
    )

    st.divider()

    if match_days:
        overrides_home = load_team_overrides()
        section_title("Match Days", "Recent series with assigned maps and scoreboard details.")
        for day in sorted(match_days, key=lambda d: d.get("date") or "", reverse=True):
            date_str = f" - {day['date']}" if day.get("date") else ""
            score = f"{day['team1_score']} x {day['team2_score']}"
            title = (
                f"{day['name']}{date_str} - "
                f"{day['team1_name']} {score} {day['team2_name']}"
            )
            with st.expander(title):
                map_ids = [m["matchid"] for m in day.get("match_day_maps", [])]
                if not map_ids:
                    st.caption("No maps assigned to this day yet.")
                    continue

                for mid in sorted(map_ids):
                    df_map = df_home[df_home["matchid"] == mid].copy()
                    if df_map.empty:
                        st.markdown(f"**Map {mid} - ?**")
                        continue

                    df_map["team"] = df_map.apply(
                        lambda row: overrides_home.get(
                            (int(row["matchid"]), row["team"]), row["team"]
                        ),
                        axis=1,
                    )
                    map_name = df_map["map_name"].iloc[0]
                    score = map_scores.get(int(mid))
                    score_label = ""
                    if score:
                        score_team1 = overrides_home.get(
                            (int(mid), score["team1_name"]),
                            score["team1_name"],
                        )
                        score_team2 = overrides_home.get(
                            (int(mid), score["team2_name"]),
                            score["team2_name"],
                        )
                        score_label = (
                            f" - {score_team1} {score['team1_score']}x"
                            f"{score['team2_score']} {score_team2}"
                        )
                    st.markdown(f"**Map {mid} - {map_name}{score_label}**")
                    df_map = df_map.sort_values("kills", ascending=False)
                    dataframe(
                        df_map[
                            [
                                "display_name",
                                "team",
                                "kills",
                                "deaths",
                                "K-D",
                                "K/D",
                                "damage",
                                "HS%",
                                "Entry%",
                            ]
                        ].rename(columns={"display_name": "player"}),
                        column_config=default_column_config(),
                    )
        st.divider()

    section_title("Overall Leaderboard", "Sorted by K-D, then kills. Player is pinned for easier scanning.")

    lb = lb.sort_values(["K-D", "kills"], ascending=False).reset_index(drop=True)
    lb.index += 1

    dataframe(
        lb[
            [
                "display_name",
                "matches",
                "kills",
                "deaths",
                "K-D",
                "K/D",
                "DMG/map",
                "HS%",
                "Accuracy%",
                "Entry%",
                "Clutches",
                "Flash Ast/map",
                "Util DMG/map",
            ]
        ].rename(columns={"display_name": "player"}),
        column_config=default_column_config(),
    )

    st.divider()
    section_title("Per-map Support Indicators", "Support, utility, entry, and clutch output normalized by map.")

    avg = (
        df_home.groupby("display_name")
        .agg(
            matches=("matchid", "nunique"),
            kills=("kills", "mean"),
            deaths=("deaths", "mean"),
            damage=("damage", "mean"),
            assists=("assists", "mean"),
            flash_successes=("flash_successes", "mean"),
            enemies_flashed=("enemies_flashed", "mean"),
            utility_damage=("utility_damage", "mean"),
            entry_count=("entry_count", "mean"),
            entry_wins=("entry_wins", "mean"),
            v1_count=("v1_count", "mean"),
            v1_wins=("v1_wins", "mean"),
            v2_count=("v2_count", "mean"),
            v2_wins=("v2_wins", "mean"),
        )
        .reset_index()
    )
    avg["Kills/map"] = avg["kills"].round(1)
    avg["Deaths/map"] = avg["deaths"].round(1)
    avg["DMG/map"] = avg["damage"].round(0).astype(int)
    avg["Assists/map"] = avg["assists"].round(1)
    avg["Flash Ast/map"] = avg["flash_successes"].round(1)
    avg["Enemies Flashed/map"] = avg["enemies_flashed"].round(1)
    avg["Util DMG/map"] = avg["utility_damage"].round(0).astype(int)
    avg["Entries/map"] = avg["entry_count"].round(1)
    avg["Entry Wins/map"] = avg["entry_wins"].round(1)
    avg["Clutch Attempts/map"] = (avg["v1_count"] + avg["v2_count"]).round(1)
    avg["Clutches/map"] = (avg["v1_wins"] + avg["v2_wins"]).round(1)
    avg = avg.sort_values(["Flash Ast/map", "Util DMG/map"], ascending=False).reset_index(drop=True)
    avg.index += 1

    dataframe(
        avg[
            [
                "display_name",
                "matches",
                "Kills/map",
                "Deaths/map",
                "DMG/map",
                "Assists/map",
                "Flash Ast/map",
                "Enemies Flashed/map",
                "Util DMG/map",
                "Entries/map",
                "Entry Wins/map",
                "Clutch Attempts/map",
                "Clutches/map",
            ]
        ].rename(columns={"display_name": "player"}),
        column_config=default_column_config(),
    )

    st.divider()
    section_title("Recent Matches")
    recent = (
        df_home[["matchid", "map_name"]]
        .drop_duplicates()
        .sort_values("matchid", ascending=False)
        .head(5)
    )
    for _, match in recent.iterrows():
        with st.expander(f"Match {match['matchid']} - {match['map_name']}"):
            df_m = df_home[df_home["matchid"] == match["matchid"]].sort_values(
                "kills", ascending=False
            )
            dataframe(
                df_m[
                    [
                        "display_name",
                        "team",
                        "kills",
                        "deaths",
                        "K-D",
                        "K/D",
                        "damage",
                        "HS%",
                        "Accuracy%",
                        "Entry%",
                    ]
                ].rename(columns={"display_name": "player"}),
                column_config=default_column_config(),
            )

    if st.button("Refresh", key="refresh_home"):
        clear_stats_cache()
        clear_players_cache()
        clear_team_overrides_cache()
        clear_match_days_cache()
        clear_map_scores_cache()
        st.rerun()
