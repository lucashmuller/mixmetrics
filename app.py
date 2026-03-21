import streamlit as st
import pandas as pd
from supabase import create_client
from PIL import Image


# ── Supabase connection ────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_stats():
    result = (
        get_supabase().table("match_stats")
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
    # key: (matchid, original_team) -> display_name
    return {(r["matchid"], r["original_team"]): r["display_name"] for r in result.data}


@st.cache_data(ttl=30)
def load_match_days():
    result = get_supabase().table("match_days").select("*, match_day_maps(matchid, winner_team)").execute()
    if not result.data:
        return []
    return result.data


@st.cache_data(ttl=30)
def load_vetoes(match_day_id):
    result = (
        get_supabase().table("series_vetoes")
        .select("*")
        .eq("match_day_id", match_day_id)
        .order("order_num")
        .execute()
    )
    return result.data or []


# ── Helpers ────────────────────────────────────────────────────────────────────
def resolve_name(steamid64, name_map, fallback):
    return name_map.get(str(steamid64), fallback)


def resolve_team(matchid, original_team, overrides):
    return overrides.get((int(matchid), original_team), original_team)


# ── Page config ────────────────────────────────────────────────────────────────

logo = Image.open("MixMetricsLogo.png")

st.set_page_config(page_title="MixMetrics", page_icon=logo, layout="wide")

# ── Admin auth (sidebar) ───────────────────────────────────────────────────────
with st.sidebar:
    st.image(logo, width=160)
    st.divider()
    if st.session_state.get("is_admin"):
        st.success("Admin mode")
        if st.button("🔓 Logout"):
            st.session_state["is_admin"] = False
            st.rerun()
    else:
        st.markdown("**Admin login**")
        pwd = st.text_input("Password", type="password", key="admin_pwd_input")
        if st.button("Login"):
            if pwd == st.secrets["ADMIN_PASSWORD"]:
                st.session_state["is_admin"] = True
                st.rerun()
            else:
                st.error("Wrong password")

is_admin = st.session_state.get("is_admin", False)

st.image(logo, width=220)
st.title("MixMetrics")

if is_admin:
    home_tab, series_tab, stats_tab, profile_tab, upload_tab, days_tab, players_tab = st.tabs([
        "🏠 Home", "📋 Series", "📊 Match Stats", "📈 Player Profile",
        "📤 Upload CSV", "📅 Match Days", "👥 Players",
    ])
else:
    home_tab, series_tab, stats_tab, profile_tab = st.tabs([
        "🏠 Home", "📋 Series", "📊 Match Stats", "📈 Player Profile",
    ])
    upload_tab = days_tab = players_tab = None


# ── Tab: Home ──────────────────────────────────────────────────────────────────
with home_tab:
    df_home = load_stats()
    name_map_home = load_players()
    overrides_home = load_team_overrides()
    match_days = load_match_days()

    if df_home.empty:
        st.info("No data yet — go to **Upload CSV** to add your first match.")
        st.stop()

    df_home["display_name"] = df_home.apply(
        lambda r: resolve_name(r["steamid64"], name_map_home, r["name"]), axis=1
    )
    df_home["K/D"] = (df_home["kills"] / df_home["deaths"].replace(0, 1)).round(2)
    df_home["HS%"] = (
        (df_home["head_shot_kills"] / df_home["kills"].replace(0, 1)) * 100
    ).round(1)

    # ── Summary numbers ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matches played", df_home["matchid"].nunique())
    c2.metric("Players", df_home["steamid64"].nunique())
    c3.metric("Total kills", f"{df_home['kills'].sum():,}")
    c4.metric("Total damage", f"{df_home['damage'].sum():,}")

    st.divider()

    # ── Match Days section ─────────────────────────────────────────────────────
    if match_days:
        st.subheader("📅 Match Days")
        for day in sorted(match_days, key=lambda d: d.get("date") or "", reverse=True):
            date_str = f" · {day['date']}" if day.get("date") else ""
            t1, score, t2 = day["team1_name"], f"{day['team1_score']} × {day['team2_score']}", day["team2_name"]

            with st.expander(f"**{day['name']}**{date_str}  —  {t1}  {score}  {t2}"):
                map_ids = [m["matchid"] for m in day.get("match_day_maps", [])]
                if not map_ids:
                    st.caption("No maps assigned to this day yet.")
                else:
                    for mid in sorted(map_ids):
                        df_map = df_home[df_home["matchid"] == mid].copy()
                        map_name = df_map["map_name"].iloc[0] if not df_map.empty else "?"
                        st.markdown(f"**Map {mid} — {map_name}**")
                        df_map = df_map.sort_values("kills", ascending=False)
                        st.dataframe(
                            df_map[["display_name", "team", "kills", "deaths", "K/D", "damage"]]
                            .rename(columns={"display_name": "player"}),
                            use_container_width=True, hide_index=True,
                        )
        st.divider()

    # ── Overall leaderboard ────────────────────────────────────────────────────
    st.subheader("🏆 Overall leaderboard")

    lb = (
        df_home.groupby("display_name")
        .agg(matches=("matchid", "nunique"), kills=("kills", "sum"),
             deaths=("deaths", "sum"), damage=("damage", "sum"),
             hs_kills=("head_shot_kills", "sum"))
        .reset_index()
    )
    lb["K/D"]  = (lb["kills"] / lb["deaths"].replace(0, 1)).round(2)
    lb["HS%"]  = ((lb["hs_kills"] / lb["kills"].replace(0, 1)) * 100).round(1)
    lb["ADR"]  = (lb["damage"] / lb["matches"].replace(0, 1)).round(0).astype(int)
    lb = lb.sort_values("kills", ascending=False).reset_index(drop=True)
    lb.index += 1

    st.dataframe(
        lb[["display_name", "matches", "kills", "deaths", "K/D", "HS%", "damage", "ADR"]]
        .rename(columns={"display_name": "player"}),
        use_container_width=True,
    )

    st.divider()

    # ── Mean stats per player ─────────────────────────────────────────────────
    st.subheader("📊 Average stats per player")

    avg = (
        df_home.groupby("display_name")
        .agg(
            matches=("matchid", "nunique"),
            kills=("kills", "mean"),
            deaths=("deaths", "mean"),
            damage=("damage", "mean"),
            hs_kills=("head_shot_kills", "mean"),
            assists=("assists", "mean"),
            flash_successes=("flash_successes", "mean"),
            utility_damage=("utility_damage", "mean"),
            entry_count=("entry_count", "mean"),
            entry_wins=("entry_wins", "mean"),
            enemy5ks=("enemy5ks", "mean"),
            enemy4ks=("enemy4ks", "mean"),
            enemy3ks=("enemy3ks", "mean"),
            enemy2ks=("enemy2ks", "mean"),
            v1_wins=("v1_wins", "mean"),
            v2_wins=("v2_wins", "mean"),
            kill_reward=("kill_reward", "mean"),
            cash_earned=("cash_earned", "mean"),
        )
        .reset_index()
    )
    avg["Avg Kills"] = avg["kills"].round(1)
    avg["Avg Deaths"] = avg["deaths"].round(1)
    avg["Avg K/D"] = (avg["kills"] / avg["deaths"].replace(0, 1)).round(2)
    avg["Avg Damage"] = avg["damage"].round(0).astype(int)
    avg["Avg HS%"] = ((avg["hs_kills"] / avg["kills"].replace(0, 1)) * 100).round(1)
    avg["Avg Assists"] = avg["assists"].round(1)
    avg["Avg Flash Assists"] = avg["flash_successes"].round(1)
    avg["Avg Util Damage"] = avg["utility_damage"].round(1)
    avg["Avg Entries"] = avg["entry_count"].round(1)
    avg["Avg Entry Wins"] = avg["entry_wins"].round(1)
    avg["Avg 5K"] = avg["enemy5ks"].round(2)
    avg["Avg 4K"] = avg["enemy4ks"].round(2)
    avg["Avg 3K"] = avg["enemy3ks"].round(2)
    avg["Avg 2K"] = avg["enemy2ks"].round(2)
    avg["Avg 1v1 Wins"] = avg["v1_wins"].round(2)
    avg["Avg 1v2 Wins"] = avg["v2_wins"].round(2)
    avg["Avg Kill Reward"] = avg["kill_reward"].round(0).astype(int)
    avg["Avg Cash Earned"] = avg["cash_earned"].round(0).astype(int)
    avg = avg.sort_values("kills", ascending=False).reset_index(drop=True)
    avg.index += 1

    st.dataframe(
        avg[["display_name", "matches", "Avg Kills", "Avg Deaths", "Avg K/D",
             "Avg HS%", "Avg Damage", "Avg Assists", "Avg Flash Assists",
             "Avg Util Damage", "Avg Entries", "Avg Entry Wins",
             "Avg 5K", "Avg 4K", "Avg 3K", "Avg 2K",
             "Avg 1v1 Wins", "Avg 1v2 Wins",
             "Avg Kill Reward", "Avg Cash Earned"]]
        .rename(columns={"display_name": "player"}),
        use_container_width=True,
    )

    st.divider()

    # ── Recent matches ─────────────────────────────────────────────────────────
    st.subheader("🗓️ Recent matches")
    recent = (
        df_home[["matchid", "map_name"]].drop_duplicates()
        .sort_values("matchid", ascending=False).head(5)
    )
    for _, m in recent.iterrows():
        with st.expander(f"Match {m['matchid']} — {m['map_name']}"):
            df_m = df_home[df_home["matchid"] == m["matchid"]].sort_values("kills", ascending=False)
            st.dataframe(
                df_m[["display_name", "team", "kills", "deaths", "K/D", "damage", "HS%"]]
                .rename(columns={"display_name": "player"}),
                use_container_width=True, hide_index=True,
            )

    if st.button("🔄 Refresh", key="refresh_home"):
        st.cache_data.clear()
        st.rerun()


# ── Tab: Series ───────────────────────────────────────────────────────────────
with series_tab:
    st.header("Series")

    df_series = load_stats()
    name_map_s = load_players()
    overrides_s = load_team_overrides()
    all_days = load_match_days()

    # Only show series that have maps assigned
    days_with_maps = [d for d in all_days if d.get("match_day_maps")]

    if df_series.empty or not days_with_maps:
        st.info("Create a match day with maps assigned in **📅 Match Days** first.")
        st.stop()

    df_series["display_name"] = df_series.apply(
        lambda r: resolve_name(r["steamid64"], name_map_s, r["name"]), axis=1
    )
    df_series["team_display"] = df_series.apply(
        lambda r: resolve_team(r["matchid"], r["team"], overrides_s), axis=1
    )

    # Series selector
    day_options = {d["id"]: d for d in days_with_maps}
    selected_day_id = st.selectbox(
        "Select series",
        options=list(day_options.keys()),
        format_func=lambda x: (
            f"{day_options[x]['name']}  —  "
            f"{day_options[x]['team1_name']} "
            f"{day_options[x]['team1_score']}×{day_options[x]['team2_score']} "
            f"{day_options[x]['team2_name']}"
        ),
    )

    day = day_options[selected_day_id]
    t1_name = day["team1_name"]
    t2_name = day["team2_name"]
    map_entries = sorted(day["match_day_maps"], key=lambda m: m["matchid"])

    # ── Series header ──────────────────────────────────────────────────────────
    st.divider()
    date_str = f" · {day['date']}" if day.get("date") else ""
    st.markdown(
        f"## {day['name']}{date_str}\n"
        f"### {t1_name} &nbsp; **{day['team1_score']}** × **{day['team2_score']}** &nbsp; {t2_name}"
    )
    st.divider()

    # ── Picks & Bans ───────────────────────────────────────────────────────────
    vetoes = load_vetoes(selected_day_id)
    if vetoes:
        st.subheader("Picks & Bans")
        ACTION_STYLE = {"ban": "🚫", "pick": "✅", "decider": "🎲"}
        cols = st.columns(len(vetoes))
        for col, v in zip(cols, vetoes):
            icon = ACTION_STYLE.get(v["action"], "")
            action_label = v["action"].upper()
            team_label = v["team"] or "Decider"
            col.markdown(
                f"<div style='text-align:center; padding:6px; border-radius:8px; "
                f"background:{'#3a1a1a' if v['action']=='ban' else '#1a3a1a' if v['action']=='pick' else '#1a2a3a'};'>"
                f"<div style='font-size:1.4em'>{icon}</div>"
                f"<div style='font-weight:bold'>{v['map_name']}</div>"
                f"<div style='font-size:0.8em; color:#aaa'>{team_label}</div>"
                f"<div style='font-size:0.75em; color:#888'>{action_label}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.divider()

    # ── Map-by-map breakdown ───────────────────────────────────────────────────
    st.subheader("Map results")

    series_matchids = [m["matchid"] for m in map_entries]
    df_all_maps = df_series[df_series["matchid"].isin(series_matchids)].copy()
    df_all_maps["K/D"] = (df_all_maps["kills"] / df_all_maps["deaths"].replace(0, 1)).round(2)
    df_all_maps["HS%"] = (
        (df_all_maps["head_shot_kills"] / df_all_maps["kills"].replace(0, 1)) * 100
    ).round(1)

    for i, entry in enumerate(map_entries, start=1):
        mid = entry["matchid"]
        winner = entry.get("winner_team")
        df_map = df_all_maps[df_all_maps["matchid"] == mid].copy()
        if df_map.empty:
            continue
        map_name_val = df_map["map_name"].iloc[0]

        # Map header with winner badge
        if winner:
            winner_badge = f"🏆 **{winner}** wins"
        else:
            winner_badge = "_(winner not set)_"
        st.markdown(f"#### Map {i} — {map_name_val} &nbsp;&nbsp; {winner_badge}")

        # Split by team
        teams_in_map = df_map["team_display"].unique().tolist()
        team_cols = st.columns(len(teams_in_map))

        for col, team in zip(team_cols, sorted(teams_in_map)):
            df_team = df_map[df_map["team_display"] == team].sort_values("kills", ascending=False)
            is_winner = (winner == team)
            col.markdown(f"**{team}**{'  🏆' if is_winner else ''}")
            col.dataframe(
                df_team[["display_name", "kills", "deaths", "K/D", "damage", "HS%"]]
                .rename(columns={"display_name": "player"}),
                use_container_width=True, hide_index=True,
            )
        st.divider()

    # ── Series totals ──────────────────────────────────────────────────────────
    st.subheader("Series totals — all maps combined")

    totals = (
        df_all_maps.groupby("display_name")
        .agg(kills=("kills", "sum"), deaths=("deaths", "sum"),
             damage=("damage", "sum"), assists=("assists", "sum"),
             hs_kills=("head_shot_kills", "sum"), maps=("matchid", "nunique"))
        .reset_index()
    )
    totals["K/D"] = (totals["kills"] / totals["deaths"].replace(0, 1)).round(2)
    totals["HS%"] = ((totals["hs_kills"] / totals["kills"].replace(0, 1)) * 100).round(1)
    totals["ADR"] = (totals["damage"] / totals["maps"].replace(0, 1)).round(0).astype(int)
    totals = totals.sort_values("kills", ascending=False).reset_index(drop=True)
    totals.index += 1

    st.dataframe(
        totals[["display_name", "maps", "kills", "deaths", "K/D", "HS%", "damage", "ADR", "assists"]]
        .rename(columns={"display_name": "player"}),
        use_container_width=True,
    )

    if st.button("🔄 Refresh", key="refresh_series"):
        st.cache_data.clear()
        st.rerun()


# ── Tab: Match Days ────────────────────────────────────────────────────────────
if days_tab:
  with days_tab:
    st.header("Match Days")

    df_days = load_stats()
    supabase = get_supabase()

    if df_days.empty:
        st.info("Upload CSV data first.")
        st.stop()

    all_matchids = sorted(df_days["matchid"].unique().tolist())
    match_labels_map = {
        mid: f"Match {mid} — {df_days[df_days['matchid'] == mid]['map_name'].iloc[0]}"
        for mid in all_matchids
    }

    # ── Create new match day ───────────────────────────────────────────────────
    with st.expander("➕ Create new match day", expanded=True):
        col1, col2 = st.columns(2)
        day_name  = col1.text_input("Day name", placeholder="LAN 1")
        day_date  = col2.date_input("Date", value=None)
        col3, col4 = st.columns(2)
        team1_name  = col3.text_input("Team 1 name", placeholder="Kuli Squad")
        team2_name  = col4.text_input("Team 2 name", placeholder="Team XD")
        col5, col6 = st.columns(2)
        team1_score = col5.number_input("Team 1 maps won", min_value=0, max_value=10, value=0)
        team2_score = col6.number_input("Team 2 maps won", min_value=0, max_value=10, value=0)
        assigned_maps = st.multiselect(
            "Maps played this day",
            options=all_matchids,
            format_func=lambda x: match_labels_map[x],
        )

        if st.button("Create match day", disabled=not (day_name.strip() and team1_name.strip() and team2_name.strip())):
            day_row = {
                "name": day_name.strip(),
                "date": str(day_date) if day_date else None,
                "team1_name": team1_name.strip(),
                "team2_name": team2_name.strip(),
                "team1_score": int(team1_score),
                "team2_score": int(team2_score),
            }
            result = supabase.table("match_days").insert(day_row).execute()
            new_id = result.data[0]["id"]
            if assigned_maps:
                supabase.table("match_day_maps").insert(
                    [{"match_day_id": new_id, "matchid": mid} for mid in assigned_maps]
                ).execute()
            st.success(f"✅ Created **{day_name}**")
            st.cache_data.clear()
            st.rerun()

    st.divider()

    # ── Edit existing match days ───────────────────────────────────────────────
    existing_days = load_match_days()
    if not existing_days:
        st.caption("No match days yet.")
    else:
        st.subheader("Edit existing days")
        for day in sorted(existing_days, key=lambda d: d.get("date") or "", reverse=True):
            current_maps = [m["matchid"] for m in day.get("match_day_maps", [])]
            with st.expander(f"{day['name']}  ·  {day['team1_name']} {day['team1_score']}×{day['team2_score']} {day['team2_name']}"):
                c1, c2 = st.columns(2)
                e_name  = c1.text_input("Day name", value=day["name"], key=f"ename_{day['id']}")
                e_date  = c2.date_input("Date", value=pd.to_datetime(day["date"]).date() if day.get("date") else None, key=f"edate_{day['id']}")
                c3, c4 = st.columns(2)
                e_t1    = c3.text_input("Team 1 name", value=day["team1_name"], key=f"et1_{day['id']}")
                e_t2    = c4.text_input("Team 2 name", value=day["team2_name"], key=f"et2_{day['id']}")
                c5, c6 = st.columns(2)
                e_s1    = c5.number_input("Team 1 score", value=day["team1_score"], min_value=0, max_value=10, key=f"es1_{day['id']}")
                e_s2    = c6.number_input("Team 2 score", value=day["team2_score"], min_value=0, max_value=10, key=f"es2_{day['id']}")
                e_maps = st.multiselect(
                    "Maps", options=all_matchids, default=current_maps,
                    format_func=lambda x: match_labels_map[x], key=f"emaps_{day['id']}",
                )

                # Per-map winner dropdowns
                winner_data = {m["matchid"]: m.get("winner_team") for m in day.get("match_day_maps", [])}
                e_winners = {}
                if e_maps:
                    st.markdown("**Map winners:**")
                    for mid in sorted(e_maps):
                        map_label = match_labels_map.get(mid, f"Match {mid}")
                        t1_val = e_t1.strip() or day["team1_name"]
                        t2_val = e_t2.strip() or day["team2_name"]
                        opts = ["— not set —", t1_val, t2_val]
                        cur_w = winner_data.get(mid)
                        w_idx = 1 if cur_w == day["team1_name"] else (2 if cur_w == day["team2_name"] else 0)
                        sel = st.selectbox(map_label, options=opts, index=w_idx, key=f"winner_{day['id']}_{mid}")
                        e_winners[mid] = None if sel == "— not set —" else sel

                # ── Picks & Bans editor ────────────────────────────────────
                st.markdown("**Picks & Bans**")
                existing_vetoes = load_vetoes(day["id"])

                # Show existing entries with delete buttons
                for v in existing_vetoes:
                    icon = {"ban": "🚫", "pick": "✅", "decider": "🎲"}.get(v["action"], "")
                    vc1, vc2 = st.columns([6, 1])
                    team_str = v["team"] or "Decider"
                    vc1.markdown(f"{v['order_num']}. {icon} **{v['map_name']}** — {team_str} ({v['action']})")
                    if vc2.button("✕", key=f"vdel_{v['id']}"):
                        supabase.table("series_vetoes").delete().eq("id", v["id"]).execute()
                        st.cache_data.clear()
                        st.rerun()

                # Add new veto entry
                with st.form(key=f"veto_form_{day['id']}"):
                    va, vb, vc, vd = st.columns([2, 2, 3, 1])
                    next_order = (max((v["order_num"] for v in existing_vetoes), default=0) + 1)
                    v_order = va.number_input("Order", value=next_order, min_value=1, key=f"vo_{day['id']}")
                    v_action = vb.selectbox("Action", ["ban", "pick", "decider"], key=f"va_{day['id']}")
                    v_map = vc.text_input("Map", placeholder="Mirage", key=f"vm_{day['id']}")
                    team_options = ["— (decider)", e_t1.strip() or day["team1_name"], e_t2.strip() or day["team2_name"]]
                    v_team = vd.selectbox("Team", team_options, key=f"vt_{day['id']}")
                    if st.form_submit_button("➕ Add"):
                        if v_map.strip():
                            supabase.table("series_vetoes").upsert({
                                "match_day_id": day["id"],
                                "order_num": int(v_order),
                                "action": v_action,
                                "map_name": v_map.strip(),
                                "team": None if v_team.startswith("—") else v_team,
                            }, on_conflict="match_day_id,order_num").execute()
                            st.cache_data.clear()
                            st.rerun()

                col_save, col_del = st.columns([1, 5])
                if col_save.button("💾 Save", key=f"esave_{day['id']}"):
                    supabase.table("match_days").update({
                        "name": e_name.strip(),
                        "date": str(e_date) if e_date else None,
                        "team1_name": e_t1.strip(),
                        "team2_name": e_t2.strip(),
                        "team1_score": int(e_s1),
                        "team2_score": int(e_s2),
                    }).eq("id", day["id"]).execute()
                    # Replace map assignments (preserving winner_team)
                    supabase.table("match_day_maps").delete().eq("match_day_id", day["id"]).execute()
                    if e_maps:
                        supabase.table("match_day_maps").insert([
                            {"match_day_id": day["id"], "matchid": mid, "winner_team": e_winners.get(mid)}
                            for mid in e_maps
                        ]).execute()
                    st.success("Saved!")
                    st.cache_data.clear()
                    st.rerun()

                if col_del.button("🗑️ Delete", key=f"edel_{day['id']}"):
                    supabase.table("match_days").delete().eq("id", day["id"]).execute()
                    st.cache_data.clear()
                    st.rerun()

    st.divider()

    # ── Team name overrides ────────────────────────────────────────────────────
    st.subheader("✏️ Edit team names per match")
    st.caption("Override the raw team names from the CSV with friendly names.")

    overrides = load_team_overrides()
    teams_per_match = (
        df_days[["matchid", "team", "map_name"]]
        .drop_duplicates()
        .sort_values(["matchid", "team"])
    )

    for matchid, grp in teams_per_match.groupby("matchid"):
        map_name = grp["map_name"].iloc[0]
        with st.expander(f"Match {matchid} — {map_name}"):
            for _, row in grp.iterrows():
                orig = row["team"]
                current = overrides.get((int(matchid), orig), "")
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.text(orig)
                new_val = c2.text_input(
                    "Display name", value=current,
                    placeholder="Friendly name", key=f"to_{matchid}_{orig}",
                    label_visibility="collapsed",
                )
                if c3.button("Save", key=f"tsave_{matchid}_{orig}"):
                    if new_val.strip():
                        supabase.table("team_name_overrides").upsert(
                            {"matchid": int(matchid), "original_team": orig, "display_name": new_val.strip()}
                        ).execute()
                        st.cache_data.clear()
                        st.rerun()


# ── Tab: Upload CSV ────────────────────────────────────────────────────────────
if upload_tab:
  with upload_tab:
    st.header("Upload match CSV")

    map_name = st.text_input("Map name (e.g. Mirage, Inferno)", placeholder="Mirage")
    csv_file = st.file_uploader("Choose a CSV file", type="csv")

    if st.button("Upload", disabled=(csv_file is None or map_name.strip() == "")):
        df = pd.read_csv(csv_file)
        df = df[df["team"].str.lower() != "spectator"]
        df["map_name"] = map_name.strip()
        rows = df.to_dict(orient="records")
        try:
            get_supabase().table("match_stats") \
                .upsert(rows, on_conflict="matchid,mapnumber,steamid64") \
                .execute()
            st.success(f"✅ Uploaded {len(rows)} rows for map **{map_name}**")
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Upload failed: {e}")

    if csv_file is None:
        st.info("Select a map name and pick a CSV file to upload.")


# ── Tab: Match Stats ───────────────────────────────────────────────────────────
with stats_tab:
    st.header("Match stats")

    df_all = load_stats()
    name_map = load_players()
    overrides_stats = load_team_overrides()

    if df_all.empty:
        st.info("No data yet — upload a CSV first.")
        st.stop()

    df_all["display_name"] = df_all.apply(
        lambda r: resolve_name(r["steamid64"], name_map, r["name"]), axis=1
    )
    df_all["team_display"] = df_all.apply(
        lambda r: resolve_team(r["matchid"], r["team"], overrides_stats), axis=1
    )

    col1, col2 = st.columns(2)
    with col1:
        matches = df_all[["matchid", "map_name"]].drop_duplicates().sort_values("matchid")
        match_labels = {
            row["matchid"]: f"Match {row['matchid']} — {row['map_name']}"
            for _, row in matches.iterrows()
        }
        selected_matchid = st.selectbox(
            "Match / Map", options=list(match_labels.keys()),
            format_func=lambda x: match_labels[x],
        )

    df_match = df_all[df_all["matchid"] == selected_matchid].copy()

    with col2:
        all_players = sorted(df_match["display_name"].unique().tolist())
        selected_players = st.multiselect("Players (leave empty for all)", options=all_players)

    if selected_players:
        df_match = df_match[df_match["display_name"].isin(selected_players)]

    df_match["K/D"] = (df_match["kills"] / df_match["deaths"].replace(0, 1)).round(2)
    df_match["HS%"] = (
        (df_match["head_shot_kills"] / df_match["kills"].replace(0, 1)) * 100
    ).round(1)

    display_cols = [
        "display_name", "team_display", "kills", "deaths", "K/D", "HS%",
        "damage", "assists", "entry_count", "entry_wins",
        "v1_count", "v1_wins", "v2_count", "v2_wins",
        "utility_damage", "flash_count", "enemies_flashed",
    ]
    df_display = (
        df_match[display_cols]
        .rename(columns={"display_name": "player", "team_display": "team"})
        .sort_values("kills", ascending=False)
    )

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.subheader("Kills per player")
    st.bar_chart(df_display.set_index("player")[["kills"]].sort_values("kills", ascending=False))

    if st.button("🔄 Refresh", key="refresh_stats"):
        st.cache_data.clear()
        st.rerun()


# ── Tab: Player Profile ────────────────────────────────────────────────────────
with profile_tab:
    st.header("Player Profile")

    df_all2 = load_stats()
    name_map2 = load_players()

    if df_all2.empty:
        st.info("No data yet — upload a CSV first.")
        st.stop()

    df_all2["display_name"] = df_all2.apply(
        lambda r: resolve_name(r["steamid64"], name_map2, r["name"]), axis=1
    )

    selected_player = st.selectbox(
        "Select player", options=sorted(df_all2["display_name"].unique().tolist())
    )

    df_player = df_all2[df_all2["display_name"] == selected_player].copy()
    df_player["K/D"] = (df_player["kills"] / df_player["deaths"].replace(0, 1)).round(2)
    df_player["HS%"] = (
        (df_player["head_shot_kills"] / df_player["kills"].replace(0, 1)) * 100
    ).round(1)
    df_player["match_label"] = df_player.apply(
        lambda r: f"M{r['matchid']} {r['map_name']}", axis=1
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Matches", df_player["matchid"].nunique())
    c2.metric("Avg Kills",  f"{df_player['kills'].mean():.1f}")
    c3.metric("Avg Deaths", f"{df_player['deaths'].mean():.1f}")
    c4.metric("Avg K/D",    f"{df_player['K/D'].mean():.2f}")
    c5.metric("Avg HS%",    f"{df_player['HS%'].mean():.1f}%")
    c6.metric("Avg Damage", f"{df_player['damage'].mean():.0f}")

    st.divider()

    df_chart = df_player.set_index("match_label").sort_index()

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Kills & Deaths per match")
        st.bar_chart(df_chart[["kills", "deaths"]])
    with col_b:
        st.subheader("K/D ratio per match")
        st.line_chart(df_chart[["K/D"]])

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Damage per match")
        st.bar_chart(df_chart[["damage"]])
    with col_d:
        st.subheader("HS% per match")
        st.line_chart(df_chart[["HS%"]])

    with st.expander("Full stats table"):
        cols = [
            "match_label", "team", "kills", "deaths", "K/D", "HS%", "damage", "assists",
            "entry_count", "entry_wins", "v1_count", "v1_wins", "v2_count", "v2_wins",
            "utility_damage", "flash_count", "enemies_flashed",
        ]
        st.dataframe(
            df_player[cols].rename(columns={"match_label": "match"}),
            use_container_width=True, hide_index=True,
        )

    if st.button("🔄 Refresh", key="refresh_profile"):
        st.cache_data.clear()
        st.rerun()


# ── Tab: Players ───────────────────────────────────────────────────────────────
if players_tab:
  with players_tab:
    st.header("Player names")
    st.caption("Set a display name for each Steam ID. This name will be used everywhere in the app.")

    df_stats = load_stats()
    name_map3 = load_players()
    supabase3 = get_supabase()

    if df_stats.empty:
        st.info("Upload a CSV first so players appear here.")
        st.stop()

    known = (
        df_stats[["steamid64", "name"]].drop_duplicates("steamid64").sort_values("name")
    )

    for _, row in known.iterrows():
        sid = str(row["steamid64"])
        current_display = name_map3.get(sid, "")
        col1, col2, col3 = st.columns([2, 2, 1])
        col1.text(row["name"])
        col1.caption(sid)
        new_name = col2.text_input(
            "Display name", value=current_display, key=f"player_{sid}",
            placeholder="Set a friendly name",
        )
        if col3.button("Save", key=f"save_{sid}"):
            if new_name.strip():
                supabase3.table("players").upsert(
                    {"steamid64": sid, "display_name": new_name.strip()}
                ).execute()
                st.success(f"Saved **{new_name}**")
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("Name cannot be empty.")
