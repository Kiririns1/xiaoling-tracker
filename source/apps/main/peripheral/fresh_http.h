#pragma once
#include "esp_err.h"
#include <stdint.h>
esp_err_t fresh_http_start(void);
esp_err_t fresh_http_enable_ap(void);
void fresh_http_frame(const uint8_t *data,unsigned size);
