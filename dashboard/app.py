import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

from loader import SESSION_TYPES, get_driver_abbreviations, get_schedule, load_session
from analysis import compare_drivers, get_fastest_lap_telemetry, get_fastest_lap_telemetry_with_position, get_lap_times

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

def format_lap_time(timedelta_obj):
    """Convert pandas Timedelta to MM:SS.mmm format."""
    try:
        total_seconds = timedelta_obj.total_seconds()
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:06.3f}"
    except:
        return "N/A"

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

    year = st.selectbox("Year", list(range(2026, 2017, -1)), index=0, key="year_selector")

    @st.cache_data(show_spinner="Loading calendar…")
    def fetch_schedule(y: int):
        return get_schedule(y)

    try:
        schedule = fetch_schedule(year)
        race_names = schedule["EventName"].tolist()
    except Exception as e:
        st.error(f"Could not load schedule: {e}")
        st.stop()

    race = st.selectbox("Grand Prix", race_names, key="race_selector")
    session_label = st.selectbox("Session", list(SESSION_TYPES.keys()), index=0, key="session_selector")
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

# Check if we have valid driver data
if not drivers or all(d is None for d in drivers):
    st.warning("⏳ Data Not Available")
    st.info("This session data is not yet available from FastF1. Please try a completed race or select a different session.")
    st.stop()

with st.sidebar:
    st.divider()
    st.markdown('<div class="sidebar-header">👥 Driver Selection</div>', unsafe_allow_html=True)
    driver1 = st.selectbox("Driver 1", drivers, index=0, format_func=lambda d: f"{get_nationality_flag(d)} {d}", key="driver1_selector")
    driver2 = st.selectbox("Driver 2", drivers, index=min(1, len(drivers) - 1), format_func=lambda d: f"{get_nationality_flag(d)} {d}", key="driver2_selector")

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
            "fastest": format_lap_time(fastest_lap),
            "average": format_lap_time(avg_lap),
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📈 Lap Times", "⚡ Speed Trace", "🔁 Driver Comparison", "🛞 Tyre Strategy", "🗺️ Track Map", "🎬 Race Replay"])

# ── Tab 1: Lap Time Progression ───────────────────────────────────────────────

with tab1:
    st.subheader(f"Lap Time Progression — {year} {race} {session_label}")

    col1, col2 = st.columns(2)
    show_d1 = col1.checkbox(f"Show {driver1}", value=True, key="show_d1")
    show_d2 = col2.checkbox(f"Show {driver2}", value=True, key="show_d2")

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

# ── Tab 5: Track Map ──────────────────────────────────────────────────────────

with tab5:
    st.subheader("🗺️ Track Map — Speed Visualization")

    try:
        tel = get_fastest_lap_telemetry_with_position(session, driver1)

        # Check if we have X and Y coordinates
        if "X" not in tel.columns or "Y" not in tel.columns:
            st.warning("Track map data (X, Y coordinates) is not available for this session.")
        else:
            # Get fastest lap time for display
            fastest_lap_time = get_lap_times(session, driver1)
            if not fastest_lap_time.empty:
                fastest_time = fastest_lap_time["LapTime"].min()
                fastest_time_str = format_lap_time(fastest_time)
            else:
                fastest_time_str = "N/A"

            # Create track map visualization
            fig_track = go.Figure()

            # Add the track with speed coloring
            fig_track.add_trace(
                go.Scatter(
                    x=tel["X"],
                    y=tel["Y"],
                    mode="markers",
                    marker=dict(
                        size=8,
                        color=tel["Speed"],
                        colorscale=[
                            [0, "#FF0000"],      # Red - slow
                            [0.5, "#FFFF00"],    # Yellow - medium
                            [1, "#00FF00"],      # Green - fast
                        ],
                        showscale=True,
                        colorbar=dict(
                            title="Speed<br>(km/h)",
                            thickness=15,
                            len=0.7,
                        ),
                        line=dict(width=0.5, color="rgba(255, 255, 255, 0.3)"),
                    ),
                    text=[f"Speed: {s:.1f} km/h<br>Distance: {d:.0f}m"
                          for s, d in zip(tel["Speed"], tel["Distance"])],
                    hovertemplate="%{text}<extra></extra>",
                    name="Track",
                )
            )

            # Add start/finish line marker
            if len(tel) > 0:
                fig_track.add_trace(
                    go.Scatter(
                        x=[tel["X"].iloc[0]],
                        y=[tel["Y"].iloc[0]],
                        mode="markers+text",
                        marker=dict(size=15, color="white", symbol="square",
                                  line=dict(width=2, color="black")),
                        text=["S/F"],
                        textposition="top center",
                        name="Start/Finish",
                        hovertemplate="Start/Finish Line<extra></extra>",
                    )
                )

            driver_team = get_driver_team(session, driver1)
            team_color = get_team_color(session, driver1)

            fig_track.update_layout(
                title=dict(
                    text=f"{get_nationality_flag(driver1)} {driver1} • {driver_team}<br><sub>Fastest Lap: {fastest_time_str}</sub>",
                    x=0.5,
                    xanchor="center",
                ),
                xaxis_title="X Position (m)",
                yaxis_title="Y Position (m)",
                height=700,
                template="plotly_dark",
                plot_bgcolor=F1_BLACK,
                paper_bgcolor=F1_BLACK,
                hovermode="closest",
                showlegend=True,
                xaxis=dict(scaleanchor="y", scaleratio=1),
                yaxis=dict(scaleanchor="x", scaleratio=1),
            )

            st.plotly_chart(fig_track, use_container_width=True)

            # Add legend explanation
            st.markdown("""
            **Track Map Legend:**
            - 🟩 **Green** - High speed areas (acceleration zones)
            - 🟨 **Yellow** - Medium speed areas (mid-corner)
            - 🔴 **Red** - Low speed areas (braking/tight corners)
            - ⬜ **S/F** - Start/Finish line
            """)

    except Exception as e:
        st.error(f"Could not load track map: {e}")

