"""Opt-in personal workspace API."""
import base64
import io
import json
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool
from accounts import same_origin
from db import UserDB

router = APIRouter()


class Profile(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: str = Field(default='', max_length=500)
    location: str = Field(default='', max_length=300)
    skills: str = Field(default='', max_length=3000)
    experience: float = Field(default=0, ge=0, le=80)
    min_salary: float = Field(default=0, ge=0, le=1e12)
    currency: str = Field(default='INR', pattern=r'^[A-Z]{3}$')
    workplace: Literal['any', 'remote', 'hybrid', 'onsite'] = 'any'
    job_type: str = Field(default='', max_length=100)
    max_posting_age: int = Field(default=7, ge=1, le=365)


def private(data):
    return JSONResponse(data, headers={'Cache-Control': 'no-store'})


@router.get('/api/profile')
def profile(request: Request):
    rows = UserDB(request).query('profiles')
    return private(rows[0] if rows else Profile().model_dump())


@router.put('/api/profile')
def save_profile(value: Profile, request: Request):
    same_origin(request)
    return private(UserDB(request).query('profiles', 'POST', value.model_dump()))


@router.get('/api/applications')
def applications(request: Request):
    return private(UserDB(request).query('applications'))


def extract(payload):
    raw = base64.b64decode(payload['file'], validate=True)
    if len(raw) > 2_000_000:
        raise ValueError()
    if payload['kind'] == 'txt':
        text = raw.decode('utf-8-sig')
    elif payload['kind'] == 'pdf':
        pdf = PdfReader(io.BytesIO(raw))
        if pdf.is_encrypted or len(pdf.pages) > 10:
            raise ValueError()
        text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    else:
        raise ValueError()
    if not 20 <= len(text) <= 30_000:
        raise ValueError()
    return text


@router.post('/api/resumes')
async def resume(request: Request):
    same_origin(request)
    db = await run_in_threadpool(UserDB, request)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 3_000_000:
            raise HTTPException(413, 'Upload request is too large.')
    try:
        payload = json.loads(body)
        text = await run_in_threadpool(extract, payload)
    except Exception:
        raise HTTPException(400, 'Use a text PDF up to ten pages or UTF-8 TXT under 2 MB.') from None
    if payload.get('store_text') is not True:
        return private({'stored': False, 'text': text})
    rows = await run_in_threadpool(db.query, 'resumes', 'POST', {'source_text': text})
    return private({'stored': True, 'resume': rows[0]})
