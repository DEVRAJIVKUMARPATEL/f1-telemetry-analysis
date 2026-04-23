import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from loader import SESSION_TYPES, get_driver_abbreviations, get_schedule, load_session
from analysis import compare_drivers, get_fastest_lap_telemetry, get_lap_times

st.set_page_config(
    page_title="F1 Telemetry Analysis",
    page_icon="🏎️",
    layout="wide",
)

# ── F1 Color Theme & Team Colors ─────────────────────────────────────────────
F1_RED = "#E8002D"
F1_WHITE = "#FFFFFF"
F1_BLACK = "#15151E"

TEAM_COLORS = {
    "Red Bull Racing": "#0600EF",
    "Ferrari": "#E8002D",
    "Mercedes": "#00D2BE",
    "McLaren": "#FF8700",
    "Aston Martin": "#006F62",
    "Alpine": "#0082FA",
    "Alfatauri": "#2B4562",
    "Alfa Romeo": "#900000",
    "Haas": "#FFFFFF",
    "Williams": "#005AFF",
}

DRIVER_NATIONALITIES = {
    "VER": "🇳🇱", "HAM": "🇬🇧", "ALO": "🇪🇸", "STE": "🇫🇮",
    "LEC": "🇲🇦", "SAI": "🇲🇽", "RUS": "🇩🇪", "NOR": "🇬🇧",
    "PIN": "🇲🇨", "PIA": "🇯🇵", "MAG": "🇩🇰", "TSU": "🇯🇵",
    "BOT": "🇫🇮", "ZHO": "🇨🇳", "GAS": "🇫🇷", "HUL": "🇩🇪",
    "OCO": "🇫🇷", "OLL": "🇨🇦", "RIC": "🇦🇺", "BER": "🇲🇽",
    "DEV": "🇬🇧", "VET": "🇩🇪", "LAT": "🇨🇴", "ROG": "🇨🇭",
}

def get_driver_team(session, driver_abbr):
    """Get driver's team name from session."""
    try:
        for num in session.drivers:
            driver_info = session.get_driver(num)
            if driver_info["Abbreviation"] == driver_abbr:
                return driver_info["TeamName"]
    except:
        pass
    return "Unknown"

def get_team_color(session, driver_abbr):
    """Get team color for a driver."""
    team = get_driver_team(session, driver_abbr)
    return TEAM_COLORS.get(team, "#888888")

def get_nationality_flag(driver_abbr):
    """Get nationality flag for driver."""
    return DRIVER_NATIONALITIES.get(driver_abbr, "🏁")

