# JobPilot public demo

Live job discovery plus request-local resume PDF generation. No Gmail tokens or email sending. Uploads are read into bounded memory; no resume is written to disk or shared application state.

Render free web service:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/health`
- Instance: **Free** only. No database, disk, or paid add-ons.

Checks Anthropic's public Greenhouse board every 600 seconds while running. Free hosting sleeps when idle. First-seen counts reset on restart; first-seen is not publication time. Resume tailoring ranks original project blocks; it does not perform AI rewriting. Accepts text PDFs up to 10 pages or UTF-8 TXT, up to 2 MB. This is not the full personal automation app.
