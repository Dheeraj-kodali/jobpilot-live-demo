# Account and Phase 1 activation

Existing infrastructure: Supabase accounts/provider_keys and Render configuration were connected earlier. Signup, email verification and saved-key generation were previously tested. The live two-account isolation test remains pending.

## Required environment (values stay outside Git)

SUPABASE_URL, SUPABASE_ANON_KEY (publishable/anonymous, never service-role), KEY_ENCRYPTION_KEY (Fernet), APP_ORIGIN (exact HTTPS origin).

Keep the encryption key stable; replacement without migration invalidates saved keys and sessions.

## Database

On existing installations, retain provider_keys. Apply migrations/001_user_workspace.sql once in a transaction with the database owner's migration access, before deploying this branch. On fresh installations, apply account-schema.sql first. Migration application is not performed automatically by app startup. These eight tables are newly added, not replacements for existing user data.

Owner-only RLS policies cover SELECT/INSERT/UPDATE/DELETE. Composite user_id/id foreign keys prevent cross-owner relationships. Client calls always use a signed-in user's access token; no user route uses a service-role key.

## Sessions

A fresh login issues encrypted Secure HttpOnly SameSite=Strict access and refresh cookies. Refresh cookies are scoped to /api/account and last up to 30 days. POST /api/account/refresh requires exact Origin. Browser refreshes on page load and every 45 minutes; provider expiration or revocation can still require login. Logout deletes both cookies, but does not revoke upstream sessions. Concurrent tabs and refresh-token reuse need live checks.

## Live acceptance checks still required

1. Apply migration in a test database and confirm all policies and constraints.
2. Create two test users. A cannot select/update/delete B's records, insert a record owned by B, or reference B's resume/claim/job/application from an A-owned row. Test directly with user JWTs, not only through the app helper.
3. Sign in again, save a profile and explicitly opt into resume text persistence. With opt-in false no resume row should be created.
4. Check expired access-token renewal, invalid/revoked refresh handling, logout, and two concurrent tabs.
5. Check anonymous access rejection, wrong-origin mutations, invalid upload rejection and saved-key generation.
6. Confirm no user content or token values appear in application logs.

The Phase 1 production migration was applied on 29 October 2026 after approval. Application deployment and live two-account Auth/API tests remain pending.

## Database verification completed 29 October 2026

Migration executed successfully in an isolated local PostgreSQL 17 cluster. tests/database_isolation.sql passed: owner read/update/delete isolation on all eight tables, insert owner spoofing rejection, cross-owner resume reference rejection, own profile CRUD, and anonymous read denial. Test records rolled back and the temporary server was stopped. auth.users/auth.uid() were test fixtures; this does not validate Supabase Auth or production roles. Live schema inspection found only provider_keys with RLS enabled. No live migration was executed.

## Live migration applied 29 October 2026

The approved 001 migration completed successfully in JobPilot Supabase. A subsequent pg_tables/pg_policies query returned all eight new tables with rowsecurity=true and owner_only policies restricting USING and WITH CHECK to auth.uid()=user_id for authenticated. Existing provider_keys retained its own_key policy. No existing keys were modified. This confirms schema and policy installation, not end-to-end two-user authentication or API behavior. The SQL Editor execution did not automatically register a Supabase CLI migration-history entry; reconcile history before adopting CLI migrations.