st.markdown("""
    <style>
    .hero-banner {
        background: linear-gradient(135deg, #E8002D 0%, #15151E 100%);
        padding: 2rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: bold;
    }
    .hero-banner p {
        margin: 0.5rem 0 0 0;
        font-size: 1.2rem;
        opacity: 0.9;
    }
    .metric-card {
        background: linear-gradient(135deg, #1f1f2e 0%, #15151e 100%);
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #E8002D;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #E8002D;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #999;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .sidebar-header {
        font-weight: bold;
        font-size: 1.1rem;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🏁 F1 Telemetry Analysis")
    st.divider()

    st.markdown('<div class="sidebar-header">📅 Session Selection</div>', unsafe_allow_html=True)

    year = st.selectbox("Year", list(range(2024, 2017, -1)), index=0)

    @st.cache_data(show_spinner="Loading calendar…")
    def fetch_schedule(y: int):
        return get_schedule(y)

    try:
        schedule = fetch_schedule(year)
        race_names = schedule["EventName"].tolist()
    except Exception as e:
        st.error(f"Could not load schedule: {e}")
        st.stop()

    race = st.selectbox("Grand Prix", race_names)
    session_label = st.selectbox("Session", list(SESSION_TYPES.keys()), index=0)
    session_type = SESSION_TYPES[session_label]

    load_btn = st.button("🚀 Load Session", type="primary", use_container_width=True)

# ── Session loading ───────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading session data (this may take a moment)…")
def fetch_session(y, r, s):
    return load_session(y, r, s)


if "session" not in st.session_state:
    st.session_state.session = None
    st.session_state.session_key = None

current_key = (year, race, session_type)

if load_btn:
    try:
        with st.spinner("Fetching session from FastF1…"):
            st.session_state.session = fetch_session(year, race, session_type)
            st.session_state.session_key = current_key
        st.success(f"Loaded: {year} {race} — {session_label}")
    except Exception as e:
        st.error(f"Failed to load session: {e}")
        st.session_state.session = None

session = st.session_state.session

if session is None:
    st.info("Select a year, Grand Prix, and session in the sidebar, then click **Load Session**.")
    st.stop()

# ── Driver selection (after session is loaded) ───────────────────────────────

try:
    drivers = get_driver_abbreviations(session)
except Exception as e:
    st.error(f"Could not retrieve drivers: {e}")
    st.stop()

with st.sidebar:
    st.divider()
    st.markdown('<div class="sidebar-header">👥 Driver Selection</div>', unsafe_allow_html=True)
    driver1 = st.selectbox("Driver 1", drivers, index=0, format_func=lambda d: f"{get_nationality_flag(d)} {d}")
    driver2 = st.selectbox("Driver 2", drivers, index=min(1, len(drivers) - 1), format_func=lambda d: f"{get_nationality_flag(d)} {d}")

# ── Hero Banner ──────────────────────────────────────────────────────────────

st.markdown(f"""
    <div class="hero-banner">
        <h1>🏁 {year} {race}</h1>
        <p>{session_label} • F1 Telemetry Analysis</p>
    </div>
""", unsafe_allow_html=True)

# ── Metric Cards ──────────────────────────────────────────────────────────────

def get_driver_metrics(session, driver):
    """Calculate metrics for a driver."""
    try:
        laps = session.laps.pick_driver(driver).copy()
        laps = laps[laps["LapTime"].notna()].copy()

        fastest_lap = laps["LapTime"].min()
        avg_lap = laps["LapTime"].mean()
        total_laps = len(laps)

        return {
            "fastest": str(fastest_lap).split(".")[0],
            "average": str(avg_lap).split(".")[0],
            "total": total_laps,
        }
    except Exception as e:
        return {"fastest": "N/A", "average": "N/A", "total": 0}

metrics1 = get_driver_metrics(session, driver1)
metrics2 = get_driver_metrics(session, driver2)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Fastest Lap</div>
            <div class="metric-value">{get_nationality_flag(driver1)} {driver1}</div>
            <div style="font-size: 1.1rem; color: #fff;">{metrics1['fastest']}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Lap Time</div>
            <div class="metric-value" style="color: #40a9ff;">{metrics1['average']}</div>
            <div style="font-size: 0.9rem; color: #999;">for {driver1}</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Laps</div>
            <div class="metric-value" style="color: #52c41a;">{metrics1['total']}</div>
            <div style="font-size: 0.9rem; color: #999;">completed</div>
        </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Fastest Lap</div>
            <div class="metric-value">{get_nationality_flag(driver2)} {driver2}</div>
            <div style="font-size: 1.1rem; color: #fff;">{metrics2['fastest']}</div>
        </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Lap Time</div>
            <div class="metric-value" style="color: #40a9ff;">{metrics2['average']}</div>
            <div style="font-size: 0.9rem; color: #999;">for {driver2}</div>
        </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Laps</div>
            <div class="metric-value" style="color: #52c41a;">{metrics2['total']}</div>
            <div style="font-size: 0.9rem; color: #999;">completed</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(["📈 Lap Times", "⚡ Speed Trace", "🔁 Driver Comparison", "🛞 Tyre Strategy"])

# ── Tab 1: Lap Time Progression ───────────────────────────────────────────────

with tab1:
    st.subheader(f"Lap Time Progression — {year} {race} {session_label}")

    col1, col2 = st.columns(2)
    show_d1 = col1.checkbox(f"Show {driver1}", value=True)
    show_d2 = col2.checkbox(f"Show {driver2}", value=True)

    fig = go.Figure()

    def add_lap_trace(drv: str, show: bool):
        if not show:
            return
        try:
            color = get_team_color(session, drv)
            df = get_lap_times(session, drv)
            if df.empty:
                st.warning(f"No lap time data for {drv}.")
                return
            fig.add_trace(
                go.Scatter(
                    x=df["LapNumber"],
                    y=df["LapTimeSeconds"],
                    mode="lines+markers",
                    name=f"{get_nationality_flag(drv)} {drv}",
                    line=dict(color=color, width=2),
                    marker=dict(size=5),
                    hovertemplate=(
                        f"<b>{get_nationality_flag(drv)} {drv}</b><br>"
                        "Lap %{x}<br>"
                        "Time: %{y:.3f}s<extra></extra>"
                    ),
                )
            )
        except Exception as e:
            st.warning(f"Could not load lap times for {drv}: {e}")

    add_lap_trace(driver1, show_d1)
    add_lap_trace(driver2, show_d2)

    fig.update_layout(
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode="x unified",
        height=500,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor=F1_BLACK,
        paper_bgcolor=F1_BLACK,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Speed Trace (fastest lap) ─────────────────────────────────────────

with tab2:
    st.subheader(f"⚡ Fastest Lap Speed Trace — {get_nationality_flag(driver1)} {driver1}")

    try:
        tel = get_fastest_lap_telemetry(session, driver1)
        color = get_team_color(session, driver1)

        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=tel["Distance"],
                y=tel["Speed"],
                mode="lines",
                name="Speed",
                line=dict(color=color, width=2),
                hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>",
            )
        )
        fig2.update_layout(
            xaxis_title="Distance (m)",
            yaxis_title="Speed (km/h)",
            height=480,
            template="plotly_dark",
            hovermode="x unified",
            plot_bgcolor=F1_BLACK,
            paper_bgcolor=F1_BLACK,
        )
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load telemetry for {driver1}: {e}")

# ── Tab 3: Driver Comparison ──────────────────────────────────────────────────

with tab3:
    st.subheader(f"🔁 Fastest Lap Comparison — {get_nationality_flag(driver1)} {driver1} vs {get_nationality_flag(driver2)} {driver2}")

    if driver1 == driver2:
        st.warning("Select two different drivers to compare.")
    else:
        try:
            tel1, tel2 = compare_drivers(session, driver1, driver2)
            color1 = get_team_color(session, driver1)
            color2 = get_team_color(session, driver2)

            fig3 = make_subplots(
                rows=3,
                cols=1,
                shared_xaxes=True,
                subplot_titles=("Speed (km/h)", "Throttle (%)", "Brake"),
                vertical_spacing=0.08,
            )

            def add_comparison_traces(fig, tel, drv, color, showlegend=True):
                flag = get_nationality_flag(drv)
                kw = dict(mode="lines", line=dict(color=color, width=1.8), legendgroup=drv)
                fig.add_trace(
                    go.Scatter(
                        x=tel["Distance"], y=tel["Speed"],
                        name=f"{flag} {drv}", showlegend=showlegend,
                        hovertemplate=f"{flag} {drv}: %{{y:.1f}} km/h<extra></extra>",
                        **kw,
                    ),
                    row=1, col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=tel["Distance"], y=tel["Throttle"],
                        name=f"{flag} {drv}", showlegend=False,
                        hovertemplate=f"{flag} {drv}: %{{y:.0f}}%<extra></extra>",
                        **kw,
                    ),
                    row=2, col=1,
                )
                # Brake is boolean (0/1) in FastF1; display as filled area for clarity
                fig.add_trace(
                    go.Scatter(
                        x=tel["Distance"], y=tel["Brake"].astype(float),
                        name=f"{flag} {drv}", showlegend=False,
                        fill="tozeroy",
                        fillcolor=color.replace(")", ", 0.25)").replace("rgb", "rgba") if color.startswith("rgb") else color,
                        line=dict(color=color, width=1),
                        hovertemplate=f"{flag} {drv} braking: %{{y}}<extra></extra>",
                        legendgroup=drv,
                    ),
                    row=3, col=1,
                )

            add_comparison_traces(fig3, tel1, driver1, color1, showlegend=True)
            add_comparison_traces(fig3, tel2, driver2, color2, showlegend=True)

            fig3.update_layout(
                height=700,
                template="plotly_dark",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                plot_bgcolor=F1_BLACK,
                paper_bgcolor=F1_BLACK,
            )
            fig3.update_xaxes(title_text="Distance (m)", row=3, col=1)
            fig3.update_yaxes(title_text="km/h", row=1, col=1)
            fig3.update_yaxes(title_text="%", row=2, col=1)
            fig3.update_yaxes(title_text="On/Off", row=3, col=1, tickvals=[0, 1])

            st.plotly_chart(fig3, use_container_width=True)

        except Exception as e:
            st.error(f"Could not load comparison data: {e}")

# ── Tab 4: Tyre Strategy ──────────────────────────────────────────────────────

with tab4:
    st.subheader("🛞 Pit Stop & Tyre Strategy")

    try:
        all_drivers = drivers

        # Create pit stop data for all drivers
        pit_data = []

        for driver in all_drivers:
            try:
                laps = session.laps.pick_driver(driver).copy()
                pit_stops = laps[laps["PitOutTime"].notna()][["LapNumber", "PitOutTime", "Compound"]].copy()

                if not pit_stops.empty:
                    for idx, row in pit_stops.iterrows():
                        pit_data.append({
                            "Driver": driver,
                            "Lap": int(row["LapNumber"]),
                            "Tyre": row["Compound"] if pd.notna(row["Compound"]) else "Unknown",
                            "Flag": get_nationality_flag(driver),
                            "Team": get_driver_team(session, driver),
                            "Color": get_team_color(session, driver),
                        })
            except Exception:
                continue

        if pit_data:
            pit_df = pd.DataFrame(pit_data)

            # Create scatter plot for pit stops
            fig4 = go.Figure()

            tyre_colors = {
                "SOFT": "#FF0000",
                "MEDIUM": "#FFFF00",
                "HARD": "#FFFFFF",
                "INTERMEDIATE": "#009900",
                "WET": "#0000FF",
            }

            for driver in sorted(pit_df["Driver"].unique()):
                driver_pits = pit_df[pit_df["Driver"] == driver]
                color = driver_pits.iloc[0]["Color"]
                flag = driver_pits.iloc[0]["Flag"]

                fig4.add_trace(
                    go.Scatter(
                        x=driver_pits["Lap"],
                        y=[driver] * len(driver_pits),
                        mode="markers",
                        name=f"{flag} {driver}",
                        marker=dict(size=12, color=color, line=dict(width=2, color="white")),
                        text=[f"{flag} {driver}<br>Lap {row['Lap']}<br>Tyre: {row['Tyre']}"
                              for _, row in driver_pits.iterrows()],
                        hovertemplate="%{text}<extra></extra>",
                    )
                )

            fig4.update_layout(
                xaxis_title="Lap Number",
                yaxis_title="Driver",
                height=400 + (len(all_drivers) * 15),
                template="plotly_dark",
                hovermode="closest",
                plot_bgcolor=F1_BLACK,
                paper_bgcolor=F1_BLACK,
                showlegend=True,
            )

            st.plotly_chart(fig4, use_container_width=True)

            # Show pit stop table
            st.subheader("Pit Stop Summary")
            display_df = pit_df[["Driver", "Lap", "Tyre"]].copy()
            display_df["Driver"] = display_df["Driver"].apply(lambda d: f"{get_nationality_flag(d)} {d}")
            display_df = display_df.sort_values("Lap")

            st.dataframe(display_df, use_container_width=True, hide_index=True)

        else:
            st.info("No pit stop data available for this session.")

    except Exception as e:
        st.error(f"Could not load pit stop data: {e}")
