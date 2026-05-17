import hashlib
import hmac
import time

import streamlit as st
import streamlit.components.v1 as components

from mixmetrics.config import get_config_value


ADMIN_COOKIE_NAME = "mixmetrics_admin"
ADMIN_COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def _admin_secret():
    return get_config_value("ADMIN_PASSWORD")


def admin_password_matches(password):
    expected_password = _admin_secret()
    if expected_password is None:
        st.error(
            "Admin password is not configured. Set ADMIN_PASSWORD in "
            ".streamlit/secrets.toml or as an environment variable."
        )
        return False

    return hmac.compare_digest(password, expected_password)


def _sign(timestamp):
    secret = _admin_secret()
    if secret is None:
        return None

    return hmac.new(
        secret.encode("utf-8"),
        str(timestamp).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_admin_token():
    timestamp = int(time.time())
    signature = _sign(timestamp)
    if signature is None:
        return None

    return f"{timestamp}.{signature}"


def verify_admin_token(token):
    if not token or "." not in token:
        return False

    timestamp_text, signature = token.split(".", 1)
    try:
        timestamp = int(timestamp_text)
    except ValueError:
        return False

    if time.time() - timestamp > ADMIN_COOKIE_MAX_AGE_SECONDS:
        return False

    expected_signature = _sign(timestamp)
    if expected_signature is None:
        return False

    return hmac.compare_digest(signature, expected_signature)


def restore_admin_session():
    if st.session_state.get("is_admin"):
        return

    cookies = getattr(st.context, "cookies", {})
    if verify_admin_token(cookies.get(ADMIN_COOKIE_NAME)):
        st.session_state["is_admin"] = True


def remember_admin_session():
    token = create_admin_token()
    if token is None:
        return

    components.html(
        f"""
        <script>
        document.cookie = "{ADMIN_COOKIE_NAME}={token}; max-age={ADMIN_COOKIE_MAX_AGE_SECONDS}; path=/; SameSite=Lax";
        </script>
        """,
        height=0,
    )


def forget_admin_session():
    components.html(
        f"""
        <script>
        document.cookie = "{ADMIN_COOKIE_NAME}=; max-age=0; path=/; SameSite=Lax";
        </script>
        """,
        height=0,
    )
