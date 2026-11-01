#pragma once
#include <stdint.h>
#include <stdbool.h>
/* A frame count gap is not an age: capture keeps running while Wi-Fi is slow. */
#define FRESH_FRAME_HISTORY 64
#define FRESH_TRACK_MAX_AGE_US 900000
typedef struct {uint32_t id;int64_t at;} fresh_frame_entry_t;
typedef struct {fresh_frame_entry_t entries[FRESH_FRAME_HISTORY];} fresh_frame_history_t;
static inline void fresh_frame_record(fresh_frame_history_t *h,uint32_t id,int64_t at){h->entries[id%FRESH_FRAME_HISTORY]=(fresh_frame_entry_t){id,at};}
static inline bool fresh_frame_recent(const fresh_frame_history_t *h,uint32_t id,int64_t now){const fresh_frame_entry_t *e=&h->entries[id%FRESH_FRAME_HISTORY];return id&&e->id==id&&now>=e->at&&now-e->at<=FRESH_TRACK_MAX_AGE_US;}
