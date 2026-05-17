from io import BytesIO

import pandas as pd
import streamlit as st

from mixmetrics.data import clear_map_scores_cache, clear_stats_cache
from mixmetrics.repository import upsert_map_score, upsert_match_stats
from mixmetrics.ui import page_header


def render_upload():
    page_header(
        "Upload CSV",
        "Import one match stats CSV at a time from your private server export.",
        "Admin",
    )

    if "upload_csv_form_version" not in st.session_state:
        st.session_state["upload_csv_form_version"] = 0

    form_version = st.session_state["upload_csv_form_version"]
    with st.form("upload_csv_form", clear_on_submit=False):
        map_name = st.text_input(
            "Map name",
            placeholder="Mirage",
            key=f"upload_map_name_{form_version}",
        )
        csv_file = st.file_uploader(
            "CSV file",
            type="csv",
            accept_multiple_files=False,
            key=f"upload_csv_file_{form_version}",
        )
        detected_teams = []
        preview_error = None
        if csv_file is not None and not isinstance(csv_file, list):
            try:
                preview_df = pd.read_csv(BytesIO(csv_file.getvalue()))
                if "team" not in preview_df.columns:
                    preview_error = "CSV must contain a team column."
                else:
                    preview_df = preview_df[
                        preview_df["team"].astype(str).str.lower() != "spectator"
                    ]
                    detected_teams = sorted(preview_df["team"].dropna().unique().tolist())
            except Exception as exc:
                preview_error = f"Could not preview CSV: {exc}"

        if preview_error:
            st.warning(preview_error)
        elif detected_teams:
            st.caption("Detected teams for this map score:")
            if len(detected_teams) == 2:
                st.write(f"{detected_teams[0]} vs {detected_teams[1]}")
            else:
                st.warning("CSV must contain exactly two non-spectator teams.")

        score_col1, score_col2 = st.columns(2)
        team1_label = (
            f"{detected_teams[0]} rounds"
            if len(detected_teams) == 2
            else "Team 1 rounds"
        )
        team2_label = (
            f"{detected_teams[1]} rounds"
            if len(detected_teams) == 2
            else "Team 2 rounds"
        )
        team1_score = score_col1.number_input(
            team1_label,
            min_value=0,
            max_value=99,
            value=0,
            key=f"upload_team1_score_{form_version}",
        )
        team2_score = score_col2.number_input(
            team2_label,
            min_value=0,
            max_value=99,
            value=0,
            key=f"upload_team2_score_{form_version}",
        )
        submitted = st.form_submit_button("Upload")

    if not submitted:
        if csv_file is None:
            st.info("Choose a CSV file and enter the map name before uploading.")
        return

    if csv_file is None:
        st.error("Choose a CSV file before uploading.")
        return
    if isinstance(csv_file, list):
        st.error("Upload only one CSV file at a time.")
        return

    clean_map_name = map_name.strip()
    if not clean_map_name:
        st.error("Map name is required.")
        return

    try:
        df = pd.read_csv(BytesIO(csv_file.getvalue()))
        if "team" not in df.columns:
            st.error("CSV must contain a team column.")
            return

        df = df[df["team"].str.lower() != "spectator"]
        detected_teams = sorted(df["team"].dropna().unique().tolist())
        if len(detected_teams) != 2:
            st.error("CSV must contain exactly two non-spectator teams to save a score.")
            return
        if df["matchid"].nunique() != 1:
            st.error("Upload one map at a time. The CSV contains multiple match IDs.")
            return

        df["map_name"] = clean_map_name
        rows = df.to_dict(orient="records")
        if not rows:
            st.warning("No non-spectator rows found in the CSV.")
            return

        upsert_match_stats(rows)
        upsert_map_score(
            {
                "matchid": int(df["matchid"].iloc[0]),
                "team1_name": detected_teams[0],
                "team2_name": detected_teams[1],
                "team1_score": int(team1_score),
                "team2_score": int(team2_score),
            }
        )
        clear_stats_cache()
        clear_map_scores_cache()
        st.success(f"Uploaded {len(rows)} rows for {clean_map_name}.")
        st.session_state["upload_csv_form_version"] += 1
        st.rerun()
    except Exception as exc:
        st.error(f"Upload failed: {exc}")
