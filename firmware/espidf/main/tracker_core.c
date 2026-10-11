#include "tracker_core.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include <time.h>

static bool number(const char *text, double *value) {
    if (!text || !*text) return false;
    char *end; *value=strtod(text,&end);
    return *end=='\0' && isfinite(*value);
}
static bool coord(const char *text, char hemisphere, bool latitude, double *result) {
    double raw;
    if (!number(text,&raw) || raw<0) return false;
    double degrees=floor(raw/100), minutes=raw-degrees*100;
    if (minutes>=60) return false;
    double converted=degrees+minutes/60;
    if (converted>(latitude?90:180)) return false;
    if (latitude && hemisphere!='N' && hemisphere!='S') return false;
    if (!latitude && hemisphere!='E' && hemisphere!='W') return false;
    *result=(hemisphere=='S'||hemisphere=='W')?-converted:converted;
    return true;
}
bool paw_parse_gpsinfo(const char *response, paw_point *point) {
    const char *start=strstr(response,"+CGPSINFO:");
    if (!start) return false;
    start+=10; while (*start==' ') start++;
    char text[256]; size_t length=strcspn(start,"\r\n");
    if (length>=sizeof(text)) return false;
    memcpy(text,start,length);text[length]=0;
    char *fields[9];fields[0]=text;int count=1;
    for (char *p=text;*p;p++) if (*p==',') { *p=0; if(count>=9)return false;fields[count++]=p+1; }
    if(count!=9 || strlen(fields[1])!=1 || strlen(fields[3])!=1) return false;
    if(!coord(fields[0],fields[1][0],true,&point->latitude) || !coord(fields[2],fields[3][0],false,&point->longitude)) return false;
    if(strlen(fields[4])!=6 || strlen(fields[5])<6) return false;
    for(int i=0;i<6;i++) if(fields[4][i]<'0'||fields[4][i]>'9'||fields[5][i]<'0'||fields[5][i]>'9')return false;
    int day,month,year,hour,minute; double second;
    if(sscanf(fields[4],"%2d%2d%2d",&day,&month,&year)!=3 || sscanf(fields[5],"%2d%2d%lf",&hour,&minute,&second)!=3) return false;
    double parsed_seconds; if(!number(fields[5]+4,&parsed_seconds))return false;
    if(month<1||month>12||day<1||day>31||hour>23||minute>59||second<0||second>=60) return false;
    struct tm tm={.tm_year=year+100,.tm_mon=month-1,.tm_mday=day,.tm_hour=hour,.tm_min=minute,.tm_sec=(int)second};
    // Firmware sets TZ=UTC before calling; portable host tests do the same.
    time_t timestamp=mktime(&tm);
    if(timestamp<0 || tm.tm_mon!=month-1 || tm.tm_mday!=day) return false;
    point->captured_at=(double)timestamp+second-floor(second);
    return true;
}
bool paw_ack_status(int status) { return status==200||status==201; }
