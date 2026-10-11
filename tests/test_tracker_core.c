#include "tracker_core.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <time.h>
int main(void) {
    setenv("TZ","UTC0",1);tzset();paw_point point={0};
    assert(paw_parse_gpsinfo("\r\n+CGPSINFO:3113.343286,N,12121.234064,E,111026,072809.33,44.1,0.0,0\r\nOK\r\n",&point));
    assert(fabs(point.latitude-31.2223881)<1e-6);
    assert(fabs(point.longitude-121.3539010667)<1e-6);
    assert(!paw_parse_gpsinfo("+CGPSINFO:,,,,,,,,\r\n",&point));
    assert(!paw_parse_gpsinfo("+CGPSINFO:3163.343286,N,12121.234064,E,111026,072809.33,44.1,0.0,0",&point));
    assert(!paw_parse_gpsinfo("+CGPSINFO:3113.343286,N,12121.234064,E,310226,072809.33,44.1,0.0,0",&point));
    assert(paw_ack_status(201));assert(!paw_ack_status(401));assert(!paw_ack_status(409));
}
