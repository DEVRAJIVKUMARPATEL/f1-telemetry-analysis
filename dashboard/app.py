import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from loader import SESSION_TYPES, get_driver_abbreviations, get_schedule, load_session
from analysis import compare_drivers, get_fastest_lap_telemetry, get_lap_times

st.set_page_config(
    page_title="F1 Telemetry Analysis",
    page_icon="🏎️",
    layout="wide",
)

st.title("🏎️ F1 Telemetry Analysis")

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Session Selection")

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

    load_btn = st.button("Load Session", type="primary", use_container_width=True)

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
    st.header("Driver Selection")
    driver1 = st.selectbox("Driver 1", drivers, index=0)
    driver2 = st.selectbox("Driver 2", drivers, index=min(1, len(drivers) - 1))

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["📈 Lap Times", "⚡ Speed Trace", "🔁 Driver Comparison"])

# ── Tab 1: Lap Time Progression ───────────────────────────────────────────────

with tab1:
    st.subheader(f"Lap Time Progression — {year} {race} {session_label}")

    col1, col2 = st.columns(2)
    show_d1 = col1.checkbox(f"Show {driver1}", value=True)
    show_d2 = col2.checkbox(f"Show {driver2}", value=True)

    fig = go.Figure()

    def add_lap_trace(drv: str, color: str, show: bool):
        if not show:
            return
        try:
            df = get_lap_times(session, drv)
            if df.empty:
                st.warning(f"No lap time data for {drv}.")
                return
            fig.add_trace(
                go.Scatter(
                    x=df["LapNumber"],
                    y=df["LapTimeSeconds"],
                    mode="lines+markers",
                    name=drv,
                    line=dict(color=color, width=2),
                    marker=dict(size=5),
                    hovertemplate=(
                        f"<b>{drv}</b><br>"
                        "Lap %{x}<br>"
                        "Time: %{y:.3f}s<extra></extra>"
                    ),
                )
            )
        except Exception as e:
            st.warning(f"Could not load lap times for {drv}: {e}")

    add_lap_trace(driver1, "#E8002D", show_d1)
    add_lap_trace(driver2, "#0090D0", show_d2)

    fig.update_layout(
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode="x unified",
        height=500,
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Speed Trace (fastest lap) ─────────────────────────────────────────

with tab2:
    st.subheader(f"Fastest Lap Speed Trace — {driver1}")

    try:
        tel = get_fastest_lap_telemetry(session, driver1)

        fig2 = go.Figure()
        fig2.add_trace(
            go.Scatter(
                x=tel["Distance"],
                y=tel["Speed"],
                mode="lines",
                name="Speed",
                line=dict(color="#E8002D", width=2),
                hovertemplate="Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>",
            )
        )
        fig2.update_layout(
            xaxis_title="Distance (m)",
            yaxis_title="Speed (km/h)",
            height=480,
            template="plotly_dark",
            hovermode="x unified",
        )
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load telemetry for {driver1}: {e}")

# ── Tab 3: Driver Comparison ──────────────────────────────────────────────────

with tab3:
    st.subheader(f"Fastest Lap Comparison — {driver1} vs {driver2}")

    if driver1 == driver2:
        st.warning("Select two different drivers to compare.")
    else:
        try:
            tel1, tel2 = compare_drivers(session, driver1, driver2)

            fig3 = make_subplots(
                rows=3,
                cols=1,
                shared_xaxes=True,
                subplot_titles=("Speed (km/h)", "Throttle (%)", "Brake"),
                vertical_spacing=0.08,
            )

            def add_comparison_traces(fig, tel, drv, color, showlegend=True):
                kw = dict(mode="lines", line=dict(color=color, width=1.8), legendgroup=drv)
                fig.add_trace(
                    go.Scatter(
                        x=tel["Distance"], y=tel["Speed"],
                        name=drv, showlegend=showlegend,
                        hovertemplate=f"{drv}: %{{y:.1f}} km/h<extra></extra>",
                        **kw,
                    ),
                    row=1, col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=tel["Distance"], y=tel["Throttle"],
                        name=drv, showlegend=False,
                        hovertemplate=f"{drv}: %{{y:.0f}}%<extra></extra>",
                        **kw,
                    ),
                    row=2, col=1,
                )
                # Brake is boolean (0/1) in FastF1; display as filled area for clarity
                fig.add_trace(
                    go.Scatter(
                        x=tel["Distance"], y=tel["Brake"].astype(float),
                        name=drv, showlegend=False,
                        fill="tozeroy",
                        fillcolor=color.replace(")", ", 0.25)").replace("rgb", "rgba") if color.startswith("rgb") else color,
                        line=dict(color=color, width=1),
                        hovertemplate=f"{drv} braking: %{{y}}<extra></extra>",
                        legendgroup=drv,
                    ),
                    row=3, col=1,
                )

            add_comparison_traces(fig3, tel1, driver1, "#E8002D", showlegend=True)
            add_comparison_traces(fig3, tel2, driver2, "#0090D0", showlegend=True)

            fig3.update_layout(
                height=700,
                template="plotly_dark",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            fig3.update_xaxes(title_text="Distance (m)", row=3, col=1)
            fig3.update_yaxes(title_text="km/h", row=1, col=1)
            fig3.update_yaxes(title_text="%", row=2, col=1)
            fig3.update_yaxes(title_text="On/Off", row=3, col=1, tickvals=[0, 1])

            st.plotly_chart(fig3, use_container_width=True)

        except Exception as e:
            st.error(f"Could not load comparison data: {e}")
