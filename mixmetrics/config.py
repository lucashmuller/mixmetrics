import os

import streamlit as st


def get_config_value(name):
    try:
        value = st.secrets[name]
    except Exception:
        value = os.environ.get(name)

    if value is None:
        return None

    value = str(value).strip()
    return value or None
