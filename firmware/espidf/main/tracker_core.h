#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
typedef struct { double latitude, longitude, captured_at; char boot_id[33]; uint32_t sequence; } paw_point;
bool paw_parse_gpsinfo(const char *response, paw_point *point);
bool paw_ack_status(int status);
bool paw_http_body(const char *response, size_t declared_length, char *output, size_t capacity);
