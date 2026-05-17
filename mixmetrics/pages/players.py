import streamlit as st

from mixmetrics.data import clear_players_cache, load_players, load_stats
from mixmetrics.repository import upsert_player_name
from mixmetrics.ui import page_header


def render_players():
    page_header(
        "Player Names",
        "Set display names for Steam IDs. Saved names are used across the app.",
        "Admin",
    )

    df_stats = load_stats()
    name_map = load_players()

    if df_stats.empty:
        st.info("Upload a CSV first so players appear here.")
        return

    known = df_stats[["steamid64", "name"]].drop_duplicates("steamid64").sort_values("name")

    for _, row in known.iterrows():
        steamid64 = str(row["steamid64"])
        current_display = name_map.get(steamid64, "")
        with st.form(f"player_form_{steamid64}", clear_on_submit=False):
            col1, col2, col3 = st.columns([2, 3, 1])
            col1.markdown(f"**{row['name']}**")
            col1.caption(steamid64)
            new_name = col2.text_input(
                "Display name",
                value=current_display,
                key=f"player_{steamid64}",
                placeholder="Set a friendly name",
                label_visibility="collapsed",
            )
            submitted = col3.form_submit_button("Save")

        if submitted:
            clean_name = new_name.strip()
            if not clean_name:
                st.warning("Name cannot be empty.")
                continue

            upsert_player_name(steamid64, clean_name)
            clear_players_cache()
            st.success(f"Saved {clean_name}.")
            st.rerun()
