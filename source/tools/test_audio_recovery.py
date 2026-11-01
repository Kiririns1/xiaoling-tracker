"""Run the real SDK audio bridge tests on Windows with a single-thread mutex stub."""
from pathlib import Path
import subprocess
import tempfile

r = Path(__file__).resolve().parents[1]
q = r / 'qumios-dev'
t = q / 'components/qm_agent/tests'
includes = [t, t/'../include', t/'../priv_include', q/'components/qm_audio/include',
            q/'components/qm_event/include', q/'components/backoff/include',
            q/'include', q/'include/qmos', q/'include/common', q/'include/hal',
            q/'utility/string', q/'utility/timer']
stub = '''
#include "qm.h"
int qm_mutex_new(qm_mutex_t *m){m->hdl=(void*)1;return 0;}
int qm_mutex_free(qm_mutex_t *m){m->hdl=0;return 0;}
int qm_mutex_lock(qm_mutex_t *m,unsigned int timeout){(void)m;(void)timeout;return 0;}
int qm_mutex_unlock(qm_mutex_t *m){(void)m;return 0;}
uint32_t qm_now_ms(void){return 1000;}
void qm_srandom(uint32_t seed){(void)seed;}
uint32_t qm_random_get(uint32_t region){(void)region;return 0;}
'''
with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    support = temp/'host.c'
    support.write_text(stub, encoding='utf-8')
    for decoder in [0, 1]:
        exe = temp/f'audio_{decoder}.exe'
        cmd = ['gcc', '-std=c99', '-ffunction-sections', '-fdata-sections',
               '-Wl,--gc-sections', f'-DCONFIG_QM_AUDIO_DECODER_SUPPORT={decoder}',
               *['-I'+str(p) for p in includes], str(t/'test_audio.c'),
               str(q/'components/backoff/src/backoff_algorithm.c'),
               str(q/'utility/timer/qm_utils_timer.c'), str(support), '-o', str(exe)]
        subprocess.run(cmd, check=True)
        subprocess.run([str(exe)], check=True)
        print(f'PASS decoder={decoder}: SDK audio suite including failed-local-reply -> two normal turns and cleanup race', flush=True)
