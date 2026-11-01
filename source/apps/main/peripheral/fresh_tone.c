#include "fresh_tone.h"
#include "fresh_control.h"
#include <string.h>
#include <stdatomic.h>
static atomic_bool acted;static atomic_int pending;static atomic_uint rev;
bool fresh_tone_init(void){return true;}
void fresh_tone_begin_turn(void){pending=0;acted=false;}
void fresh_tone_feed(const char *text,bool final){(void)final;if(!acted&&fresh_tone_is_negative(text)){rev=fresh_control_revision();pending=1;}}
void fresh_tone_playback(bool active){if(!active)pending=0;}
void fresh_tone_cancel(void){pending=0;}
int fresh_tone_parse(const char *s){return s&&!strncmp(s,"[SHAKE]",7);}
bool fresh_tone_is_negative(const char *s){
 if(!s)return false;
 const char *starts[]={"[SHAKE]","不是这样的","不是哦","不对哦","不可以","不能这样","我不同意","并不是","并非如此"};
 for(unsigned i=0;i<sizeof(starts)/sizeof(*starts);++i)if(!strncmp(s,starts[i],strlen(starts[i])))return true;
 return false;
}
void qm_agent_reply_observe(const char *text,int final){fresh_tone_feed(text,final!=0);}
void qm_agent_user_turn_observe(void){fresh_tone_begin_turn();}
void qm_audio_app_output_observe(void){if(atomic_exchange(&pending,0)&&!atomic_exchange(&acted,true)){fresh_control_try_shake(atomic_load(&rev));}}
