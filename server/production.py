"""Deployable application; real WeChat credentials and hardware verification still required."""
import os
import asyncio
import threading
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Literal
import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, model_validator
from server.storage import Store, digest

class Model(BaseModel):
    model_config=ConfigDict(extra='forbid', strict=True)
class Login(Model):
    code: str = Field(min_length=1,max_length=256)
class Binding(Model):
    code: str = Field(min_length=16,max_length=128)
    name: str = Field(default='我的宠物', min_length=1,max_length=30)
class Mode(Model):
    mode: Literal['normal','finding']
class Point(Model):
    bootId: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    sequence: int = Field(ge=0,le=2**53-1)
    capturedAt: float = Field(gt=0,allow_inf_nan=False)
    latitude: float = Field(ge=-90,le=90,allow_inf_nan=False)
    longitude: float = Field(ge=-180,le=180,allow_inf_nan=False)
    coordinateSystem: Literal['wgs84','gcj02'] = 'wgs84'
    battery: float | None = Field(default=None,ge=0,le=100,allow_inf_nan=False)
    @model_validator(mode='after')
    def check_time(self):
        if self.capturedAt > time.time()+60 or self.capturedAt < time.time()-30*86400:
            raise ValueError('timestamp outside retained window')
        return self
class Heartbeat(Model):
    battery: float | None = Field(default=None,ge=0,le=100,allow_inf_nan=False)
    fixValid: bool
    appliedMode: Literal['normal','finding']
    firmware: str = Field(min_length=1,max_length=64)

class Limits:
    def __init__(self): self.lock=threading.Lock(); self.events=defaultdict(deque)
    def check(self,key,limit,window=60):
        now=time.monotonic()
        with self.lock:
            # Bound memory and clear idle clients; one process is the supported deployment.
            for stale in list(self.events):
                if not self.events[stale] or self.events[stale][-1] <= now-window:
                    del self.events[stale]
            values=self.events[key]
            while values and values[0] <= now-window: values.popleft()
            if len(values)>=limit: raise HTTPException(429,'请求过于频繁，请稍后重试',headers={'Retry-After':'60'})
            if len(self.events)>10000: raise HTTPException(503,'服务繁忙')
            values.append(now)

async def exchange(code):
    appid,secret=os.environ.get('WECHAT_APP_ID'),os.environ.get('WECHAT_APP_SECRET')
    if not appid or not secret: raise HTTPException(503,'微信登录尚未配置')
    try:
        async with httpx.AsyncClient(timeout=8,follow_redirects=False) as client:
            result=await client.get('https://api.weixin.qq.com/sns/jscode2session',params={
                'appid':appid,'secret':secret,'js_code':code,'grant_type':'authorization_code'})
        result.raise_for_status(); data=result.json()
    except (httpx.HTTPError,ValueError): raise HTTPException(502,'微信登录服务暂不可用')
    if not isinstance(data,dict) or data.get('errcode') or not isinstance(data.get('openid'),str) or not data['openid']:
        raise HTTPException(401,'微信登录失效，请重试')
    return data['openid']

def serialize(row):
    if row is None: return None
    return {'bootId':row['boot_id'],'sequence':row['sequence'],'capturedAt':row['captured_at'],
            'receivedAt':row['received_at'],'latitude':row['latitude'],'longitude':row['longitude'],
            'coordinateSystem':row['coordinate_system'],'battery':row['battery']}

