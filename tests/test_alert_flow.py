import base64
import io
import json
import unittest
import asyncio
from unittest.mock import patch
from fastapi import HTTPException
from starlette.requests import Request
import zipfile
from alert_flow import parse_alert, canonical_url, build_packet, payload


class AlertFlow(unittest.TestCase):
    def test_signed_out_import_rejected(self):
        request = Request({'type': 'http', 'headers': []})
        with patch('alert_flow.same_origin'), patch('alert_flow.UserDB', side_effect=HTTPException(401)):
            with self.assertRaises(HTTPException) as error:
                asyncio.run(payload(request))
            self.assertEqual(error.exception.status_code, 401)

    def test_wrong_origin_rejected_before_identity(self):
        request = Request({'type': 'http', 'headers': []})
        with patch('alert_flow.same_origin', side_effect=HTTPException(403)), patch('alert_flow.UserDB') as identity:
            with self.assertRaises(HTTPException):
                asyncio.run(payload(request))
            identity.assert_not_called()

    def test_tracking_removed_but_requisitions_preserved(self):
        result = parse_alert('https://jobs.example/view?id=1&utm_source=email https://jobs.example/view?id=1 https://jobs.example/view?id=2')
        self.assertEqual(len(result['links']), 2)
        self.assertEqual(result['duplicates_removed'], 1)

    def test_mime_html_and_unsafe_links(self):
        result = parse_alert('MIME-Version: 1.0\nContent-Type: text/html; charset=utf-8\n\n<a href="javascript:alert(1)">bad</a><a href="https://jobs.example/1">Job</a>')
        self.assertEqual(result['links'], [{'url': 'https://jobs.example/1', 'status': 'Needs job details'}])
        self.assertIsNone(canonical_url('https://user:secret@example.com'))

    def test_packet_preserves_claims_and_has_line_evidence(self):
        source = 'TEST PERSON\nSkills\nPython\nProjects\nCSV tool\n- Created 3 reports.\nEducation\nDegree 2026'
        value = dict(file=base64.b64encode(source.encode()).decode(), kind='txt', title='Engineer at Example', url='https://jobs.example/1', description='Python engineer with Kubernetes experience required.')
        with zipfile.ZipFile(io.BytesIO(build_packet(value))) as archive:
            self.assertEqual(archive.read('resume.txt').decode(), source)
            report = json.loads(archive.read('evidence.json'))
            self.assertIn('kubernetes', report['not_evidenced_terms'])
            for item in report['evidence']:
                self.assertEqual(item['exact_text'], source.splitlines()[item['source_line']-1])
            self.assertTrue(archive.read('resume.pdf').startswith(b'%PDF'))
            self.assertNotIn('Kubernetes', archive.read('email-draft.txt').decode())

    def test_invalid_description_rejected(self):
        with self.assertRaises(ValueError):
            build_packet(dict(file=base64.b64encode(b'Original factual resume text').decode(), kind='txt', description='short'))
