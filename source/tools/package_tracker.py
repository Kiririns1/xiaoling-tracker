"""Package the current verified release, excluding all device Flash backups."""
from pathlib import Path
import hashlib,json,re,zipfile
r=Path(__file__).resolve().parents[1];out=r/'deliverables';out.mkdir(exist_ok=True)
build=r/'apps/build'
status=json.loads((r/'validation/STATUS.json').read_text(encoding='utf-8'))
assert status['version']==re.search(r'set\(PROJECT_VER "([^"]+)"\)',(r/'apps/CMakeLists.txt').read_text())[1]
assert status['validation']['esp_idf_build']=='passed'
secret=re.search(r'#define\s+CONFIG_XJIANG_CLOUD_SECERT\s+"([^"]+)"',(r/'apps/main/cloud/ljyd_cloud.h').read_text(encoding='utf-8'))[1].encode()
for item in status['images'].values():
 data=(build/item['file']).read_bytes()
 assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],item['file']
docs=['使用说明.md','坐姿语音整合说明.md']
roots={'apps','components','custom_components','idf_patches','qumios-dev','pc','tests','tools'}
top={'CMakeLists.txt','build.ps1','README.md','REFERENCE_LATEST.json','REFERENCE_FINAL.json','requirements.txt','run_pc.cmd','run_pc.ps1','setup_pc.ps1','setup_pc.cmd','LICENSE','.gitignore',*docs}
logs={'STATUS.json','build_final.log','pc_tests_final.log','firmware_host_final.log','dialog_light_host_final.log','boot_COM3_final.log','boot_COM3_final_summary.json','flash_COM3_final.log','FLASH_COM3_FINAL_RECORD.json','http_final.json','audio_before.log','audio_recovery_before.log','audio_recovery_after.log','build_chat_fix.log','dialog_light_chat_fix.log','flash_chat_fix.log','boot_COM3_chat_fix.log','boot_COM3_chat_fix_summary.json','FLASH_COM3_CHAT_FIX_RECORD.json','http_chat_fix.json','silent_controls_before.log','silent_controls_after.log','motion_silent_controls.log','audio_silent_controls.log','build_silent_controls.log','flash_silent_controls.log','boot_COM3_silent_controls.log','boot_COM3_silent_controls_summary.json','FLASH_COM3_SILENT_CONTROLS_RECORD.json','boot_COM3_silent_controls_followup.log','boot_COM3_silent_controls_followup_summary.json'}
excluded={'build','__pycache__','.git','.venv','.venv-xiaoling','.mpl-cache','backups','deliverables','release','checkpoints'}
with zipfile.ZipFile(out/'小灵_灵机一动_固件.zip','w',zipfile.ZIP_DEFLATED) as z:
 for item in status['images'].values():z.write(build/item['file'],item['file'])
 for name in ['flash_args','app-flash_args']:z.write(build/name,name)
 for name in docs:z.write(r/name,name)
 z.write(r/'validation/STATUS.json','STATUS.json')
with zipfile.ZipFile(out/'小灵_电脑追踪程序.zip','w',zipfile.ZIP_DEFLATED) as z:
 for sub in ['pc','tests']:
  for f in sorted((r/sub).rglob('*')):
   if f.is_file() and not excluded.intersection(f.relative_to(r).parts):z.write(f,'Xiaoling_Tracker_LJYD/'+f.relative_to(r).as_posix())
 for name in [*docs,'requirements.txt','run_pc.cmd','run_pc.ps1','setup_pc.ps1','setup_pc.cmd']:z.write(r/name,'Xiaoling_Tracker_LJYD/'+name)
with zipfile.ZipFile(out/'小灵_灵机一动_源码.zip','w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
 for f in sorted(r.rglob('*')):
  if not f.is_file():continue
  rel=f.relative_to(r)
  if excluded.intersection(rel.parts):continue
  if len(rel.parts)==1:
   if f.name not in top:continue
  elif rel.parts[0]=='validation':
   if f.name not in logs:continue
  elif rel.parts[0] not in roots:continue
  data=f.read_bytes().replace(secret,b'PASTE_YOUR_PRODUCT_11885_SECRET');assert secret not in data
  z.writestr('Xiaoling_Tracker_LJYD/'+rel.as_posix(),data)
for f in out.glob('*.zip'):
 with zipfile.ZipFile(f) as z:
  assert z.testzip() is None
  assert not any('backups' in Path(n).parts for n in z.namelist())
  if '源码' in f.name or '电脑' in f.name:assert all(secret not in z.read(n) for n in z.namelist())
(out/'STATUS.json').write_bytes((r/'validation/STATUS.json').read_bytes())
for name in docs:(out/name).write_bytes((r/name).read_bytes())
print(json.dumps({'version':status['version'],'archives':{f.name:{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in out.glob('*.zip')}},ensure_ascii=False,indent=2))
