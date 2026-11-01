from pathlib import Path
import json,time,urllib.request,urllib.error
root=Path(__file__).resolve().parents[1]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
base='http://172.20.10.2'
result={}
for path in ['/api/control','/api/camera']:
 with opener.open(base+':81'+path,timeout=4) as r:result[path]=json.load(r)
for i in range(4):
 try:
  with opener.open(base+'/frame.jpg?q=55',timeout=4) as r:
   b=r.read();assert b[:2]==b'\xff\xd8' and b[-2:]==b'\xff\xd9'
   result['jpeg']={'bytes':len(b),'frame_id':r.headers.get('X-Frame-Id')}
   (root/'validation/pair_fix_preview.jpg').write_bytes(b);break
 except urllib.error.HTTPError as e:
  if e.code!=503:raise
  time.sleep(.3)
else:raise RuntimeError('no JPEG')
(root/'validation/pair_live_result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
