import streamlit as st

from mixmetrics.data import (
    clear_match_days_cache,
    clear_players_cache,
    clear_stats_cache,
    clear_team_overrides_cache,
    clear_vetoes_cache,
    load_match_days,
    load_players,
    load_stats,
    load_team_overrides,
    load_vetoes,
)
from mixmetrics.transforms import (
    add_aggregate_indicators,
    add_basic_rates,
    add_player_display_names,
    add_team_display_names,
)
from mixmetrics.ui import dataframe, default_column_config, page_header, section_title


def render_series():
    page_header(
        "Series",
        "Review each series by scoreline, veto flow, map results, and player totals.",
        "Match review",
    )

    df_series = load_stats()
    all_days = load_match_days()
    days_with_maps = [day for day in all_days if day.get("match_day_maps")]

    if df_series.empty or not days_with_maps:
        st.info("Create a match day with maps assigned first.")
        return

    name_map = load_players()
    overrides = load_team_overrides()
    df_series = add_player_display_names(df_series, name_map)
    df_series = add_team_display_names(df_series, overrides)

    sorted_days = sorted(
        days_with_maps,
        key=lambda day: (day.get("date") or "", day.get("id") or 0),
        reverse=True,
    )
    day_options = {day["id"]: day for day in sorted_days}
    selected_day_id = st.selectbox(
        "Select series",
        options=[day["id"] for day in sorted_days],
        format_func=lambda day_id: (
            f"{day_options[day_id]['name']} - "
            f"{day_options[day_id]['team1_name']} "
            f"{day_options[day_id]['team1_score']}x"
            f"{day_options[day_id]['team2_score']} "
            f"{day_options[day_id]['team2_name']}"
        ),
    )

    day = day_options[selected_day_id]
    map_entries = sorted(day["match_day_maps"], key=lambda row: row["matchid"])

    date_str = f" - {day['date']}" if day.get("date") else ""
    st.markdown(
        f"""
        <div style="border:1px solid var(--mix-border);background:var(--mix-panel);
                    border-radius:8px;padding:1rem 1.1rem;margin:0.4rem 0 1rem 0">
          <div class="mix-page-kicker">{day['name']}{date_str}</div>
          <div style="font-size:1.55rem;font-weight:800">
            {day['team1_name']} <span class="mix-winner">{day['team1_score']}</span>
            x <span class="mix-winner">{day['team2_score']}</span> {day['team2_name']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vetoes = load_vetoes(selected_day_id)
    if vetoes:
        section_title("Picks & Bans")
        action_style = {"ban": "X", "pick": "Pick", "decider": "Decider"}
        cols = st.columns(len(vetoes))
        for col, veto in zip(cols, vetoes):
            action_label = action_style.get(veto["action"], veto["action"].title())
            team_label = veto["team"] or "Decider"
            col.markdown(
                f"""
                <div style="border:1px solid var(--mix-border);border-radius:8px;
                            background:var(--mix-panel-soft);padding:0.7rem;text-align:center">
                  <div class="mix-page-kicker">{action_label}</div>
                  <div style="font-weight:800">{veto['map_name']}</div>
                  <div style="color:var(--mix-muted);font-size:0.84rem">{team_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.divider()

    section_title("Map Results", "Each map is split by team for quick scoreboard comparison.")

    series_matchids = [entry["matchid"] for entry in map_entries]
    df_all_maps = df_series[df_series["matchid"].isin(series_matchids)].copy()
    df_all_maps = add_basic_rates(df_all_maps)

    for index, entry in enumerate(map_entries, start=1):
        mid = entry["matchid"]
        winner = entry.get("winner_team")
        df_map = df_all_maps[df_all_maps["matchid"] == mid].copy()
        if df_map.empty:
            continue

        map_name = df_map["map_name"].iloc[0]
        winner_label = f"Winner: **{winner}**" if winner else "_Winner not set_"
        st.markdown(f"#### Map {index} - {map_name} - {winner_label}")

        teams_in_map = sorted(df_map["team_display"].unique().tolist())
        team_cols = st.columns(len(teams_in_map))
        for col, team in zip(team_cols, teams_in_map):
            df_team = df_map[df_map["team_display"] == team].sort_values(
                "kills", ascending=False
            )
            col.markdown(f"**{team}**{' - winner' if winner == team else ''}")
            dataframe(
                df_team[
                    [
                        "display_name",
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

    section_title("Series Totals", "Combined player output across all maps in the selected series.")
    totals = (
        df_all_maps.groupby("display_name")
        .agg(
            kills=("kills", "sum"),
            deaths=("deaths", "sum"),
            damage=("damage", "sum"),
            assists=("assists", "sum"),
            hs_kills=("head_shot_kills", "sum"),
            maps=("matchid", "nunique"),
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
    totals = add_aggregate_indicators(totals)
    totals = totals.sort_values(["K-D", "kills"], ascending=False).reset_index(drop=True)
    totals.index += 1

    dataframe(
        totals[
            [
                "display_name",
                "maps",
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
                "assists",
            ]
        ].rename(columns={"display_name": "player"}),
        column_config=default_column_config(),
    )

    if st.button("Refresh", key="refresh_series"):
        clear_stats_cache()
        clear_players_cache()
        clear_team_overrides_cache()
        clear_match_days_cache()
        clear_vetoes_cache()
        st.rerun()
