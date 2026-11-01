"""Reset the flashed board and record bounded startup evidence (no motor commands)."""
from pathlib import Path
import serial,time,json,re
from esptool.reset import HardReset
r=Path(__file__).resolve().parents[1]
raw=bytearray()
with serial.Serial('COM3',115200,timeout=.25) as port:
    port.dtr=False
    HardReset(port)()
    end=time.monotonic()+35
    while time.monotonic()<end:
        raw.extend(port.read(max(1,port.in_waiting)))
text=raw.decode('utf-8','replace')
(r/'validation/boot_COM3.log').write_text(text,encoding='utf-8')
patterns={
 'version':r'3\.0\.0-tracker-ljyd',
 'audio_ready':r'qm_audio ready',
 'cloud_connected':r'cloud connected',
 'agora_connected':r'agora connected',
 'http_ready':r'preview :80, control :81 ready',
 'camera_frames':r'decoded=[1-9]\d*',
 'crash':r'Guru Meditation|panic\(|abort\(\)|assert failed|CORRUPT HEAP',
 'provisioning':r'ble provision start',
}
result={k:bool(re.search(v,text,re.I)) for k,v in patterns.items()}
result['ip_addresses']=list(dict.fromkeys(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b',text)))
(r/'validation/boot_COM3_summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
