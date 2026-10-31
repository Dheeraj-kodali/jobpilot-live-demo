"""Request-local alert previews. No URL fetching, mailbox access or sending."""
import base64
import io
import json
import re
import zipfile
from email import policy
from email.parser import Parser
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from starlette.concurrency import run_in_threadpool
from accounts import same_origin
from db import UserDB
from workspace import extract, private
from tailoring import tailor, keywords
from resume_layout import render_pdf

router = APIRouter()


def canonical_url(value):
    try:
        p = urlsplit(value.strip().rstrip('.,;)'))
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            return None
        query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                 if not k.lower().startswith('utm_')]
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, urlencode(query), ''))
    except ValueError:
        return None


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)


def parse_alert(text):
    """Links are candidates, never inferred to be verified job postings."""
    candidates = []
    if re.search(r'(?im)^(subject|mime-version|content-type):', text):
        message = Parser(policy=policy.default).parsestr(text)
        bodies = []
        for part in message.walk():
            if part.get_content_disposition() == 'attachment':
                continue
            if part.get_content_type() in ('text/plain', 'text/html'):
                try:
                    bodies.append(part.get_content())
                except (LookupError, UnicodeError):
                    continue
    else:
        bodies = [text]
    for body in bodies:
        parser = Links(); parser.feed(body)
        candidates.extend(parser.links)
        candidates.extend(re.findall(r'https?://[^\s<>"\']+', body))
    unique = {}; duplicates = 0
    for raw in candidates:
        url = canonical_url(raw)
        if not url:
            continue
        if url in unique:
            duplicates += 1
        else:
            unique[url] = {'url': url, 'status': 'Needs job details'}
    return {'links': list(unique.values())[:100], 'duplicates_removed': duplicates,
            'truncated': len(unique) > 100,
            'notice': 'Links may include tracking or unsubscribe pages. Confirm the job and paste its description. No links were fetched.'}


async def payload(request):
    same_origin(request)
    await run_in_threadpool(UserDB, request)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 3_000_000:
            raise HTTPException(413, 'Request is too large.')
    try:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeError):
        raise HTTPException(400, 'Invalid request.') from None


@router.get('/alerts')
def page():
    return FileResponse(Path(__file__).with_name('alerts.html'))


@router.post('/api/alerts/preview')
async def preview(request: Request):
    value = await payload(request)
    text = value.get('text')
    if not isinstance(text, str) or not 20 <= len(text) <= 200_000:
        raise HTTPException(400, 'Paste an alert or upload an EML/TXT file under 200,000 characters.')
    return private(parse_alert(text))


def build_packet(value):
    source = extract(value)
    description = value.get('description', '')
    title = value.get('title', '')
    if not isinstance(description, str) or not 20 <= len(description) <= 20_000:
        raise ValueError()
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 200 or '\n' in title or '\r' in title:
        raise ValueError()
    url = canonical_url(value.get('url', ''))
    if not url:
        raise ValueError()
    result, report = tailor(source, description)
    target = keywords(description)
    evidence = [{'source_line': i, 'exact_text': line, 'matched_terms': sorted(keywords(line) & target)}
                for i, line in enumerate(source.splitlines(), 1) if line.strip()]
    report.update(source_url=url, evidence=evidence,
                  limitation='Keyword overlap is not a qualification assessment. Unmatched terms are not necessarily missing skills.',
                  status='Draft only; no application sent. Source facts are preserved, not independently verified.')
    email = f'Subject: Application for {title.strip()}\n\nHello,\n\nI would like to apply for the {title.strip()} position. I have attached my resume for your consideration.\n\nThank you for your time.\n'
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('resume.pdf', render_pdf(result))
        archive.writestr('resume.txt', result)
        archive.writestr('email-draft.txt', email)
        archive.writestr('evidence.json', json.dumps(report, indent=2, ensure_ascii=False))
    return output.getvalue()


@router.post('/api/alerts/packet')
async def packet(request: Request):
    value = await payload(request)
    try:
        result = await run_in_threadpool(build_packet, value)
    except Exception:
        raise HTTPException(400, 'Use a valid PDF/TXT resume, job link, title and description.') from None
    return Response(result, media_type='application/zip', headers={
        'Content-Disposition': 'attachment; filename="jobpilot-application-draft.zip"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
