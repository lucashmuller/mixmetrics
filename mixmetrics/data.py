import pandas as pd
import streamlit as st

from mixmetrics.supabase_client import get_supabase


@st.cache_data(ttl=30)
def load_stats():
    result = (
        get_supabase()
        .table("match_stats")
        .select("*")
        .neq("team", "Spectator")
        .execute()
    )
    if not result.data:
        return pd.DataFrame()
    return pd.DataFrame(result.data)


@st.cache_data(ttl=30)
def load_players():
    result = get_supabase().table("players").select("*").execute()
    if not result.data:
        return {}
    return {row["steamid64"]: row["display_name"] for row in result.data}


@st.cache_data(ttl=30)
def load_team_overrides():
    result = get_supabase().table("team_name_overrides").select("*").execute()
    if not result.data:
        return {}
    return {
        (int(row["matchid"]), row["original_team"]): row["display_name"]
        for row in result.data
    }


@st.cache_data(ttl=30)
def load_match_days():
    result = (
        get_supabase()
        .table("match_days")
        .select("*, match_day_maps(matchid, winner_team)")
        .execute()
    )
    return result.data or []


@st.cache_data(ttl=30)
def load_vetoes(match_day_id):
    result = (
        get_supabase()
        .table("series_vetoes")
        .select("*")
        .eq("match_day_id", match_day_id)
        .order("order_num")
        .execute()
    )
    return result.data or []


@st.cache_data(ttl=30)
def load_map_scores():
    result = get_supabase().table("map_scores").select("*").execute()
    return {
        int(row["matchid"]): row
        for row in (result.data or [])
    }


def clear_stats_cache():
    load_stats.clear()


def clear_players_cache():
    load_players.clear()


def clear_team_overrides_cache():
    load_team_overrides.clear()


def clear_match_days_cache():
    load_match_days.clear()


def clear_vetoes_cache():
    load_vetoes.clear()


def clear_map_scores_cache():
    load_map_scores.clear()
