import pandas as pd
import fastf1


def get_lap_times(session: fastf1.core.Session, driver: str) -> pd.DataFrame:
    laps = session.laps.pick_driver(driver).copy()
    laps = laps[laps["LapTime"].notna()].copy()
    laps["LapTimeSeconds"] = laps["LapTime"].dt.total_seconds()
    return laps[["LapNumber", "LapTime", "LapTimeSeconds"]].reset_index(drop=True)


def get_fastest_lap_telemetry(session: fastf1.core.Session, driver: str) -> pd.DataFrame:
    laps = session.laps.pick_driver(driver)
    fastest = laps.pick_fastest()
    telemetry = fastest.get_telemetry()
    return telemetry[["Distance", "Speed", "Throttle", "Brake", "nGear", "RPM"]].copy()


def compare_drivers(
    session: fastf1.core.Session, driver1: str, driver2: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tel1 = get_fastest_lap_telemetry(session, driver1)
    tel2 = get_fastest_lap_telemetry(session, driver2)
    return tel1, tel2
