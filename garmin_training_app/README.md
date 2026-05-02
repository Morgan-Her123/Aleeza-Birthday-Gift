# Garmin Training Log (Local Web App)

A local browser app (Chrome/Firefox) that imports activities from a connected Garmin watch and logs all training sessions.

## Features
- One-click import from watch folder (`/Volumes/GARMIN/GARMIN/Activity` by default)
- Stores sessions in local SQLite (`data/training.db`)
- Deduplicates by file hash/source
- Miles/feet/mph conversion
- Per-activity time series saved as JSON
- Auto-generated key-spec graphs (speed/cadence/HR/elevation gain vs time)

## Run
```bash
cd "/Users/minghe/Documents/New project/garmin_training_app"
python3 -m pip install --user -r requirements.txt
python3 server.py
```

Then open:
- http://127.0.0.1:5055

## Notes
- Keep your watch connected before clicking **Import From Connected Watch**.
- If your mount path differs, update it in the input field and import.
