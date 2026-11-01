#pragma once
#include <stdbool.h>
bool tracker_dialog_init(void);
void tracker_dialog_network(bool connected);
void tracker_dialog_wake(void);
void tracker_dialog_sleep(void);
bool tracker_dialog_awake(void);
bool tracker_dialog_controls_allowed(void);
bool tracker_dialog_audio_allowed(void);
void tracker_dialog_asr(const char *text,bool final);
void tracker_dialog_say(const char *text);
void tracker_dialog_notify(const char *text);
