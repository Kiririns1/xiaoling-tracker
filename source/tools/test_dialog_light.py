"""Run actual dialog admission and light state with queued speech/PWM substitutes."""
from pathlib import Path
import tempfile,subprocess
r=Path(__file__).resolve().parents[1];p=r/'apps/main/peripheral'
cjson=Path(r'C:/Users/kiririns/Desktop/hack/ljyd_xjwb03_agent_public_developer/esp-idf/components/json/cJSON')
source=''
for name in ['tracker_light.c','tracker_dialog.c']:
    source+='\n'.join(x for x in (p/name).read_text(encoding='utf-8').splitlines() if not any(t in x for t in ['#include "bsp_ws2812.h"','#include "agent_app.h"','#include "qm_agent.h"','#include "esp_','#include "freertos/']))+'\n'
stub=r'''
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <setjmp.h>
#include "fresh_control.h"
#include "tracker_dialog.h"
typedef void* SemaphoreHandle_t;typedef void* QueueHandle_t;typedef void* TaskHandle_t;
#define QM_EOK 0
#define pdTRUE 1
#define pdPASS 1
#define portMAX_DELAY 0
#define pdMS_TO_TICKS(x) (x)
#define ESP_LOGI(...) ((void)0)
static int64_t now_us=1000000;static int brightness_byte;static int selection=-1,stops;static char posture_action[40];static unsigned queued;static char queued_text[192];
static unsigned item_size,corpus_calls,resume_calls,abort_calls;
static unsigned char queued_job[512];
static bool replay_queue,delivered,interrupt_during_delay,sleep_during_corpus,upload_running=true;
static jmp_buf worker_escape;
static int64_t esp_timer_get_time(void){return now_us;}
static void* xSemaphoreCreateMutex(void){return (void*)1;}
static int xSemaphoreTake(void* p,int x){return 1;}
static void xSemaphoreGive(void* p){}
static int bsp_ws2812_init(void){return 0;}
static int bsp_ws2812_fill(int a,int b,int c){assert(a==b&&b==c);brightness_byte=a;return 0;}
static void* xQueueCreate(int a,int b){assert(b<=sizeof(queued_job));item_size=b;return (void*)1;}
static int xQueueOverwrite(void* q,const void* job){++queued;memcpy(queued_job,job,item_size);snprintf(queued_text,sizeof(queued_text),"%s",(const char*)job);return 1;}
static int xQueueReceive(void* q,void* job,int t){if(replay_queue&&!delivered){memcpy(job,queued_job,item_size);delivered=true;return 1;}longjmp(worker_escape,1);return 0;}
static int xTaskCreate(void(*fn)(void*),const char*n,int s,void* arg,int pr,void** handle){if(handle)*handle=(void*)1;return 1;}
static unsigned ulTaskNotifyTake(int a,int b){return 0;}
static void xTaskNotifyGive(void* t){}
static void vTaskDelay(int x){if(interrupt_during_delay){interrupt_during_delay=false;tracker_dialog_sleep();}}
static int agent_app_abort_output(void){++abort_calls;upload_running=false;return 0;}
static void agent_app_resume_upload(void){++resume_calls;upload_running=true;}
static int agent_app_user_corpus(const char* s){++corpus_calls;assert(tracker_dialog_audio_allowed());if(sleep_during_corpus){sleep_during_corpus=false;tracker_dialog_sleep();assert(!tracker_dialog_audio_allowed());}return 0;}
static int agent_app_wait_tts_complete(unsigned x){return 0;}
unsigned tracker_boot_id(void){return 123;}
bool tracker_select(const char *mode,bool on){selection=!strcmp(mode,"face");return true;}
bool fresh_control_action(const char*a,float b,int c){++stops;return true;}
bool fresh_control_text(const char*t){return false;}
bool tracker_posture_action(const char*a){snprintf(posture_action,sizeof(posture_action),"%s",a);return true;}
void fresh_control_audio(bool b){}
void fresh_control_state(char *b,unsigned cap,bool hb){snprintf(b,cap,"{\"tracking_mode\":\"hand\"}");}
'''
checks=r'''
static void run_queued_reply(void){
 replay_queue=true;delivered=false;
 if(setjmp(worker_escape)==0)worker(NULL);
 replay_queue=false;
}
int main(void){
 assert(tracker_light_init());assert(!on&&percent==25);
 assert(tracker_dialog_init());tracker_dialog_network(true);
 tracker_dialog_asr("开始追踪手",true);assert(selection==0&&!tracker_dialog_awake()&&!tracker_dialog_audio_allowed()&&queued==0);
 tracker_dialog_asr("你好小林",false);assert(!tracker_dialog_awake());
 tracker_dialog_asr("你好小林",true);assert(tracker_dialog_awake());
 tracker_dialog_asr("开始追踪手",true);assert(selection==0);
 tracker_dialog_asr("开始追踪脸",true);assert(selection==1);
 tracker_dialog_asr("调节亮度",true);assert(atomic_load(&brightness_until)>0);
 tracker_dialog_asr("五",true);assert(on&&percent==50&&brightness_byte==128);
 tracker_dialog_asr("亮度调整为11",true);assert(percent==50);
 tracker_dialog_asr("0",true);assert(!on&&brightness_byte==0&&percent==0);
 tracker_dialog_asr("调节亮度",true);now_us+=60001000;tracker_dialog_asr("十",true);assert(percent==0);
 tracker_dialog_asr("停止聊天",true);assert(!tracker_dialog_awake()&&!tracker_dialog_audio_allowed());
 tracker_dialog_asr("开始追踪手",true);assert(selection==0&&!tracker_dialog_awake()&&!tracker_dialog_audio_allowed());
 tracker_dialog_asr("你好小灵，开始追踪手",true);assert(tracker_dialog_awake()&&selection==0);
 tracker_dialog_asr("亮度调整为10",true);assert(percent==100&&brightness_byte==255);
 const char *commands[]={"开启坐姿检测","关闭坐姿检测","校准坐姿","暂停坐姿追脸","恢复坐姿追脸","查询坐姿状态","旋转画面","退出电脑程序"};
 const char *actions[]={"posture_on","posture_off","posture_calibrate","posture_pause","posture_resume","posture_status","posture_rotate","posture_exit"};
 for(int i=0;i<8;++i){tracker_dialog_asr(commands[i],true);assert(!strcmp(posture_action,actions[i]));}
 // Reproduce face-follow -> stop chatting -> posture controls, without speech.
 tracker_dialog_asr("开始追踪脸",true);assert(selection==1);
 int before_stops=stops;tracker_dialog_asr("停止聊天",true);
 assert(selection==1&&stops==before_stops&&tracker_dialog_controls_allowed()&&!tracker_dialog_awake());
 unsigned q=queued;
 for(int i=0;i<8;++i){posture_action[0]=0;tracker_dialog_asr(commands[i],true);assert(!strcmp(posture_action,actions[i]));assert(queued==q&&!tracker_dialog_awake()&&!tracker_dialog_audio_allowed());}
 tracker_dialog_asr("调节亮度",true);assert(atomic_load(&brightness_until)>0);
 tracker_dialog_asr("五",true);assert(percent==50&&on&&queued==q&&!tracker_dialog_audio_allowed());
 tracker_dialog_asr("关灯",true);assert(!on&&queued==q);
 tracker_dialog_asr("开灯",true);assert(on&&queued==q);
 tracker_dialog_asr("讲个笑话",true);assert(!tracker_dialog_awake()&&!tracker_dialog_audio_allowed()&&queued==q);
 tracker_dialog_notify("请注意坐姿");assert(queued==q&&!tracker_dialog_awake());
 atomic_store(&custom_speaking,true);assert(!tracker_dialog_audio_allowed());atomic_store(&custom_speaking,false);
 assert(tracker_light_alert());
 // Wake restores normal confirmations and background speech.
 tracker_dialog_asr("你好小灵，开启坐姿检测",true);assert(tracker_dialog_awake()&&!strcmp(posture_action,"posture_on")&&queued==q+1);
 run_queued_reply();assert(corpus_calls==1&&upload_running);
 tracker_dialog_asr("介绍一下你自己",true);assert(tracker_dialog_awake()&&tracker_dialog_audio_allowed());
 tracker_dialog_notify("请注意坐姿");assert(queued==q+2);
 sleep_during_corpus=true;run_queued_reply();assert(corpus_calls==2&&!tracker_dialog_awake()&&!tracker_dialog_audio_allowed()&&upload_running);
 // A stop arriving in the 150ms handoff must resume ASR, not leave it paused.
 tracker_dialog_wake();tracker_dialog_say("测试回执");
 unsigned before_resume=resume_calls;interrupt_during_delay=true;run_queued_reply();
 assert(corpus_calls==2&&resume_calls==before_resume+1&&upload_running&&!tracker_dialog_awake()&&tracker_dialog_controls_allowed());
 // Already-queued notifications are discarded after mute.
 tracker_dialog_wake();tracker_dialog_notify("请注意坐姿");tracker_dialog_sleep();run_queued_reply();assert(corpus_calls==2&&!tracker_dialog_audio_allowed());
 tracker_dialog_network(false);assert(!tracker_dialog_awake()&&!tracker_dialog_audio_allowed());
 assert(!tracker_dialog_controls_allowed());posture_action[0]=0;tracker_dialog_asr("开启坐姿检测",true);assert(!posture_action[0]);
 tracker_dialog_network(true);assert(tracker_dialog_controls_allowed()&&!tracker_dialog_awake());
 tracker_dialog_asr("校准坐姿",true);assert(!strcmp(posture_action,"posture_calibrate")&&!tracker_dialog_audio_allowed());
 assert(!tracker_light_level(-1)&&!tracker_light_level(11));
 cJSON *j=cJSON_Parse("{\"action\":\"toggle\",\"boot_id\":123,\"event_id\":\"0123456789abcdef0123456789abcdef\"}");
 assert(tracker_light_request(j));bool first=on;assert(tracker_light_request(j)&&on==first);cJSON_Delete(j);
 j=cJSON_Parse("{\"action\":\"toggle\",\"boot_id\":124,\"event_id\":\"1123456789abcdef0123456789abcdef\"}");
 assert(!tracker_light_request(j)&&on==first);cJSON_Delete(j);
 puts("PASS: actual C silent controls, face-follow preservation, all posture actions, quiet brightness, notification mute, wake recovery, in-flight mute and ASR handoff cancellation; prior light/wake tests passed");
}
'''
with tempfile.TemporaryDirectory() as tmp:
    f=Path(tmp)/'dialog.c';f.write_text(stub+source+checks,encoding='utf-8');exe=Path(tmp)/'dialog.exe'
    subprocess.run(['gcc','-std=c11','-I'+str(p),'-I'+str(cjson),str(f),str(p/'tracker_intent.c'),str(cjson/'cJSON.c'),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