# ── Tab 6: Race Replay ────────────────────────────────────────────────────────

with tab6:
    st.subheader("🎬 Race Replay — Lap-by-Lap Position Tracker")

    selected_drivers = st.multiselect(
        "Select Drivers",
        options=drivers,
        default=drivers[:5] if len(drivers) >= 5 else drivers,
        format_func=lambda d: f"{get_nationality_flag(d)} {d}",
        key="replay_drivers",
    )

    if not selected_drivers:
        st.info("Select at least one driver to view their position.")
    else:
        # Determine lap range from session data
        try:
            lap_nums = sorted(session.laps["LapNumber"].dropna().unique().astype(int).tolist())
            min_lap, max_lap = lap_nums[0], lap_nums[-1]
        except Exception:
            min_lap, max_lap = 1, 56

        selected_lap = st.slider(
            "Lap Number",
            min_value=min_lap,
            max_value=max_lap,
            value=min_lap,
            step=1,
            key="replay_lap_slider",
        )

        fig_replay = go.Figure()

        # Draw track outline from first driver that has position data
        for ref_drv in selected_drivers:
            try:
                ref_tel = get_fastest_lap_telemetry_with_position(session, ref_drv)
                if "X" in ref_tel.columns and "Y" in ref_tel.columns and len(ref_tel) > 0:
                    fig_replay.add_trace(
                        go.Scatter(
                            x=ref_tel["X"],
                            y=ref_tel["Y"],
                            mode="lines",
                            line=dict(color="rgba(180,180,180,0.25)", width=14),
                            showlegend=False,
                            hoverinfo="skip",
                            name="_track",
                        )
                    )
                    break
            except Exception:
                continue

        # Place each driver as a dot at their lap-start position
        any_plotted = False
        for drv in selected_drivers:
            try:
                drv_laps = session.laps.pick_driver(drv)
                lap_row = drv_laps[drv_laps["LapNumber"] == selected_lap]
                if lap_row.empty:
                    continue
                tel = lap_row.iloc[0].get_telemetry()
                if tel is None or tel.empty:
                    continue
                if "X" not in tel.columns or "Y" not in tel.columns:
                    continue
                x_pos = float(tel["X"].iloc[0])
                y_pos = float(tel["Y"].iloc[0])
                color = get_team_color(session, drv)
                flag = get_nationality_flag(drv)
                fig_replay.add_trace(
                    go.Scatter(
                        x=[x_pos],
                        y=[y_pos],
                        mode="markers+text",
                        marker=dict(
                            size=18,
                            color=color,
                            line=dict(width=2, color="white"),
                        ),
                        text=[drv],
                        textposition="top center",
                        textfont=dict(color="white", size=11),
                        name=f"{flag} {drv}",
                        hovertemplate=(
                            f"<b>{flag} {drv}</b><br>"
                            f"Lap {selected_lap}<extra></extra>"
                        ),
                    )
                )
                any_plotted = True
            except Exception:
                continue

        if any_plotted:
            fig_replay.update_layout(
                title=dict(
                    text=f"Driver Positions — Lap {selected_lap}",
                    x=0.5,
                    xanchor="center",
                    font=dict(size=16),
                ),
                height=700,
                template="plotly_dark",
                plot_bgcolor=F1_BLACK,
                paper_bgcolor=F1_BLACK,
                hovermode="closest",
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(
                    scaleanchor="y",
                    scaleratio=1,
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False,
                ),
                yaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    showticklabels=False,
                ),
            )
            st.plotly_chart(fig_replay, use_container_width=True)
            st.caption("Use the Lap Number slider above to scrub through the race. Each dot marks where a driver began that lap.")
        else:
            st.info(f"No position data found for any selected driver on lap {selected_lap}.")
