"""Synthetic tone-only API smoke test; never prints the private key."""
from pathlib import Path
import re,json,urllib.request,urllib.error,time
root=Path(__file__).resolve().parents[1]
source=(root/'apps/main/peripheral/fresh_tone.c').read_text(encoding='utf-8')
match=re.search(r'cJSON_AddStringToObject\(system,"content",("(?:[^"\\]|\\.)*")\)',source)
assert match
prompt=json.loads(match[1])
private=(root/'apps/main/peripheral/fresh_private.h').read_text(encoding='utf-8')
key=re.search(r'#define FRESH_DEEPSEEK_API_KEY\s+(".*")',private)
model=re.search(r'#define FRESH_DEEPSEEK_MODEL\s+(".*")',private)
assert key and model
results=[]
for text,expected in [('不是，我不是人类，我是一个语音助手。','negative'),('是的，你的理解完全正确。','affirmative'),('明天下午多云，气温二十六度。','neutral')]:
 payload={'model':json.loads(model[1]),'messages':[{'role':'system','content':prompt},{'role':'user','content':text}],'temperature':0,'max_tokens':96,'stream':False,'response_format':{'type':'json_object'}}
 request=urllib.request.Request('https://api.deepseek.com/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+json.loads(key[1])})
 start=time.monotonic()
 try:
  with urllib.request.urlopen(request,timeout=20) as response:body=json.load(response)
  choice=body['choices'][0];answer=json.loads(choice['message']['content'])
  result={'expected':expected,'result':answer,'elapsed_ms':round((time.monotonic()-start)*1000),'finish_reason':choice.get('finish_reason')}
  results.append(result);print(json.dumps(result,ensure_ascii=True),flush=True)
 except urllib.error.HTTPError as e:
  print('API test failed HTTP',e.code,flush=True);raise SystemExit(1)
 except Exception as e:
  print('API test failed',type(e).__name__,flush=True);raise SystemExit(1)
assert all(r['result'].get('tone')==r['expected'] and r['finish_reason']=='stop' for r in results),results
(root/'validation').mkdir(exist_ok=True)
(root/'validation/deepseek_smoke.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: three real DeepSeek synthetic tone requests; no device/audio interaction.')
