#pragma once
#include <stdbool.h>
bool fresh_tone_init(void);
void fresh_tone_begin_turn(void);
/* Cumulative provider reply, observed before public notices can truncate it. */
void fresh_tone_feed(const char *text,bool final);
void fresh_tone_playback(bool active);
void fresh_tone_cancel(void);
bool fresh_tone_is_negative(const char *content);
int fresh_tone_parse(const char *content);
