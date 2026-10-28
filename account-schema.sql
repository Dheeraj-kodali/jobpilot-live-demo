create table public.provider_keys (
  user_id uuid primary key references auth.users(id) on delete cascade,
  ciphertext text not null
);
alter table public.provider_keys enable row level security;
revoke all on public.provider_keys from anon;
grant select, insert, update, delete on public.provider_keys to authenticated;
create policy own_key on public.provider_keys for all to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);
