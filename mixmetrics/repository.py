from mixmetrics.supabase_client import get_supabase


def create_match_day(day_row, assigned_maps):
    result = get_supabase().table("match_days").insert(day_row).execute()
    new_id = result.data[0]["id"]
    if assigned_maps:
        get_supabase().table("match_day_maps").insert(
            [{"match_day_id": new_id, "matchid": matchid} for matchid in assigned_maps]
        ).execute()
    return new_id


def update_match_day(day_id, day_row):
    return get_supabase().table("match_days").update(day_row).eq("id", day_id).execute()


def replace_match_day_maps(day_id, map_rows):
    get_supabase().table("match_day_maps").delete().eq("match_day_id", day_id).execute()
    if map_rows:
        get_supabase().table("match_day_maps").insert(map_rows).execute()


def delete_match_day(day_id):
    return get_supabase().table("match_days").delete().eq("id", day_id).execute()


def upsert_veto(veto_row):
    return (
        get_supabase()
        .table("series_vetoes")
        .upsert(veto_row, on_conflict="match_day_id,order_num")
        .execute()
    )


def delete_veto(veto_id):
    return get_supabase().table("series_vetoes").delete().eq("id", veto_id).execute()


def upsert_team_override(matchid, original_team, display_name):
    return (
        get_supabase()
        .table("team_name_overrides")
        .upsert(
            {
                "matchid": int(matchid),
                "original_team": original_team,
                "display_name": display_name,
            }
        )
        .execute()
    )


def upsert_match_stats(rows):
    return (
        get_supabase()
        .table("match_stats")
        .upsert(rows, on_conflict="matchid,mapnumber,steamid64")
        .execute()
    )


def upsert_player_name(steamid64, display_name):
    return (
        get_supabase()
        .table("players")
        .upsert({"steamid64": str(steamid64), "display_name": display_name})
        .execute()
    )
