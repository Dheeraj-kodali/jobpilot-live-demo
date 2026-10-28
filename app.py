"""Public JobPilot demo. Resume processing is request-local; no email transport."""
import html
import threading
from datetime import datetime, timezone
from pathlib import Path
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, Response

app = FastAPI(docs_url=None, redoc_url=None)
lock = threading.Lock()
stop = threading.Event()
cache = {'jobs': [], 'last_success': None, 'error': None, 'new_count': 0}

def refresh():
    try:
        response = requests.get('https://boards-api.greenhouse.io/v1/boards/anthropic/jobs', timeout=25)
        response.raise_for_status()
        payload = response.json()['jobs']
        stamp = datetime.now(timezone.utc).isoformat()
        with lock:
            known = {j['id']:j for j in cache['jobs']}
            jobs = []
            for item in payload:
                url = item['absolute_url']
                if not url.startswith('https://'): continue
                jobs.append(dict(id=item['id'], title=html.unescape(item['title']),
                    location=item.get('location',{}).get('name','Not disclosed'), url=url,
                    first_seen=known.get(item['id'],{}).get('first_seen',stamp)))
            cache.update(jobs=jobs,last_success=stamp,error=None,
                new_count=sum(j['id'] not in known for j in jobs))
    except Exception:
        with lock: cache['error']='The job feed is temporarily unavailable. Previous results remain visible.'

def run():
    while not stop.is_set():
        refresh()
        stop.wait(600)

@app.on_event('startup')
def startup():
    stop.clear()
    threading.Thread(target=run,daemon=True).start()

@app.on_event('shutdown')
def shutdown(): stop.set()

@app.get('/')
def home(): return FileResponse(Path(__file__).with_name('index.html'))

@app.get('/health')
def health(): return {'status':'ok'}

@app.get('/api/jobs')
def jobs():
    with lock: return dict(cache)


@app.post('/api/tailor')
async def tailor_resume(request: Request):
    import base64, binascii, io, json
    from pypdf import PdfReader
    from tailoring import tailor
    from resume_layout import render_pdf
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>3000000: raise HTTPException(413,'Resume request must be under 3 MB')
    try:
        payload=json.loads(data)
        description=payload['description']
        if not isinstance(description,str) or not 20<=len(description)<=20000:
            raise ValueError()
        raw=base64.b64decode(payload['file'],validate=True)
        if len(raw)>2000000: raise ValueError()
        kind=payload['kind']
        if kind=='pdf':
            reader=PdfReader(io.BytesIO(raw))
            if reader.is_encrypted or len(reader.pages)>10: raise ValueError()
            source='\n'.join(page.extract_text() or '' for page in reader.pages)
        elif kind=='txt': source=raw.decode('utf-8-sig')
        else: raise ValueError()
        if not 20<=len(source)<=30000: raise ValueError()
    except Exception:
        raise HTTPException(400,'Use a text-based PDF (up to 10 pages) or UTF-8 TXT under 2 MB, and a job description of 20–20,000 characters.')
    if payload.get('mode')=='ai':
        if payload.get('consent') is not True: raise HTTPException(400,'Confirm sharing the bullet text and job description with Groq.')
        from ai_rewrite import rewrite, RewriteError
        from starlette.concurrency import run_in_threadpool
        try: source=await run_in_threadpool(rewrite,source,description,payload.get('key',''))
        except RewriteError as exc: raise HTTPException(400,str(exc))
    result,report=tailor(source,description)
    return Response(render_pdf(result),media_type='application/pdf',headers={
        'Content-Disposition':'attachment; filename="jobpilot-tailored-resume.pdf"',
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
