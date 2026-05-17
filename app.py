from pathlib import Path

import streamlit as st
from PIL import Image

from mixmetrics.auth import (
    admin_password_matches,
    forget_admin_session,
    remember_admin_session,
    restore_admin_session,
)
from mixmetrics.pages.home import render_home
from mixmetrics.pages.match_days import render_match_days
from mixmetrics.pages.players import render_players
from mixmetrics.pages.profile import render_player_profile
from mixmetrics.pages.series import render_series
from mixmetrics.pages.stats import render_match_stats
from mixmetrics.pages.upload import render_upload
from mixmetrics.ui import inject_theme


LOGO_PATH = Path(__file__).with_name("MixMetricsLogo.png")


def load_logo():
    return Image.open(LOGO_PATH)


def render_sidebar_auth(logo):
    with st.sidebar:
        st.image(logo, width=160)
        st.divider()

        if st.session_state.get("is_admin"):
            st.success("Admin mode")
            if st.button("Logout"):
                st.session_state["is_admin"] = False
                forget_admin_session()
        else:
            st.markdown("**Admin login**")
            password = st.text_input(
                "Password",
                type="password",
                key="admin_pwd_input",
            )
            if st.button("Login"):
                if admin_password_matches(password):
                    st.session_state["is_admin"] = True
                    remember_admin_session()
                else:
                    st.error("Wrong password")

        st.divider()


def build_navigation():
    pages = {
        "Analytics": [
            st.Page(render_home, title="Overview", default=True),
            st.Page(render_series, title="Series"),
            st.Page(render_match_stats, title="Match Stats"),
            st.Page(render_player_profile, title="Player Profile"),
        ],
    }
    if st.session_state.get("is_admin"):
        pages["Admin"] = [
            st.Page(render_upload, title="Upload CSV"),
            st.Page(render_match_days, title="Match Days"),
            st.Page(render_players, title="Players"),
        ]

    return st.navigation(pages, position="sidebar", expanded=True)


def main():
    logo = load_logo()
    st.set_page_config(page_title="MixMetrics", page_icon=logo, layout="wide")
    inject_theme()
    restore_admin_session()
    render_sidebar_auth(logo)

    selected_page = build_navigation()
    selected_page.run()


if __name__ == "__main__":
    main()
