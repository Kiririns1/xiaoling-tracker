#pragma once
#include <stdbool.h>
#include "cJSON.h"
bool tracker_light_init(void);
bool tracker_light_level(int level);
bool tracker_light_action(const char *action,int percent);
bool tracker_light_request(const cJSON *json);
void tracker_light_state(char *out,unsigned cap);

bool tracker_light_alert(void);
