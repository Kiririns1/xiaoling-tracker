"""Exercise the actual firmware state machine and JSON validators with fake time/PWM."""
from pathlib import Path
import subprocess,tempfile,re
root=Path(__file__).resolve().parents[1]
src=root/'apps/main/peripheral'
cjson=Path('C:/Users/kiririns/Desktop/hack/ljyd_xjwb03_agent_public_developer/esp-idf/components/json/cJSON')
stub=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "fresh_control.h"
#include "fresh_frame_guard.h"
typedef void *SemaphoreHandle_t;
typedef void *esp_timer_handle_t;
typedef int esp_err_t;
typedef int ledc_channel_t;
typedef struct {int speed_mode,timer_num,duty_resolution,freq_hz,clk_cfg;} ledc_timer_config_t;
typedef struct {int gpio_num,speed_mode,channel,timer_sel,duty;} ledc_channel_config_t;
typedef struct {void(*callback)(void*);const char *name;} esp_timer_create_args_t;
enum {LEDC_LOW_SPEED_MODE,LEDC_CHANNEL_4,LEDC_CHANNEL_5,LEDC_TIMER_2,LEDC_TIMER_14_BIT,LEDC_AUTO_CLK};
#define pdTRUE 1
#define portMAX_DELAY 99999
#define ESP_OK 0
static int64_t now_us=1000000;
static unsigned duty[8];
static int64_t esp_timer_get_time(void){return now_us;}
static void* xSemaphoreCreateMutex(void){return (void*)1;}
static int xSemaphoreTake(void* x,int t){(void)x;(void)t;return pdTRUE;}
static void xSemaphoreGive(void* x){(void)x;}
static int ledc_set_duty(int a,int b,unsigned d){(void)a;duty[b]=d;return 0;}
static int ledc_update_duty(int a,int b){(void)a;(void)b;return 0;}
static int ledc_stop(int a,int b,unsigned idle){(void)a;duty[b]=idle;return 0;}
static int ledc_timer_config(ledc_timer_config_t *x){(void)x;return 0;}
static int ledc_channel_config(ledc_channel_config_t *x){assert(x->gpio_num==5||x->gpio_num==6);return 0;}
static int esp_timer_create(esp_timer_create_args_t *x,void **p){(void)x;*p=(void*)1;return 0;}
static int esp_timer_start_periodic(void *p,int t){(void)p;(void)t;return 0;}
'''
control=(src/'fresh_control.c').read_text(encoding='utf-8')
control='\n'.join(x for x in control.splitlines() if not re.match(r'#include "(driver/|freertos/|esp_)',x))
commands=(src/'fresh_commands.c').read_text(encoding='utf-8')
commands=commands[commands.index('static bool number('):commands.index('static void cli(')]
tone=(src/'fresh_tone.c').read_text(encoding='utf-8')
tone_globals=tone[tone.index('#define TEXT_CAP'):tone.index('typedef struct {char body')]
tone_apply=tone[tone.index('static void apply_classification('):tone.index('static void worker(')]
tone_lifecycle=tone[tone.index('void fresh_tone_begin_turn('):]
tone=tone_globals+tone_apply+tone_lifecycle
tone=re.sub(r'\bgate\b','tone_gate',tone)
tone=re.sub(r'\bpending\b','tone_pending',tone)
tone=tone.replace('static QueueHandle_t jobs;','typedef void *QueueHandle_t;\nstatic QueueHandle_t jobs;')
tone=tone.replace('static int64_t last_pcm_us;','static int64_t last_pcm_us;\nstatic tone_job_t queued_tone;\nstatic void xQueueOverwrite(void *q, const tone_job_t *job){(void)q;queued_tone=*job;}\n#define ESP_LOGI(...) ((void)0)')
checks=r'''
static void advance(int ms){now_us+=(int64_t)ms*1000;tick(NULL);}
static bool json_plan(const char *text){cJSON *j=cJSON_Parse(text);bool ok=fresh_control_json(j);cJSON_Delete(j);return ok;}
int main(void){
 char state[384];
 assert(fresh_control_init());assert(!duty[LEDC_CHANNEL_4]&&!duty[LEDC_CHANNEL_5]);
 assert(!fresh_control_action("track_on",.15f,300));
 fresh_control_state(state,sizeof(state),true);
 assert(fresh_control_action("track_on",.15f,300));unsigned r=revision;
 assert(fresh_control_step(.2f,r));assert(speed_now>0&&pitch_speed==0);
 advance(360);assert(speed_now==0&&mode==1);
 assert(!fresh_control_step(NAN,r));assert(!fresh_control_step(.36f,r));
 assert(fresh_control_action("stop",.15f,300));assert(!fresh_control_step(.2f,r));
 assert(!fresh_control_try_gesture(true,r));
 r=revision;assert(fresh_control_try_gesture(true,r));
 assert(pitch_speed>0&&speed_now==0&&duty[LEDC_CHANNEL_4]==0);
 advance(100);assert(pitch_speed==0);advance(100);assert(pitch_speed<0);advance(100);
 assert(pitch_speed==0&&mode==0&&!duty[LEDC_CHANNEL_5]);
 r=revision;assert(fresh_control_try_gesture(false,r));assert(speed_now>0&&pitch_speed==0);
 advance(150);advance(100);assert(speed_now<0);advance(300);advance(100);assert(speed_now>0);advance(150);assert(mode==0&&speed_now==0);
 assert(fresh_control_action("left",.15f,300));r=revision;assert(!fresh_control_try_gesture(true,r));
 assert(fresh_control_action("stop",.15f,300));assert(pitch_speed==0&&speed_now==0);
 fresh_control_audio(true);assert(fresh_control_action("right",.15f,300));assert(pending&&speed_now==0);
 advance(200);assert(pending&&speed_now==0);fresh_control_audio(false);advance(20);assert(speed_now>0);advance(300);assert(mode==0);
 fresh_control_audio(true);assert(fresh_control_action("left",.15f,300));advance(30001);assert(mode==0&&speed_now==0);fresh_control_audio(false);
 assert(json_plan("{\"action\":\"sequence\",\"repeat\":2,\"interval_ms\":100,\"steps\":[{\"action\":\"right\",\"duration_ms\":100},{\"action\":\"wait\",\"duration_ms\":50},{\"action\":\"left\",\"duration_ms\":100}]}"));
 assert(speed_now>0);advance(100);assert(speed_now==0);advance(50);assert(speed_now<0);advance(100);assert(gap&&cycles==1);advance(100);assert(speed_now>0);advance(100);advance(50);advance(100);assert(mode==0);
 assert(!json_plan("{\"action\":\"right\",\"repeat\":1.5}"));assert(!json_plan("{\"action\":\"right\",\"speed\":0.36}"));
 assert(!json_plan("{\"action\":\"right\",\"duration_ms\":3600000,\"repeat\":2}"));
 assert(!json_plan("{\"action\":\"unknown\"}"));assert(!json_plan("{\"action\":\"sequence\",\"steps\":[]}"));
 fresh_control_state(state,sizeof(state),true);assert(fresh_control_action("track_on",.15f,300));r=revision;
 assert(fresh_control_step(.1f,r));advance(3100);assert(mode==0&&speed_now==0&&revision!=r);
 assert(fresh_control_text("请摄像头向右转三百毫秒。"));assert(speed_now>0);advance(300);assert(mode==0);
 assert(!fresh_control_text("不要向左转"));assert(!fresh_control_text("你能向右转吗？"));assert(!fresh_control_text("向右转三百度"));
 assert(fresh_control_text("向右转八百毫秒三次每次间隔0.5秒"));assert(cycles==3&&interval_ms==500&&count==1&&plan[0].duration_ms==800);fresh_control_action("stop",.15f,300);
 assert(fresh_control_text("先向右转800毫秒然后向左转500毫秒"));assert(count==2&&plan[0].speed>0&&plan[1].speed<0);fresh_control_action("stop",.15f,300);
 assert(fresh_control_text("摄像头向上转300ms。"));assert(pitch_speed>0&&speed_now==0);advance(300);assert(pitch_speed==0&&mode==0);
 assert(fresh_control_text("请摄像头向下转三百毫秒"));assert(pitch_speed<0&&speed_now==0);advance(300);assert(pitch_speed==0&&mode==0);
 assert(!fresh_control_text("摄像头向下转300mm"));assert(!fresh_control_text("不要向上转300ms"));
 assert(!fresh_control_action("up",.15f,1001));
 assert(json_plan("{\"action\":\"up\",\"duration_ms\":300}"));assert(pitch_speed>0);fresh_control_action("stop",.15f,300);
 assert(json_plan("{\"action\":\"sequence\",\"steps\":[{\"action\":\"up\",\"duration_ms\":100},{\"action\":\"left\",\"duration_ms\":100},{\"action\":\"down\",\"duration_ms\":100}]}"));
 assert(pitch_speed>0&&speed_now==0);advance(100);assert(pitch_speed==0&&speed_now<0);advance(100);assert(pitch_speed<0&&speed_now==0);advance(100);assert(pitch_speed==0&&mode==0);
 fresh_frame_history_t history={0};int64_t t=1000000;
 for(unsigned id=100;id<=112;++id)fresh_frame_record(&history,id,t+(id-100)*33000);
 assert(fresh_frame_recent(&history,100,t+396000)); // 12 frames behind, genuinely <500ms old.
 assert(!fresh_frame_recent(&history,100,t+500001));
 assert(!fresh_frame_recent(&history,113,t+396000));
 fresh_frame_record(&history,164,t+600000);assert(!fresh_frame_recent(&history,100,t+600000));
 assert(!fresh_control_text("向右转一小时一百次"));
 assert(fresh_tone_parse("{\"tone\":\"negative\",\"confidence\":0.9}")==1);
 assert(fresh_tone_parse("{\"tone\":\"affirmative\",\"confidence\":1}")==2);
 assert(!fresh_tone_parse("{\"tone\":\"negative\",\"confidence\":0.79}"));assert(!fresh_tone_parse("{\"tone\":\"negative\",\"confidence\":2}"));
 assert(!fresh_tone_parse("{\"tone\":\"shake\",\"confidence\":1}"));assert(!fresh_tone_parse("not json"));
 assert(!fresh_tone_parse("{\"tone\":\"negative\",\"confidence\":\"1\"}"));
 assert(!fresh_tone_parse("{\"tone\":\"negative\",\"confidence\":1}extra"));
 tone_gate=(void*)1;jobs=(void*)1;
 fresh_tone_begin_turn();fresh_tone_feed("不是，我是语音助手。",false);assert(!submitted);
 fresh_tone_feed("不是，我是语音助手。",true);assert(submitted&&!strcmp(queued_tone.text,"不是，我是语音助手。"));
 fresh_tone_playback(true);apply_classification(&queued_tone,1);assert(tone_pending&&!acted&&mode==0);
 qm_audio_app_output_observe();assert(acted&&mode==2&&gesture_axis==0);fresh_tone_playback(false);assert(mode==2);advance(150);advance(100);advance(300);advance(100);advance(150);assert(mode==0&&speed_now==0);
 fresh_tone_begin_turn();fresh_tone_feed("是的，你说得对。",true);tone_job_t old_job=queued_tone;
 fresh_tone_cancel();qm_audio_app_output_observe();apply_classification(&old_job,2);assert(mode==0&&!tone_pending);
 fresh_tone_begin_turn();fresh_tone_feed("是的。",true);apply_classification(&queued_tone,2);assert(tone_pending);
 fresh_control_action("stop",.15f,300);qm_audio_app_output_observe();assert(!acted&&mode==0);
 fresh_tone_begin_turn();fresh_tone_feed("是的。",true);advance(8001);apply_classification(&queued_tone,2);qm_audio_app_output_observe();assert(!acted&&mode==0);
 fresh_tone_begin_turn();fresh_tone_feed("是的。",true);qm_audio_app_output_observe();apply_classification(&queued_tone,2);assert(acted&&pitch_speed>0&&speed_now==0);fresh_tone_cancel();assert(pitch_speed==0);
 fresh_tone_begin_turn();char too_long[TEXT_CAP+1];memset(too_long,'a',TEXT_CAP);too_long[TEXT_CAP]=0;fresh_tone_feed(too_long,true);assert(overflow&&!submitted);
 puts("PASS: dual-axis PWM isolation, gesture completion, stop/revision, tracking timeouts, audio queue, sequence/repeat limits, Chinese commands, tone schema.");
}
'''
with tempfile.TemporaryDirectory(prefix='fresh_test_',dir=root.parent/'tmp') as folder:
 p=Path(folder);(p/'test.c').write_text(stub+control+commands+tone+checks,encoding='utf-8')
 subprocess.run(['C:/mingw64/bin/gcc.exe','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function',f'-I{src}',f'-I{cjson}',str(p/'test.c'),str(cjson/'cJSON.c'),'-o',str(p/'test.exe')],check=True)
 subprocess.run([str(p/'test.exe')],check=True)
