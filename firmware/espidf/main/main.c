#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "driver/uart.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "cJSON.h"
#include "tracker_core.h"

#define UART UART_NUM_1
#define CAPACITY 64
static nvs_handle_t storage;
static uint32_t head, count, sequence;
static char boot[33];
static char response[3072];
static bool finding;

static bool wait_for(const char *expected, unsigned timeout) {
    size_t used=0;int64_t deadline=esp_timer_get_time()+timeout*1000LL;
    response[0]=0;
    while(esp_timer_get_time()<deadline) {
        int received=uart_read_bytes(UART,response+used,sizeof(response)-used-1,pdMS_TO_TICKS(100));
        if(received>0) {
            used+=received;response[used]=0;
            if(strstr(response,"\r\nERROR\r\n")||strstr(response,"+CME ERROR:"))return false;
            char *matched=strstr(response,expected);
            if(matched && (strcmp(expected,"+HTTPACTION:")!=0 || strchr(matched,'\n')))return true;
            if(used==sizeof(response)-1)return false;
        }
    }
    return false;
}
static bool command(const char *text,const char *expected,unsigned timeout) {
    uart_flush_input(UART);
    uart_write_bytes(UART,text,strlen(text));uart_write_bytes(UART,"\r\n",2);
    // Never print AT commands: headers contain the device secret.
    return wait_for(expected,timeout);
}
static bool ok(const char *text) {return command(text,"\r\nOK\r\n",10000);}
static bool metadata(void) {
    return nvs_set_u32(storage,"head",head)==ESP_OK && nvs_set_u32(storage,"count",count)==ESP_OK && nvs_commit(storage)==ESP_OK;
}
static bool enqueue(paw_point *point) {
    if(count>=CAPACITY)return false;
    char key[12];snprintf(key,sizeof(key),"p%lu",(unsigned long)((head+count)%CAPACITY));
    if(nvs_set_blob(storage,key,point,sizeof(*point))!=ESP_OK || nvs_commit(storage)!=ESP_OK)return false;
    count++;return metadata();
}
static bool peek(paw_point *point) {
    if(!count)return false;
    char key[12];snprintf(key,sizeof(key),"p%lu",(unsigned long)head);size_t size=sizeof(*point);
    return nvs_get_blob(storage,key,point,&size)==ESP_OK&&size==sizeof(*point);
}
static void pop(void) {head=(head+1)%CAPACITY;count--;if(!metadata())abort();}
static cJSON *post(const char *path,cJSON *payload) {
    char text[512];char *body=cJSON_PrintUnformatted(payload);if(!body)return NULL;
    cJSON *result=NULL;
    ok("AT+HTTPTERM"); // Reset a prior interrupted transaction, even when no HTTP context exists.
    if(!ok("AT+HTTPINIT"))goto done;
    snprintf(text,sizeof(text),"AT+HTTPPARA=\"URL\",\"%s%s\"",CONFIG_PAWTRACK_API_BASE,path);
    if(!ok(text)||!ok("AT+HTTPPARA=\"CONTENT\",\"application/json\"")||!ok("AT+HTTPPARA=\"SSLCFG\",0"))goto done;
    snprintf(text,sizeof(text),"AT+HTTPPARA=\"USERDATA\",\"Authorization: Bearer %s\"",CONFIG_PAWTRACK_DEVICE_TOKEN);
    if(!ok(text))goto done;
    snprintf(text,sizeof(text),"AT+HTTPDATA=%u,30",(unsigned)strlen(body));
    if(!command(text,"DOWNLOAD",10000))goto done;
    uart_write_bytes(UART,body,strlen(body));if(!wait_for("\r\nOK\r\n",10000))goto done;
    if(!command("AT+HTTPACTION=1","+HTTPACTION:",60000))goto done;
    char *action=strstr(response,"+HTTPACTION:");int method,status,length;
    if(!action||sscanf(action,"+HTTPACTION: %d,%d,%d",&method,&status,&length)!=3||method!=1||!paw_ack_status(status)||length<=0||length>1500)goto done;
    snprintf(text,sizeof(text),"AT+HTTPREAD=0,%d",length);
    if(!command(text,"+HTTPREAD: 0",20000))goto done;
    // Parse only the declared JSON body, excluding modem framing.
    char *header=strstr(response,"+HTTPREAD:");int read_length=0;
    if(!header||sscanf(header,"+HTTPREAD: %d",&read_length)!=1||read_length!=length)goto done;
    char *data=strstr(header,"\r\n");if(!data)goto done;data+=2;
    if(strlen(data)<(size_t)length)goto done;
    data[length]=0;result=cJSON_Parse(data);
done:
    free(body);ok("AT+HTTPTERM");return result;
}
static bool configure(void) {
    if(!ok("AT")||!ok("ATE0")||!ok("AT+CPIN?"))return false;
    if(!strstr(response,"+CPIN: READY"))return false;
    char text[256];
    snprintf(text,sizeof(text),"AT+CGDCONT=1,\"IP\",\"%s\"",CONFIG_PAWTRACK_APN);
    if(!ok(text)||!ok("AT+CGNSSPWR=1"))return false;
    ok("AT+CGNSSTST=0");ok("AT+CTZU=1");
    // Fail closed: no disabled certificate validation or insecure HTTP fallback.
    if(!ok("AT+CSSLCFG=\"sslversion\",0,3")||!ok("AT+CSSLCFG=\"authmode\",0,1")||!ok("AT+CSSLCFG=\"ignorelocaltime\",0,0")||!ok("AT+CSSLCFG=\"enableSNI\",0,1"))return false;
    snprintf(text,sizeof(text),"AT+CSSLCFG=\"cacert\",0,\"%s\"",CONFIG_PAWTRACK_CA_FILE);
    return ok(text);
}
void app_main(void) {
    if(strncmp(CONFIG_PAWTRACK_API_BASE,"https://",8)||strstr(CONFIG_PAWTRACK_API_BASE,".invalid")||strlen(CONFIG_PAWTRACK_DEVICE_TOKEN)<32||!strlen(CONFIG_PAWTRACK_APN)) {
        ESP_LOGE("pawtrack","Configure HTTPS endpoint, private device token and APN before flashing");return;
    }
    setenv("TZ","UTC0",1);tzset();
    ESP_ERROR_CHECK(nvs_flash_init());ESP_ERROR_CHECK(nvs_open("pawtrack",NVS_READWRITE,&storage));
    nvs_get_u32(storage,"head",&head);nvs_get_u32(storage,"count",&count);
    if(head>=CAPACITY||count>CAPACITY){ESP_LOGE("pawtrack","Invalid queue metadata");return;}
    uint8_t random[16];esp_fill_random(random,sizeof(random));
    for(int i=0;i<16;i++)snprintf(boot+i*2,3,"%02x",random[i]);
    uart_config_t config={.baud_rate=115200,.data_bits=UART_DATA_8_BITS,.parity=UART_PARITY_DISABLE,.stop_bits=UART_STOP_BITS_1,.flow_ctrl=UART_HW_FLOWCTRL_DISABLE,.source_clk=UART_SCLK_DEFAULT};
    ESP_ERROR_CHECK(uart_driver_install(UART,4096,0,0,NULL,0));
    ESP_ERROR_CHECK(uart_param_config(UART,&config));
    ESP_ERROR_CHECK(uart_set_pin(UART,CONFIG_PAWTRACK_TX_PIN,CONFIG_PAWTRACK_RX_PIN,UART_PIN_NO_CHANGE,UART_PIN_NO_CHANGE));
    unsigned backoff=5;
    while(!configure()){vTaskDelay(pdMS_TO_TICKS(backoff*1000));if(backoff<60)backoff*=2;}
    bool clock_ready=false;double last_capture=0;unsigned interval=60;
    for(;;) {
        int64_t started=esp_timer_get_time();paw_point fix={0};
        bool valid=command("AT+CGPSINFO","\r\nOK\r\n",10000)&&paw_parse_gpsinfo(response,&fix);
        if(valid) {
            if(!clock_ready) {
                time_t utc=(time_t)fix.captured_at;struct tm tm;gmtime_r(&utc,&tm);char clock[96];
                snprintf(clock,sizeof(clock),"AT+CCLK=\"%02d/%02d/%02d,%02d:%02d:%02d+00\"",tm.tm_year%100,tm.tm_mon+1,tm.tm_mday,tm.tm_hour,tm.tm_min,tm.tm_sec);
                clock_ready=ok(clock);
            }
            if(fix.captured_at>last_capture) {
                strncpy(fix.boot_id,boot,sizeof(fix.boot_id));fix.sequence=sequence++;
                if(enqueue(&fix))last_capture=fix.captured_at;else ESP_LOGW("pawtrack","Queue full or write failed; point not stored");
            }
        }
        if(clock_ready) {
            cJSON *heartbeat=cJSON_CreateObject();cJSON_AddNullToObject(heartbeat,"battery");
            cJSON_AddBoolToObject(heartbeat,"fixValid",valid);cJSON_AddStringToObject(heartbeat,"appliedMode",finding?"finding":"normal");cJSON_AddStringToObject(heartbeat,"firmware","pawtrack-0.2.0");
            cJSON *reply=post("/v1/device/heartbeat",heartbeat);cJSON_Delete(heartbeat);
            if(reply) {
                cJSON *mode=cJSON_GetObjectItemCaseSensitive(reply,"desiredMode");
                if(cJSON_IsString(mode))finding=strcmp(mode->valuestring,"finding")==0;
                interval=finding?10:60;cJSON_Delete(reply);
            }
            // Limit backlog work per loop so fresh GNSS reads and heartbeats continue.
            for(int sent=0;sent<3&&peek(&fix);sent++) {
                if(valid&&fix.captured_at<last_capture-30*86400){pop();continue;}
                cJSON *point=cJSON_CreateObject();cJSON_AddStringToObject(point,"bootId",fix.boot_id);
                cJSON_AddNumberToObject(point,"sequence",fix.sequence);cJSON_AddNumberToObject(point,"capturedAt",fix.captured_at);
                cJSON_AddNumberToObject(point,"latitude",fix.latitude);cJSON_AddNumberToObject(point,"longitude",fix.longitude);
                cJSON_AddStringToObject(point,"coordinateSystem","wgs84");cJSON_AddNullToObject(point,"battery");
                reply=post("/v1/device/positions",point);cJSON_Delete(point);
                bool accepted=reply&&cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(reply,"accepted"));cJSON_Delete(reply);
                if(!accepted) break;
                pop();
            }
        }
        int64_t remaining=interval*1000000LL-(esp_timer_get_time()-started);
        vTaskDelay(pdMS_TO_TICKS(remaining>1000000?remaining/1000:1000));
    }
}
