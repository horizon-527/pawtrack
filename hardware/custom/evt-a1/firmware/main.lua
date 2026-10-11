PROJECT='pawtrack_eg'
VERSION='0.1.0'
_G.sys=require('sys')
local protocol=require('protocol')
local Queue=require('queue')
local config=require('config')
local exgnss=require('exgnss')
assert(config.base_url:match('^https://[%w%.%-]+$'),'HTTPS origin without path required')
assert(config.device_token~='SET-PER-DEVICE-TOKEN' and #config.device_token>=24,'provision per-device token')
assert(config.tls_qualified==true,'TLS qualification required before uploading credentials or locations')
local ca=assert(io.readFile(config.ca_file),'missing CA')
assert(ca:find('BEGIN CERTIFICATE',1,true),'invalid CA file')
fskv.init()
local bootcount=(fskv.get('pt_boot') or 0)+1
assert(fskv.set('pt_boot',bootcount),'boot identity commit failed')
local boot='eg-'..bootcount
local queue=Queue.open(fskv,64)
local mode,interval,sequence='normal',60,0
local newest,next_capture=nil,0
local function request(path,payload)
    local code,_,body=http.request('POST',config.base_url..path,
        {['Content-Type']='application/json',['Authorization']='Bearer '..config.device_token},
        json.encode(payload,'7f'),{timeout=15000},ca).wait()
    -- No cross-origin redirects, no cleartext fallback, no CA-free retry.
    if code~=200 and code~=201 then return nil,code end
    local decoded,ok=json.decode(body or '')
    if not ok then return nil,code end
    return decoded,code
end
gpio.setup(27,0) -- NMOS off, CE pulled high: default charging disabled
adc.setRange(adc.ADC_RANGE_MIN);adc.open(0);adc.open(1)
sys.timerLoopStart(function()
    gpio.set(27,0) -- A driver exception cannot leave the previous charging state enabled.
    local ok,mv=pcall(function() local _,value=adc.read(1);return value end)
    if ok and config.charge_qualified==true and protocol.charge_allowed(mv) then gpio.set(27,1) end
end,1000)
-- Voltage is diagnostic only. Do not label it as SOC or post false percentages.
local function battery_mv()
    local _,mv=adc.read(0)
    if type(mv)~='number' or mv<0 or mv>1500 then return nil end
    return math.floor(mv*4.3+.5)
end
exgnss.setup({gnssmode=1,agps_enable=false,debug=false,rtc=true,hz=1,auto_open=false})
exgnss.open(exgnss.DEFAULT,{tag='PAWTRACK'})
sys.taskInit(function()
    while true do
        local now=os.time()
        newest=protocol.position(exgnss.rmc(2),boot,sequence,now)
        if newest and now>=next_capture then
            if queue:append(newest) then sequence=sequence+1 end
            next_capture=now+interval
        end
        sys.wait(1000)
    end
end)
sys.taskInit(function()
    -- NTP bootstrap allows TLS and online heartbeats before GNSS fix.
    sys.waitUntil('IP_READY',60000)
    socket.sntp()
    while true do
        local now=os.time()
        if now>=1735689600 then
            local response=request('/v1/device/heartbeat',{
                fixValid=newest~=nil,appliedMode=mode,firmware='air780egh-evt-a1/'..VERSION})
            local desired,seconds=protocol.mode(response)
            if desired then
                if desired~=mode then next_capture=0 end
                mode,interval=desired,seconds
            end
            -- Single sender; preserve identity across retries; stop draining on first failure.
            for _=1,16 do
                local point=queue:peek()
                if not point then break end
                local result=request('/v1/device/positions',point)
                if not protocol.accepted(result,point) then break end
                queue:ack()
            end
        end
        if now<1735689600 then socket.sntp() end
        sys.wait(10000)
    end
end)
-- Do not print credentials, location, ICCID or IMEI to the factory console.
sys.run()
