import streamlit as st

from mixmetrics.data import (
    clear_players_cache,
    clear_stats_cache,
    clear_team_overrides_cache,
    load_players,
    load_stats,
    load_team_overrides,
)
from mixmetrics.transforms import (
    add_basic_rates,
    add_player_display_names,
    add_team_display_names,
)
from mixmetrics.ui import dataframe, default_column_config, page_header, section_title, stat_card


def render_match_stats():
    page_header(
        "Match Stats",
        "Inspect one map at a time with fragging, aim, entry, clutch, and support indicators.",
        "Map analysis",
    )

    df_all = load_stats()
    if df_all.empty:
        st.info("No data yet. Upload a CSV first.")
        return

    df_all = add_player_display_names(df_all, load_players())
    df_all = add_team_display_names(df_all, load_team_overrides())

    section_title("Filters")
    col1, col2 = st.columns([1.2, 1])
    with col1:
        matches = df_all[["matchid", "map_name"]].drop_duplicates().sort_values("matchid")
        match_labels = {
            row["matchid"]: f"Match {row['matchid']} - {row['map_name']}"
            for _, row in matches.iterrows()
        }
        selected_matchid = st.selectbox(
            "Match / Map",
            options=list(match_labels.keys()),
            format_func=lambda matchid: match_labels[matchid],
        )

    df_match = df_all[df_all["matchid"] == selected_matchid].copy()

    with col2:
        all_players = sorted(df_match["display_name"].unique().tolist())
        selected_players = st.multiselect(
            "Players (leave empty for all)",
            options=all_players,
        )

    if selected_players:
        df_match = df_match[df_match["display_name"].isin(selected_players)]

    df_match = add_basic_rates(df_match)
    map_name = df_match["map_name"].iloc[0] if not df_match.empty else "Selected map"
    stat_cols = st.columns(5)
    stat_card(stat_cols[0], "Map", map_name)
    stat_card(stat_cols[1], "Players", df_match["steamid64"].nunique())
    stat_card(stat_cols[2], "Total kills", int(df_match["kills"].sum()))
    stat_card(stat_cols[3], "Top K-D", df_match.sort_values(["K-D", "kills"], ascending=False)["display_name"].iloc[0])
    stat_card(stat_cols[4], "Top DMG", df_match.sort_values("damage", ascending=False)["display_name"].iloc[0])

    display_cols = [
        "display_name",
        "team_display",
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
    df_display = (
        df_match[display_cols]
        .rename(columns={"display_name": "player", "team_display": "team"})
        .sort_values(["K-D", "kills"], ascending=False)
    )

    section_title("Scoreboard", "Sorted by K-D, then kills.")
    dataframe(
        df_display,
        column_config=default_column_config(),
    )

    section_title("Comparisons")
    chart_data = df_display.set_index("player")
    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.caption("Fragging")
        st.bar_chart(chart_data[["K-D"]].sort_values("K-D", ascending=False))
    with chart_cols[1]:
        st.caption("Damage and utility")
        st.bar_chart(chart_data[["damage", "utility_damage"]].sort_values("damage", ascending=False))

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.caption("Entry success")
        st.bar_chart(chart_data[["entry_wins", "entry_count"]].sort_values("entry_wins", ascending=False))
    with chart_cols[1]:
        st.caption("Support")
        st.bar_chart(chart_data[["flash_successes", "enemies_flashed"]].sort_values("flash_successes", ascending=False))

    if st.button("Refresh", key="refresh_stats"):
        clear_stats_cache()
        clear_players_cache()
        clear_team_overrides_cache()
        st.rerun()
