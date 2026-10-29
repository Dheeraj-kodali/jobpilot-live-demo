import base64
import asyncio
import json
import unittest
from unittest.mock import patch
from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request
import accounts
from db import UserDB
from workspace import extract, Profile

class PhaseOne(unittest.TestCase):
 def setUp(self):
  self.cipher=Fernet(Fernet.generate_key())
  self.cfg=patch('accounts.config',return_value=('https://example.test','public',self.cipher,'https://app.test'));self.cfg.start();self.addCleanup(self.cfg.stop)
 def request(self,origin='https://app.test',cookie=''):
  return Request({'type':'http','headers':[(b'origin',origin.encode()),(b'cookie',cookie.encode())]})
 def test_owner_filters_on_read_update_delete(self):
  for owner in ['user-a','user-b']:
   with patch('db.identity',return_value=('token-'+owner,owner)),patch('db.remote',return_value=[]) as remote:
    db=UserDB(self.request())
    for method in ['GET','PATCH','DELETE']:
     db.query('resumes',method,{'source_text':'a'*20} if method=='PATCH' else None)
     args,kwargs=remote.call_args
     self.assertEqual(args[2],'token-'+owner);self.assertEqual(kwargs['params']['user_id'],'eq.'+owner)
 def test_owner_override_rejected(self):
  with patch('db.identity',return_value=('token','user-a')),patch('db.remote') as remote:
   with self.assertRaises(HTTPException) as error: UserDB(self.request()).query('profiles','POST',{'user_id':'user-b'})
   self.assertEqual(error.exception.status_code,403);remote.assert_not_called()
 def test_auth_failure_prevents_database_access(self):
  with patch('db.identity',side_effect=HTTPException(401)),patch('db.remote') as remote:
   with self.assertRaises(HTTPException): UserDB(self.request())
   remote.assert_not_called()
 def test_database_failure_propagates(self):
  with patch('db.identity',return_value=('token','a')),patch('db.remote',side_effect=HTTPException(503)):
   with self.assertRaises(HTTPException): UserDB(self.request()).query('profiles')
 def test_refresh_rotates_both_encrypted_cookies(self):
  old=self.cipher.encrypt(b'old-refresh').decode()
  with patch('accounts.remote',return_value={'access_token':'new-access','refresh_token':'new-refresh'}) as remote:
   response=accounts.refresh_session(self.request(cookie=accounts.REFRESH_COOKIE+'='+old))
   self.assertEqual(remote.call_args.kwargs['json'],{'refresh_token':'old-refresh'})
   cookies=response.headers.getlist('set-cookie');self.assertEqual(len(cookies),2)
   for cookie in cookies:
    self.assertIn('HttpOnly',cookie);self.assertIn('Secure',cookie);self.assertIn('SameSite=strict',cookie)
    self.assertNotIn('new-access',cookie);self.assertNotIn('new-refresh',cookie)
 def test_refresh_wrong_origin(self):
  with patch('accounts.remote') as remote:
   with self.assertRaises(HTTPException) as e: accounts.refresh_session(self.request(origin='https://other.test'))
   self.assertEqual(e.exception.status_code,403);remote.assert_not_called()
 def test_refresh_bad_cookie(self):
  with self.assertRaises(HTTPException) as e: accounts.refresh_session(self.request(cookie=accounts.REFRESH_COOKIE+'=invalid'))
  self.assertEqual(e.exception.status_code,401)
 def test_logout_clears_both_cookies(self):
  self.assertEqual(len(accounts.logout(self.request()).headers.getlist('set-cookie')),2)
 def test_extract_text(self):
  text='Original source resume with factual details.'
  self.assertEqual(extract({'kind':'txt','file':base64.b64encode(text.encode()).decode()}),text)
 def test_reject_invalid_upload(self):
  for payload in [{'kind':'txt','file':'!'}, {'kind':'exe','file':'YWJj'}, {'kind':'pdf','file':'YWJj'}]:
   with self.assertRaises(Exception): extract(payload)
 def test_profile_rejects_owner_injection(self):
  with self.assertRaises(ValueError): Profile(user_id='someone-else')
 def test_profile_rejects_invalid_preferences(self):
  for value in [{'experience':-1},{'min_salary':-1},{'max_posting_age':0},{'currency':'invalid'}]:
   with self.assertRaises(ValueError): Profile(**value)

 def test_resume_storage_requires_explicit_opt_in(self):
  from workspace import resume
  for opt_in in [False, None, 'true', True]:
   payload={'kind':'txt','file':base64.b64encode(b'Original resume evidence and details.').decode(),'store_text':opt_in}
   class Upload:
    async def stream(self): yield json.dumps(payload).encode()
   with patch('workspace.same_origin'),patch('workspace.UserDB') as db:
    db.return_value.query.return_value=[{'id':'saved'}]
    response=asyncio.run(resume(Upload()))
    self.assertEqual(json.loads(response.body)['stored'],opt_in is True)
    self.assertEqual(db.return_value.query.called,opt_in is True)

if __name__=='__main__': unittest.main()
