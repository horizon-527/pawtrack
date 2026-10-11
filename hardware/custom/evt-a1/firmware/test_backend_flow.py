"""Run actual main.lua with SDK doubles and a real loopback HTTP backend.
No modem/TLS/radio/WeChat proof: the HTTP SDK double maps the HTTPS test origin
onto an isolated localhost server. All identities and coordinates are synthetic.
"""
from pathlib import Path
import copy,datetime,json,sys,tempfile,threading,time,urllib.request,urllib.error
from lupa.lua53 import LuaRuntime
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[3]
sys.path.insert(0,str(REPO))
import uvicorn
from server.production import create_app

def plain(x):
    if hasattr(x,'items'):return {k:plain(v) for k,v in x.items()}
    return x
with tempfile.TemporaryDirectory() as tmp:
    async def wx_fixture(code):return 'isolated-lua-fixture'
    app=create_app(Path(tmp)/'test.sqlite3',wx_fixture)
    device=app.state.store.provision('lua-test')
    service=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=18789,log_level='error',access_log=False))
    th=threading.Thread(target=service.run);th.start()
    def call(path,payload=None,token=None,method=None):
        req=urllib.request.Request('http://127.0.0.1:18789'+path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})},method=method)
        try:
            with urllib.request.urlopen(req,timeout=3) as r:return r.status,json.loads(r.read() or b'null')
        except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
    try:
        for _ in range(50):
            if service.started:break
            time.sleep(.1)
        assert service.started
        status,login=call('/v1/auth/wechat',{'code':'isolated-fixture'});assert status==200
        owner=login['token'];token=device['deviceToken']
        assert call('/v1/devices/bind',{'code':device['bindingCode']},owner)[0]==200
        assert call('/v1/devices/lua-test/mode',{'mode':'finding'},owner)[0]==200
        store={};lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('package.path=... .. package.path',str(ROOT/'?.lua')+';')
        globals=lua.globals()
        globals.py_now=lambda:int(time.time())
        globals.py_encode=lambda obj,*ignored:json.dumps(plain(obj))
        globals.py_decode=lambda txt:(lua.table_from(json.loads(txt),recursive=True),True)
        globals.py_get=lambda key:lua.table_from(copy.deepcopy(store[key]),recursive=True) if key in store else None
        globals.py_set=lambda key,obj:(store.__setitem__(key,copy.deepcopy(plain(obj))) or True)
        globals.py_del=lambda key:store.pop(key,None)
        globals.fixture_token=token
        def sdk_http(method,url,headers,body):
            assert method=='POST' and url.startswith('https://fixture.invalid/')
            auth=headers['Authorization'];assert auth=='Bearer '+token
            status,result=call(url.removeprefix('https://fixture.invalid'),json.loads(body),token)
            return status,lua.table_from({}),json.dumps(result)
        globals.py_http=sdk_http
        lua.execute(r'''
        sdk_tasks={};sdk_timers={};sdk_gpio={};sdk_ntc_mv=174
        package.preload.sys=function()return {
          taskInit=function(fn)table.insert(sdk_tasks,coroutine.create(fn))end,
          wait=function(ms)coroutine.yield(ms)end,
          waitUntil=function()return true end,
          timerLoopStart=function(fn)table.insert(sdk_timers,fn)end,
          run=function()end}end
        package.preload.config=function()return {base_url='https://fixture.invalid',device_token=fixture_token,ca_file='test.pem',tls_qualified=true,charge_qualified=false}end
        package.preload.exgnss=function()return {DEFAULT=1,setup=function()end,open=function()end,
          rmc=function()local d=os.date('!*t',py_now());d.min=d.min;d.valid=true;d.lat=31.2304;d.lng=121.4737;return d end}end
        io.readFile=function()return '-----BEGIN CERTIFICATE-----\nTEST ONLY\n-----END CERTIFICATE-----'end
        json={encode=py_encode,decode=py_decode}
        fskv={init=function()return true end,get=py_get,set=py_set,del=py_del}
        gpio={setup=function(p,v)sdk_gpio[p]=v end,set=function(p,v)sdk_gpio[p]=v end}
        adc={ADC_RANGE_MIN=1,setRange=function()end,open=function()end,read=function(ch)return 0,ch==1 and sdk_ntc_mv or 900 end}
        socket={sntp=function()end}
        http={request=function(method,url,headers,body,opts,ca)
          assert(opts.timeout==15000 and ca:find('BEGIN CERTIFICATE',1,true))
          return {wait=function()return py_http(method,url,headers,body)end}end}
        os.time=py_now
        function step(i)local ok,err=coroutine.resume(sdk_tasks[i]);assert(ok,err)end
        ''')
        lua.execute((ROOT/'main.lua').read_text())
        lua.execute('sdk_timers[1]();assert(sdk_gpio[27]==0);require("config").charge_qualified=true;sdk_timers[1]();assert(sdk_gpio[27]==1);sdk_ntc_mv=0;sdk_timers[1]();assert(sdk_gpio[27]==0);adc.read=function()error("ADC error")end;sdk_timers[1]();assert(sdk_gpio[27]==0)')
        lua.execute('step(1);step(2);step(1);step(2)')
        status,snapshot=call('/v1/devices/lua-test/snapshot',token=owner)
        assert status==200 and snapshot['online'] and snapshot['appliedMode']=='finding'
        assert snapshot['latest']['coordinateSystem']=='wgs84' and snapshot['latest']['battery'] is None
        assert snapshot['latest']['sequence']==1
        assert store['pt_queue']['head']==store['pt_queue']['tail']==2
        assert call('/v1/account',token=owner,method='DELETE')[0]==204
        lua.execute('step(1)') # sampling deadline after finding is 10s; inject a queued point instead
        q=lua.eval('require("queue").open(fskv,64)')
        r=lua.table_from(dict(year=datetime.datetime.now(datetime.timezone.utc).year,month=datetime.datetime.now(datetime.timezone.utc).month,day=datetime.datetime.now(datetime.timezone.utc).day,hour=datetime.datetime.now(datetime.timezone.utc).hour,min=datetime.datetime.now(datetime.timezone.utc).minute,sec=datetime.datetime.now(datetime.timezone.utc).second,valid=True,lat=31.2304,lng=121.4737))
        point=lua.eval('require("protocol").position')(r,'eg-1',2,int(time.time()));assert point is not None
        assert q.append(q,point)
        lua.execute('step(2)')
        assert store['pt_queue']['tail']-store['pt_queue']['head']==1
        print('PASS: actual main.lua → real loopback API: bind/upload/ACK/mode/SOC-null/revocation queue; charging gates/fault. SDK is mocked, TLS and physical hardware untested.')
    finally:
        service.should_exit=True;th.join(timeout=10);assert not th.is_alive()
