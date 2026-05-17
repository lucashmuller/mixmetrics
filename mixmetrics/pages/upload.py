import pandas as pd
import streamlit as st

from mixmetrics.data import clear_stats_cache
from mixmetrics.repository import upsert_match_stats
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
        df = pd.read_csv(csv_file)
        if "team" not in df.columns:
            st.error("CSV must contain a team column.")
            return

        df = df[df["team"].str.lower() != "spectator"]
        df["map_name"] = clean_map_name
        rows = df.to_dict(orient="records")
        if not rows:
            st.warning("No non-spectator rows found in the CSV.")
            return

        upsert_match_stats(rows)
        clear_stats_cache()
        st.success(f"Uploaded {len(rows)} rows for {clean_map_name}.")
        st.session_state["upload_csv_form_version"] += 1
        st.rerun()
    except Exception as exc:
        st.error(f"Upload failed: {exc}")