def create_app(path=None, login_exchange=None):
    store=Store(path or os.environ.get('PAWTRACK_DB','data/pawtrack.sqlite3'))
    limiter=Limits(); login_exchange=login_exchange or exchange
    @asynccontextmanager
    async def lifespan(application):
        async def maintain():
            while True:
                await asyncio.to_thread(store.cleanup)
                await asyncio.sleep(3600)
        task=asyncio.create_task(maintain())
        try: yield
        finally:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
    app=FastAPI(lifespan=lifespan,title='PawTrack',version='1.0.0',docs_url=None,redoc_url=None,openapi_url=None)
    app.state.store=store
    bearer=HTTPBearer(auto_error=False)
    def token(credentials: HTTPAuthorizationCredentials | None=Depends(bearer)):
        if not credentials: raise HTTPException(401,'请先登录')
        return credentials.credentials
    def user(value=Depends(token)):
        result=store.user(value)
        if not result: raise HTTPException(401,'登录已过期，请重新登录')
        limiter.check('user:'+result,300)
        return result
    def device(value=Depends(token)):
        result=store.device(value)
        if not result: raise HTTPException(401,'设备身份无效')
        limiter.check('device:'+result,120)
        return result
    def own(device_id, user_id):
        row=store.owned(user_id,device_id)
        if not row: raise HTTPException(404,'设备不存在或未绑定')
        return row
    @app.middleware('http')
    async def boundary(request,call_next):
        # Reject oversized requests before JSON parsing; streaming cannot bypass this.
        if request.method in ('POST','PUT','PATCH'):
            body=bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body)>8192: return Response(status_code=413)
            request._body=bytes(body)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
    from fastapi.exceptions import RequestValidationError
    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422,content={'detail':'请求字段无效'})
    @app.exception_handler(Exception)
    async def internal_error(request, error):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500,content={'detail':'服务暂不可用'})
    @app.get('/health')
    def health():
        with store.connection() as con: con.execute('SELECT 1')
        return {'ok':True}
    @app.post('/v1/auth/wechat')
    async def login(body:Login,request:Request):
        limiter.check('login:'+(request.client.host if request.client else 'unknown'),10)
        openid=await login_exchange(body.code)
        return store.login(openid)
    @app.post('/v1/auth/logout',status_code=204)
    def logout(value=Depends(token)):
        with store.connection() as con: con.execute('DELETE FROM sessions WHERE digest=?',(digest(value),))
        return Response(status_code=204)
    @app.post('/v1/devices/bind')
    def bind(body:Binding,user_id=Depends(user)):
        limiter.check('bind:'+user_id,5)
        device_id=store.bind(user_id,body.code,body.name.strip() or '我的宠物')
        if not device_id: raise HTTPException(400,'绑定码无效、过期或已使用')
        return {'deviceId':device_id}
    @app.get('/v1/devices')
    def devices(user_id=Depends(user)):
        with store.connection() as con: rows=con.execute('SELECT id,name FROM devices WHERE owner_id=? ORDER BY id',(user_id,)).fetchall()
        return [{'id':row['id'],'name':row['name']} for row in rows]
    @app.post('/v1/devices/{device_id}/mode')
    def mode(device_id:str,body:Mode,user_id=Depends(user)):
        own(device_id,user_id)
        with store.connection() as con: cursor=con.execute('UPDATE devices SET desired_mode=? WHERE id=? AND owner_id=?',(body.mode,device_id,user_id))
        if cursor.rowcount != 1: raise HTTPException(404,'设备不存在或未绑定')
        return {'desiredMode':body.mode,'status':'pending-device-ack'}
    @app.get('/v1/devices/{device_id}/snapshot')
    def snapshot(device_id:str,user_id=Depends(user)):
        row=own(device_id,user_id)
        with store.connection() as con:
            latest=con.execute('SELECT p.* FROM points p JOIN devices d ON p.device_id=d.id WHERE p.device_id=? AND d.owner_id=? ORDER BY p.captured_at DESC,p.id DESC LIMIT 1',(device_id,user_id)).fetchone()
        last=serialize(latest)
        if last:
            last['ageSeconds']=max(0,int(time.time()-last['capturedAt']))
            last['stale']=last['ageSeconds']>120
        seen=row['last_seen']
        return {'deviceId':device_id,'name':row['name'],'latest':last,'battery':row['battery'],
                'lastSeen':seen,'online':seen is not None and time.time()-seen<180,
                'fixValid':bool(row['fix_valid']) if row['fix_valid'] is not None else None,
                'desiredMode':row['desired_mode'],'appliedMode':row['applied_mode']}
    @app.get('/v1/devices/{device_id}/track')
    def track(device_id:str,start:float,end:float,after:int=0,user_id=Depends(user)):
        own(device_id,user_id)
        import math
        if not math.isfinite(start) or not math.isfinite(end) or start<=0 or end<=start or end-start>86400 or after<0:
            raise HTTPException(400,'查询范围须在一天以内')
        with store.connection() as con:
            # Paginate in insertion order to include delayed uploads, then client sorts by capture time.
            rows=con.execute('SELECT p.* FROM points p JOIN devices d ON p.device_id=d.id WHERE p.device_id=? AND d.owner_id=? AND p.captured_at>=? AND p.captured_at<? AND p.id>? ORDER BY p.id LIMIT 1001',
                             (device_id,user_id,start,end,after)).fetchall()
        page=rows[:1000]
        return {'points':[serialize(row) for row in page], 'nextCursor':page[-1]['id'] if len(rows)>1000 else None}
    @app.post('/v1/device/positions')
    def position(body:Point,response:Response,device_id=Depends(device)):
        with store.connection() as con:
            owner=con.execute('SELECT owner_id FROM devices WHERE id=?',(device_id,)).fetchone()['owner_id']
        if owner is None: raise HTTPException(409,'设备尚未绑定，不接收位置')
        result=store.insert(device_id,body)
        if result=='unbound': raise HTTPException(409,'设备尚未绑定，不接收位置')
        if result=='conflict': raise HTTPException(409,'消息序号冲突')
        response.status_code=201 if result=='inserted' else 200
        return {'accepted':True,'duplicate':result=='duplicate'}
    @app.post('/v1/device/heartbeat')
    def heartbeat(body:Heartbeat,device_id=Depends(device)):
        with store.connection() as con:
            con.execute('UPDATE devices SET last_seen=?, battery=?,fix_valid=?,applied_mode=?,firmware=? WHERE id=?',
                        (time.time(),body.battery,int(body.fixValid),body.appliedMode,body.firmware,device_id))
            mode=con.execute('SELECT desired_mode FROM devices WHERE id=?',(device_id,)).fetchone()['desired_mode']
        return {'desiredMode':mode,'reportIntervalSeconds':10 if mode=='finding' else 60,'serverTime':time.time()}
    @app.delete('/v1/account',status_code=204)
    def delete_account(user_id=Depends(user)):
        with store.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('DELETE FROM points WHERE device_id IN (SELECT id FROM devices WHERE owner_id=?)',(user_id,))
            owned_devices=con.execute('SELECT id FROM devices WHERE owner_id=?',(user_id,)).fetchall()
            for revoked in owned_devices:
                con.execute('UPDATE devices SET secret_digest=? WHERE id=?',(digest(secrets.token_urlsafe(32)),revoked['id']))
            con.execute("UPDATE devices SET owner_id=NULL,binding_digest=NULL,binding_expires=NULL,name='我的宠物',desired_mode='normal',applied_mode=NULL,last_seen=NULL,battery=NULL,fix_valid=NULL,firmware=NULL WHERE owner_id=?",(user_id,))
            con.execute('DELETE FROM users WHERE id=?',(user_id,))
        return Response(status_code=204)
    return app
