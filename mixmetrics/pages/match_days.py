import pandas as pd
import streamlit as st

from mixmetrics.data import (
    clear_match_days_cache,
    clear_map_scores_cache,
    clear_team_overrides_cache,
    clear_vetoes_cache,
    load_map_scores,
    load_match_days,
    load_stats,
    load_team_overrides,
    load_vetoes,
)
from mixmetrics.repository import (
    create_match_day,
    delete_match_day,
    delete_veto,
    replace_match_day_maps,
    update_match_day,
    upsert_map_score,
    upsert_team_override,
    upsert_veto,
)
from mixmetrics.ui import page_header, section_title


def _match_labels(df_stats):
    all_matchids = sorted(df_stats["matchid"].unique().tolist())
    labels = {
        matchid: (
            f"Match {matchid} - "
            f"{df_stats[df_stats['matchid'] == matchid]['map_name'].iloc[0]}"
        )
        for matchid in all_matchids
    }
    return all_matchids, labels


def _clear_match_day_related_caches():
    clear_match_days_cache()
    clear_vetoes_cache()


def render_match_days():
    page_header(
        "Match Days",
        "Manage series metadata, maps, winners, vetoes, and per-match team names.",
        "Admin",
    )

    df_days = load_stats()
    if df_days.empty:
        st.info("Upload CSV data first.")
        return

    all_matchids, match_labels = _match_labels(df_days)

    _render_create_match_day(all_matchids, match_labels)
    st.divider()
    _render_existing_match_days(all_matchids, match_labels)
    st.divider()
    _render_map_scores_editor(df_days)
    st.divider()
    _render_team_overrides(df_days)


