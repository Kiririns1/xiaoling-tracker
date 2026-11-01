"""Package the built image and a credential-redacted complete source snapshot."""
from pathlib import Path
import json,hashlib,zipfile,re,shutil,subprocess
root=Path(__file__).resolve().parents[1]
build=root/'apps/build'
log=root.parent/'tmp/build_control_202.log'
assert 'Project build complete.' in log.read_text(encoding='utf-8'), 'Build has not completed successfully'
out=root/'release';out.mkdir(exist_ok=True)
config=json.loads((build/'flasher_args.json').read_text(encoding='utf-8'))
source_manifest=json.loads((root/'REFERENCE_MANIFEST.json').read_text(encoding='utf-8'))
reference=Path(source_manifest['reference'])
assert all(hashlib.sha256((reference/name).read_bytes()).hexdigest()==digest for name,digest in source_manifest['files'].items()),'Reference was changed'
official='C:/Users/kiririns/Desktop/hack/ljyd_xjwb03_agent_public_developer'
status=subprocess.check_output(['git','-c','safe.directory='+official,'-C',official,'status','--short'],text=True)
assert not status.strip(),'Original official repository has changed'
firmware={}
for offset,name in config['flash_files'].items():
 p=build/name
 target='xiaoling_11885_dual_servo.bin' if name.endswith('xiaoling_11885.bin') else p.name
 shutil.copy2(p,out/target)
 firmware[offset]={'file':target,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
args=' '.join(config['write_flash_args'])+'\n'+'\n'.join(address+' '+info['file'] for address,info in firmware.items())+'\n'
(out/'flash_args').write_text(args,encoding='ascii')
(out/'app_flash_args').write_text('--flash_mode dio --flash_freq 80m --flash_size detect\n0x20000 xiaoling_11885_dual_servo.bin\n',encoding='ascii')
shutil.copy2(root/'README_DUAL_SERVO.md',out/'README_DUAL_SERVO.md')
shutil.copy2(log,out/'build.log')
shutil.copy2(build/'xiaoling_11885.elf',out/'xiaoling_11885_dual_servo.elf')
shutil.copy2(root/'validation/host_tests.log',out/'host_tests.log')
shutil.copy2(root/'validation/deepseek_smoke.json',out/'deepseek_smoke.json')
manifest={'project':'xiaoling_lingji_dual_servo','version':'2.0.1-ble','pid':11885,'idf':'5.4.1','official_commit':'bebdc8020','yaw_gpio':5,'pitch_gpio':6,'chip':'esp32s3','flash':'16MB','psram':'8MB OPI','flashed':False,'serial_port_accessed':False,'reference_sources_unchanged':True,'original_official_repository_clean':True,'validation':{'build':'passed','host_state_machine':'passed','deepseek_synthetic_requests':3,'hardware':'not tested; board removed by user'},'images':firmware}
manifest.update(version='2.0.2-control', flashed=True, serial_port_accessed=True, pairing='saved Wi-Fi reconnect; BLE for initial/manual provisioning')
manifest['validation']['hardware']='COM3 flash verified; see validation/control202_result.json for camera and restart results'
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
secret_text=(root/'apps/main/peripheral/fresh_private.h').read_text(encoding='utf-8')
api_key=json.loads(re.search(r'#define FRESH_DEEPSEEK_API_KEY\s+(".*")',secret_text)[1])
cloud=(root/'apps/main/cloud/ljyd_cloud.h').read_text(encoding='utf-8')
product_secret=re.search(r'#define\s+CONFIG_XJIANG_CLOUD_SECERT\s+"([^"]+)"',cloud)[1]
files=0
with zipfile.ZipFile(out/'xiaoling_dual_servo_source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
 for p in root.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(root)
  if rel.parts[0]=='release' or rel.parts[:2]==('apps','build') or any(x in rel.parts for x in ['.git','__pycache__']):continue
  data=p.read_bytes()
  if rel.as_posix()=='apps/main/peripheral/fresh_private.h':data=b'#pragma once\n#define FRESH_DEEPSEEK_MODEL "deepseek-flash"\n#define FRESH_DEEPSEEK_API_KEY "PASTE_YOUR_DEEPSEEK_API_KEY"\n'
  if rel.as_posix()=='apps/main/cloud/ljyd_cloud.h':data=data.replace(product_secret.encode(),b'PASTE_YOUR_PRODUCT_11885_SECRET')
  assert api_key.encode() not in data and product_secret.encode() not in data, 'Unredacted secret in '+str(rel)
  archive.writestr('xiaoling_lingji_dual_servo/'+rel.as_posix(),data);files+=1
with zipfile.ZipFile(out/'xiaoling_dual_servo_source.zip') as archive:assert archive.testzip() is None
with zipfile.ZipFile(out/'xiaoling_11885_dual_servo_firmware.zip','w',zipfile.ZIP_DEFLATED) as archive:
 for p in out.iterdir():
  if p.suffix in ['.zip','.elf']:continue
  if p.is_file():archive.write(p,p.name)
print(json.dumps({'release':str(out),'source_files':files,'app_bytes':firmware['0x20000']['bytes'],'flash_performed':False},ensure_ascii=True))
