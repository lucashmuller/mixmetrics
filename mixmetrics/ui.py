import streamlit as st


def inject_theme():
    st.markdown(
        """
        <style>
        :root {
            --mix-bg: #0f141b;
            --mix-panel: #151c24;
            --mix-panel-soft: #1b2530;
            --mix-border: #293544;
            --mix-text: #e7edf5;
            --mix-muted: #96a3b3;
            --mix-accent: #31d07f;
            --mix-accent-2: #58a6ff;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(49, 208, 127, 0.10), transparent 30rem),
                linear-gradient(180deg, #0f141b 0%, #111820 55%, #0d1218 100%);
            color: var(--mix-text);
        }

        [data-testid="stSidebar"] {
            background: #0b1016;
            border-right: 1px solid var(--mix-border);
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        .block-container {
            padding-top: 3.25rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(180deg, var(--mix-panel) 0%, #111820 100%);
            border: 1px solid var(--mix-border);
            border-radius: 8px;
            padding: 0.9rem 1rem;
            min-height: 104px;
        }

        div[data-testid="stMetricLabel"] {
            color: var(--mix-muted);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }

        div[data-testid="stMetricValue"] {
            color: var(--mix-text);
            font-size: 1.45rem;
            line-height: 1.15;
        }

        div[data-testid="stMetricDelta"] {
            color: var(--mix-accent);
            font-size: 0.86rem;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--mix-border);
            border-radius: 8px;
            overflow: hidden;
        }

        .mix-page-kicker {
            color: var(--mix-accent);
            display: block;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1.35;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-top: 0.25rem;
            margin-bottom: 0.25rem;
        }

        .mix-page-title {
            display: block;
            font-size: 2rem;
            line-height: 1.12;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .mix-page-subtitle {
            color: var(--mix-muted);
            margin-bottom: 1.25rem;
            max-width: 860px;
        }

        .mix-section-title {
            color: var(--mix-text);
            font-size: 1.12rem;
            font-weight: 750;
            margin: 1.4rem 0 0.55rem 0;
        }

        .mix-section-caption {
            color: var(--mix-muted);
            margin-top: -0.35rem;
            margin-bottom: 0.7rem;
        }

        .mix-badge {
            display: inline-block;
            border: 1px solid var(--mix-border);
            background: var(--mix-panel-soft);
            color: var(--mix-muted);
            border-radius: 999px;
            padding: 0.2rem 0.55rem;
            font-size: 0.78rem;
            margin-right: 0.35rem;
        }

        .mix-winner {
            color: var(--mix-accent);
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, subtitle=None, kicker=None):
    if kicker:
        st.markdown(f"<div class='mix-page-kicker'>{kicker}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='mix-page-title'>{title}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f"<div class='mix-page-subtitle'>{subtitle}</div>",
            unsafe_allow_html=True,
        )


def section_title(title, caption=None):
    st.markdown(f"<div class='mix-section-title'>{title}</div>", unsafe_allow_html=True)
    if caption:
        st.markdown(
            f"<div class='mix-section-caption'>{caption}</div>",
            unsafe_allow_html=True,
        )


def stat_card(column, label, value, detail=None):
    column.metric(label, value, detail)


def dataframe(data, *, column_config=None, column_order=None, height="content"):
    kwargs = {
        "data": data,
        "width": "stretch",
        "height": height,
        "hide_index": True,
    }
    if column_config is not None:
        kwargs["column_config"] = column_config
    if column_order is not None:
        kwargs["column_order"] = column_order

    st.dataframe(**kwargs)


def default_column_config():
    return {
        "player": st.column_config.TextColumn("Player", pinned=True),
        "team": st.column_config.TextColumn("Team"),
        "match": st.column_config.TextColumn("Match", pinned=True),
        "map": st.column_config.TextColumn("Map"),
        "map_name": st.column_config.TextColumn("Map"),
        "Map%": st.column_config.NumberColumn("Map share", format="%.1f%%"),
        "maps": st.column_config.NumberColumn("Maps", format="%d"),
        "matches": st.column_config.NumberColumn("Maps", format="%d"),
        "kills": st.column_config.NumberColumn("Kills", format="%d"),
        "deaths": st.column_config.NumberColumn("Deaths", format="%d"),
        "K-D": st.column_config.NumberColumn("K-D", format="%+d"),
        "K/D": st.column_config.NumberColumn("K/D", format="%.2f"),
        "DMG/map": st.column_config.NumberColumn("DMG/map", format="%d"),
        "damage": st.column_config.NumberColumn("Damage", format="%d"),
        "Kills/map": st.column_config.NumberColumn("Kills/map", format="%.1f"),
        "Deaths/map": st.column_config.NumberColumn("Deaths/map", format="%.1f"),
        "K-D/map": st.column_config.NumberColumn("K-D/map", format="%+.1f"),
        "HS%": st.column_config.NumberColumn("HS%", format="%.1f%%"),
        "Accuracy%": st.column_config.NumberColumn("Accuracy", format="%.1f%%"),
        "Entry%": st.column_config.NumberColumn("Entry", format="%.1f%%"),
        "Clutch%": st.column_config.NumberColumn("Clutch", format="%.1f%%"),
        "Clutches": st.column_config.NumberColumn("Clutches", format="%d"),
        "Flash Ast/map": st.column_config.NumberColumn("Flash/map", format="%.1f"),
        "Util DMG/map": st.column_config.NumberColumn("Util/map", format="%d"),
        "Assists/map": st.column_config.NumberColumn("Assists/map", format="%.1f"),
        "Enemies Flashed/map": st.column_config.NumberColumn("Flashed/map", format="%.1f"),
        "Entries/map": st.column_config.NumberColumn("Entries/map", format="%.1f"),
        "Entry Wins/map": st.column_config.NumberColumn("Entry wins/map", format="%.1f"),
        "Clutch Attempts/map": st.column_config.NumberColumn("Clutch att/map", format="%.1f"),
        "Clutches/map": st.column_config.NumberColumn("Clutches/map", format="%.1f"),
        "assists": st.column_config.NumberColumn("Assists", format="%d"),
        "flash_successes": st.column_config.NumberColumn("Flash ast", format="%d"),
        "enemies_flashed": st.column_config.NumberColumn("Flashed", format="%d"),
        "utility_damage": st.column_config.NumberColumn("Util dmg", format="%d"),
        "entry_count": st.column_config.NumberColumn("Entries", format="%d"),
        "entry_wins": st.column_config.NumberColumn("Entry wins", format="%d"),
        "entries": st.column_config.NumberColumn("Entries", format="%d"),
        "entry wins": st.column_config.NumberColumn("Entry wins", format="%d"),
        "flash ast": st.column_config.NumberColumn("Flash ast", format="%d"),
        "flashed": st.column_config.NumberColumn("Flashed", format="%d"),
        "util dmg": st.column_config.NumberColumn("Util dmg", format="%d"),
    }
