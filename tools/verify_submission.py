"""Check the distributed files without importing GUI packages or touching hardware."""
from pathlib import Path
import hashlib
import json
import re
import sys

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root/'RELEASE_MANIFEST.json').read_text(encoding='utf-8'))
errors = []
count = 0
for section, subdir in [('source_files','source'),
                        ('runtime_files','runtime/Xiaoling_Tracker_LJYD'),
                        ('firmware_files','firmware')]:
    entries = manifest.get(section)
    if not entries:
        errors.append(f'Missing manifest section: {section}')
        continue
    for name, expected in entries.items():
        target = root/subdir/name
        if not target.is_file():
            errors.append(f'Missing file: {subdir}/{name}')
            continue
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != expected['sha256']:
            errors.append(f'Changed file: {subdir}/{name}')
        count += 1

for entry in manifest['credential_redactions']:
    text = (root/entry['file']).read_text(encoding='utf-8')
    for field in entry['fields']:
        if field.startswith('demo_AP_'):
            continue
        match = re.search(r'^\s*#\s*define\s+'+re.escape(field)+r'\s+"([^"\r\n]*)"', text, re.M)
        if match is None or match[1]:
            errors.append(f'Credential must be blank before upload: {entry["file"]}: {field}')
ap = (root/'source/apps/main/peripheral/fresh_http.c').read_text(encoding='utf-8')
if '.ssid="",.password="",.ssid_len=0' not in ap:
    errors.append('Release camera AP configuration must remain blank before upload')
for folder in [root/'source', root/'runtime']:
    for name in ['backups', '.venv', 'build']:
        # These local generated folders must not be copied into a published ZIP.
        if folder.name == 'source' and name == 'build' and (folder/'apps/build').exists():
            print('NOTE: a local source/apps/build directory exists; do not add it to Git.')

if errors:
    print('FAIL: submission differs from the checked blank-credential release:')
    for error in errors[:30]:
        print(' - '+error)
    sys.exit(1)
print(f'PASS: {count} source/runtime/firmware files match the release manifest.')
print('PASS: publishable configuration fields are blank.')
print('Configure your own product credentials, Wi-Fi and platform API settings before deployment.')
