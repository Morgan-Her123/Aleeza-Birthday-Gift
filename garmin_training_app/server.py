from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fitparse import FitFile
from flask import Flask, jsonify, make_response, redirect, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
TIMESERIES_DIR = DATA_DIR / 'timeseries'
PLOTS_DIR = DATA_DIR / 'plots'
GOAL_NOTIFICATIONS_DIR = DATA_DIR / 'goal_notifications'
DB_PATH = DATA_DIR / 'training.db'
DEFAULT_WATCH_ACTIVITY_PATH = Path('/Volumes/GARMIN/GARMIN/Activity')
MPL_CONFIG_DIR = DATA_DIR / '.mplconfig'
os.environ.setdefault('MPLCONFIGDIR', str(MPL_CONFIG_DIR))

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def ensure_dirs() -> None:
    TIMESERIES_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GOAL_NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    ensure_dirs()
    with get_db() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL UNIQUE,
                source_name TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                start_time_local TEXT,
                sport TEXT,
                sub_sport TEXT,
                distance_miles REAL,
                elapsed_seconds REAL,
                moving_seconds REAL,
                avg_speed_mph REAL,
                max_speed_mph REAL,
                avg_pace_min_per_mile REAL,
                best_pace_min_per_mile REAL,
                avg_hr_bpm INTEGER,
                max_hr_bpm INTEGER,
                calories INTEGER,
                ascent_ft REAL,
                descent_ft REAL,
                record_count INTEGER,
                timeseries_path TEXT,
                plot_path TEXT
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS weekly_notes (
                week_key TEXT PRIMARY KEY,
                note TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS training_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_date TEXT NOT NULL,
                session_period TEXT NOT NULL DEFAULT 'Morning',
                title TEXT NOT NULL,
                workout_label TEXT NOT NULL DEFAULT '',
                distance_miles REAL,
                duration_min REAL,
                notes TEXT NOT NULL DEFAULT '',
                reminder_time TEXT NOT NULL DEFAULT '07:00',
                completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                matched_activity_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        columns = {r['name'] for r in conn.execute("PRAGMA table_info(training_plans)").fetchall()}
        if 'session_period' not in columns:
            conn.execute(
                "ALTER TABLE training_plans ADD COLUMN session_period TEXT NOT NULL DEFAULT 'Morning'"
            )
        if 'workout_label' not in columns:
            conn.execute(
                "ALTER TABLE training_plans ADD COLUMN workout_label TEXT NOT NULL DEFAULT ''"
            )
        if 'completed' not in columns:
            conn.execute(
                "ALTER TABLE training_plans ADD COLUMN completed INTEGER NOT NULL DEFAULT 0"
            )
        if 'completed_at' not in columns:
            conn.execute(
                "ALTER TABLE training_plans ADD COLUMN completed_at TEXT"
            )
        if 'matched_activity_id' not in columns:
            conn.execute(
                "ALTER TABLE training_plans ADD COLUMN matched_activity_id INTEGER"
            )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS activity_feedback (
                activity_id INTEGER PRIMARY KEY,
                grade_label TEXT,
                grade_points REAL,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(activity_id) REFERENCES activities(id) ON DELETE CASCADE
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type TEXT NOT NULL,
                title TEXT NOT NULL,
                target_value REAL,
                target_unit TEXT NOT NULL DEFAULT '',
                week_key TEXT,
                due_date TEXT,
                weekly_completion_date TEXT,
                weekly_target_hours REAL,
                weekly_target_miles REAL,
                weekly_target_gain_ft REAL,
                weekly_percent_change REAL,
                weekly_race_goal TEXT,
                final_target_time TEXT,
                final_target_event TEXT,
                final_target_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                completed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )
        goal_columns = {r['name'] for r in conn.execute("PRAGMA table_info(goals)").fetchall()}
        if 'weekly_completion_date' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN weekly_completion_date TEXT")
        if 'weekly_target_hours' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN weekly_target_hours REAL")
        if 'weekly_target_miles' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN weekly_target_miles REAL")
        if 'weekly_target_gain_ft' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN weekly_target_gain_ft REAL")
        if 'weekly_percent_change' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN weekly_percent_change REAL")
        if 'weekly_race_goal' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN weekly_race_goal TEXT")
        if 'final_target_time' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN final_target_time TEXT")
        if 'final_target_event' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN final_target_event TEXT")
        if 'final_target_date' not in goal_columns:
            conn.execute("ALTER TABLE goals ADD COLUMN final_target_date TEXT")
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS race_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                race_date TEXT NOT NULL,
                race_name TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            '''
        )


GRADE_SCALE: dict[str, float] = {
    'A': 5.0,
    'B': 4.0,
    'C': 3.0,
    'D': 2.0,
    'F': 1.0,
}


def points_to_grade(points: float | None) -> str | None:
    if points is None:
        return None
    if points >= 4.5:
        return 'A'
    if points >= 3.5:
        return 'B'
    if points >= 2.5:
        return 'C'
    if points >= 1.5:
        return 'D'
    return 'F'


def sport_label(sport: str | None) -> str:
    if not sport:
        return 'Workout'
    token = str(sport).replace('_', ' ').strip().lower()
    if token in ('cycling', 'bike', 'biking'):
        return 'Bike'
    if token in ('running', 'run'):
        return 'Run'
    return token.title()


def review_label_for_sport(sport: str | None) -> str:
    token = str(sport or '').replace('_', ' ').strip().lower()
    if token in ('cycling', 'bike', 'biking'):
        return 'Cycling'
    if token in ('running', 'run'):
        return 'Running'
    return sport_label(sport)


def parse_flexible_number(raw: Any, field_name: str) -> float | None:
    if raw in (None, ''):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)

    text = str(raw).strip().replace(',', '.')
    if not text:
        return None

    # Accept ranges like "3-4" and use midpoint (3.5).
    range_match = re.match(r'^\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$', text)
    if range_match:
        a = float(range_match.group(1))
        b = float(range_match.group(2))
        return (a + b) / 2.0

    token_match = re.search(r'-?\d+(?:\.\d+)?', text)
    if token_match:
        return float(token_match.group(0))

    raise ValueError(f'{field_name} must be numeric (example: 5.5 or 3-4)')


def normalize_date_input(raw: Any, field_name: str) -> str:
    text = str(raw or '').strip()
    if not text:
        raise ValueError(f'{field_name} is required')

    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y'):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f'{field_name} must be YYYY-MM-DD or MM/DD/YYYY')


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open('rb') as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def to_local_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone().isoformat()


def pace_min_per_mile_from_speed(speed_mps: float | None) -> float | None:
    if speed_mps is None or speed_mps <= 0:
        return None
    return 1609.344 / speed_mps / 60.0


def parse_fit(path: Path) -> dict[str, Any]:
    fit = FitFile(str(path))

    session = None
    for msg in fit.get_messages('session'):
        session = {f.name: f.value for f in msg}
        break

    records: list[dict[str, Any]] = []
    for msg in fit.get_messages('record'):
        r = {f.name: f.value for f in msg}
        if 'timestamp' in r:
            records.append(r)

    if session is None:
        raise RuntimeError(f'No session message in {path.name}')

    start_utc = session.get('start_time')
    if start_utc is None and records:
        start_utc = records[0].get('timestamp')

    timeseries = []
    prev_alt_ft = None
    cum_gain_ft = 0.0

    for r in records:
        t_utc = r.get('timestamp')
        if t_utc is None or start_utc is None:
            continue

        elapsed_s = (t_utc - start_utc).total_seconds()
        dist_m = r.get('distance')
        speed_mps = r.get('enhanced_speed') if r.get('enhanced_speed') is not None else r.get('speed')
        alt_m = r.get('enhanced_altitude') if r.get('enhanced_altitude') is not None else r.get('altitude')

        dist_miles = (dist_m / 1609.344) if dist_m is not None else None
        speed_mph = (speed_mps * 2.2369362921) if speed_mps is not None else None
        alt_ft = (alt_m * 3.280839895) if alt_m is not None else None

        if alt_ft is not None and prev_alt_ft is not None:
            delta = alt_ft - prev_alt_ft
            if delta > 0:
                cum_gain_ft += delta
        if alt_ft is not None:
            prev_alt_ft = alt_ft

        timeseries.append(
            {
                'timestamp_local': to_local_iso(t_utc),
                'elapsed_min': elapsed_s / 60.0,
                'distance_miles': dist_miles,
                'speed_mph': speed_mph,
                'pace_min_per_mile': (60.0 / speed_mph) if speed_mph and speed_mph > 0 else None,
                'heart_rate_bpm': r.get('heart_rate'),
                'cadence_spm': r.get('cadence'),
                'elevation_ft': alt_ft,
                'cum_elevation_gain_ft': cum_gain_ft,
                'temperature_f': (r.get('temperature') * 9.0 / 5.0 + 32.0)
                if r.get('temperature') is not None
                else None,
            }
        )

    summary = {
        'start_time_local': to_local_iso(start_utc),
        'sport': session.get('sport'),
        'sub_sport': session.get('sub_sport'),
        'distance_miles': ((session.get('total_distance') or 0.0) / 1609.344),
        'elapsed_seconds': session.get('total_elapsed_time'),
        'moving_seconds': session.get('total_timer_time'),
        'avg_speed_mph': (session.get('avg_speed') * 2.2369362921) if session.get('avg_speed') else None,
        'max_speed_mph': (session.get('max_speed') * 2.2369362921) if session.get('max_speed') else None,
        'avg_pace_min_per_mile': pace_min_per_mile_from_speed(session.get('avg_speed')),
        'best_pace_min_per_mile': pace_min_per_mile_from_speed(session.get('max_speed')),
        'avg_hr_bpm': session.get('avg_heart_rate'),
        'max_hr_bpm': session.get('max_heart_rate'),
        'calories': session.get('total_calories'),
        'ascent_ft': (session.get('total_ascent') or 0.0) * 3.280839895,
        'descent_ft': (session.get('total_descent') or 0.0) * 3.280839895,
        'record_count': len(timeseries),
    }

    return {'summary': summary, 'timeseries': timeseries}


def generate_plot(timeseries: list[dict[str, Any]], out_path: Path) -> None:
    if not timeseries:
        return

    x = [datetime.fromisoformat(r['timestamp_local']) for r in timeseries if r.get('timestamp_local')]
    speed = [r.get('speed_mph') for r in timeseries]
    cadence = [r.get('cadence_spm') for r in timeseries]
    hr = [r.get('heart_rate_bpm') for r in timeseries]
    elev = [r.get('elevation_ft') for r in timeseries]
    gain = [r.get('cum_elevation_gain_ft') for r in timeseries]

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True, constrained_layout=True)

    axes[0].plot(x, speed, color='#1f77b4', linewidth=1.3)
    axes[0].set_ylabel('Speed (mph)')
    axes[0].grid(alpha=0.25)

    axes[1].plot(x, cadence, color='#2ca02c', linewidth=1.2)
    axes[1].set_ylabel('Cadence (spm)')
    axes[1].grid(alpha=0.25)

    axes[2].plot(x, hr, color='#d62728', linewidth=1.2)
    axes[2].set_ylabel('HR (bpm)')
    axes[2].grid(alpha=0.25)

    axes[3].plot(x, elev, color='#8c564b', linewidth=1.1)
    ax2 = axes[3].twinx()
    ax2.plot(x, gain, color='#ff7f0e', linewidth=1.2)
    axes[3].set_ylabel('Elev (ft)')
    ax2.set_ylabel('Gain (ft)')
    axes[3].set_xlabel('Local Time')
    axes[3].grid(alpha=0.25)

    locator = mdates.AutoDateLocator(minticks=6, maxticks=12)
    formatter = mdates.ConciseDateFormatter(locator)
    axes[3].xaxis.set_major_locator(locator)
    axes[3].xaxis.set_major_formatter(formatter)

    fig.suptitle('Activity Key Metrics vs Time (Miles-based units)')
    fig.savefig(out_path, dpi=260)
    plt.close(fig)


def import_activity_file(conn: sqlite3.Connection, fit_file: Path) -> tuple[bool, str]:
    file_hash = sha1_file(fit_file)

    existing = conn.execute(
        'SELECT id FROM activities WHERE source_file = ? OR file_hash = ?',
        (str(fit_file), file_hash),
    ).fetchone()
    if existing:
        return False, f'skipped duplicate: {fit_file.name}'

    parsed = parse_fit(fit_file)
    summary = parsed['summary']
    timeseries = parsed['timeseries']

    stem = fit_file.stem
    ts_rel = f'timeseries/{stem}.json'
    plot_rel = f'plots/{stem}.png'

    ts_path = DATA_DIR / ts_rel
    plot_path = DATA_DIR / plot_rel

    ts_path.write_text(json.dumps(timeseries, ensure_ascii=True), encoding='utf-8')
    generate_plot(timeseries, plot_path)

    conn.execute(
        '''
        INSERT INTO activities (
            source_file, source_name, file_hash, imported_at,
            start_time_local, sport, sub_sport,
            distance_miles, elapsed_seconds, moving_seconds,
            avg_speed_mph, max_speed_mph,
            avg_pace_min_per_mile, best_pace_min_per_mile,
            avg_hr_bpm, max_hr_bpm, calories,
            ascent_ft, descent_ft, record_count,
            timeseries_path, plot_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            str(fit_file),
            fit_file.name,
            file_hash,
            datetime.now().isoformat(timespec='seconds'),
            summary.get('start_time_local'),
            summary.get('sport'),
            summary.get('sub_sport'),
            summary.get('distance_miles'),
            summary.get('elapsed_seconds'),
            summary.get('moving_seconds'),
            summary.get('avg_speed_mph'),
            summary.get('max_speed_mph'),
            summary.get('avg_pace_min_per_mile'),
            summary.get('best_pace_min_per_mile'),
            summary.get('avg_hr_bpm'),
            summary.get('max_hr_bpm'),
            summary.get('calories'),
            summary.get('ascent_ft'),
            summary.get('descent_ft'),
            summary.get('record_count'),
            ts_rel,
            plot_rel,
        ),
    )

    return True, f'imported: {fit_file.name}'


