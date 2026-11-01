"""Read image/state and exercise rejection/stop paths without moving motors."""
import json
from pathlib import Path
import urllib.request
import urllib.error

root = Path(__file__).resolve().parents[1]
client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
base = 'http://172.20.10.2'
def request(path, body=None):
    req = urllib.request.Request(base+path, data=None if body is None else json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with client.open(req, timeout=4) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
def post(path, body):
    code, data = request(':81'+path, body)
    return code, json.loads(data)
result = {}
try:
    assert post('/api/control', {'action':'stop'})[0] == 200
    assert post('/api/control', {'action':'track_on'})[0] == 200
    state = json.loads(request(':81/api/control')[1])
    rev = state['revision']
    code, data = post('/api/servo', {'speed':0, 'revision':rev+1})
    assert code == 409 and data['reason'] == 'stale_revision'
    result['stale_revision'] = data['reason']
    code, data = post('/api/servo', {'speed':0.1, 'revision':rev, 'frame_id':4294967295})
    assert code == 409 and data['reason'] == 'stale_frame'
    result['stale_frame'] = data['reason']
    assert post('/api/servo', {'speed':0, 'revision':rev})[0] == 200
    page = request('/')[1].decode()
    assert 'data-action="up"' in page and 'data-action="down"' in page
    result['web_up_down'] = True
    result['camera'] = json.loads(request(':81/api/camera')[1])
    assert result['camera']['have_image']
finally:
    result['stop'] = post('/api/control', {'action':'stop'})[0] == 200
(root/'validation/control202_result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
