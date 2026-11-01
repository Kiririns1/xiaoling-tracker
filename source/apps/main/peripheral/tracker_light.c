#include "tracker_light.h"
#include "fresh_control.h"
#include "bsp_ws2812.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include <string.h>
#include <stdio.h>
#include <math.h>
static SemaphoreHandle_t lock;
static bool ready,on;
static TaskHandle_t alert_task;
static int percent=25;
static char events[16][33];static unsigned cursor;
static bool render(bool next_on,int next_percent){
 int value=next_on?(next_percent*255+50)/100:0;
 if(bsp_ws2812_fill(value,value,value)!=QM_EOK)return false;
 on=next_on;percent=next_percent;return true;
}
static void posture_flash(void *unused){
 (void)unused;for(;;){ulTaskNotifyTake(pdTRUE,portMAX_DELAY);
  for(int i=0;i<6;++i){
   xSemaphoreTake(lock,portMAX_DELAY);
   if(i%2==0)bsp_ws2812_fill(64,32,0);else render(on,percent);
   xSemaphoreGive(lock);vTaskDelay(pdMS_TO_TICKS(250));
  }
  xSemaphoreTake(lock,portMAX_DELAY);render(on,percent);xSemaphoreGive(lock);
 }
}
bool tracker_light_alert(void){if(!ready||!alert_task)return false;xTaskNotifyGive(alert_task);return true;}
bool tracker_light_init(void){lock=xSemaphoreCreateMutex();ready=lock&&bsp_ws2812_init()==QM_EOK;if(ready)xTaskCreate(posture_flash,"posture_flash",2048,NULL,2,&alert_task);return ready;}
bool tracker_light_action(const char *a,int p){
 if(!ready||!a){return false;}
 xSemaphoreTake(lock,portMAX_DELAY);bool result=false;
 if(!strcmp(a,"toggle"))result=render(!on,percent);
 else if(!strcmp(a,"on")||!strcmp(a,"off"))result=render(!strcmp(a,"on"),percent);
 else if(!strcmp(a,"brightness")&&p>=0&&p<=100)result=render(on,p);
 xSemaphoreGive(lock);return result;
}
bool tracker_light_level(int level){
 if(!ready||level<0||level>10)return false;
 xSemaphoreTake(lock,portMAX_DELAY);bool result=render(level>0,level*10);xSemaphoreGive(lock);return result;
}
bool tracker_light_request(const cJSON *j){
 if(!ready)return false;
 const cJSON *a=cJSON_GetObjectItem(j,"action"),*b=cJSON_GetObjectItem(j,"boot_id"),*e=cJSON_GetObjectItem(j,"event_id"),*p=cJSON_GetObjectItem(j,"percent");
 if(!cJSON_IsString(a)||!cJSON_IsString(e)||strlen(e->valuestring)!=32||!cJSON_IsNumber(b)||b->valuedouble!=tracker_boot_id())return false;
 bool toggle=!strcmp(a->valuestring,"toggle"),brightness=!strcmp(a->valuestring,"brightness");
 if(!toggle&&!brightness)return false;
 if(brightness&&(!cJSON_IsNumber(p)||floor(p->valuedouble)!=p->valuedouble||(p->valueint!=25&&p->valueint!=50&&p->valueint!=75&&p->valueint!=100)))return false;
 xSemaphoreTake(lock,portMAX_DELAY);
 for(int i=0;i<16;++i)if(!strcmp(events[i],e->valuestring)){xSemaphoreGive(lock);return true;}
 bool result=render(toggle?!on:on,brightness?p->valueint:percent);
 if(result)strcpy(events[cursor++%16],e->valuestring);
 xSemaphoreGive(lock);return result;
}
void tracker_light_state(char *out,unsigned cap){
 if(!ready){snprintf(out,cap,"{\"ready\":false}");return;}
 xSemaphoreTake(lock,portMAX_DELAY);snprintf(out,cap,"{\"ready\":true,\"on\":%s,\"percent\":%d,\"brightness\":%d,\"level\":%.1f,\"pin\":7,\"count\":8}",on?"true":"false",percent,(percent*255+50)/100,percent/10.0);xSemaphoreGive(lock);
}
