# Account activation checklist

Infrastructure configured on 2026-10-28: separate free Supabase project, schema applied, Render environment saved and redeployed, and confirmation Site URL set to the account page. Live account status reports configured. Unsigned key saves return 401 and cross-origin saves return 403. User signup, email verification, saved-key generation, and two-account isolation tests are still pending.

1. Create a free Supabase project owned by the user. Keep email confirmation enabled.
2. Run account-schema.sql. Verify with two real test accounts that each can only select/update/delete its own encrypted row. Anonymous table access must fail.
3. In Render add SUPABASE_URL, SUPABASE_ANON_KEY (publishable/anon, never service-role), KEY_ENCRYPTION_KEY (a generated Fernet key), APP_ORIGIN=https://jobpilot-live-demo.onrender.com. Do not commit secret values.
4. Keep the encryption key stable across deployments. Replacing it invalidates existing saved provider keys.
5. Configure Supabase Site URL to the deployed app origin. Configure email delivery and provider rate limits as needed for public signup.
6. Test signup, email verification, login, saved-key generation, logout, key deletion, expiry and cross-account isolation before enabling for users.

Sessions use encrypted Secure HttpOnly SameSite=Strict cookies and expire after one hour. Passwords are forwarded to Supabase over HTTPS, not stored by this app. Provider keys are encrypted before insertion and accessed with the authenticated user's token plus RLS. Account infrastructure is configured; live cross-user and signed-in saved-key tests remain pending.
