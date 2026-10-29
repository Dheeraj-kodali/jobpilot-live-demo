# JobPilot public demo

FastAPI job discovery and resume tailoring, with Supabase accounts and an optional personal workspace. This branch implements Phase 1; its workspace migration was applied to Supabase on 29 October 2026; application deployment remains pending.

## Existing public features

- Anthropic Greenhouse job feed, title/location filters, refresh every 600 seconds while the process runs.
- First-seen is not publication time. Cache resets on restart; Render Free may sleep. No continuous polling guarantee.
- Request-local PDF/TXT resume generation. PDF up to ten pages, decoded input under 2 MB, JSON request under 3 MB.
- Source-preserving project ranking or optional Groq bullet rewriting. Consent is required for sharing bullets and job descriptions; keys may be supplied per request or saved encrypted per account.
- Rewrite checks reduce risk but do not establish semantic accuracy. Review output.
- No Gmail delivery, universal scraping, or automatic job application in this deployment.

## Phase 1 branch

- Numbered migration `migrations/001_user_workspace.sql` adds profiles, resumes, claims, evidence_links, job_sources, user_jobs, applications and application_events. Existing provider_keys is unchanged.
- Every table has owner-only RLS; composite foreign keys prevent cross-owner parent references.
- GET/PUT /api/profile: role, location, skills, experience, minimum salary/currency, workplace, job type and posting age.
- POST /api/resumes: same base64 JSON file/kind format as tailoring, with optional boolean store_text. Only literal true persists extracted text; otherwise it returns extracted text without storing. Requires login and same-origin request. Original uploaded files are not saved.
- GET /api/applications returns at most 100 current-user records. Application creation and pagination UI are later work.
- These workspace endpoints do not yet have profile/resume management screens.
- POST /api/account/refresh rotates encrypted HttpOnly refresh and access cookies. Browser renews on load, every 45 minutes and on eligible 401 responses. Refresh cookie lifetime is 30 days, subject to upstream revocation/session settings. Existing users need one new login to receive it.
- Logout clears both cookies; upstream token revocation is not implemented. Cross-tab refresh coordination remains a hardening item.

## Run and test

Build: pip install -r requirements.txt
Start: uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1
Tests: python -B -m unittest discover -s tests -v
Health: /health (process liveness, not provider readiness)

No passwords or keys belong in Git. See ACCOUNT_SETUP.md for migration and environment setup.

## Verification limits

Local mocked tests cover owner-scoped requests and session behavior; they do not prove database RLS. Earlier live tests verified saved-key Groq generation and an Oracle-targeted resume. The Phase 1 schema and owner policies were verified on Supabase. Live two-account isolation, session expiry/rotation, and new workspace routes still need production verification. No real emails have been sent.
