"""Public, read-only JobPilot demo. No resumes, credentials or email transport."""
import html
import threading
from datetime import datetime, timezone
from pathlib import Path
import requests
from fastapi import FastAPI
from fastapi.responses import FileResponse

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
