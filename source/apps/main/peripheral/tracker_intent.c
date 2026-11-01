#include "tracker_intent.h"
#include <string.h>
#include <stdlib.h>
#include <ctype.h>
static bool eq(const char *a,const char *b){return !strcmp(a,b);}
tracker_intent tracker_parse(const char *text,bool waiting){
 tracker_intent result={TI_NONE,-1,0};if(!text)return result;
 char clean[512];size_t n=0;
 while(*text){if(isspace((unsigned char)*text)){++text;continue;}
  const char *marks[]={"，","。","！","？",",","!","?"};bool skip=false;
  for(unsigned i=0;i<sizeof(marks)/sizeof(*marks);++i)if(!strncmp(text,marks[i],strlen(marks[i]))){text+=strlen(marks[i]);skip=true;break;}
  if(skip){continue;}
  if(n+1>=sizeof(clean)){return result;}
  clean[n++]=*text++;}clean[n]=0;
 const char *p=clean;const char *wake[]={"你好小灵","你好小林","小灵","小林"};
 for(unsigned i=0;i<4;++i)if(!strncmp(p,wake[i],strlen(wake[i]))){result.wake_bytes=strlen(wake[i]);p+=result.wake_bytes;break;}
 const char *prefix[]={"请","帮我"};for(int i=0;i<2;++i)if(!strncmp(p,prefix[i],strlen(prefix[i])))p+=strlen(prefix[i]);
 if(!*p&&result.wake_bytes){result.kind=TI_WAKE;return result;}
 if(eq(p,"停止聊天")||eq(p,"结束聊天")||eq(p,"退出聊天"))result.kind=TI_SLEEP;
 else if(eq(p,"开启坐姿检测")||eq(p,"开始坐姿检测"))result.kind=TI_POSTURE_ON;
 else if(eq(p,"关闭坐姿检测")||eq(p,"停止坐姿检测"))result.kind=TI_POSTURE_OFF;
 else if(eq(p,"校准坐姿")||eq(p,"重新校准坐姿"))result.kind=TI_POSTURE_CALIBRATE;
 else if(eq(p,"暂停坐姿追脸"))result.kind=TI_POSTURE_PAUSE;
 else if(eq(p,"恢复坐姿追脸"))result.kind=TI_POSTURE_RESUME;
 else if(eq(p,"查询坐姿状态"))result.kind=TI_POSTURE_STATUS;
 else if(eq(p,"退出电脑程序"))result.kind=TI_PC_EXIT;
 else if(eq(p,"旋转画面"))result.kind=TI_ROTATE;
 else if(eq(p,"开始追踪手")||eq(p,"开启手部追踪")||eq(p,"追踪手")||eq(p,"开始跟踪手"))result.kind=TI_HAND;
 else if(eq(p,"开始追踪脸")||eq(p,"开启人脸追踪")||eq(p,"追踪脸")||eq(p,"开始跟踪脸"))result.kind=TI_FACE;
 else if(eq(p,"停止追踪")||eq(p,"停止跟踪")||eq(p,"关闭追踪"))result.kind=TI_STOP;
 else if(eq(p,"切换追踪模式")||eq(p,"切换追踪"))result.kind=TI_SWITCH;
 else if(eq(p,"开灯")||eq(p,"打开灯"))result.kind=TI_LIGHT_ON;
 else if(eq(p,"关灯")||eq(p,"关闭灯"))result.kind=TI_LIGHT_OFF;
 else if(eq(p,"取消")||eq(p,"算了"))result.kind=waiting?TI_CANCEL:TI_NONE;
 else if(eq(p,"调节亮度")||eq(p,"调整亮度")||eq(p,"设置亮度")||eq(p,"亮度调节"))result.kind=TI_BRIGHTNESS_ASK;
 else {
  bool explicit_level=false;const char *forms[]={"亮度调整为","亮度调节为","亮度设置为","亮度调到","亮度调整到","亮度设为","亮度为","亮度"};
  for(unsigned i=0;i<sizeof(forms)/sizeof(*forms);++i)if(!strncmp(p,forms[i],strlen(forms[i]))){p+=strlen(forms[i]);explicit_level=true;break;}
  if(explicit_level||waiting){
   const char *digits[]={"零","一","二","三","四","五","六","七","八","九","十","两"};int value=-1;const char *end=p;
   if(isdigit((unsigned char)*p)){char *q;long v=strtol(p,&q,10);end=q;if(v>=0&&v<=10)value=(int)v;}
   else for(int i=0;i<12;++i)if(!strncmp(p,digits[i],strlen(digits[i]))){value=i==11?2:i;end=p+strlen(digits[i]);break;}
   if(eq(end,"档")||eq(end,"级"))end+=strlen(end);
   if(value>=0&&!*end){result.kind=TI_BRIGHTNESS_SET;result.level=value;}
   else if(explicit_level||isdigit((unsigned char)*p)||*p=='-'||end!=p)result.kind=TI_BRIGHTNESS_INVALID;
  }
 }
 return result;
}
