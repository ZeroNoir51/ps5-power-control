#!/usr/bin/python3
"""PS5 Power Control hardware service. Root-owned daemon with a fixed API."""
import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import signal
import socket
import struct
import threading
import time

ROOT = Path('/sys')
FAN = ROOT / 'bus/platform/devices/ps5-fan/target_temp'
GPU = ROOT / 'class/devfreq/ps5-gpufreq'
HWMON = ROOT / 'class/hwmon'
BEEP = ROOT / 'class/misc/ps5_buzzer/beep'
STATE = Path('/var/lib/ps5-power-control/settings.json')
SOCKET = Path('/run/ps5-power-control/control.sock')
DEFAULT = {'alarm': False, 'threshold': 95}

LOG = logging.getLogger('ps5-power-control')


def read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return None


def sensors():
    items = []
    for hw in sorted(HWMON.glob('hwmon*')):
        chip = read(hw / 'name')
        if not chip:
            continue
        for p in sorted(hw.glob('temp[0-9]*_input')):
            try:
                val = int(p.read_text().strip()) / 1000
                if -20 <= val <= 150:
                    label = read(hw / p.name.replace('_input', '_label')) or p.stem.replace('_input', '')
                    items.append({'chip': chip, 'label': label, 'temp': val})
            except (ValueError, OSError):
                continue
    return items


def cpu_temp(items):
    values = [x['temp'] for x in items if x['chip'] == 'k10temp']
    return max(values) if values else None


def read_state():
    try:
        data = json.loads(STATE.read_text())
    except (ValueError, OSError):
        data = {}
    state = dict(DEFAULT)
    if not isinstance(data, dict):
        return state
    if type(data.get('alarm')) is bool:
        state['alarm'] = data['alarm']
    threshold = data.get('threshold')
    if type(threshold) is int and 80 <= threshold <= 100:
        state['threshold'] = threshold
    return state


class Controller:
    def __init__(self):
        self.lock = threading.RLock()
        self.state = read_state()
        self.alarm_active = False
        self.error = None

    def save(self):
        STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = STATE.with_suffix('.tmp')
        with tmp.open('w') as f:
            json.dump(self.state, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE)

    def write_fan(self, value):
        if type(value) is not int or not 40 <= value <= 90:
            raise ValueError('Fan target must be a whole number from 40 to 90 °C')
        FAN.write_text(str(value))
        if read(FAN) != str(value):
            raise OSError('Fan target verification failed')

    def gpu_status(self):
        def hz(name):
            v = read(GPU / name)
            try: return int(v) / 1_000_000
            except (TypeError, ValueError): return None
        allowed = (read(GPU / 'available_governors') or '').split()
        clocks = (read(GPU / 'available_frequencies') or '').split()
        freqs = sorted({int(v) // 1_000_000 for v in clocks if v.isdigit() and int(v) > 0})
        return {'available': GPU.is_dir(), 'governors': [g for g in allowed if g in ('simple_ondemand', 'performance', 'powersave', 'userspace')],
                'governor': read(GPU / 'governor'), 'current': hz('cur_freq'), 'target': hz('target_freq'),
                'min': hz('min_freq'), 'max': hz('max_freq'), 'frequencies': freqs}

    def gpu_governor(self, governor):
        if governor not in self.gpu_status()['governors']:
            raise ValueError('GPU governor unavailable')
        (GPU / 'governor').write_text(governor)
        if read(GPU / 'governor') != governor:
            raise OSError('GPU governor verification failed')

    def tick(self):
        with self.lock:
            temp = cpu_temp(sensors())
            if temp is None:
                if self.state['alarm']:
                    self.error = 'CPU k10temp sensor unavailable'
                return
            self.error = None
            hot = temp >= self.state['threshold']
            cold = temp <= self.state['threshold'] - 10
            if self.state['alarm'] and hot and not self.alarm_active:
                try:
                    BEEP.write_text('2')
                    self.alarm_active = True
                except OSError as e:
                    self.error = f'Alarm failed: {e}'
            if cold or not self.state['alarm']:
                self.alarm_active = False

    def action(self, req):
        with self.lock:
            action = req.get('action')
            if action == 'status':
                return {'state': self.state.copy(), 'fan': read(FAN), 'gpu': self.gpu_status(),
                        'sensors': sensors(),
                        'alarm_active': self.alarm_active, 'error': self.error}
            if action == 'fan':
                self.write_fan(req.get('value'))
            elif action == 'gpu_governor':
                self.gpu_governor(req.get('value'))
            elif action == 'settings':
                key, value = req.get('key'), req.get('value')
                if key == 'alarm' and type(value) is bool:
                    self.state[key] = value
                elif key == 'threshold' and type(value) is int and 80 <= value <= 100:
                    self.state[key] = value
                else: raise ValueError('Invalid setting')
            else: raise ValueError('Unknown action')
            self.save()
            return {'ok': True}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--uid', type=int, required=True); args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    SOCKET.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    # Lock before unlinking: a second instance must not disturb the running service.
    lock = (SOCKET.parent / 'service.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    SOCKET.unlink(missing_ok=True)
    ctl = Controller()
    stop = threading.Event()
    def poll():
        while not stop.wait(2):
            try: ctl.tick()
            except Exception: LOG.exception('Thermal monitoring failure')
    thread = threading.Thread(target=poll, daemon=True); thread.start()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET)); os.chmod(SOCKET, 0o666); server.listen(4); server.settimeout(1)
    def shutdown(*_): stop.set()
    signal.signal(signal.SIGTERM, shutdown); signal.signal(signal.SIGINT, shutdown)
    try:
        while not stop.is_set():
            try: conn, _ = server.accept()
            except socket.timeout: continue
            with conn:
                conn.settimeout(3)
                try:
                    _, uid, _ = struct.unpack('3i', conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid not in (0, args.uid): raise PermissionError('Unauthorized user')
                    data = b''
                    while b'\n' not in data and len(data) <= 8192:
                        chunk = conn.recv(8192)
                        if not chunk: break
                        data += chunk
                    if len(data) > 8192: raise ValueError('Request too large')
                    request = json.loads(data.split(b'\n', 1)[0])
                    if not isinstance(request, dict): raise ValueError('Invalid request')
                    response = {'success': True, 'data': ctl.action(request)}
                except Exception as e:
                    response = {'success': False, 'error': str(e)}
                try: conn.sendall((json.dumps(response) + '\n').encode())
                except OSError: pass
    finally:
        stop.set(); thread.join(timeout=3); server.close(); SOCKET.unlink(missing_ok=True)

if __name__ == '__main__': main()