def detect_watch_activity_path() -> Path | None:
    volumes_root = Path('/Volumes')
    if not volumes_root.exists():
        return None

    # Common Garmin mount layout on macOS:
    # /Volumes/<VOLNAME>/GARMIN/Activity
    for volume in volumes_root.iterdir():
        candidate = volume / 'GARMIN' / 'Activity'
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def period_for_local_iso(dt_iso: str | None) -> str:
    if not dt_iso:
        return 'Morning'
    try:
        dt = datetime.fromisoformat(dt_iso)
    except ValueError:
        return 'Morning'
    return 'Morning' if dt.hour < 12 else 'Afternoon'


def reconcile_training_plan_completions(conn: sqlite3.Connection) -> int:
    plans = conn.execute(
        '''
        SELECT id, plan_date, session_period, title, workout_label, completed, matched_activity_id, completed_at
        FROM training_plans
        ORDER BY
            plan_date ASC,
            CASE session_period WHEN 'Morning' THEN 0 ELSE 1 END ASC,
            reminder_time ASC,
            id ASC
        '''
    ).fetchall()
    if not plans:
        return 0

    activities = conn.execute(
        '''
        SELECT id, start_time_local
        FROM activities
        WHERE start_time_local IS NOT NULL
        ORDER BY start_time_local ASC, id ASC
        '''
    ).fetchall()
    if not activities:
        return 0

    used_activity_ids: set[int] = set()
    for p in plans:
        matched = p['matched_activity_id']
        if matched is not None and int(p['completed'] or 0) == 1:
            used_activity_ids.add(int(matched))

    by_date_period: dict[tuple[str, str], list[int]] = {}
    by_date: dict[str, list[int]] = {}
    for a in activities:
        aid = int(a['id'])
        if aid in used_activity_ids:
            continue
        date_key = str(a['start_time_local'])[:10]
        period = period_for_local_iso(a['start_time_local'])

        by_date_period.setdefault((date_key, period), []).append(aid)
        by_date.setdefault(date_key, []).append(aid)

    matched_count = 0
    now_iso = datetime.now().isoformat(timespec='seconds')
    today_key = datetime.now().astimezone().date().isoformat()

    # Rule: any "strength" plan is auto-completed after its day passes.
    for p in plans:
        if int(p['completed'] or 0) == 1:
            continue
        title = str(p['title'] or '').strip().lower()
        label = str(p['workout_label'] or '').strip().lower()
        if ('strength' not in title) and ('strength' not in label):
            continue
        if str(p['plan_date'] or '') >= today_key:
            continue
        conn.execute(
            '''
            UPDATE training_plans
            SET completed = 1, completed_at = ?, matched_activity_id = NULL, updated_at = ?
            WHERE id = ?
            ''',
            (
                now_iso,
                now_iso,
                p['id'],
            ),
        )
        matched_count += 1

    for p in plans:
        if int(p['completed'] or 0) == 1:
            continue
        date_key = p['plan_date']
        period = p['session_period'] or 'Morning'
        candidate = None

        period_bucket = by_date_period.get((date_key, period), [])
        while period_bucket and (period_bucket[0] in used_activity_ids):
            period_bucket.pop(0)
        if period_bucket:
            candidate = period_bucket.pop(0)

        if candidate is None:
            date_bucket = by_date.get(date_key, [])
            while date_bucket and (date_bucket[0] in used_activity_ids):
                date_bucket.pop(0)
            if date_bucket:
                candidate = date_bucket.pop(0)

        if candidate is None:
            continue

        used_activity_ids.add(candidate)
        conn.execute(
            '''
            UPDATE training_plans
            SET completed = 1, completed_at = ?, matched_activity_id = ?, updated_at = ?
            WHERE id = ?
            ''',
            (
                p['completed_at'] or now_iso,
                candidate,
                now_iso,
                p['id'],
            ),
        )
        matched_count += 1

    return matched_count


