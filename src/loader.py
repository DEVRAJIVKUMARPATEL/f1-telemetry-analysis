import fastf1
import pandas as pd
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

SESSION_TYPES = {
    "Race": "R",
    "Qualifying": "Q",
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Sprint": "S",
    "Sprint Qualifying": "SQ",
}


def get_schedule(year: int) -> pd.DataFrame:
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return schedule[schedule["EventName"].notna()].reset_index(drop=True)


def load_session(year: int, race: str, session_type: str) -> fastf1.core.Session:
    session = fastf1.get_session(year, race, session_type)
    session.load(telemetry=True, laps=True, weather=False, messages=False)
    return session


def get_driver_abbreviations(session: fastf1.core.Session) -> list[str]:
    abbrevs = []
    for number in session.drivers:
        try:
            abbrevs.append(session.get_driver(number)["Abbreviation"])
        except Exception:
            pass
    return sorted(abbrevs)
