#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "cJSON.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { float speed; int duration_ms; } fresh_step_t;
bool fresh_control_init(void);
bool fresh_control_action(const char *action, float speed, int ms);
bool fresh_control_plan(const fresh_step_t *steps, int count, int repeat, int interval_ms);
bool fresh_control_plan_axes(const fresh_step_t *steps,const int *axes,int count,int repeat,int interval_ms);
bool fresh_control_json(const cJSON *json);
bool fresh_control_text(const char *text);
bool fresh_control_step(float speed, unsigned revision);
const char *fresh_control_step_error(float speed,unsigned revision);
void fresh_control_state(char *out, unsigned capacity, bool heartbeat);
void fresh_control_audio(bool busy);
void fresh_control_shake(bool start);
unsigned fresh_control_revision(void);
bool fresh_control_try_shake(unsigned expected_revision);
bool fresh_control_try_gesture(bool nod,unsigned expected_revision);
unsigned tracker_boot_id(void);
bool tracker_posture_action(const char *action);
bool tracker_select(const char *mode,bool enable);
bool tracker_follow(float yaw,float pitch,unsigned revision);
bool tracker_fist_nod(unsigned revision);
#ifdef __cplusplus
}
#endif