def write_watch_goal_notification(goal: dict[str, Any]) -> dict[str, Any]:
    activity_path = detect_watch_activity_path()
    if activity_path is None:
        return {
            'sent': False,
            'message': 'Watch not mounted. Connect Garmin and retry.',
            'watch_path': None,
            'file_path': None,
        }

    garmin_root = activity_path.parent
    watch_alerts_dir = garmin_root / 'GOAL_ALERTS'
    watch_alerts_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    timestamp = now.strftime('%Y%m%d_%H%M%S')
    goal_id = goal.get('id', 'x')
    goal_type = str(goal.get('goal_type') or '').title()
    title = str(goal.get('title') or '').strip()
    weekly_hours = goal.get('weekly_target_hours')
    weekly_miles = goal.get('weekly_target_miles')
    weekly_gain = goal.get('weekly_target_gain_ft')
    weekly_change = goal.get('weekly_percent_change')
    weekly_race_goal = str(goal.get('weekly_race_goal') or '').strip()
    final_time = str(goal.get('final_target_time') or '').strip()
    final_event = str(goal.get('final_target_event') or '').strip()
    final_date = str(goal.get('final_target_date') or '').strip()
    completion_date = str(goal.get('weekly_completion_date') or '').strip()

    if str(goal.get('goal_type') or '').lower() == 'weekly':
        bits = []
        if weekly_hours not in (None, ''):
            bits.append(f'{float(weekly_hours):g} h')
        if weekly_miles not in (None, ''):
            bits.append(f'{float(weekly_miles):g} mi')
        if weekly_gain not in (None, ''):
            bits.append(f'{float(weekly_gain):g} ft gain')
        if weekly_change not in (None, ''):
            bits.append(f'{float(weekly_change):g}% vs last week')
        if weekly_race_goal:
            bits.append(f'race: {weekly_race_goal}')
        if completion_date:
            bits.append(f'complete by {completion_date}')
        target_text = (' (' + ', '.join(bits) + ')') if bits else ''
    else:
        bits = []
        if final_event:
            bits.append(final_event)
        if final_date:
            bits.append(final_date)
        if final_time:
            bits.append(final_time)
        target_text = (' (' + ', '.join(bits) + ')') if bits else ''

    line_1 = 'GOAL ACCOMPLISHED'
    line_2 = f'{goal_type} goal: {title}{target_text}'.strip()
    line_3 = f'Completed at {now.isoformat(timespec="seconds")}'
    content = '\n'.join([line_1, line_2, line_3]) + '\n'

    watch_file = watch_alerts_dir / f'goal_{goal_id}_{timestamp}.txt'
    watch_file.write_text(content, encoding='utf-8')

    # Keep a local copy in the app data folder for traceability.
    local_file = GOAL_NOTIFICATIONS_DIR / f'goal_{goal_id}_{timestamp}.txt'
    local_file.write_text(content, encoding='utf-8')

    return {
        'sent': True,
        'message': 'Goal accomplished notification file written to watch.',
        'watch_path': str(watch_alerts_dir),
        'file_path': str(watch_file),
    }


