-- Factory-only diagnostic entry. Select this INSTEAD OF main.lua in a test session.
-- No SIM identifiers, tokens or positions are logged. Charger remains disabled by default.
PROJECT='pawtrack_factory'
VERSION='0.1.0'
_G.sys=require('sys')
local protocol=require('protocol')
local CHARGE_TEST_ARMED=false -- Engineer-controlled fixture only after reviewing battery/NTC limits.
gpio.setup(27,0)
adc.setRange(adc.ADC_RANGE_MIN);adc.open(0);adc.open(1)
sys.timerLoopStart(function()
    gpio.set(27,0)
    local ok,result=pcall(function()
        local _,bat=adc.read(0);local _,ts=adc.read(1)
        return {bat=bat,ts=ts}
    end)
    if not ok then log.warn('factory','ADC failure, charging disabled');return end
    local temp=protocol.temperature(result.ts)
    if CHARGE_TEST_ARMED and protocol.charge_allowed(result.ts) then gpio.set(27,1) end
    log.info('factory','battery_mV',type(result.bat)=='number' and math.floor(result.bat*4.3) or 'invalid',
        'ts_adc_mV',result.ts or 'invalid','estimated_C',temp or 'invalid','charge_armed',CHARGE_TEST_ARMED)
end,1000)
log.info('factory','core_version',rtos.version())
sys.run()
