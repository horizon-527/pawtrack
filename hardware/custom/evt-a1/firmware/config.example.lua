-- Copy to config.lua outside Git; include in Luatools user files.
return {
    base_url='https://YOUR-API-DOMAIN',
    device_token='SET-PER-DEVICE-TOKEN',
    ca_file='/luadb/pawtrack-ca.pem',
    -- Set true ONLY after the exact deployed LuatOS version passes all four TLS cases.
    tls_qualified=false,
    -- Enable only after temperature calibration, cutoffs and charger fault tests.
    charge_qualified=false,
}
