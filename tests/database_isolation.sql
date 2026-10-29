-- Run only against an isolated PostgreSQL test database after migration.
-- auth.users and auth.uid() are minimal test fixtures, not Supabase Auth.
BEGIN;
INSERT INTO auth.users(id) VALUES ('00000000-0000-0000-0000-000000000001'),('00000000-0000-0000-0000-000000000002');
SET ROLE authenticated;
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000002',true);
INSERT INTO profiles(user_id,role) VALUES(auth.uid(),'Private B');
INSERT INTO resumes(id,user_id,source_text) VALUES('10000000-0000-0000-0000-000000000002',auth.uid(),'Private B resume source content.');
INSERT INTO claims(id,user_id,resume_id,section,exact_text,source_span) VALUES('20000000-0000-0000-0000-000000000002',auth.uid(),'10000000-0000-0000-0000-000000000002','projects','Original claim','{}');
INSERT INTO evidence_links(user_id,claim_id,url) VALUES(auth.uid(),'20000000-0000-0000-0000-000000000002','https://example.test/evidence');
INSERT INTO job_sources(id,user_id,ats,board_slug) VALUES('30000000-0000-0000-0000-000000000002',auth.uid(),'greenhouse','test');
INSERT INTO user_jobs(id,user_id,source_id,external_id,snapshot) VALUES('40000000-0000-0000-0000-000000000002',auth.uid(),'30000000-0000-0000-0000-000000000002','job','{}');
INSERT INTO applications(id,user_id,job_id,resume_id) VALUES('50000000-0000-0000-0000-000000000002',auth.uid(),'40000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002');
INSERT INTO application_events(user_id,application_id,event) VALUES(auth.uid(),'50000000-0000-0000-0000-000000000002','test');
SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);
DO $$
DECLARE t text; n integer;
BEGIN
 FOREACH t IN ARRAY ARRAY['profiles','resumes','claims','evidence_links','job_sources','user_jobs','applications','application_events'] LOOP
  EXECUTE format('SELECT count(*) FROM public.%I',t) INTO n;
  IF n<>0 THEN RAISE EXCEPTION 'Read isolation failed for %',t; END IF;
  EXECUTE format('UPDATE public.%I SET user_id=auth.uid()',t); GET DIAGNOSTICS n=ROW_COUNT;
  IF n<>0 THEN RAISE EXCEPTION 'Update isolation failed for %',t; END IF;
  EXECUTE format('DELETE FROM public.%I',t); GET DIAGNOSTICS n=ROW_COUNT;
  IF n<>0 THEN RAISE EXCEPTION 'Delete isolation failed for %',t; END IF;
 END LOOP;
 BEGIN
  INSERT INTO resumes(user_id,source_text) VALUES('00000000-0000-0000-0000-000000000002','Attempt to write another owner.');
  RAISE EXCEPTION 'Owner spoofing succeeded';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
 BEGIN
  INSERT INTO claims(user_id,resume_id,section,exact_text,source_span) VALUES(auth.uid(),'10000000-0000-0000-0000-000000000002','test','test','{}');
  RAISE EXCEPTION 'Cross-owner parent reference succeeded';
 EXCEPTION WHEN foreign_key_violation THEN NULL; END;
 INSERT INTO profiles(user_id,role) VALUES(auth.uid(),'Owned A');
 UPDATE profiles SET role='Updated A' WHERE user_id=auth.uid();
 IF (SELECT role FROM profiles WHERE user_id=auth.uid())<>'Updated A' THEN RAISE EXCEPTION 'Own update failed'; END IF;
 DELETE FROM profiles WHERE user_id=auth.uid();
END $$;
RESET ROLE;
SET ROLE anon;
DO $$ BEGIN
 BEGIN
  PERFORM * FROM public.resumes;
  RAISE EXCEPTION 'Anonymous read succeeded';
 EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE;
ROLLBACK;
SELECT 'PASS: RLS on eight tables, owner spoofing, parent ownership, own CRUD and anonymous denial' AS result;
