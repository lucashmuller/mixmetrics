import streamlit as st
from supabase import create_client

from mixmetrics.config import get_config_value


@st.cache_resource
def get_supabase():
    url = get_config_value("SUPABASE_URL")
    key = get_config_value("SUPABASE_KEY")
    if url is None or key is None:
        st.error(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "in .streamlit/secrets.toml or as environment variables."
        )
        st.stop()

    return create_client(url, key)
