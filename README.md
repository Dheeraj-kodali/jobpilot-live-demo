# JobPilot public demo

Live job discovery plus request-local resume PDF generation. No Gmail tokens or email sending. Uploads are read into bounded memory; no resume is written to disk or shared application state.

Render free web service:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check: `/health`
- Instance: **Free** only. No database, disk, or paid add-ons.

Checks Anthropic's public Greenhouse board every 600 seconds while running. Free hosting sleeps when idle. First-seen counts reset on restart; first-seen is not publication time. Resume tailoring ranks original project blocks; it does not perform AI rewriting. Accepts text PDFs up to 10 pages or UTF-8 TXT, up to 2 MB. This is not the full personal automation app.

## Optional AI rewriting

Groq mode rewrites recognized bullets only. Explicit consent and a per-request key are required; keys and resume content are not stored by the app. Only bullet text and the job description go to Groq, which may still contain personal information. Fixed fields remain unchanged and numerical changes are rejected. These checks do not prove semantic accuracy; users must review output. No automatic provider retries or paid subscriptions are enabled. Free-tier quota may be exhausted. Mocked provider checks passed; a live request with a user key is still required.
