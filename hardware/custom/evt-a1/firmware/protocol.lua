-- Pure protocol logic. Coordinates are WGS84; battery SOC stays unknown until calibrated.
local M={}
local function integer(n) return type(n)=='number' and n==math.floor(n) end
function M.epoch(r)
    if type(r)~='table' then return nil end
    for _,k in ipairs({'year','month','day','hour','min','sec'}) do if not integer(r[k]) then return nil end end
    local y,m,d=r.year,r.month,r.day
    if y<2025 or y>2099 or m<1 or m>12 or r.hour<0 or r.hour>23 or r.min<0 or r.min>59 or r.sec<0 or r.sec>59 then return nil end
    local leap=(y%4==0 and (y%100~=0 or y%400==0))
    local days={31,leap and 29 or 28,31,30,31,30,31,31,30,31,30,31}
    if d<1 or d>days[m] then return nil end
    y=y-(m<=2 and 1 or 0)
    local era=math.floor(y/400);local yoe=y-era*400
    local mp=m+(m>2 and -3 or 9)
    local doy=math.floor((153*mp+2)/5)+d-1
    local doe=yoe*365+math.floor(yoe/4)-math.floor(yoe/100)+doy
    return (era*146097+doe-719468)*86400+r.hour*3600+r.min*60+r.sec
end
function M.position(r,boot,seq,now)
    local t=M.epoch(r)
    if not t or r.valid~=true or type(r.lat)~='number' or type(r.lng)~='number' or r.lat~=r.lat or r.lng~=r.lng or math.abs(r.lat)>90 or math.abs(r.lng)>180 then return nil end
    if type(now)~='number' or math.abs(now-t)>5 then return nil end
    if type(boot)~='string' or not boot:match('^[%w_-]+$') or #boot>64 or not integer(seq) or seq<0 then return nil end
    return {bootId=boot,sequence=seq,capturedAt=t,latitude=r.lat,longitude=r.lng,coordinateSystem='wgs84'}
end
function M.accepted(reply,point)
    return type(reply)=='table' and reply.accepted==true and reply.bootId==point.bootId and reply.sequence==point.sequence
end
function M.mode(reply)
    if type(reply)~='table' then return nil end
    local mode=reply.desiredMode
    if mode=='normal' then return mode,60 end
    if mode=='finding' then return mode,10 end
    return nil
end
function M.temperature(mv)
    if type(mv)~='number' or mv~=mv or mv<=0 or mv>=1500 then return nil end
    local v=mv/1000*4.3
    if v<0.05 or v>2.4 then return nil end
    local current=0.000075-v/4300000
    local resistance=v/current
    return 1/(1/298.15+math.log(resistance/10000)/3435)-273.15
end
function M.charge_allowed(mv)
    local t=M.temperature(mv)
    return t~=nil and t>=5 and t<=40
end
return M
