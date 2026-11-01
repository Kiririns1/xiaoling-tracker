#pragma once
#include <stdbool.h>
#include <stddef.h>
typedef enum {TI_NONE,TI_WAKE,TI_SLEEP,TI_HAND,TI_FACE,TI_STOP,TI_SWITCH,TI_BRIGHTNESS_ASK,TI_BRIGHTNESS_SET,TI_BRIGHTNESS_INVALID,TI_LIGHT_ON,TI_LIGHT_OFF,TI_CANCEL,TI_POSTURE_ON,TI_POSTURE_OFF,TI_POSTURE_CALIBRATE,TI_POSTURE_PAUSE,TI_POSTURE_RESUME,TI_POSTURE_STATUS,TI_ROTATE,TI_PC_EXIT} tracker_intent_kind;
typedef struct {tracker_intent_kind kind;int level;size_t wake_bytes;} tracker_intent;
tracker_intent tracker_parse(const char *text,bool waiting_brightness);