def monday_key_for_iso(dt_iso: str) -> str:
    dt = datetime.fromisoformat(dt_iso)
    day = dt.weekday()  # Monday=0 ... Sunday=6
    monday = dt - timedelta(days=day)
    return monday.date().isoformat()


def build_workweek_groups(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        r = dict(row)
        ts = r.get('start_time_local')
        if not ts:
            continue
        dt = datetime.fromisoformat(ts)
        if dt.weekday() > 4:  # Monday-Friday only
            continue
        key = monday_key_for_iso(ts)
        if key not in grouped:
            monday = datetime.fromisoformat(key + 'T00:00:00')
            friday = monday + timedelta(days=4)
            grouped[key] = {
                'week_key': key,
                'monday': monday.date().isoformat(),
                'friday': friday.date().isoformat(),
                'records': [],
                'totals': {'seconds': 0.0, 'miles': 0.0, 'gain': 0.0, 'loss': 0.0},
            }
        grouped[key]['records'].append(r)
        grouped[key]['totals']['seconds'] += float(r.get('moving_seconds') or r.get('elapsed_seconds') or 0.0)
        grouped[key]['totals']['miles'] += float(r.get('distance_miles') or 0.0)
        grouped[key]['totals']['gain'] += float(r.get('ascent_ft') or 0.0)
        grouped[key]['totals']['loss'] += float(r.get('descent_ft') or 0.0)

    weeks = sorted(grouped.values(), key=lambda w: w['week_key'], reverse=True)
    for w in weeks:
        w['records'].sort(key=lambda r: r.get('start_time_local') or '', reverse=True)
    return weeks


def _safe_parse_ts(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def compute_week_time_distribution(week_records: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {
        'z2': 0.0,
        'vertical': 0.0,
        'interval': 0.0,
        'strength': 0.0,
    }
    total_s = 0.0

    for rec in week_records:
        ts_rel = rec.get('timeseries_path')
        if not ts_rel:
            continue
        ts_path = DATA_DIR / str(ts_rel)
        if not ts_path.exists():
            continue
        try:
            points = json.loads(ts_path.read_text(encoding='utf-8'))
        except Exception:
            continue
        if not points or len(points) < 2:
            continue

        hr_vals = [p.get('heart_rate_bpm') for p in points if p.get('heart_rate_bpm') is not None]
        speed_vals = [p.get('speed_mph') for p in points if p.get('speed_mph') is not None]
        max_hr = float(rec.get('max_hr_bpm') or (max(hr_vals) if hr_vals else 190.0))
        avg_speed = (sum(speed_vals) / len(speed_vals)) if speed_vals else 0.0

        prev_gain = points[0].get('cum_elevation_gain_ft')
        prev_ts = _safe_parse_ts(points[0].get('timestamp_local'))

        for i in range(1, len(points)):
            p = points[i]
            ts = _safe_parse_ts(p.get('timestamp_local'))
            if ts is None or prev_ts is None:
                prev_ts = ts
                prev_gain = p.get('cum_elevation_gain_ft')
                continue

            dt_s = (ts - prev_ts).total_seconds()
            if dt_s <= 0 or dt_s > 30:
                prev_ts = ts
                prev_gain = p.get('cum_elevation_gain_ft')
                continue

            gain_now = p.get('cum_elevation_gain_ft')
            gain_delta = 0.0
            if gain_now is not None and prev_gain is not None:
                gain_delta = float(gain_now) - float(prev_gain)

            hr = p.get('heart_rate_bpm')
            speed = p.get('speed_mph')
            hr_ratio = (float(hr) / max_hr) if (hr is not None and max_hr > 0) else None

            is_interval = False
            if hr_ratio is not None and hr_ratio >= 0.88:
                is_interval = True
            if not is_interval and speed is not None and avg_speed > 0 and float(speed) >= avg_speed * 1.20:
                is_interval = True

            is_vertical = (gain_delta > 1.0)
            is_z2 = (hr_ratio is not None and 0.70 <= hr_ratio < 0.80)

            if is_interval:
                buckets['interval'] += dt_s
            elif is_vertical:
                buckets['vertical'] += dt_s
            elif is_z2:
                buckets['z2'] += dt_s
            else:
                # Remaining time is treated as strength/steady support work.
                buckets['strength'] += dt_s

            total_s += dt_s
            prev_ts = ts
            prev_gain = gain_now

    def pct(v: float) -> float:
        if total_s <= 0:
            return 0.0
        return (v / total_s) * 100.0

    return {
        'seconds': total_s,
        'z2_seconds': buckets['z2'],
        'z2_percent': pct(buckets['z2']),
        'vertical_seconds': buckets['vertical'],
        'vertical_percent': pct(buckets['vertical']),
        'strength_seconds': buckets['strength'],
        'strength_percent': pct(buckets['strength']),
        'interval_seconds': buckets['interval'],
        'interval_percent': pct(buckets['interval']),
    }


def ics_escape(value: str) -> str:
    return value.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def create_app() -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    init_db()

    @app.after_request
    def add_no_cache_headers(response):  # type: ignore[override]
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/', methods=['GET'])
    def home() -> str:
        return render_template('home.html')

    @app.route('/records', methods=['GET'])
    def records_page() -> str:
        return render_template('records.html', default_watch_path=str(DEFAULT_WATCH_ACTIVITY_PATH))

    @app.route('/week/<week_key>', methods=['GET', 'POST'])
    @app.route('/week/<week_key>/', methods=['GET', 'POST'])
    @app.route('/weeks/<week_key>', methods=['GET', 'POST'])
    def week_page(week_key: str) -> Any:
        # week_key should be YYYY-MM-DD (Monday date)
        try:
            datetime.strptime(week_key, '%Y-%m-%d')
        except ValueError:
            return redirect('/records')

        with get_db() as conn:
            if request.method == 'POST':
                note = (request.form.get('note') or '').strip()
                conn.execute(
                    '''
                    INSERT INTO weekly_notes (week_key, note, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(week_key) DO UPDATE SET
                        note=excluded.note,
                        updated_at=excluded.updated_at
                    ''',
                    (week_key, note, datetime.now().isoformat(timespec='seconds')),
                )
                conn.commit()
                return redirect(f'/week/{week_key}?saved=1')

            rows = conn.execute(
                'SELECT * FROM activities WHERE start_time_local IS NOT NULL ORDER BY start_time_local DESC, id DESC'
            ).fetchall()
            note_row = conn.execute('SELECT note, updated_at FROM weekly_notes WHERE week_key = ?', (week_key,)).fetchone()

        weeks = build_workweek_groups(list(rows))
        week = next((w for w in weeks if w['week_key'] == week_key), None)
        if week is None:
            return redirect('/records')

        prev_week = None
        for i, w in enumerate(weeks):
            if w['week_key'] == week_key and i + 1 < len(weeks):
                prev_week = weeks[i + 1]
                break

        activity_ids = [int(r['id']) for r in week['records']]
        feedback_by_activity: dict[int, dict[str, Any]] = {}
        if activity_ids:
            qmarks = ','.join('?' for _ in activity_ids)
            with get_db() as conn:
                fb_rows = conn.execute(
                    f'''
                    SELECT activity_id, grade_label, grade_points, notes, updated_at
                    FROM activity_feedback
                    WHERE activity_id IN ({qmarks})
                    ''',
                    activity_ids,
                ).fetchall()
            feedback_by_activity = {int(r['activity_id']): dict(r) for r in fb_rows}

        for rec in week['records']:
            fb = feedback_by_activity.get(int(rec['id']))
            raw_points = fb.get('grade_points') if fb else None
            norm_label = points_to_grade(float(raw_points)) if raw_points is not None else None
            rec['grade_label'] = norm_label
            rec['grade_points'] = GRADE_SCALE.get(norm_label) if norm_label else None

        daily_map: dict[str, list[float]] = {}
        for rec in week['records']:
            points = rec.get('grade_points')
            if points is None:
                continue
            day_key = (rec.get('start_time_local') or '')[:10]
            if not day_key:
                continue
            if day_key not in daily_map:
                daily_map[day_key] = []
            daily_map[day_key].append(float(points))

        daily_breakdown: list[dict[str, Any]] = []
        for day_key in sorted(daily_map.keys()):
            vals = daily_map[day_key]
            avg_points = (sum(vals) / len(vals)) if vals else None
            daily_breakdown.append(
                {
                    'date': day_key,
                    'avg_points': avg_points,
                    'grade_label': points_to_grade(avg_points),
                    'count': len(vals),
                }
            )

        weekly_points = None
        weekly_grade_label = None
        if daily_breakdown:
            weekly_points = sum(d['avg_points'] for d in daily_breakdown if d['avg_points'] is not None) / len(daily_breakdown)
            weekly_grade_label = points_to_grade(weekly_points)

        week_distribution = compute_week_time_distribution(week['records'])

        note = note_row['note'] if note_row else ''
        saved = request.args.get('saved') == '1'
        return render_template(
            'week_detail.html',
            week=week,
            prev_week=prev_week,
            note=note,
            saved=saved,
            weekly_points=weekly_points,
            weekly_grade_label=weekly_grade_label,
            daily_breakdown=daily_breakdown,
            week_distribution=week_distribution,
        )

    @app.route('/records/<int:activity_id>', methods=['GET'])
    def records_legacy_detail(activity_id: int) -> Any:
        return redirect(f'/session/{activity_id}')

    @app.route('/session/<int:activity_id>', methods=['GET', 'POST'])
    def record_detail_page(activity_id: int) -> Any:
        if request.method == 'POST':
            grade_label = (request.form.get('grade_label') or '').strip().upper()
            notes = (request.form.get('workout_notes') or '').strip()
            grade_points = GRADE_SCALE.get(grade_label) if grade_label in GRADE_SCALE else None
            now_iso = datetime.now().isoformat(timespec='seconds')
            with get_db() as conn:
                conn.execute(
                    '''
                    INSERT INTO activity_feedback (activity_id, grade_label, grade_points, notes, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(activity_id) DO UPDATE SET
                        grade_label=excluded.grade_label,
                        grade_points=excluded.grade_points,
                        notes=excluded.notes,
                        updated_at=excluded.updated_at
                    ''',
                    (activity_id, grade_label if grade_label else None, grade_points, notes, now_iso),
                )
                conn.commit()
            return redirect(f'/session/{activity_id}?saved=1')

        with get_db() as conn:
            row = conn.execute('SELECT * FROM activities WHERE id = ?', (activity_id,)).fetchone()
            feedback_row = conn.execute(
                '''
                SELECT grade_label, grade_points, notes, updated_at
                FROM activity_feedback
                WHERE activity_id = ?
                ''',
                (activity_id,),
            ).fetchone()
        if row is None:
            return redirect('/records')

        activity = dict(row)
        activity['event_label'] = sport_label(activity.get('sport'))
        ts_stats = None
        ts_rel = activity.get('timeseries_path')
        if ts_rel:
            ts_path = DATA_DIR / ts_rel
            if ts_path.exists():
                points = json.loads(ts_path.read_text(encoding='utf-8'))
                if points:
                    cadence = [p.get('cadence_spm') for p in points if p.get('cadence_spm') is not None]
                    speed = [p.get('speed_mph') for p in points if p.get('speed_mph') is not None]
                    hr = [p.get('heart_rate_bpm') for p in points if p.get('heart_rate_bpm') is not None]
                    gain = [p.get('cum_elevation_gain_ft') for p in points if p.get('cum_elevation_gain_ft') is not None]

                    def avg(vals: list[float]) -> float | None:
                        return (sum(vals) / len(vals)) if vals else None

                    ts_stats = {
                        'points': len(points),
                        'avg_cadence': avg(cadence),
                        'max_cadence': max(cadence) if cadence else None,
                        'avg_speed': avg(speed),
                        'avg_hr': avg(hr),
                        'total_gain': gain[-1] if gain else None,
                    }

        feedback = dict(feedback_row) if feedback_row else {'grade_label': '', 'grade_points': None, 'notes': ''}
        if feedback.get('grade_points') is not None:
            feedback['grade_label'] = points_to_grade(float(feedback['grade_points'])) or ''
        saved = request.args.get('saved') == '1'
        return render_template(
            'record_detail.html',
            activity=activity,
            ts_stats=ts_stats,
            feedback=feedback,
            saved=saved,
            grade_options=['A', 'B', 'C', 'D', 'F'],
            review_label=review_label_for_sport(activity.get('sport')),
        )

    @app.route('/overview', methods=['GET'])
    def overview_page() -> str:
        return render_template('overall.html')

    @app.route('/planner', methods=['GET'])
    def planner_page() -> str:
        return render_template('planner.html')

    @app.route('/goals', methods=['GET'])
    def goals_page() -> str:
        return render_template('goals.html')

    @app.route('/api/activities', methods=['GET'])
    def list_activities() -> Any:
        with get_db() as conn:
            rows = conn.execute(
                'SELECT * FROM activities ORDER BY start_time_local DESC, id DESC'
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/activities/<int:activity_id>', methods=['GET'])
    def activity_detail(activity_id: int) -> Any:
        with get_db() as conn:
            row = conn.execute('SELECT * FROM activities WHERE id = ?', (activity_id,)).fetchone()
        if row is None:
            return jsonify({'error': 'not found'}), 404
        return jsonify(dict(row))

    @app.route('/api/overview', methods=['GET'])
    def overview_data() -> Any:
        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT
                    id,
                    start_time_local,
                    distance_miles,
                    avg_pace_min_per_mile,
                    avg_hr_bpm
                FROM activities
                WHERE start_time_local IS NOT NULL
                ORDER BY start_time_local ASC, id ASC
                '''
            ).fetchall()

        sessions = [dict(r) for r in rows]
        total_distance = sum((r.get('distance_miles') or 0.0) for r in sessions)
        avg_distance = (total_distance / len(sessions)) if sessions else 0.0

        rolling_7: list[dict[str, Any]] = []
        window_sum = 0.0
        for i, s in enumerate(sessions):
            window_sum += s.get('distance_miles') or 0.0
            if i >= 7:
                window_sum -= sessions[i - 7].get('distance_miles') or 0.0
            if i >= 6:
                rolling_7.append(
                    {
                        'start_time_local': s.get('start_time_local'),
                        'rolling_distance_miles': window_sum,
                    }
                )

        return jsonify(
            {
                'session_count': len(sessions),
                'total_distance_miles': total_distance,
                'avg_distance_miles': avg_distance,
                'sessions': sessions,
                'rolling_7': rolling_7,
            }
        )

    @app.route('/api/training-plans', methods=['GET', 'POST'])
    def training_plans() -> Any:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            plan_date = (payload.get('plan_date') or '').strip()
            session_period = (payload.get('session_period') or 'Morning').strip().title()
            if session_period not in ('Morning', 'Afternoon'):
                session_period = 'Morning'
            title = (payload.get('title') or '').strip()
            workout_label = (payload.get('workout_label') or '').strip()
            reminder_default = '07:00' if session_period == 'Morning' else '16:30'
            reminder_time = (payload.get('reminder_time') or reminder_default).strip()
            notes = (payload.get('notes') or '').strip()

            try:
                datetime.strptime(plan_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'ok': False, 'error': 'plan_date must be YYYY-MM-DD'}), 400

            if not title:
                return jsonify({'ok': False, 'error': 'title is required'}), 400

            try:
                datetime.strptime(reminder_time, '%H:%M')
            except ValueError:
                reminder_time = reminder_default

            try:
                distance_miles = parse_flexible_number(payload.get('distance_miles'), 'distance_miles')
                duration_min = parse_flexible_number(payload.get('duration_min'), 'duration_min')
            except ValueError as exc:
                return jsonify({'ok': False, 'error': str(exc)}), 400
            now_iso = datetime.now().isoformat(timespec='seconds')

            with get_db() as conn:
                cur = conn.execute(
                    '''
                    INSERT INTO training_plans (
                        plan_date, session_period, title, workout_label, distance_miles, duration_min,
                        notes, reminder_time, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        plan_date,
                        session_period,
                        title,
                        workout_label,
                        distance_miles,
                        duration_min,
                        notes,
                        reminder_time,
                        now_iso,
                        now_iso,
                    ),
                )
                conn.commit()
                new_id = cur.lastrowid

            return jsonify({'ok': True, 'id': new_id})

        with get_db() as conn:
            matched_count = reconcile_training_plan_completions(conn)
            if matched_count > 0:
                conn.commit()
            rows = conn.execute(
                '''
                SELECT * FROM training_plans
                ORDER BY
                    plan_date ASC,
                    CASE session_period WHEN 'Morning' THEN 0 ELSE 1 END ASC,
                    reminder_time ASC,
                    id ASC
                '''
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/training-plans/<int:plan_id>', methods=['PUT', 'DELETE'])
    def update_or_delete_training_plan(plan_id: int) -> Any:
        if request.method == 'PUT':
            payload = request.get_json(silent=True) or {}
            plan_date = (payload.get('plan_date') or '').strip()
            session_period = (payload.get('session_period') or 'Morning').strip().title()
            if session_period not in ('Morning', 'Afternoon'):
                session_period = 'Morning'
            title = (payload.get('title') or '').strip()
            workout_label = (payload.get('workout_label') or '').strip()
            reminder_default = '07:00' if session_period == 'Morning' else '16:30'
            reminder_time = (payload.get('reminder_time') or reminder_default).strip()
            notes = (payload.get('notes') or '').strip()

            try:
                datetime.strptime(plan_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'ok': False, 'error': 'plan_date must be YYYY-MM-DD'}), 400

            if not title:
                return jsonify({'ok': False, 'error': 'title is required'}), 400

            try:
                datetime.strptime(reminder_time, '%H:%M')
            except ValueError:
                reminder_time = reminder_default

            try:
                distance_miles = parse_flexible_number(payload.get('distance_miles'), 'distance_miles')
                duration_min = parse_flexible_number(payload.get('duration_min'), 'duration_min')
            except ValueError as exc:
                return jsonify({'ok': False, 'error': str(exc)}), 400

            now_iso = datetime.now().isoformat(timespec='seconds')
            with get_db() as conn:
                existing = conn.execute(
                    'SELECT id FROM training_plans WHERE id = ?',
                    (plan_id,),
                ).fetchone()
                if existing is None:
                    return jsonify({'ok': False, 'error': 'workout not found'}), 404
                conn.execute(
                    '''
                    UPDATE training_plans
                    SET
                        plan_date = ?,
                        session_period = ?,
                        title = ?,
                        workout_label = ?,
                        distance_miles = ?,
                        duration_min = ?,
                        notes = ?,
                        reminder_time = ?,
                        completed = 0,
                        completed_at = NULL,
                        matched_activity_id = NULL,
                        updated_at = ?
                    WHERE id = ?
                    ''',
                    (
                        plan_date,
                        session_period,
                        title,
                        workout_label,
                        distance_miles,
                        duration_min,
                        notes,
                        reminder_time,
                        now_iso,
                        plan_id,
                    ),
                )
                rematched = reconcile_training_plan_completions(conn)
                conn.commit()
            return jsonify({'ok': True, 'id': plan_id, 'plans_marked_completed': rematched})

        with get_db() as conn:
            conn.execute('DELETE FROM training_plans WHERE id = ?', (plan_id,))
            conn.commit()
        return jsonify({'ok': True})

    @app.route('/api/training-plans/today', methods=['GET'])
    def today_training_plan() -> Any:
        today = datetime.now().astimezone().date().isoformat()
        with get_db() as conn:
            matched_count = reconcile_training_plan_completions(conn)
            if matched_count > 0:
                conn.commit()
            rows = conn.execute(
                '''
                SELECT * FROM training_plans
                WHERE plan_date = ?
                ORDER BY
                    CASE session_period WHEN 'Morning' THEN 0 ELSE 1 END ASC,
                    reminder_time ASC,
                    id ASC
                ''',
                (today,),
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/training-plans.ics', methods=['GET'])
    def training_plans_ics() -> Any:
        today = datetime.now().astimezone().date().isoformat()
        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT * FROM training_plans
                WHERE plan_date >= ?
                ORDER BY
                    plan_date ASC,
                    CASE session_period WHEN 'Morning' THEN 0 ELSE 1 END ASC,
                    reminder_time ASC,
                    id ASC
                ''',
                (today,),
            ).fetchall()

        now_utc = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Runners Log//Training Planner//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
        ]

        for row in rows:
            date_key = row['plan_date']
            period = (row['session_period'] or 'Morning')
            rem = row['reminder_time'] or ('07:00' if period == 'Morning' else '16:30')
            start_local = datetime.fromisoformat(f'{date_key}T{rem}:00')
            end_local = start_local + timedelta(minutes=int(row['duration_min'] or 45))
            dt_start = start_local.strftime('%Y%m%dT%H%M%S')
            dt_end = end_local.strftime('%Y%m%dT%H%M%S')
            summary = ics_escape(f"{period} Workout: {row['title']}")

            pieces = []
            pieces.append(f"Session: {period}")
            if row['distance_miles'] is not None:
                pieces.append(f"Distance: {row['distance_miles']:.2f} mi")
            if row['duration_min'] is not None:
                pieces.append(f"Duration: {row['duration_min']:.0f} min")
            if row['notes']:
                pieces.append(row['notes'])
            description = ics_escape('\n'.join(pieces)) if pieces else 'Planned training session'

            lines.extend(
                [
                    'BEGIN:VEVENT',
                    f'UID:runnerslog-plan-{row["id"]}@local',
                    f'DTSTAMP:{now_utc}',
                    f'DTSTART:{dt_start}',
                    f'DTEND:{dt_end}',
                    f'SUMMARY:{summary}',
                    f'DESCRIPTION:{description}',
                    'BEGIN:VALARM',
                    'TRIGGER:-PT30M',
                    'ACTION:DISPLAY',
                    'DESCRIPTION:Workout reminder',
                    'END:VALARM',
                    'END:VEVENT',
                ]
            )

        lines.append('END:VCALENDAR')
        body = '\r\n'.join(lines) + '\r\n'
        response = make_response(body)
        response.headers['Content-Type'] = 'text/calendar; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=training_plan.ics'
        return response

    @app.route('/api/races', methods=['GET', 'POST'])
    def race_events_api() -> Any:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            race_date = (payload.get('race_date') or '').strip()
            race_name = (payload.get('race_name') or '').strip()
            notes = (payload.get('notes') or '').strip()

            try:
                datetime.strptime(race_date, '%Y-%m-%d')
            except ValueError:
                return jsonify({'ok': False, 'error': 'race_date must be YYYY-MM-DD'}), 400
            if not race_name:
                return jsonify({'ok': False, 'error': 'race_name is required'}), 400

            now_iso = datetime.now().isoformat(timespec='seconds')
            with get_db() as conn:
                cur = conn.execute(
                    '''
                    INSERT INTO race_events (race_date, race_name, notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (race_date, race_name, notes, now_iso, now_iso),
                )
                conn.commit()
                new_id = cur.lastrowid
            return jsonify({'ok': True, 'id': new_id})

        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT * FROM race_events
                ORDER BY race_date ASC, id ASC
                '''
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/races/<int:race_id>', methods=['DELETE'])
    def delete_race_event(race_id: int) -> Any:
        with get_db() as conn:
            conn.execute('DELETE FROM race_events WHERE id = ?', (race_id,))
            conn.commit()
        return jsonify({'ok': True})

    @app.route('/api/goals', methods=['GET', 'POST'])
    def goals_api() -> Any:
        if request.method == 'POST':
            payload = request.get_json(silent=True) or {}
            goal_type = (payload.get('goal_type') or '').strip().lower()
            title = (payload.get('title') or '').strip()
            notes = (payload.get('notes') or '').strip()
            target_unit = ''
            target_value = None
            due_date = ''
            weekly_completion_date = (payload.get('weekly_completion_date') or '').strip()
            final_target_time = (payload.get('final_target_time') or '').strip()
            final_target_event = (payload.get('final_target_event') or '').strip()
            final_target_date = (payload.get('final_target_date') or '').strip()
            weekly_target_hours = None
            weekly_target_miles = None
            weekly_target_gain_ft = None
            weekly_percent_change = None
            weekly_race_goal = ''
            week_key = ''

            if goal_type not in ('weekly', 'final'):
                return jsonify({'ok': False, 'error': 'goal_type must be weekly or final'}), 400

            if goal_type == 'weekly':
                try:
                    weekly_completion_date = normalize_date_input(weekly_completion_date, 'weekly_completion_date')
                except ValueError as exc:
                    return jsonify({'ok': False, 'error': str(exc)}), 400
                if not title:
                    title = f'Weekly Goal {weekly_completion_date}'
                week_key = monday_key_for_iso(weekly_completion_date + 'T00:00:00')
                try:
                    weekly_target_hours = parse_flexible_number(payload.get('weekly_target_hours'), 'weekly_target_hours')
                    weekly_target_miles = parse_flexible_number(payload.get('weekly_target_miles'), 'weekly_target_miles')
                    weekly_target_gain_ft = parse_flexible_number(payload.get('weekly_target_gain_ft'), 'weekly_target_gain_ft')
                    weekly_percent_change = parse_flexible_number(payload.get('weekly_percent_change'), 'weekly_percent_change')
                    weekly_race_goal = (payload.get('weekly_race_goal') or '').strip()
                except ValueError as exc:
                    return jsonify({'ok': False, 'error': str(exc)}), 400
            else:
                if not title:
                    return jsonify({'ok': False, 'error': 'title is required'}), 400
                if not final_target_event:
                    return jsonify({'ok': False, 'error': 'final_target_event is required'}), 400
                if not final_target_date:
                    return jsonify({'ok': False, 'error': 'final_target_date is required'}), 400
                if not final_target_time:
                    return jsonify({'ok': False, 'error': 'final_target_time is required'}), 400
                try:
                    final_target_date = normalize_date_input(final_target_date, 'final_target_date')
                except ValueError as exc:
                    return jsonify({'ok': False, 'error': str(exc)}), 400

            now_iso = datetime.now().isoformat(timespec='seconds')

            with get_db() as conn:
                cur = conn.execute(
                    '''
                    INSERT INTO goals (
                        goal_type, title, target_value, target_unit, week_key, due_date,
                        weekly_completion_date, weekly_target_hours, weekly_target_miles, weekly_target_gain_ft, weekly_percent_change, weekly_race_goal,
                        final_target_time, final_target_event, final_target_date,
                        notes, completed, completed_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, ?, ?)
                    ''',
                    (
                        goal_type,
                        title,
                        target_value,
                        target_unit,
                        week_key if week_key else None,
                        due_date if due_date else None,
                        weekly_completion_date if weekly_completion_date else None,
                        weekly_target_hours,
                        weekly_target_miles,
                        weekly_target_gain_ft,
                        weekly_percent_change,
                        weekly_race_goal if weekly_race_goal else None,
                        final_target_time if final_target_time else None,
                        final_target_event if final_target_event else None,
                        final_target_date if final_target_date else None,
                        notes,
                        now_iso,
                        now_iso,
                    ),
                )
                conn.commit()
                goal_id = cur.lastrowid
            return jsonify({'ok': True, 'id': goal_id})

        with get_db() as conn:
            rows = conn.execute(
                '''
                SELECT * FROM goals
                ORDER BY
                    completed ASC,
                    CASE goal_type WHEN 'weekly' THEN 0 ELSE 1 END ASC,
                    COALESCE(weekly_completion_date, final_target_date, week_key, due_date, created_at) ASC,
                    id ASC
                '''
            ).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.route('/api/goals/<int:goal_id>/complete', methods=['POST'])
    def complete_goal(goal_id: int) -> Any:
        payload = request.get_json(silent=True) or {}
        completed = bool(payload.get('completed', True))
        send_watch_notification = bool(payload.get('send_watch_notification', True))
        now_iso = datetime.now().isoformat(timespec='seconds')

        with get_db() as conn:
            row = conn.execute('SELECT * FROM goals WHERE id = ?', (goal_id,)).fetchone()
            if row is None:
                return jsonify({'ok': False, 'error': 'goal not found'}), 404
            conn.execute(
                '''
                UPDATE goals
                SET completed = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
                ''',
                (
                    1 if completed else 0,
                    now_iso if completed else None,
                    now_iso,
                    goal_id,
                ),
            )
            conn.commit()
            updated = conn.execute('SELECT * FROM goals WHERE id = ?', (goal_id,)).fetchone()

        watch_result = {'sent': False, 'message': 'Notification not requested.'}
        if completed and send_watch_notification:
            watch_result = write_watch_goal_notification(dict(updated))

        return jsonify({'ok': True, 'goal': dict(updated), 'watch_notification': watch_result})

    @app.route('/api/goals/<int:goal_id>', methods=['DELETE'])
    def delete_goal(goal_id: int) -> Any:
        with get_db() as conn:
            conn.execute('DELETE FROM goals WHERE id = ?', (goal_id,))
            conn.commit()
        return jsonify({'ok': True})

    @app.route('/api/activities/<int:activity_id>/timeseries', methods=['GET'])
    def activity_timeseries(activity_id: int) -> Any:
        with get_db() as conn:
            row = conn.execute(
                'SELECT timeseries_path FROM activities WHERE id = ?', (activity_id,)
            ).fetchone()
        if row is None:
            return jsonify({'error': 'not found'}), 404

        ts_path = DATA_DIR / row['timeseries_path']
        if not ts_path.exists():
            return jsonify({'error': 'timeseries missing'}), 404

        return jsonify(json.loads(ts_path.read_text(encoding='utf-8')))

    @app.route('/plots/<path:filename>', methods=['GET'])
    def plot_file(filename: str) -> Any:
        return send_from_directory(PLOTS_DIR, filename)

    @app.route('/api/import-watch', methods=['POST'])
    def import_watch() -> Any:
        payload = request.get_json(silent=True) or {}
        requested_path = payload.get('watch_path')
        watch_path = Path(requested_path) if requested_path else DEFAULT_WATCH_ACTIVITY_PATH

        if not watch_path.exists() or not watch_path.is_dir():
            detected = detect_watch_activity_path()
            if detected is not None:
                watch_path = detected
            else:
                mounted_volumes = []
                volumes_root = Path('/Volumes')
                if volumes_root.exists():
                    mounted_volumes = sorted(
                        [p.name for p in volumes_root.iterdir() if p.name != 'Macintosh HD']
                    )
            return (
                jsonify(
                    {
                        'ok': False,
                        'error': f'Watch activity path not found: {watch_path}',
                        'hint': 'Connect/unlock the watch and wait for it to mount, then retry import.',
                        'mounted_volumes': mounted_volumes if 'mounted_volumes' in locals() else [],
                    }
                ),
                400,
            )

        fit_files = sorted(watch_path.glob('*.fit'))
        imported = 0
        skipped = 0
        messages: list[str] = []

        with get_db() as conn:
            for fit_file in fit_files:
                try:
                    was_imported, msg = import_activity_file(conn, fit_file)
                    if was_imported:
                        imported += 1
                    else:
                        skipped += 1
                    messages.append(msg)
                except Exception as exc:
                    messages.append(f'error on {fit_file.name}: {exc}')
            plans_marked_completed = reconcile_training_plan_completions(conn)
            conn.commit()

        return jsonify(
            {
                'ok': True,
                'watch_path': str(watch_path),
                'total_files': len(fit_files),
                'imported': imported,
                'skipped': skipped,
                'plans_marked_completed': plans_marked_completed,
                'messages': messages,
            }
        )

    return app


app = create_app()


def find_available_port(start_port: int, host: str = '127.0.0.1', max_tries: int = 25) -> int:
    for port in range(start_port, start_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if s.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f'No available port found in range {start_port}-{start_port + max_tries - 1}')


def detect_lan_ip() -> str | None:
    # Best-effort LAN IP detection for sharing on the same Wi-Fi.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        return None
    return None


if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1').strip() or '127.0.0.1'
    preferred_port = int(os.environ.get('PORT', '5055'))
    port = find_available_port(preferred_port, host=host, max_tries=25)
    if port != preferred_port:
        print(f'Port {preferred_port} is in use. Falling back to {port}.')
    print(f'Open http://{host}:{port}/')
    if host == '0.0.0.0':
        lan_ip = detect_lan_ip()
        if lan_ip:
            print(f'Share on same Wi-Fi: http://{lan_ip}:{port}/')
        else:
            print('Share mode is on, but LAN IP could not be detected automatically.')
    app.run(host=host, port=port, debug=False)