def _render_create_match_day(all_matchids, match_labels):
    with st.expander("Create new match day", expanded=True):
        with st.form("create_match_day_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            day_name = col1.text_input("Day name", placeholder="LAN 1")
            day_date = col2.date_input("Date", value=None)

            col3, col4 = st.columns(2)
            team1_name = col3.text_input("Team 1 name", placeholder="Kuli Squad")
            team2_name = col4.text_input("Team 2 name", placeholder="Team XD")

            col5, col6 = st.columns(2)
            team1_score = col5.number_input(
                "Team 1 maps won", min_value=0, max_value=10, value=0
            )
            team2_score = col6.number_input(
                "Team 2 maps won", min_value=0, max_value=10, value=0
            )
            assigned_maps = st.multiselect(
                "Maps played this day",
                options=all_matchids,
                format_func=lambda matchid: match_labels[matchid],
            )
            submitted = st.form_submit_button("Create match day")

        if not submitted:
            return

        clean_day = day_name.strip()
        clean_t1 = team1_name.strip()
        clean_t2 = team2_name.strip()
        if not clean_day or not clean_t1 or not clean_t2:
            st.error("Day name and both team names are required.")
            return

        create_match_day(
            {
                "name": clean_day,
                "date": str(day_date) if day_date else None,
                "team1_name": clean_t1,
                "team2_name": clean_t2,
                "team1_score": int(team1_score),
                "team2_score": int(team2_score),
            },
            assigned_maps,
        )
        clear_match_days_cache()
        st.success(f"Created {clean_day}.")
        st.rerun()


def _render_existing_match_days(all_matchids, match_labels):
    existing_days = load_match_days()
    if not existing_days:
        st.caption("No match days yet.")
        return

    section_title("Edit Existing Days")
    for day in sorted(existing_days, key=lambda row: row.get("date") or "", reverse=True):
        current_maps = [row["matchid"] for row in day.get("match_day_maps", [])]
        title = (
            f"{day['name']} - {day['team1_name']} "
            f"{day['team1_score']}x{day['team2_score']} {day['team2_name']}"
        )
        with st.expander(title):
            _render_match_day_details_form(day)
            _render_match_day_maps_form(day, current_maps, all_matchids, match_labels)
            _render_veto_editor(day)
            _render_delete_match_day(day)


def _render_match_day_details_form(day):
    st.markdown("**Series Info**")
    with st.form(f"match_day_details_{day['id']}", clear_on_submit=False):
        col1, col2 = st.columns(2)
        day_name = col1.text_input("Day name", value=day["name"])
        day_date = col2.date_input(
            "Date",
            value=pd.to_datetime(day["date"]).date() if day.get("date") else None,
        )
        col3, col4 = st.columns(2)
        team1_name = col3.text_input("Team 1 name", value=day["team1_name"])
        team2_name = col4.text_input("Team 2 name", value=day["team2_name"])
        col5, col6 = st.columns(2)
        team1_score = col5.number_input(
            "Team 1 score",
            value=int(day["team1_score"]),
            min_value=0,
            max_value=10,
        )
        team2_score = col6.number_input(
            "Team 2 score",
            value=int(day["team2_score"]),
            min_value=0,
            max_value=10,
        )
        submitted = st.form_submit_button("Save series info")

    if not submitted:
        return

    clean_day = day_name.strip()
    clean_t1 = team1_name.strip()
    clean_t2 = team2_name.strip()
    if not clean_day or not clean_t1 or not clean_t2:
        st.error("Day name and both team names are required.")
        return

    update_match_day(
        day["id"],
        {
            "name": clean_day,
            "date": str(day_date) if day_date else None,
            "team1_name": clean_t1,
            "team2_name": clean_t2,
            "team1_score": int(team1_score),
            "team2_score": int(team2_score),
        },
    )
    clear_match_days_cache()
    st.success("Series info saved.")
    st.rerun()


def _render_match_day_maps_form(day, current_maps, all_matchids, match_labels):
    st.markdown("**Maps & Winners**")
    winner_data = {
        row["matchid"]: row.get("winner_team") for row in day.get("match_day_maps", [])
    }
    with st.form(f"match_day_maps_{day['id']}", clear_on_submit=False):
        selected_maps = st.multiselect(
            "Maps",
            options=all_matchids,
            default=current_maps,
            format_func=lambda matchid: match_labels[matchid],
        )

        selected_winners = {}
        if selected_maps:
            st.caption("Winner options use the saved team names. Save series info first if you renamed teams.")
            for matchid in sorted(selected_maps):
                options = ["Not set", day["team1_name"], day["team2_name"]]
                current_winner = winner_data.get(matchid)
                index = options.index(current_winner) if current_winner in options else 0
                selected = st.selectbox(
                    match_labels.get(matchid, f"Match {matchid}"),
                    options=options,
                    index=index,
                )
                selected_winners[matchid] = None if selected == "Not set" else selected

        submitted = st.form_submit_button("Save maps and winners")

    if not submitted:
        return

    replace_match_day_maps(
        day["id"],
        [
            {
                "match_day_id": day["id"],
                "matchid": matchid,
                "winner_team": selected_winners.get(matchid),
            }
            for matchid in selected_maps
        ],
    )
    clear_match_days_cache()
    st.success("Maps and winners saved.")
    st.rerun()


def _render_veto_editor(day):
    st.markdown("**Picks & Bans**")
    existing_vetoes = load_vetoes(day["id"])

    if existing_vetoes:
        for veto in existing_vetoes:
            col1, col2 = st.columns([6, 1])
            team_str = veto["team"] or "Decider"
            col1.markdown(
                f"{veto['order_num']}. **{veto['map_name']}** - "
                f"{team_str} ({veto['action']})"
            )
            if col2.button("Delete", key=f"vdel_{veto['id']}"):
                delete_veto(veto["id"])
                clear_vetoes_cache()
                st.success("Veto deleted.")
                st.rerun()
    else:
        st.caption("No vetoes yet.")

    with st.form(key=f"veto_form_{day['id']}", clear_on_submit=False):
        col1, col2, col3, col4 = st.columns([1, 2, 3, 2])
        next_order = max((veto["order_num"] for veto in existing_vetoes), default=0) + 1
        order_num = col1.number_input("Order", value=next_order, min_value=1)
        action = col2.selectbox("Action", ["ban", "pick", "decider"])
        map_name = col3.text_input("Map", placeholder="Mirage")
        team_options = ["Decider", day["team1_name"], day["team2_name"]]
        team = col4.selectbox("Team", team_options)
        submitted = st.form_submit_button("Add / replace veto")

    if not submitted:
        return

    clean_map = map_name.strip()
    if not clean_map:
        st.error("Map name is required for a veto.")
        return

    upsert_veto(
        {
            "match_day_id": day["id"],
            "order_num": int(order_num),
            "action": action,
            "map_name": clean_map,
            "team": None if team == "Decider" else team,
        }
    )
    clear_vetoes_cache()
    st.success("Veto saved.")
    st.rerun()


def _render_delete_match_day(day):
    st.markdown("**Danger Zone**")
    confirm_text = f"delete {day['name']}"
    with st.form(f"delete_match_day_{day['id']}", clear_on_submit=False):
        confirmation = st.text_input(
            "Type the confirmation text to delete this match day",
            placeholder=confirm_text,
        )
        submitted = st.form_submit_button("Delete match day")

    if not submitted:
        return

    if confirmation.strip() != confirm_text:
        st.error(f"Type exactly: {confirm_text}")
        return

    delete_match_day(day["id"])
    _clear_match_day_related_caches()
    st.success("Match day deleted.")
    st.rerun()


def _render_map_scores_editor(df_days):
    section_title(
        "Map Scores",
        "Edit the round score saved during upload for each map.",
    )
    map_scores = load_map_scores()
    maps = (
        df_days[["matchid", "map_name", "team"]]
        .drop_duplicates()
        .sort_values(["matchid", "team"])
    )

    for matchid, group in maps.groupby("matchid"):
        teams = sorted(group["team"].dropna().unique().tolist())
        if len(teams) != 2:
            with st.expander(f"Match {matchid} - {group['map_name'].iloc[0]}"):
                st.warning("This map does not have exactly two teams, so score editing is disabled.")
            continue

        current = map_scores.get(int(matchid), {})
        team1_name = current.get("team1_name") or teams[0]
        team2_name = current.get("team2_name") or teams[1]
        with st.expander(f"Match {matchid} - {group['map_name'].iloc[0]}"):
            with st.form(f"map_score_{matchid}", clear_on_submit=False):
                col1, col2 = st.columns(2)
                team1_score = col1.number_input(
                    f"{team1_name} rounds",
                    min_value=0,
                    max_value=99,
                    value=int(current.get("team1_score") or 0),
                )
                team2_score = col2.number_input(
                    f"{team2_name} rounds",
                    min_value=0,
                    max_value=99,
                    value=int(current.get("team2_score") or 0),
                )
                submitted = st.form_submit_button("Save map score")

            if not submitted:
                continue

            upsert_map_score(
                {
                    "matchid": int(matchid),
                    "team1_name": team1_name,
                    "team2_name": team2_name,
                    "team1_score": int(team1_score),
                    "team2_score": int(team2_score),
                }
            )
            clear_map_scores_cache()
            st.success("Map score saved.")
            st.rerun()


def _render_team_overrides(df_days):
    section_title(
        "Team Names Per Match",
        "Override raw CSV team names with friendly names.",
    )

    overrides = load_team_overrides()
    teams_per_match = (
        df_days[["matchid", "team", "map_name"]]
        .drop_duplicates()
        .sort_values(["matchid", "team"])
    )

    for matchid, group in teams_per_match.groupby("matchid"):
        map_name = group["map_name"].iloc[0]
        with st.expander(f"Match {matchid} - {map_name}"):
            with st.form(f"team_override_{matchid}", clear_on_submit=False):
                proposed_values = {}
                for _, row in group.iterrows():
                    original = row["team"]
                    current = overrides.get((int(matchid), original), "")
                    col1, col2 = st.columns([2, 3])
                    col1.markdown(f"**{original}**")
                    proposed_values[original] = col2.text_input(
                        "Display name",
                        value=current,
                        placeholder="Friendly name",
                        key=f"to_{matchid}_{original}",
                        label_visibility="collapsed",
                    )
                submitted = st.form_submit_button("Save team names")

            if not submitted:
                continue

            changed = 0
            for original, display_name in proposed_values.items():
                clean_name = display_name.strip()
                if not clean_name:
                    continue
                if clean_name == overrides.get((int(matchid), original), ""):
                    continue

                upsert_team_override(matchid, original, clean_name)
                changed += 1

            if changed:
                clear_team_overrides_cache()
                st.success(f"Saved {changed} team name override(s).")
                st.rerun()
            else:
                st.info("No non-empty team name changes to save.")
