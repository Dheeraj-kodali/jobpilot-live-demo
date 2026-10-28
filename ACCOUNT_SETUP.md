# Account activation checklist

Not active until a Supabase project and Render environment are configured.

1. Create a free Supabase project owned by the user. Keep email confirmation enabled.
2. Run account-schema.sql. Verify with two real test accounts that each can only select/update/delete its own encrypted row. Anonymous table access must fail.
3. In Render add SUPABASE_URL, SUPABASE_ANON_KEY (publishable/anon, never service-role), KEY_ENCRYPTION_KEY (a generated Fernet key), APP_ORIGIN=https://jobpilot-live-demo.onrender.com. Do not commit secret values.
4. Keep the encryption key stable across deployments. Replacing it invalidates existing saved provider keys.
5. Configure Supabase Site URL to the deployed app origin. Configure email delivery and provider rate limits as needed for public signup.
6. Test signup, email verification, login, saved-key generation, logout, key deletion, expiry and cross-account isolation before enabling for users.

Sessions use encrypted Secure HttpOnly SameSite=Strict cookies and expire after one hour. Passwords are forwarded to Supabase over HTTPS, not stored by this app. Provider keys are encrypted before insertion and accessed with the authenticated user's token plus RLS. No account configuration or live cross-user test has been completed yet.
