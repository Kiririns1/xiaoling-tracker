"""Reset COM3 and collect redacted startup/health evidence; no motion commands."""
from pathlib import Path
import json
import re
import time
import serial
import argparse

r = Path(__file__).resolve().parents[1]
args = argparse.ArgumentParser()
args.add_argument('--seconds', type=int, default=60)
args.add_argument('--tag', default='final')
args.add_argument('--no-reset', action='store_true')
opt = args.parse_args()
assert re.fullmatch(r'[a-zA-Z0-9_-]+', opt.tag)
version = re.search(r'set\(PROJECT_VER "([^"]+)"\)', (r/'apps/CMakeLists.txt').read_text())[1]
lines = []
port = serial.Serial()
port.port, port.baudrate, port.timeout = 'COM3', 115200, .2
port.dtr = port.rts = False
monitor_error = None
started_at = time.monotonic()
deny = re.compile(r'secret|secert|password|credential|token|auth|payload|topic|signature|device.?key|product.?key|cert|-----BEGIN', re.I)
allow = re.compile(r'boot:|app_init:|main_task:|camera|spi_cam|spi_video|bf3901|servo|qm_audio|tracker|route=|asr final|tts final|dialog=|playback|local reply|console|app_alarm|time_sync|provision|wifi|Wi-Fi|cloud.*connect|agora.*connect|iot start|dynreg.*(fail|success|ret)|panic|abort\(|error|fail|reset|ready|CORRUPT|NVS|Backtrace|EXCVADDR|EXCCAUSE|IP_EVENT|got ip', re.I)
try:
    port.open()
    if not opt.no_reset:
        port.rts = True
        time.sleep(.12)
        port.rts = False
    deadline = time.monotonic() + opt.seconds
    queried = False
    while time.monotonic() < deadline:
        if not queried and time.monotonic() > deadline - 30:
            port.write(b'/control\r\n/camera\r\n')
            queried = True
        line = port.readline().decode('utf-8', 'replace').strip()
        line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        if not line or deny.search(line) or not allow.search(line):
            continue
        line = re.sub(r'(ssid=)[^\s,]+', r'\1[redacted]', line, flags=re.I)
        line = re.sub(r'text=.*', 'text=[redacted]', line)
        line = re.sub(r'(wifi:connected with )[^,]+', r'\1[redacted]', line)
        line = re.sub(r'bssid = [0-9a-f:]+', 'bssid = [redacted]', line, flags=re.I)
        lines.append(line)
except (serial.SerialException, OSError) as error:
    monitor_error = str(error)
finally:
    port.close()
    (r/f'validation/boot_COM3_{opt.tag}.log').write_text('\n'.join(lines), encoding='utf-8')

text = '\n'.join(lines)
muted = False
muted_controls = []
muted_playback_starts = 0
mute_seen = wake_after_mute = False
for line in lines:
    if 'chat muted; controls remain enabled' in line:
        muted = mute_seen = True
    if 'chat voice enabled' in line:
        if mute_seen:
            wake_after_mute = True
        muted = False
    match = re.search(r'control=(\S+) accepted=1 muted=1', line)
    if match:
        muted_controls.append(match[1])
    if muted and 'tts playback started' in line:
        muted_playback_starts += 1
summary = {
    'version': version in text,
    'version_name': version,
    'audio_ready': bool(re.search(r'qm_audio.*ready', text, re.I)),
    'cloud_connected': bool(re.search(r'cloud connected', text, re.I)),
    'agora_connected': bool(re.search(r'agora.*(?:connected|connection.*success)', text, re.I)),
    'http_ready': 'preview :80, control :81 ready' in text,
    'camera_frames': bool(re.search(r'camera.*(?:decoded|frames=[1-9]|frame=[1-9])', text, re.I)),
    'crash': bool(re.search(r'Guru Meditation|panic|abort\(|CORRUPT|assert failed|Backtrace:', text, re.I)),
    'provisioning': 'no saved Wi-Fi' in text,
    'saved_wifi': 'saved Wi-Fi: reconnect automatically' in text,
    'ip_addresses': sorted(set(re.findall(r'(?:ip:|ip=|IP:|IP=)\s*(\d+\.\d+\.\d+\.\d+)', text))),
    'observed_seconds': round(time.monotonic() - started_at, 1),
    'monitor_error': monitor_error,
    'ordinary_chat_routes': len(re.findall(r'route=cloud_chat', text)),
    'playback_started': len(re.findall(r'tts playback started', text)),
    'playback_failed': len(re.findall(r'tts playback failed generation', text)),
    'serial_closed': True,
    'mute_seen': mute_seen,
    'muted_controls_accepted': muted_controls,
    'playback_starts_while_muted': muted_playback_starts,
    'wake_after_mute': wake_after_mute,
}
(r/f'validation/boot_COM3_{opt.tag}_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(summary, indent=2))
for line in lines:
    if re.search(r'Project|version|ready|connect|no saved|saved Wi-Fi|provision start|panic|abort|CORRUPT|route=|control=|chat muted|chat voice|dialog=|playback|console|camera.*(?:decoded|frames=|frame=)', line, re.I):
        print(line)
