OrbitCore (Flask) - Deployment Guide

This is a Flask app with templates under `templates/` and static assets under `static/`. The WSGI entrypoint is `backhand/app.py` exposing `app`.

Local run

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
$env:FLASK_DEBUG="1"; python backhand/app.py
```

App will start on http://localhost:5000

Deploy to Render (recommended free/simple)

1. Push this repo to GitHub.
2. Create a new Web Service on Render.
3. Select your repo and use these settings:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn backhand.app:app --preload --workers=2 --threads=4 --timeout=120`
   - Runtime: Python 3.10+ (default)
4. Render will set `PORT`; the app binds to `0.0.0.0:$PORT` automatically.

Deploy to Railway (alternative)

1. New Project → Deploy from GitHub.
2. Add a Service using your repo.
3. Set Start command: `gunicorn backhand.app:app`
4. Railway injects `PORT` automatically.

Notes
- Do not use `flask run` in production; WSGI server `gunicorn` is used via `Procfile`.
- Toggle debug locally with `FLASK_DEBUG=1`.
- Static and templates are configured via `Flask(..., template_folder=templates, static_folder=static)` in `backhand/app.py`.

