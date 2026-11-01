#include "tracker_dialog.h"
#include "tracker_intent.h"
#include "tracker_light.h"
#include "fresh_control.h"
#include "agent_app.h"
#include "qm_agent.h"
#include "esp_timer.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include <stdatomic.h>
#include <string.h>
#include <stdio.h>
static atomic_bool awake,local_reply,custom_speaking,connected;
static atomic_int turn;
static atomic_uint brightness_until;
static QueueHandle_t replies;
typedef struct {char text[192];int turn;} reply_job;
static void worker(void *unused){
 (void)unused;reply_job job;
 for(;;)if(xQueueReceive(replies,&job,portMAX_DELAY)==pdTRUE){
  if(job.turn!=atomic_load(&turn)||!atomic_load(&awake)||!atomic_load(&connected))continue;
  (void)agent_app_abort_output();
  // Drain queued output before admitting a custom corpus; all HTTP runs off RTC callbacks.
  vTaskDelay(pdMS_TO_TICKS(150));
  if(job.turn!=atomic_load(&turn)||!atomic_load(&awake)||!atomic_load(&connected)){
   // abort_output paused upload; a superseded reply must not leave ASR paused.
   agent_app_resume_upload();continue;
  }
  atomic_store(&custom_speaking,true);
  int ret=agent_app_user_corpus(job.text);
  if(ret==0)ret=agent_app_wait_tts_complete(15000);
  atomic_store(&custom_speaking,false);
  ESP_LOGI("tracker_dialog","local reply ret=%d",ret);
  agent_app_resume_upload();
  fresh_control_audio(false);
 }
}
bool tracker_dialog_init(void){
 replies=xQueueCreate(1,sizeof(reply_job));
 return replies&&xTaskCreate(worker,"tracker_dialog",8192,NULL,4,NULL)==pdPASS;
}
void tracker_dialog_network(bool up){
 atomic_store(&connected,up);
 if(!up){atomic_store(&awake,false);atomic_store(&local_reply,true);atomic_store(&custom_speaking,false);atomic_store(&brightness_until,0);atomic_fetch_add(&turn,1);}
}
void tracker_dialog_wake(void){atomic_store(&awake,true);atomic_store(&local_reply,false);atomic_store(&brightness_until,0);atomic_fetch_add(&turn,1);ESP_LOGI("tracker_dialog","chat voice enabled");}
void tracker_dialog_sleep(void){atomic_store(&awake,false);atomic_store(&local_reply,true);atomic_store(&custom_speaking,false);atomic_store(&brightness_until,0);atomic_fetch_add(&turn,1);ESP_LOGI("tracker_dialog","chat muted; controls remain enabled");}
bool tracker_dialog_awake(void){return atomic_load(&awake);}
bool tracker_dialog_controls_allowed(void){return atomic_load(&connected);}
bool tracker_dialog_audio_allowed(void){return atomic_load(&connected)&&atomic_load(&awake)&&(atomic_load(&custom_speaking)||!atomic_load(&local_reply));}
void tracker_dialog_say(const char *text){
 if(!replies||!text||!atomic_load(&awake)||!atomic_load(&connected))return;
 atomic_store(&local_reply,true);reply_job job={.turn=atomic_load(&turn)};snprintf(job.text,sizeof(job.text),"%s",text);xQueueOverwrite(replies,&job);
}
void tracker_dialog_asr(const char *text,bool final){
 if(!text||!final||!tracker_dialog_controls_allowed())return;
 unsigned expires=atomic_load(&brightness_until);bool waiting=expires&&(int32_t)(expires-(uint32_t)(esp_timer_get_time()/1000))>0;
 tracker_intent intent=tracker_parse(text,waiting);
 // Wake controls speech only. Local commands keep running while voice is muted.
 if(intent.wake_bytes&&!atomic_load(&awake))tracker_dialog_wake();
 atomic_fetch_add(&turn,1);atomic_store(&custom_speaking,false);atomic_store(&local_reply,false);
 bool ok;char reply[192];
 switch(intent.kind){
 case TI_POSTURE_ON:case TI_POSTURE_OFF:case TI_POSTURE_CALIBRATE:case TI_POSTURE_PAUSE:case TI_POSTURE_RESUME:case TI_POSTURE_STATUS:case TI_ROTATE:case TI_PC_EXIT:{
  const char *actions[]={"posture_on","posture_off","posture_calibrate","posture_pause","posture_resume","posture_status","posture_rotate","posture_exit"};
  atomic_store(&brightness_until,0);ok=tracker_posture_action(actions[intent.kind-TI_POSTURE_ON]);
  ESP_LOGI("tracker_dialog","control=%s accepted=%d muted=%d",actions[intent.kind-TI_POSTURE_ON],ok,!atomic_load(&awake));
  tracker_dialog_say(ok?"请求已接收，请保持电脑程序运行。":"操作未执行，请先开启坐姿检测。");return;}
 case TI_WAKE:tracker_dialog_say("我在，我是小灵，你说吧。");return;
 case TI_SLEEP:tracker_dialog_sleep();(void)agent_app_abort_output();agent_app_resume_upload();fresh_control_audio(false);return;
 case TI_HAND:case TI_FACE:
  atomic_store(&brightness_until,0);ok=tracker_select(intent.kind==TI_HAND?"hand":"face",true);
  ESP_LOGI("tracker_dialog","control=track_%s accepted=%d muted=%d",intent.kind==TI_HAND?"hand":"face",ok,!atomic_load(&awake));
  tracker_dialog_say(ok?(intent.kind==TI_HAND?"已开启手部追踪，请保持电脑端追踪程序运行。":"已开启人脸追踪，请保持电脑端追踪程序运行。"):"追踪控制器不可用。");return;
 case TI_STOP:atomic_store(&brightness_until,0);ok=fresh_control_action("stop",.07f,300);tracker_dialog_say(ok?"已停止追踪。":"停止请求失败，请检查设备。");return;
 case TI_SWITCH:{char state[1200];fresh_control_state(state,sizeof(state),false);cJSON *j=cJSON_Parse(state);cJSON *m=cJSON_GetObjectItem(j,"tracking_mode");bool face=cJSON_IsString(m)&&!strcmp(m->valuestring,"face");cJSON_Delete(j);ok=tracker_select(face?"hand":"face",true);tracker_dialog_say(ok?(face?"已切换为手部追踪。":"已切换为人脸追踪。"):"切换失败。");return;}
 case TI_BRIGHTNESS_ASK:atomic_store(&brightness_until,(uint32_t)(esp_timer_get_time()/1000)+60000);tracker_dialog_say("需要调到多少亮度？请说零到十，例如亮度调整为五。");return;
 case TI_BRIGHTNESS_INVALID:atomic_store(&brightness_until,(uint32_t)(esp_timer_get_time()/1000)+60000);tracker_dialog_say("亮度范围是零到十，请再说一次。");return;
 case TI_BRIGHTNESS_SET:
  ok=tracker_light_level(intent.level);atomic_store(&brightness_until,0);
  snprintf(reply,sizeof(reply),ok?"亮度已调整为%d。":"灯光设置失败，目标亮度%d未生效。",intent.level);tracker_dialog_say(reply);return;
 case TI_CANCEL:atomic_store(&brightness_until,0);tracker_dialog_say("已取消亮度调节。");return;
 case TI_LIGHT_ON:case TI_LIGHT_OFF:
  ok=tracker_light_action(intent.kind==TI_LIGHT_ON?"on":"off",0);tracker_dialog_say(ok?(intent.kind==TI_LIGHT_ON?"已开灯。":"已关灯。"):"灯光控制失败。");return;
 default:atomic_store(&brightness_until,0);break;
 }
 if(fresh_control_text(text))tracker_dialog_say("已接受动作请求。");
 else ESP_LOGI("tracker_dialog","route=cloud_chat turn=%d audio_allowed=%d",atomic_load(&turn),tracker_dialog_audio_allowed());
}
// Invoked with the complete ASR text before it is truncated into a public notice.
void qm_agent_user_text_observe(const char *text,int final){tracker_dialog_asr(text,final!=0);}
int qm_agent_app_audio_allowed(void){return tracker_dialog_audio_allowed();}

void tracker_dialog_notify(const char *text){
 tracker_dialog_say(text);
}
