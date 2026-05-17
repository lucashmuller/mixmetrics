import streamlit as st

from mixmetrics.data import clear_players_cache, clear_stats_cache, load_players, load_stats
from mixmetrics.transforms import add_basic_rates, add_player_display_names
from mixmetrics.ui import dataframe, default_column_config, page_header, section_title, stat_card


def render_player_profile():
    page_header(
        "Player Profile",
        "Track one player across maps with impact, role output, and match-by-match trends.",
        "Player analysis",
    )

    df_all = load_stats()
    if df_all.empty:
        st.info("No data yet. Upload a CSV first.")
        return

    df_all = add_player_display_names(df_all, load_players())

    selected_player = st.selectbox(
        "Select player",
        options=sorted(df_all["display_name"].unique().tolist()),
    )

    df_player = df_all[df_all["display_name"] == selected_player].copy()
    df_player = add_basic_rates(df_player)
    df_player["match_label"] = df_player.apply(
        lambda row: f"M{row['matchid']} {row['map_name']}",
        axis=1,
    )
    df_player = df_player.sort_values("matchid", ascending=False)

    maps = df_player["matchid"].nunique()
    kills = df_player["kills"].sum()
    deaths = df_player["deaths"].sum()
    damage_per_map = df_player["damage"].sum() / max(maps, 1)
    entry_attempts = df_player["entry_count"].sum()
    entry_wins = df_player["entry_wins"].sum()
    flash_assists_per_map = df_player["flash_successes"].sum() / max(maps, 1)
    utility_damage_per_map = df_player["utility_damage"].sum() / max(maps, 1)
    accuracy = (
        df_player["shots_on_target_total"].sum()
        / max(df_player["shots_fired_total"].sum(), 1)
        * 100
    )
    hs_percent = (
        df_player["head_shot_kills"].sum() / max(df_player["kills"].sum(), 1) * 100
    )
    best_match = df_player.sort_values(["K-D", "kills"], ascending=False).iloc[0]
    map_summary = (
        df_player.groupby("map_name")
        .agg(
            maps=("matchid", "nunique"),
            kills=("kills", "mean"),
            deaths=("deaths", "mean"),
            kd_diff=("K-D", "mean"),
            damage=("damage", "mean"),
            assists=("assists", "mean"),
            hs_percent=("HS%", "mean"),
            accuracy=("Accuracy%", "mean"),
            entries=("entry_count", "mean"),
            entry_wins=("entry_wins", "mean"),
            entry_percent=("Entry%", "mean"),
            flash_successes=("flash_successes", "mean"),
            enemies_flashed=("enemies_flashed", "mean"),
            utility_damage=("utility_damage", "mean"),
            clutches=("Clutches", "mean"),
        )
        .reset_index()
    )
    map_summary["Map%"] = (map_summary["maps"] / max(maps, 1) * 100).round(1)
    map_summary["Kills/map"] = map_summary["kills"].round(1)
    map_summary["Deaths/map"] = map_summary["deaths"].round(1)
    map_summary["K-D/map"] = map_summary["kd_diff"].round(1)
    map_summary["DMG/map"] = map_summary["damage"].round(0).astype(int)
    map_summary["Assists/map"] = map_summary["assists"].round(1)
    map_summary["HS%"] = map_summary["hs_percent"].round(1)
    map_summary["Accuracy%"] = map_summary["accuracy"].round(1)
    map_summary["Entries/map"] = map_summary["entries"].round(1)
    map_summary["Entry Wins/map"] = map_summary["entry_wins"].round(1)
    map_summary["Entry%"] = map_summary["entry_percent"].round(1)
    map_summary["Flash Ast/map"] = map_summary["flash_successes"].round(1)
    map_summary["Enemies Flashed/map"] = map_summary["enemies_flashed"].round(1)
    map_summary["Util DMG/map"] = map_summary["utility_damage"].round(0).astype(int)
    map_summary["Clutches/map"] = map_summary["clutches"].round(1)
    map_summary = map_summary.sort_values(
        ["K-D/map", "DMG/map", "maps"],
        ascending=False,
    )
    best_map = map_summary.iloc[0]

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    stat_card(c1, "Maps", maps)
    stat_card(c2, "K-D", f"{kills - deaths:+}")
    stat_card(c3, "K/D", f"{kills / max(deaths, 1):.2f}")
    stat_card(c4, "DMG/map", f"{damage_per_map:.0f}")
    stat_card(c5, "Entry%", f"{entry_wins / max(entry_attempts, 1) * 100:.1f}%")
    stat_card(c6, "Clutches", int(df_player["Clutches"].sum()))

    section_title("Impact Snapshot", "Best map, aim, support, and entry profile.")
    i1, i2, i3, i4 = st.columns(4)
    stat_card(
        i1,
        "Best Match",
        f"M{best_match['matchid']} {best_match['map_name']}",
        f"{best_match['K-D']:+} K-D",
    )
    stat_card(i2, "Aim", f"{accuracy:.1f}% acc", f"{hs_percent:.1f}% HS")
    stat_card(
        i3,
        "Support",
        f"{flash_assists_per_map:.1f} flash/map",
        f"{utility_damage_per_map:.0f} util dmg/map",
    )
    stat_card(i4, "Entries", int(entry_wins), f"{int(entry_attempts)} attempts")

    section_title(
        "Map Pool",
        "Map share and average output by map name for the selected player.",
    )
    m1, m2, m3, m4 = st.columns(4)
    stat_card(
        m1,
        "Best Map",
        best_map["map_name"],
        f"{best_map['K-D/map']:+.1f} K-D/map",
    )
    most_played_map = map_summary.sort_values(["maps", "Map%"], ascending=False).iloc[0]
    stat_card(
        m2,
        "Most Played",
        most_played_map["map_name"],
        f"{most_played_map['Map%']:.1f}%",
    )
    stat_card(m3, "Best DMG/map", best_map["map_name"], f"{best_map['DMG/map']}")
    stat_card(m4, "Map Types", len(map_summary))

    dataframe(
        map_summary[
            [
                "map_name",
                "maps",
                "Map%",
                "Kills/map",
                "Deaths/map",
                "K-D/map",
                "DMG/map",
                "HS%",
                "Accuracy%",
                "Entry%",
                "Flash Ast/map",
                "Util DMG/map",
                "Clutches/map",
            ]
        ].rename(columns={"map_name": "map"}),
        column_config=default_column_config(),
    )

    section_title("Role Breakdown", "Compact match-by-match tables by role.")
    role_cols = st.columns(4)
    with role_cols[0]:
        dataframe(
            df_player[["match_label", "kills", "deaths", "K-D", "damage"]].rename(
                columns={"match_label": "match"}
            ),
            column_config=default_column_config(),
            height=248,
        )
    with role_cols[1]:
        dataframe(
            df_player[["match_label", "entry_count", "entry_wins", "Entry%"]].rename(
                columns={
                    "match_label": "match",
                    "entry_count": "entries",
                    "entry_wins": "entry wins",
                }
            ),
            column_config=default_column_config(),
            height=248,
        )
    with role_cols[2]:
        dataframe(
            df_player[
                ["match_label", "flash_successes", "enemies_flashed", "utility_damage"]
            ].rename(
                columns={
                    "match_label": "match",
                    "flash_successes": "flash ast",
                    "enemies_flashed": "flashed",
                    "utility_damage": "util dmg",
                }
            ),
            column_config=default_column_config(),
            height=248,
        )
    with role_cols[3]:
        dataframe(
            df_player[["match_label", "Clutches", "Clutch Attempts", "Clutch%"]].rename(
                columns={"match_label": "match"}
            ),
            column_config=default_column_config(),
            height=248,
        )

    st.divider()
    section_title("Trends")
    df_chart = df_player.sort_values("matchid").set_index("match_label")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("K-D per match")
        st.bar_chart(df_chart[["K-D"]])
    with col_b:
        st.subheader("Damage and utility per match")
        st.bar_chart(df_chart[["damage", "utility_damage"]])

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Entry success per match")
        st.line_chart(df_chart[["Entry%"]])
    with col_d:
        st.subheader("Accuracy and HS% per match")
        st.line_chart(df_chart[["Accuracy%", "HS%"]])

    with st.expander("Full stats table"):
        cols = [
            "match_label",
            "map_name",
            "team",
            "kills",
            "deaths",
            "K-D",
            "K/D",
            "damage",
            "HS%",
            "Accuracy%",
            "assists",
            "entry_count",
            "entry_wins",
            "Entry%",
            "Clutches",
            "Clutch%",
            "utility_damage",
            "flash_successes",
            "enemies_flashed",
        ]
        dataframe(
            df_player[cols].rename(columns={"match_label": "match", "map_name": "map"}),
            column_config=default_column_config(),
        )

    if st.button("Refresh", key="refresh_profile"):
        clear_stats_cache()
        clear_players_cache()
        st.rerun()
