from __future__ import annotations

import os
import random
import socket
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, redirect, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "training_log.db"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    ensure_dirs()
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                sport TEXT NOT NULL,
                start_time TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                distance_miles REAL NOT NULL DEFAULT 0,
                elevation_ft REAL NOT NULL DEFAULT 0,
                avg_hr INTEGER,
                avg_power INTEGER,
                intensity TEXT NOT NULL DEFAULT 'Endurance',
                rpe INTEGER NOT NULL DEFAULT 5,
                notes TEXT NOT NULL DEFAULT '',
                planned_load REAL NOT NULL DEFAULT 0,
                completed_load REAL NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS athlete_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                athlete_name TEXT NOT NULL DEFAULT 'Minghe',
                ftp INTEGER NOT NULL DEFAULT 245,
                threshold_hr INTEGER NOT NULL DEFAULT 168,
                threshold_pace_seconds INTEGER NOT NULL DEFAULT 435,
                swim_threshold_seconds_per_100 INTEGER NOT NULL DEFAULT 105
            )
            """
        )

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(workouts)").fetchall()}
        if "avg_power" not in columns:
            conn.execute("ALTER TABLE workouts ADD COLUMN avg_power INTEGER")

        settings_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(athlete_settings)").fetchall()
        }
        if "threshold_hr" not in settings_columns:
            conn.execute("ALTER TABLE athlete_settings ADD COLUMN threshold_hr INTEGER NOT NULL DEFAULT 168")
        if "threshold_pace_seconds" not in settings_columns:
            conn.execute(
                "ALTER TABLE athlete_settings ADD COLUMN threshold_pace_seconds INTEGER NOT NULL DEFAULT 435"
            )
        if "swim_threshold_seconds_per_100" not in settings_columns:
            conn.execute(
                """
                ALTER TABLE athlete_settings
                ADD COLUMN swim_threshold_seconds_per_100 INTEGER NOT NULL DEFAULT 105
                """
            )

        conn.execute(
            """
            INSERT INTO athlete_settings (
                id, athlete_name, ftp, threshold_hr, threshold_pace_seconds, swim_threshold_seconds_per_100
            )
            VALUES (1, 'Minghe', 245, 168, 435, 105)
            ON CONFLICT(id) DO NOTHING
            """
        )
        conn.commit()

    seed_workouts_if_empty()


def week_start(dt: datetime) -> datetime:
    return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)


def seconds_to_pace(seconds: float | int | None) -> str:
    if seconds is None or seconds <= 0:
        return "-"
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    remainder = total_seconds % 60
    return f"{minutes}:{remainder:02d}/mi"


def seconds_to_swim_pace(seconds: float | int | None) -> str:
    if seconds is None or seconds <= 0:
        return "-"
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    remainder = total_seconds % 60
    return f"{minutes}:{remainder:02d}/100y"


def pace_seconds(distance_miles: float, duration_minutes: int) -> int | None:
    if distance_miles <= 0 or duration_minutes <= 0:
        return None
    return int(round((duration_minutes * 60) / distance_miles))


def pace_text(distance_miles: float, duration_minutes: int) -> str:
    return seconds_to_pace(pace_seconds(distance_miles, duration_minutes))


def fetch_settings() -> dict[str, Any]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM athlete_settings WHERE id = 1").fetchone()
    assert row is not None
    settings = dict(row)
    settings["threshold_pace_text"] = seconds_to_pace(settings["threshold_pace_seconds"])
    settings["swim_threshold_text"] = seconds_to_swim_pace(settings["swim_threshold_seconds_per_100"])
    return settings


def derive_if(workout: dict[str, Any], settings: dict[str, Any]) -> float:
    sport = workout["sport"]
    duration_minutes = max(int(workout["duration_minutes"]), 1)
    if sport == "Run":
        actual_pace = pace_seconds(float(workout["distance_miles"]), duration_minutes)
        threshold_pace = settings["threshold_pace_seconds"]
        if actual_pace:
            return max(0.45, min(1.5, threshold_pace / actual_pace))
        if workout.get("avg_hr"):
            return max(0.45, min(1.35, float(workout["avg_hr"]) / settings["threshold_hr"]))
    if sport == "Bike":
        if workout.get("avg_power"):
            return max(0.4, min(1.5, float(workout["avg_power"]) / settings["ftp"]))
        if workout.get("avg_hr"):
            return max(0.45, min(1.35, float(workout["avg_hr"]) / settings["threshold_hr"]))
    if sport == "Swim":
        distance = float(workout["distance_miles"])
        if distance > 0:
            yards = distance * 1760
            sec_per_100 = (duration_minutes * 60) / max(yards / 100.0, 1)
            return max(0.45, min(1.45, settings["swim_threshold_seconds_per_100"] / sec_per_100))
    return max(0.4, min(1.3, 0.55 + int(workout["rpe"]) * 0.075))


def stress_label(sport: str) -> str:
    return {
        "Run": "rTSS",
        "Bike": "TSS",
        "Swim": "sTSS",
        "Strength": "sRPE",
    }.get(sport, "Load")


def stress_score(workout: dict[str, Any], settings: dict[str, Any]) -> float:
    duration_hours = max(float(workout["duration_minutes"]) / 60.0, 1 / 60.0)
    intensity_factor = derive_if(workout, settings)
    if workout["sport"] == "Strength":
        return round(duration_hours * float(workout["rpe"]) * 9.0, 1)
    return round(duration_hours * (intensity_factor**2) * 100.0, 1)


def efficiency_index(workout: dict[str, Any]) -> float | None:
    avg_hr = workout.get("avg_hr")
    distance = float(workout["distance_miles"])
    duration_minutes = int(workout["duration_minutes"])
    if not avg_hr or distance <= 0 or duration_minutes <= 0:
        return None
    mph = distance / (duration_minutes / 60.0)
    return round((mph * 100.0) / float(avg_hr), 2)


def zone_distribution(workout: dict[str, Any], settings: dict[str, Any]) -> list[dict[str, Any]]:
    if_value = derive_if(workout, settings)
    zones = [
        {"name": "Z1", "label": "Recovery", "pct": 0},
        {"name": "Z2", "label": "Endurance", "pct": 0},
        {"name": "Z3", "label": "Tempo", "pct": 0},
        {"name": "Z4", "label": "Threshold", "pct": 0},
        {"name": "Z5", "label": "VO2+", "pct": 0},
    ]
    if if_value < 0.75:
        pcts = [38, 42, 14, 5, 1]
    elif if_value < 0.9:
        pcts = [18, 39, 26, 13, 4]
    elif if_value < 1.02:
        pcts = [10, 20, 30, 28, 12]
    else:
        pcts = [6, 12, 20, 32, 30]
    for zone, pct in zip(zones, pcts):
        zone["pct"] = pct
    return zones


def load_score(duration_minutes: int, rpe: int, intensity: str) -> float:
    intensity_map = {
        "Recovery": 0.7,
        "Endurance": 1.0,
        "Tempo": 1.15,
        "Threshold": 1.28,
        "VO2": 1.45,
        "Race": 1.55,
        "Strength": 0.9,
    }
    factor = intensity_map.get(intensity, 1.0)
    return round((duration_minutes / 10.0) * (0.6 + rpe / 10.0) * factor, 1)


def seed_workouts_if_empty() -> None:
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM workouts").fetchone()["count"]
        if existing:
            return

        sports = ["Run", "Bike", "Swim", "Strength"]
        intensity_cycle = ["Recovery", "Endurance", "Tempo", "Threshold", "VO2", "Strength"]
        title_cycle = {
            "Run": ["Aerobic Run", "Long Run", "Hill Repeats", "Tempo Run", "Progression Run"],
            "Bike": ["Endurance Ride", "Sweet Spot Ride", "Cadence Session", "Climbing Ride"],
            "Swim": ["Technique Swim", "Threshold Swim", "Pull Session"],
            "Strength": ["Gym Session", "Mobility + Strength"],
        }
        now = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
        rows: list[tuple[Any, ...]] = []

        for i in range(56):
            day = now - timedelta(days=i)
            if day.weekday() == 6:
                continue

            sport = random.choices(sports, weights=[20, 11, 5, 4])[0]
            intensity = random.choice(intensity_cycle if sport != "Swim" else intensity_cycle[:4])
            title = random.choice(title_cycle[sport])
            duration = random.randint(35, 125) if sport != "Strength" else random.randint(35, 65)
            distance = 0.0
            elevation = 0.0
            avg_hr = None
            avg_power = None

            if sport == "Run":
                distance = round(duration / random.uniform(7.0, 9.8), 1)
                elevation = round(random.uniform(100, 1500), 0)
                avg_hr = random.randint(132, 171)
            elif sport == "Bike":
                distance = round(duration / 60.0 * random.uniform(16, 22), 1)
                elevation = round(random.uniform(250, 2400), 0)
                avg_hr = random.randint(124, 158)
                avg_power = random.randint(145, 255)
            elif sport == "Swim":
                distance = round(random.uniform(1.0, 2.8), 1)
                avg_hr = random.randint(118, 150)
            else:
                avg_hr = random.randint(102, 134)

            rpe = random.randint(3, 9)
            completed = load_score(duration, rpe, intensity)
            planned = round(completed * random.uniform(0.92, 1.08), 1)
            notes = {
                "Recovery": "Kept the effort relaxed and focused on smooth movement.",
                "Endurance": "Steady aerobic work with controlled breathing throughout.",
                "Tempo": "Built pressure through the middle and stayed composed late.",
                "Threshold": "Strong sustained work near the edge of comfort.",
                "VO2": "Short hard reps with full focus on quality.",
                "Strength": "Good movement quality and posterior-chain focus.",
            }[intensity]

            rows.append(
                (
                    title,
                    sport,
                    day.isoformat(),
                    duration,
                    distance,
                    elevation,
                    avg_hr,
                    avg_power,
                    intensity,
                    rpe,
                    notes,
                    planned,
                    completed,
                )
            )

        conn.executemany(
            """
            INSERT INTO workouts (
                title, sport, start_time, duration_minutes, distance_miles, elevation_ft,
                avg_hr, avg_power, intensity, rpe, notes, planned_load, completed_load
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()


def enrich_workout(workout: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    item = dict(workout)
    item["pace_seconds"] = pace_seconds(float(item["distance_miles"]), int(item["duration_minutes"]))
    item["pace"] = seconds_to_pace(item["pace_seconds"])
    item["intensity_factor"] = round(derive_if(item, settings), 2)
    item["stress_label"] = stress_label(item["sport"])
    item["stress_score"] = stress_score(item, settings)
    item["completed_load"] = item["stress_score"]
    item["efficiency_index"] = efficiency_index(item)
    item["zones"] = zone_distribution(item, settings)
    return item


def fetch_workouts(desc: bool = True) -> list[dict[str, Any]]:
    order = "DESC" if desc else "ASC"
    settings = fetch_settings()
    with get_db() as conn:
        rows = conn.execute(f"SELECT * FROM workouts ORDER BY start_time {order}, id {order}").fetchall()
    return [enrich_workout(dict(row), settings) for row in rows]


def build_fitness_series(workouts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_day: dict[str, float] = {}
    for workout in workouts:
        day = datetime.fromisoformat(workout["start_time"]).date().isoformat()
        by_day[day] = by_day.get(day, 0.0) + float(workout["stress_score"])

    if workouts:
        start = datetime.fromisoformat(workouts[0]["start_time"]).date()
        end = datetime.fromisoformat(workouts[-1]["start_time"]).date()
    else:
        today = datetime.now().date()
        start = today - timedelta(days=42)
        end = today

    ctl = 0.0
    atl = 0.0
    current = start
    series = []
    while current <= end:
        stress = by_day.get(current.isoformat(), 0.0)
        ctl = ctl + (stress - ctl) / 42.0
        atl = atl + (stress - atl) / 7.0
        tsb = ctl - atl
        series.append(
            {
                "date": current.isoformat(),
                "stress": round(stress, 1),
                "ctl": round(ctl, 1),
                "atl": round(atl, 1),
                "tsb": round(tsb, 1),
            }
        )
        current += timedelta(days=1)
    return series


def build_dashboard() -> dict[str, Any]:
    workouts = fetch_workouts(desc=True)
    settings = fetch_settings()
    now = datetime.now()
    this_week = week_start(now)
    prev_week = this_week - timedelta(days=7)
    four_weeks_ago = this_week - timedelta(days=21)

    current = {"distance": 0.0, "duration": 0, "stress": 0.0, "sessions": 0}
    previous = {"distance": 0.0, "duration": 0, "stress": 0.0, "sessions": 0}
    last_4 = {"distance": 0.0, "duration": 0, "stress": 0.0}
    sport_mix: dict[str, int] = {}
    weekly_map: dict[str, dict[str, Any]] = {}

    for workout in workouts:
        dt = datetime.fromisoformat(workout["start_time"])
        wkey = week_start(dt).date().isoformat()
        bucket = weekly_map.setdefault(
            wkey,
            {"week_key": wkey, "distance": 0.0, "duration": 0, "stress": 0.0, "sessions": 0},
        )
        bucket["distance"] += float(workout["distance_miles"])
        bucket["duration"] += int(workout["duration_minutes"])
        bucket["stress"] += float(workout["stress_score"])
        bucket["sessions"] += 1
        sport_mix[workout["sport"]] = sport_mix.get(workout["sport"], 0) + 1

        if dt >= this_week:
            current["distance"] += float(workout["distance_miles"])
            current["duration"] += int(workout["duration_minutes"])
            current["stress"] += float(workout["stress_score"])
            current["sessions"] += 1
        elif prev_week <= dt < this_week:
            previous["distance"] += float(workout["distance_miles"])
            previous["duration"] += int(workout["duration_minutes"])
            previous["stress"] += float(workout["stress_score"])
            previous["sessions"] += 1

        if dt >= four_weeks_ago:
            last_4["distance"] += float(workout["distance_miles"])
            last_4["duration"] += int(workout["duration_minutes"])
            last_4["stress"] += float(workout["stress_score"])

    weekly = sorted(weekly_map.values(), key=lambda item: item["week_key"])[-10:]
    for row in weekly:
        row["distance"] = round(row["distance"], 1)
        row["duration_hours"] = round(row["duration"] / 60.0, 1)
        row["stress"] = round(row["stress"], 1)

    fitness = build_fitness_series(list(reversed(workouts)))
    latest_fitness = fitness[-1] if fitness else {"ctl": 0.0, "atl": 0.0, "tsb": 0.0}

    return {
        "settings": settings,
        "headline": {
            "current_week_stress": round(current["stress"], 1),
            "current_week_distance": round(current["distance"], 1),
            "current_week_sessions": current["sessions"],
            "previous_week_stress": round(previous["stress"], 1),
            "stress_delta": round(current["stress"] - previous["stress"], 1),
            "consistency_hours": round(last_4["duration"] / 60.0 / 4.0, 1),
            "ctl": latest_fitness["ctl"],
            "atl": latest_fitness["atl"],
            "tsb": latest_fitness["tsb"],
        },
        "totals": {
            "sessions": len(workouts),
            "distance": round(sum(float(w["distance_miles"]) for w in workouts), 1),
            "stress": round(sum(float(w["stress_score"]) for w in workouts), 1),
            "last_4_distance": round(last_4["distance"], 1),
            "last_4_hours": round(last_4["duration"] / 60.0, 1),
            "last_4_stress": round(last_4["stress"], 1),
        },
        "weekly": weekly,
        "sport_mix": [{"sport": k, "count": v} for k, v in sorted(sport_mix.items(), key=lambda item: (-item[1], item[0]))],
        "recent": workouts[:6],
        "fitness": fitness[-42:],
    }


def build_log() -> dict[str, Any]:
    workouts = fetch_workouts(desc=True)
    grouped: dict[str, dict[str, Any]] = {}
    for workout in workouts:
        dt = datetime.fromisoformat(workout["start_time"])
        wk = week_start(dt)
        key = wk.date().isoformat()
        bucket = grouped.setdefault(
            key,
            {
                "week_key": key,
                "label": f"Week of {wk.strftime('%b %d, %Y')}",
                "workouts": [],
                "distance": 0.0,
                "duration": 0,
                "stress": 0.0,
            },
        )
        bucket["workouts"].append(workout)
        bucket["distance"] += float(workout["distance_miles"])
        bucket["duration"] += int(workout["duration_minutes"])
        bucket["stress"] += float(workout["stress_score"])

    weeks = sorted(grouped.values(), key=lambda item: item["week_key"], reverse=True)
    for week in weeks:
        week["distance"] = round(week["distance"], 1)
        week["duration_hours"] = round(week["duration"] / 60.0, 1)
        week["stress"] = round(week["stress"], 1)
    return {"weeks": weeks}


def build_trends() -> dict[str, Any]:
    workouts = fetch_workouts(desc=False)
    sessions = []
    rolling = []
    rolling_stress = 0.0
    for index, workout in enumerate(workouts):
        sessions.append(
            {
                "id": workout["id"],
                "date": workout["start_time"],
                "distance": workout["distance_miles"],
                "duration": workout["duration_minutes"],
                "stress": workout["stress_score"],
                "avg_hr": workout["avg_hr"],
                "rpe": workout["rpe"],
                "intensity_factor": workout["intensity_factor"],
            }
        )
        rolling_stress += float(workout["stress_score"])
        if index >= 6:
            rolling_stress -= float(workouts[index - 6]["stress_score"])
        if index >= 5:
            rolling.append({"date": workout["start_time"], "stress": round(rolling_stress, 1)})

    return {"sessions": sessions, "rolling": rolling, "fitness": build_fitness_series(workouts)}


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    init_db()

    @app.after_request
    def no_cache(response):  # type: ignore[override]
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

    @app.route("/")
    def home() -> str:
        return render_template("home.html")

    @app.route("/calendar")
    def calendar_page() -> str:
        return render_template("calendar.html")

    @app.route("/workouts/new")
    def new_workout_page() -> str:
        return render_template("new_workout.html", settings=fetch_settings())

    @app.route("/settings")
    def settings_page() -> str:
        return render_template("settings.html", settings=fetch_settings())

    @app.route("/workouts/<int:workout_id>")
    def workout_detail_page(workout_id: int) -> Any:
        settings = fetch_settings()
        with get_db() as conn:
            row = conn.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
        if row is None:
            return redirect("/calendar")
        workout = enrich_workout(dict(row), settings)
        return render_template("workout_detail.html", workout=workout, settings=settings)

    @app.route("/api/dashboard")
    def dashboard_api() -> Any:
        return jsonify(build_dashboard())

    @app.route("/api/calendar")
    def calendar_api() -> Any:
        return jsonify(build_log())

    @app.route("/api/trends")
    def trends_api() -> Any:
        return jsonify(build_trends())

    @app.route("/api/settings", methods=["GET", "POST"])
    def settings_api() -> Any:
        if request.method == "GET":
            return jsonify(fetch_settings())

        payload = request.get_json(silent=True) or {}
        athlete_name = (payload.get("athlete_name") or "Minghe").strip()
        ftp = int(payload.get("ftp") or 245)
        threshold_hr = int(payload.get("threshold_hr") or 168)
        threshold_pace_seconds = int(payload.get("threshold_pace_seconds") or 435)
        swim_threshold_seconds_per_100 = int(payload.get("swim_threshold_seconds_per_100") or 105)

        with get_db() as conn:
            conn.execute(
                """
                UPDATE athlete_settings
                SET athlete_name = ?, ftp = ?, threshold_hr = ?, threshold_pace_seconds = ?,
                    swim_threshold_seconds_per_100 = ?
                WHERE id = 1
                """,
                (
                    athlete_name,
                    ftp,
                    threshold_hr,
                    threshold_pace_seconds,
                    swim_threshold_seconds_per_100,
                ),
            )
            conn.commit()
        return jsonify({"ok": True, "settings": fetch_settings()})

    @app.route("/api/workouts/<int:workout_id>")
    def workout_api(workout_id: int) -> Any:
        settings = fetch_settings()
        with get_db() as conn:
            row = conn.execute("SELECT * FROM workouts WHERE id = ?", (workout_id,)).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(enrich_workout(dict(row), settings))

    @app.route("/api/workouts", methods=["POST"])
    def create_workout_api() -> Any:
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "").strip()
        sport = (payload.get("sport") or "Run").strip()
        start_time = (payload.get("start_time") or "").strip()
        intensity = (payload.get("intensity") or "Endurance").strip()
        notes = (payload.get("notes") or "").strip()
        duration_minutes = int(payload.get("duration_minutes") or 0)
        distance_miles = float(payload.get("distance_miles") or 0)
        elevation_ft = float(payload.get("elevation_ft") or 0)
        avg_hr = payload.get("avg_hr")
        avg_hr = int(avg_hr) if avg_hr not in (None, "", "null") else None
        avg_power = payload.get("avg_power")
        avg_power = int(avg_power) if avg_power not in (None, "", "null") else None
        rpe = int(payload.get("rpe") or 5)

        if not title or not start_time or duration_minutes <= 0:
            return jsonify({"ok": False, "error": "Title, start time, and duration are required."}), 400

        try:
            datetime.fromisoformat(start_time)
        except ValueError:
            return jsonify({"ok": False, "error": "Start time must be a valid ISO datetime."}), 400

        planned_load = load_score(duration_minutes, rpe, intensity)
        temp_workout = {
            "title": title,
            "sport": sport,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "distance_miles": distance_miles,
            "elevation_ft": elevation_ft,
            "avg_hr": avg_hr,
            "avg_power": avg_power,
            "intensity": intensity,
            "rpe": rpe,
            "notes": notes,
            "planned_load": planned_load,
        }
        completed_load = stress_score(temp_workout, fetch_settings())

        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO workouts (
                    title, sport, start_time, duration_minutes, distance_miles, elevation_ft,
                    avg_hr, avg_power, intensity, rpe, notes, planned_load, completed_load
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    sport,
                    start_time,
                    duration_minutes,
                    distance_miles,
                    elevation_ft,
                    avg_hr,
                    avg_power,
                    intensity,
                    rpe,
                    notes,
                    planned_load,
                    completed_load,
                ),
            )
            conn.commit()
            workout_id = cur.lastrowid

        return jsonify({"ok": True, "workout_id": workout_id})

    return app


app = create_app()


def find_port(start_port: int = 5060, host: str = "127.0.0.1") -> int:
    for port in range(start_port, start_port + 25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError("No open port found.")


if __name__ == "__main__":
    host = "127.0.0.1"
    port = find_port(int(os.environ.get("PORT", "5060")), host=host)
    print(f"Open http://{host}:{port}/")
    app.run(host=host, port=port, debug=False)
