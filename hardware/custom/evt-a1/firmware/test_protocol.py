"""Host tests of actual Lua modules. No GNSS/radio/hardware emulation claim."""
from pathlib import Path
import datetime,json
from lupa.lua53 import LuaRuntime
ROOT=Path(__file__).resolve().parent
lua=LuaRuntime(unpack_returned_tuples=True)
lua.execute("package.path="+json.dumps(str(ROOT/'?.lua')+';',ensure_ascii=False)+"..package.path")
protocol=lua.eval("require('protocol')")
def table(**kw):return lua.table_from(kw)
r=table(year=2026,month=10,day=11,hour=12,min=1,sec=2,valid=True,lat=31.2304,lng=121.4737)
now=int(datetime.datetime(2026,10,11,12,1,2,tzinfo=datetime.timezone.utc).timestamp())
assert protocol.epoch(r)==now
point=protocol.position(r,'eg-12',5,now)
assert point['coordinateSystem']=='wgs84' and point['latitude']==31.2304
assert protocol.position(r,'eg-12',5,now+6) is None
assert protocol.position(r,'invalid/id',5,now) is None
r['valid']=False;assert protocol.position(r,'eg-12',5,now) is None;r['valid']=True
r['lat']=float('nan');assert protocol.position(r,'eg-12',5,now) is None;r['lat']=31.2304
r['month']=2;r['day']=29;assert protocol.epoch(r) is None
r['year']=2028;assert protocol.epoch(r)==int(datetime.datetime(2028,2,29,12,1,2,tzinfo=datetime.timezone.utc).timestamp())
assert protocol.accepted(table(accepted=True,bootId='eg-12',sequence=5),point)
assert not protocol.accepted(table(accepted=True,bootId='eg-13',sequence=5),point)
assert not protocol.accepted(table(accepted=True,bootId='eg-12',sequence=6),point)
assert protocol.mode(table(desiredMode='finding'))==('finding',10)
assert protocol.mode(table(desiredMode='normal'))==('normal',60)
assert protocol.mode(table(desiredMode='wrong')) is None
assert 24<protocol.temperature(174)<26
assert protocol.charge_allowed(174)
assert not protocol.charge_allowed(0)
assert not protocol.charge_allowed(1500)
assert not protocol.charge_allowed(None)
assert not protocol.charge_allowed(float('nan'))
assert not protocol.charge_allowed(30)  # hot
assert not protocol.charge_allowed(550) # cold
# KV semantics copies tables at commits, matching durable serialization.
lua.execute('''
local Queue=require('queue')
local store={}
local function copy(x) if type(x)~='table' then return x end local y={} for k,v in pairs(x) do y[k]=copy(v) end return y end
local kv={get=function(k)return copy(store[k])end,set=function(k,v)store[k]=copy(v);return true end,del=function(k)store[k]=nil end}
local q=Queue.open(kv,2)
assert(q:append({sequence=1}));assert(q:append({sequence=2}));assert(not q:append({sequence=3}))
assert(q:peek().sequence==1 and q.meta.dropped==1)
q=Queue.open(kv,2);assert(q:peek().sequence==1);q:ack();assert(q:peek().sequence==2)
assert(q:append({sequence=3}));q:ack();assert(q:peek().sequence==3);q:ack();assert(q:peek()==nil)
-- Interrupted append: prewritten slot ignored until metadata commit.
kv.set('pt_q_0',{sequence=99});q=Queue.open(kv,2);assert(q:peek()==nil)
''')
# Parse all deployment Lua files, including pinned upstream library.
for f in [*ROOT.glob('*.lua'),*ROOT.glob('vendor/*.lua')]:
 lua.execute('assert(load(...))',f.read_text())
print('PASS: UTC/leap dates, stale/invalid fixes, WGS84, ack identity, modes, bounded durable queue, all Lua syntax')
