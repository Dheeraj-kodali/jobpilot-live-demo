# JobPilot public demo

Read-only live job discovery. No private resumes, Gmail tokens, uploads, or email sending.

Render free web service:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/health`
- Instance: **Free** only. No database, disk, or paid add-ons.

Checks Anthropic's public Greenhouse board every 600 seconds while running. Free hosting sleeps when idle. First-seen counts reset on restart; first-seen is not publication time. This is a discovery demo, not the full personal automation app.
