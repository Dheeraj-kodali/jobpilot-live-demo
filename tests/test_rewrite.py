import json
import unittest
from unittest.mock import Mock,patch
import requests
from ai_rewrite import rewrite,RewriteError

SOURCE='TEST CANDIDATE\nPROJECTS\n- Created 3 reports from sample data.\nEDUCATION\nDegree, 2026'
class RewriteTests(unittest.TestCase):
 def response(self,bullets):
  r=Mock(status_code=200);r.json.return_value={'choices':[{'message':{'content':json.dumps({'bullets':bullets})}}]};return r
 def test_valid_numeric_bullet_and_fixed_fields(self):
  with patch('ai_rewrite.requests.post',return_value=self.response({'2':'Created 3 reports using sample data.'})):
   result=rewrite(SOURCE,'Python reporting','x'*25)
   self.assertIn('Created 3 reports using sample data.',result);self.assertIn('Degree, 2026',result)
 def test_rejections_identify_category(self):
  cases=[({'2':'Created three reports.'},'numeric evidence'),({'2':'Created 3 reports with 3 dashboards.'},'numeric evidence'),({'7':'Created 3 reports.'},'bullet IDs'),({'2':'Created 3 reports at https://example.test'},'link'),({'2':''},'format')]
  for bullets,error in cases:
   with self.subTest(error=error),patch('ai_rewrite.requests.post',return_value=self.response(bullets)):
    with self.assertRaisesRegex(RewriteError,error): rewrite(SOURCE,'Python reporting','x'*25)
 def test_malformed_provider_response(self):
  r=Mock(status_code=200);r.json.return_value={}
  with patch('ai_rewrite.requests.post',return_value=r):
   with self.assertRaisesRegex(RewriteError,'unreadable'): rewrite(SOURCE,'Python reporting','x'*25)
 def test_timeout_is_distinct(self):
  with patch('ai_rewrite.requests.post',side_effect=requests.Timeout()):
   with self.assertRaisesRegex(RewriteError,'timed out'): rewrite(SOURCE,'Python reporting','x'*25)
 def test_quota_rejection(self):
  with patch('ai_rewrite.requests.post',return_value=Mock(status_code=429)):
   with self.assertRaisesRegex(RewriteError,'limit reached'): rewrite(SOURCE,'Python reporting','x'*25)
