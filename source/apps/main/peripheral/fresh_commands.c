#include "fresh_commands.h"
#include "fresh_control.h"
#include "fresh_tone.h"
#include "ljyd_provision.h"
#include "bsp_camera.h"
#include "agent_app.h"
#include "qm_cli.h"
#include "qm_log.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>

static bool number(const char *p,size_t n,double *out){
 if(!n||n>=64){return false;}
 char b[64];memcpy(b,p,n);b[n]=0;
 if(!strcmp(b,"半")){*out=.5;return true;}
 if(b[0]>='0'&&b[0]<='9'){char *end;*out=strtod(b,&end);return !*end&&isfinite(*out)&&*out>=0;}
 const char *digits[]={"零","一","二","三","四","五","六","七","八","九","两"};
 int total=0,digit=-1,last_unit=10000;const char *at=b;
 while(*at){bool found=false;for(int i=0;i<11;++i)if(!strncmp(at,digits[i],strlen(digits[i]))){if(digit>0)return false;digit=i==10?2:i;at+=strlen(digits[i]);found=true;break;}if(found)continue;
 const char *units[]={"十","百","千"};int scales[]={10,100,1000};for(int i=0;i<3;++i)if(!strncmp(at,units[i],strlen(units[i]))){int u=scales[i];if(u>=last_unit||(digit<0&&u!=10))return false;total+=(digit<0?1:digit)*u;digit=-1;last_unit=u;at+=strlen(units[i]);found=true;break;}if(!found)return false;}
 *out=total+(digit<0?0:digit);return true;
}
static bool duration(const char *s,int *ms){const char *units[]={"毫秒","ms","秒","s","分钟"};int scales[]={1,1,1000,1000,60000};size_t n=strlen(s);
 for(unsigned i=0;i<5;++i){size_t k=strlen(units[i]);if(n>k&&!strcmp(s+n-k,units[i])){double v;if(!number(s,n-k,&v))return false;v*=scales[i];if(v<1||v>3600000||floor(v)!=v)return false;*ms=(int)v;return true;}}return false;
}
static bool parse_motion_plan(const char *input){
 char text[512];if(strlen(input)>=sizeof(text))return false;strcpy(text,input);char *p=text;
 int repeat=1,interval=0;char *gap=strstr(p,"每次间隔");if(!gap)gap=strstr(p,"间隔");
 if(gap){char *amount=gap+strlen(!strncmp(gap,"每次间隔",strlen("每次间隔"))?"每次间隔":"间隔");if(!duration(amount,&interval))return false;*gap=0;}
 char *times=strstr(p,"次");if(times){if(times[strlen("次")])return false;char *start=times;
  char *explicit_repeat=strstr(p,"重复");if(explicit_repeat){start=explicit_repeat+strlen("重复");}
  else{const char *units[]={"毫秒","秒","ms","s","分钟"};char *unit_end=NULL;for(unsigned i=0;i<5;++i){char *at=strstr(p,units[i]);while(at&&at<times){char *end=at+strlen(units[i]);if(!unit_end||end>unit_end)unit_end=end;at=strstr(end,units[i]);}}if(!unit_end)return false;start=unit_end;}
  double value;if(!number(start,times-start,&value)||value<1||value>100||floor(value)!=value)return false;repeat=(int)value;*(explicit_repeat?explicit_repeat:start)=0;
 }
 fresh_step_t steps[32];int axes[32]={0};int n=0;
 while(*p){if(!strncmp(p,"先",strlen("先")))p+=strlen("先");
  const char *joins[]={"然后","接着","再"};char *split=NULL;size_t join_len=0;for(unsigned i=0;i<3;++i){char *at=strstr(p,joins[i]);if(at&&(!split||at<split)){split=at;join_len=strlen(joins[i]);}}
  if(split)*split=0;
  const char *directions[]={"向右转","往右转","右转","向左转","往左转","左转","向上转","往上转","上转","向下转","往下转","下转","等待","暂停"};bool found=false;float speed=0;int axis=0;const char *tail=NULL;
  for(int i=0;i<14;++i){size_t k=strlen(directions[i]);if(!strncmp(p,directions[i],k)){tail=p+k;speed=i<3?.15f:i<6?-.15f:i<9?.15f:i<12?-.15f:0;axis=i>=6&&i<12?1:0;found=true;break;}}
  if(!found||n>=32){return false;}
  int ms=300;
  if(*tail&&strcmp(tail,"一下")&&strcmp(tail,"一点")&&!duration(tail,&ms))return false;
  if(speed==0&&!*tail){return false;}
  axes[n]=axis;steps[n++]=(fresh_step_t){speed,ms};
  if(!split){break;}
  p=split+join_len;if(!*p)return false;
 }
 return fresh_control_plan_axes(steps,axes,n,repeat,interval);
}
bool fresh_control_text(const char *input){
 if(!input){return false;}
 char b[512];size_t n=0;
 while(*input){if(*input==' '||*input=='\r'||*input=='\n'||*input=='\t'){++input;continue;}const char *marks[]={"，","。","！"};bool skip=false;for(int i=0;i<3;++i)if(!strncmp(input,marks[i],strlen(marks[i]))){input+=strlen(marks[i]);skip=true;break;}if(skip)continue;if(n+1>=sizeof(b))return false;b[n++]=*input++;}b[n]=0;
 const char *p=b;const char *prefix[]={"你好","小灵","小林","请","帮我","把","摄像头","舵机"};
 for(int pass=0;pass<8;++pass){bool found=false;for(int i=0;i<8;++i)if(!strncmp(p,prefix[i],strlen(prefix[i]))){p+=strlen(prefix[i]);found=true;break;}if(!found)break;}
 const char *stop[]={"停止","停止转动","关闭自动锁定","停止跟随","停止锁定","关闭自动跟随"};for(int i=0;i<6;++i)if(!strcmp(p,stop[i]))return fresh_control_action("stop",.15f,300);
 if(!strcmp(p,"开启自动锁定")||!strcmp(p,"开启自动跟随"))return fresh_control_action("track_on",.15f,300);
 if(!strcmp(p,"点头")||!strcmp(p,"点一下头"))return fresh_control_try_gesture(true,fresh_control_revision());
 if(!strcmp(p,"摇头")||!strcmp(p,"摇一下头"))return fresh_control_try_gesture(false,fresh_control_revision());
 if(strstr(p,"次")||strstr(p,"然后")||strstr(p,"接着")||!strncmp(p,"先",strlen("先")))return parse_motion_plan(p);
 const char *directions[]={"向右转","往右转","右转","向左转","往左转","左转","向上转","往上转","上转","向下转","往下转","下转","抬头","低头"};
 for(int i=0;i<14;++i){size_t k=strlen(directions[i]);if(strncmp(p,directions[i],k))continue;const char *tail=p+k;int ms=300;if(*tail&&strcmp(tail,"一下")&&strcmp(tail,"一点")&&!duration(tail,&ms))return false;const char *a=i<3?"right":i<6?"left":i<9?"up":i<12?"down":i==12?"up":"down";return fresh_control_action(a,.15f,ms);}
 return false;
}
static void cli(char *buf,int cap,int argc,char **argv){
 const char *cmd=argv[0];int ret=0;(void)buf;(void)cap;
 if(!strcmp(cmd,"/help")){QM_LOGI("console","/voice /chaton /chatoff /control /lock /stop /left [ms] /right [ms] /up [ms] /down [ms] /plan JSON /camera /say TEXT");return;}
 if(!strcmp(cmd,"/voice")||!strcmp(cmd,"/chaton")){ret=agent_app_start_conversation();}
 else if(!strcmp(cmd,"/chatoff")){ret=agent_app_leave();}
 else if(!strcmp(cmd,"/pair")){fresh_control_action("stop",.15f,300);ljyd_provision_pairing_and_reboot();return;}
 else if(!strcmp(cmd,"/control")){char state[1200];fresh_control_state(state,sizeof(state),false);QM_LOGI("console","%s",state);return;}
 else if(!strcmp(cmd,"/camera")){QM_LOGI("console","camera ready=%d",bsp_camera_is_available());return;}
 else if(!strcmp(cmd,"/say")){if(argc<2)return;char text[512]="";for(int i=1;i<argc;++i){if(strlen(text)+strlen(argv[i])+2>=sizeof(text))return;if(i>1)strcat(text," ");strcat(text,argv[i]);}ret=agent_app_user_corpus(text);}
 else if(!strcmp(cmd,"/plan")){if(argc!=2)return;cJSON *j=cJSON_Parse(argv[1]);bool ok=fresh_control_json(j);cJSON_Delete(j);QM_LOGI("console","plan accepted=%d",ok);return;}
 else if(!strcmp(cmd,"/nod")||!strcmp(cmd,"/shake")){fresh_tone_cancel();bool ok=fresh_control_try_gesture(!strcmp(cmd,"/nod"),fresh_control_revision());QM_LOGI("console","gesture accepted=%d",ok);return;}
 else {const char *action=!strcmp(cmd,"/lock")?"track_on":cmd+1;int ms=300;if(argc>1){char *end;long v=strtol(argv[1],&end,10);if(*end||v<1||v>3600000){QM_LOGW("console","invalid duration");return;}ms=v;}QM_LOGI("console","%s accepted=%d",action,fresh_control_action(action,.15f,ms));return;}
 QM_LOGI("console","%s ret=%d",cmd,ret);
}
void fresh_commands_init(void){static const struct qm_cli_command commands[]={
 {"/help","list fresh commands",cli},{"/voice","start Lingji voice",cli},{"/chaton","continuous Lingji conversation",cli},{"/chatoff","leave conversation",cli},{"/control","motor state",cli},{"/lock","enable PC tracking",cli},{"/stop","stop both motors",cli},{"/left","left [ms]",cli},{"/right","right [ms]",cli},{"/plan","validated JSON motion plan",cli},{"/camera","camera state",cli},{"/say","cloud TTS text",cli},{"/nod","short pitch gesture GPIO6",cli},{"/shake","short yaw gesture GPIO5",cli}};
 static const struct qm_cli_command pair={"/pair","reopen BLE, retain credentials",cli};qm_cli_register_command(&pair);
 static const struct qm_cli_command pitch[]={{"/up","pitch up [ms], max 1000ms",cli},{"/down","pitch down [ms], max 1000ms",cli}};
 qm_cli_register_command(&pitch[0]);qm_cli_register_command(&pitch[1]);
 for(unsigned i=0;i<sizeof(commands)/sizeof(commands[0]);++i)qm_cli_register_command(&commands[i]);
}
