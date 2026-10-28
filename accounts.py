"""Optional Supabase accounts and per-user encrypted provider credentials."""
import os
import secrets
from urllib.parse import urlparse
import requests
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from pydantic import BaseModel, Field

router=APIRouter()
COOKIE='jobpilot_session'

def config():
    values=[os.getenv(k,'') for k in ('SUPABASE_URL','SUPABASE_ANON_KEY','KEY_ENCRYPTION_KEY','APP_ORIGIN')]
    if not all(values): raise HTTPException(503,'Account setup is not connected yet. Existing request-only mode is available.')
    url,key,encryption,origin=values
    if urlparse(url).scheme!='https' or urlparse(origin).scheme!='https':
        raise HTTPException(503,'Account configuration requires HTTPS.')
    try: cipher=Fernet(encryption.encode())
    except Exception: raise HTTPException(503,'Account encryption is not configured.')
    return url.rstrip('/'),key,cipher,origin.rstrip('/')

def remote(method,path,token=None,**kwargs):
    url,key,_,_=config()
    headers={'apikey':key}
    if token: headers['Authorization']='Bearer '+token
    headers.update(kwargs.pop('headers',{}))
    try:
        r=requests.request(method,url+path,headers=headers,timeout=15,**kwargs)
        if not r.ok:
            try: code=r.json().get('code','')
            except (ValueError, AttributeError): code=''
            messages={
                'email_not_confirmed':'Please verify your email first. Open the confirmation email (also check Spam), click its link, then sign in.',
                'invalid_credentials':'Email or password is incorrect. Use the password you chose when creating your JobPilot account.',
                'over_email_send_rate_limit':'Too many verification emails requested. Wait a few minutes before trying again.',
                'over_request_rate_limit':'Too many attempts. Please wait a few minutes and try again.',
                'user_already_exists':'An account already exists. Verify your email, then choose Sign in.',
                'weak_password':'Choose a stronger password with at least eight characters.',
                'email_address_invalid':'Enter a valid email address.',
            }
            raise HTTPException(400,messages.get(code,'Account request failed. Please check your details or try again later.'))
        return r.json() if r.content else None
    except requests.RequestException: raise HTTPException(503,'Account service is temporarily unavailable.') from None

def same_origin(request):
    if request.headers.get('origin')!=config()[3]: raise HTTPException(403,'Open this form on the JobPilot site.')

def identity(request):
    _,_,cipher,_=config()
    try: token=cipher.decrypt(request.cookies.get(COOKIE,'').encode(),ttl=3600).decode()
    except (InvalidToken,ValueError): raise HTTPException(401,'Please sign in.')
    user=remote('GET','/auth/v1/user',token)
    if not user or not user.get('id'): raise HTTPException(401,'Please sign in again.')
    return token,user['id']

def saved_key(request):
    token,uid=identity(request)
    rows=remote('GET','/rest/v1/provider_keys',token,params={'user_id':'eq.'+uid,'select':'ciphertext'})
    if not rows: raise HTTPException(400,'Save your Groq key in Account first.')
    try: return config()[2].decrypt(rows[0]['ciphertext'].encode()).decode()
    except InvalidToken: raise HTTPException(503,'Saved key could not be unlocked. Save it again.')

class Credentials(BaseModel):
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(min_length=8,max_length=128)

class ProviderKey(BaseModel):
    key:str=Field(min_length=20,max_length=300)

@router.get('/account')
def account_page(): return FileResponse(Path(__file__).with_name('account.html'))

@router.get('/api/account')
def account_status(request:Request):
    response={'configured':False,'signed_in':False,'key_saved':False}
    try: config();response['configured']=True
    except HTTPException: return JSONResponse(response,headers={'Cache-Control':'no-store'})
    if request.cookies.get(COOKIE):
        try:
            token,uid=identity(request)
            rows=remote('GET','/rest/v1/provider_keys',token,params={'user_id':'eq.'+uid,'select':'user_id'})
            response.update(signed_in=True,key_saved=bool(rows))
        except HTTPException: pass
    return JSONResponse(response,headers={'Cache-Control':'no-store'})

@router.post('/api/account/signup')
def signup(value:Credentials,request:Request):
    same_origin(request)
    remote('POST','/auth/v1/signup',json=value.model_dump())
    return {'message':'Check your email to verify your account, then sign in.'}

@router.post('/api/account/login')
def login(value:Credentials,request:Request):
    same_origin(request)
    result=remote('POST','/auth/v1/token?grant_type=password',json=value.model_dump())
    if not result or not result.get('access_token'): raise HTTPException(401,'Sign-in failed.')
    response=JSONResponse({'message':'Signed in.'},headers={'Cache-Control':'no-store'})
    response.set_cookie(COOKIE,config()[2].encrypt(result['access_token'].encode()).decode(),
                        httponly=True,secure=True,samesite='strict',max_age=3600)
    return response

@router.post('/api/account/logout')
def logout(request:Request):
    same_origin(request)
    response=JSONResponse({'message':'Signed out.'})
    response.delete_cookie(COOKIE,secure=True,httponly=True,samesite='strict')
    return response

@router.post('/api/account/key')
def save_key(value:ProviderKey,request:Request):
    same_origin(request);token,uid=identity(request)
    encrypted=config()[2].encrypt(value.key.strip().encode()).decode()
    remote('POST','/rest/v1/provider_keys',token,json={'user_id':uid,'ciphertext':encrypted},
           headers={'Prefer':'resolution=merge-duplicates'})
    return {'message':'Groq key saved encrypted for your account.'}

@router.delete('/api/account/key')
def remove_key(request:Request):
    same_origin(request);token,uid=identity(request)
    remote('DELETE','/rest/v1/provider_keys',token,params={'user_id':'eq.'+uid})
    return {'message':'Saved key removed.'}
