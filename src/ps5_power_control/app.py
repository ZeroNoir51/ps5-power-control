from collections import deque
from pathlib import Path
import subprocess
import os
import sys
import json
import asyncio
import socket
import xml.etree.ElementTree as ET
from rich.text import Text

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static, Select, Input

CPU = Path('/sys/devices/system/cpu/cpufreq/policy0')


def read_number(path, divisor=1):
    try:
        return float(Path(path).read_text().strip()) / divisor
    except (OSError, ValueError):
        return None


def temperature():
    for zone in sorted(Path('/sys/class/thermal').glob('thermal_zone*')):
        try:
            kind = (zone / 'type').read_text().strip().lower()
        except OSError:
            continue
        if any(word in kind for word in ('cpu', 'k10temp', 'tctl', 'tdie', 'x86_pkg')):
            value = read_number(zone / 'temp', 1000)
            if value is not None:
                return value, kind
    for hwmon in sorted(Path('/sys/class/hwmon').glob('hwmon*')):
        try:
            name = (hwmon / 'name').read_text().strip().lower()
        except OSError:
            continue
        if name in ('k10temp', 'zenpower', 'coretemp'):
            for sensor in sorted(hwmon.glob('temp*_input')):
                value = read_number(sensor, 1000)
                if value is not None:
                    return value, name
    return None, 'sensor not found'


def hardware_request(request):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(3)
        sock.connect('/run/ps5-power-control/control.sock')
        sock.sendall((json.dumps(request) + '\n').encode())
        data = b''
        while b'\n' not in data and len(data) < 65536:
            part = sock.recv(4096)
            if not part:
                break
            data += part
    response = json.loads(data.split(b'\n', 1)[0])
    if not response.get('success'):
        raise ValueError(response.get('error', 'Service error'))
    return response['data']


CPU_MAX = 3.5


class CpuUsage:
    def __init__(self):
        self.previous = None

    def sample(self, path=Path('/proc/stat')):
        try:
            fields = list(map(int, path.read_text().splitlines()[0].split()[1:9]))
            current = (sum(fields), fields[3] + (fields[4] if len(fields) > 4 else 0))
        except (OSError, ValueError, IndexError):
            self.previous = None
            return None
        previous, self.previous = self.previous, current
        if previous is None or current[0] <= previous[0]:
            return None
        total, idle = current[0] - previous[0], current[1] - previous[1]
        return max(0.0, min(100.0, 100 * (total - idle) / total))


def memory():
    try:
        fields = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
        total = int(fields['MemTotal'].split()[0]) / 1048576
        available = int(fields['MemAvailable'].split()[0]) / 1048576
        return total - available, total
    except (OSError, ValueError, KeyError):
        return None, None


def temperature_limit():
    override = os.environ.get('PS5_TEMP_MAX_C')
    if override:
        try:
            value = float(override)
            if 0 < value < 200:
                return value
        except ValueError:
            pass
    for hw in sorted(Path('/sys/class/hwmon').glob('hwmon*')):
        try:
            if (hw / 'name').read_text().strip() not in ('k10temp', 'zenpower', 'coretemp'):
                continue
        except OSError:
            continue
        for f in sorted(hw.glob('temp*_crit')):
            value = read_number(f, 1000)
            if value is not None and 0 < value < 200:
                return value
    return 100.0


def level(value, reference):
    ratio = value / reference
    return 'red' if ratio > .9 else '#ffaf00' if ratio >= .9 else 'green'


def meter(label, value, reference, unit, width=34):
    scale = reference if unit == '%' else reference * 1.05
    result = Text(f'{label:<12}', style='cyan')
    result.append('[' , style='cyan')
    if value is None:
        result.append(' ' * width + ']  —')
        return result
    filled = round(min(max(value / scale, 0), 1) * width)
    result.append('|' * filled, style=level(value, reference))
    result.append(' ' * (width - filled))
    result.append(f'] {value:.1f}%' if unit == '%' else f'] {value:.2f}/{scale:.2f} {unit}', style='cyan')
    return result


class PowerApp(App):
    TITLE = 'PS5 Power Control 0.2'
    CSS = """
    Screen { background: #101820; color: #e7f1f5; overflow-y: auto; }
    Header { background: #202e39; }
    Select { width: 30; margin: 0 1; }
    .meter { height: 1; margin: 0 1; }
    #governor, #legend, #help, #status { height: auto; padding: 1; }
    #controls { height: auto; }
    Button { min-width: 12; margin: 0 1; }
    Input { width: 16; margin: 0 1; }
    #hwstatus, #sensors, #hardware-title, #gpu-title, #fan-title { height: auto; padding: 0 1; }
    .row { height: auto; }
    .row Select { width: 16; }
    """
    BINDINGS = [('1', 'profile("powersave")', ''),
                ('2', 'profile("normal")', ''),
                ('3', 'profile("performance")', ''),
                ('q', 'quit', '')]

    def __init__(self):
        super().__init__()
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        self.languages = {}
        for path in (root / 'languages').glob('*.xml'):
            tree = ET.parse(path).getroot()
            self.languages[tree.attrib['code']] = {e.attrib['id']: e.text or '' for e in tree}
        self.config_path = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'ps5-power-control/settings.json'
        try:
            self.lang = json.loads(self.config_path.read_text()).get('language', 'en')
        except (OSError, ValueError):
            self.lang = 'en'
        if self.lang not in self.languages:
            self.lang = 'en'
        self.cpu_usage = CpuUsage()
        self.cpu_usage.sample()
        self.temp_max = temperature_limit()
        self.busy = False
        self.status_key = 'ready'
        self.hardware = None
        self.hw_busy = False

    def tr(self, key):
        return self.languages[self.lang].get(key, key)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Select([('English', 'en'), ('Español', 'es')], value=self.lang, allow_blank=False, id='language')
        for name in ('usage', 'memory', 'temp', 'freq'):
            yield Static(id=name, classes='meter')
        yield Static(id='governor', markup=False)
        yield Static(id='legend')
        with Horizontal(id='controls'):
            for name in ('powersave', 'normal', 'performance'):
                yield Button(id=name)
        yield Static(id='hardware-title')
        yield Static(id='gpu-title')
        yield Static(id='hwstatus', markup=False)
        with Horizontal(classes='row'):
            yield Select([('Ondemand', 'simple_ondemand'), ('Performance', 'performance'), ('Powersave', 'powersave'), ('Userspace', 'userspace')], id='gpu-governor')
            yield Button(id='apply-gpu')
        yield Static(id='fan-title')
        yield Static(id='sensors', markup=False)
        with Horizontal(classes='row'):
            yield Select([(self.tr('quiet') + ' 85°C', 85), (self.tr('default') + ' 80°C', 80), (self.tr('balanced') + ' 72°C', 72), (self.tr('cool') + ' 65°C', 65), (self.tr('maxcool') + ' 50°C', 50)], id='fan-preset')
            yield Button(id='apply-preset')
            yield Input(placeholder='40–90 °C', id='fan-target')
            yield Button(id='apply-target')
        with Horizontal(classes='row'):
            yield Select([(self.tr('on'), 'on'), (self.tr('off'), 'off')], id='alarm')
            yield Button(id='save-alarm')
            yield Input(placeholder='80–100 °C', id='threshold')
            yield Button(id='save-threshold')
        yield Static(id='status', markup=False)
        yield Static(id='help')

    def on_mount(self):
        self.translate()
        self.set_interval(1, self.refresh_metrics)
        self.set_interval(2, self.poll_hardware)
        self.poll_hardware()

    def translate(self):
        for i, name in enumerate(('powersave', 'normal', 'performance'), 1):
            self.query_one('#' + name, Button).label = f'{i} · {self.tr(name)}'
        for name in ('hardware-title', 'gpu-title', 'fan-title'):
            self.query_one('#' + name, Static).update(self.tr(name))
        for name in ('apply-gpu', 'apply-preset', 'apply-target', 'save-alarm', 'save-threshold'):
            self.query_one('#' + name, Button).label = self.tr(name)
        for name in ('alarm',):
            widget = self.query_one('#' + name, Select)
            old = widget.value
            widget.set_options([(self.tr('on'), 'on'), (self.tr('off'), 'off')])
            if old in ('on', 'off'):
                widget.value = old
        widget = self.query_one('#fan-preset', Select)
        old = widget.value
        widget.set_options([(self.tr('quiet') + ' 85°C', 85), (self.tr('default') + ' 80°C', 80), (self.tr('balanced') + ' 72°C', 72), (self.tr('cool') + ' 65°C', 65), (self.tr('maxcool') + ' 50°C', 50)])
        if old in (85, 80, 72, 65, 50):
            widget.value = old
        self.query_one('#legend', Static).update(self.tr('legend'))
        self.query_one('#help', Static).update(self.tr('help'))
        self.query_one('#status', Static).update(self.tr(self.status_key))
        self.refresh_metrics()

    def on_select_changed(self, event: Select.Changed):
        if event.value in self.languages:
            self.lang = event.value
            self.translate()
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                self.config_path.write_text(json.dumps({'language': self.lang}))
            except OSError:
                self.query_one('#status', Static).update(self.tr('save_error'))

    def refresh_metrics(self):
        temp, source = temperature()
        freq = read_number(CPU / 'scaling_cur_freq', 1_000_000)
        used, total = memory()
        width = max(5, self.size.width - 40)
        for name, value, reference, unit in [('usage', self.cpu_usage.sample(), 100, '%'), ('temp', temp, self.temp_max, '°C'), ('freq', freq, CPU_MAX, 'GHz'), ('memory', used, total or 1, 'GiB')]:
            self.query_one('#' + name, Static).update(meter(self.tr(name), value, reference, unit, width))
        try:
            governor = (CPU / 'scaling_governor').read_text().strip()
        except OSError:
            governor = self.tr('unavailable')
        self.query_one('#governor', Static).update(f"{self.tr('governor')}: {governor}")

    def on_resize(self):
        if self.is_mounted:
            self.refresh_metrics()

    def on_button_pressed(self, event: Button.Pressed):
        name = event.button.id
        if name in ('powersave', 'normal', 'performance'):
            self.action_profile(name)
        else:
            self.run_worker(self.hardware_action(name))

    def poll_hardware(self):
        if not self.hw_busy:
            self.run_worker(self.get_hardware())

    async def get_hardware(self):
        self.hw_busy = True
        try:
            data = await asyncio.to_thread(hardware_request, {'action': 'status'})
            self.hardware = data
            g = data['gpu']
            text = self.tr('gpu-status').format(gov=g['governor'] or '—', current=g['current'], target=g['target'], minimum=g['min'], maximum=g['max'], available=', '.join(map(str, g['frequencies'])) or '—')
            state = data['state']
            text += '\n' + self.tr('state-status').format(fan=data['fan'] or '—', alarm=state['alarm'], threshold=state['threshold'])
            if data['error']:
                text += '\n' + data['error']
            self.query_one('#hwstatus', Static).update(text)
            display = Text()
            for sensor in data['sensors']:
                value = sensor['temp']
                color = 'red' if value >= state['threshold'] else '#ffaf00' if value >= state['threshold'] * .9 else 'green'
                display.append(f"{sensor['chip']} {sensor['label']}: {value:.1f} °C  ", style=color)
            if not data['sensors']:
                display.append(self.tr('no-sensors'))
            self.query_one('#sensors', Static).update(display)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            self.query_one('#hwstatus', Static).update(self.tr('service-error') + ': ' + str(e))
        finally:
            self.hw_busy = False

    async def hardware_action(self, name):
        try:
            if name == 'apply-gpu':
                req = {'action': 'gpu_governor', 'value': self.query_one('#gpu-governor', Select).value}
            elif name == 'apply-preset':
                req = {'action': 'fan', 'value': self.query_one('#fan-preset', Select).value}
            elif name == 'apply-target':
                req = {'action': 'fan', 'value': int(self.query_one('#fan-target', Input).value)}
            elif name == 'save-threshold':
                req = {'action': 'settings', 'key': 'threshold', 'value': int(self.query_one('#threshold', Input).value)}
            else:
                lookup = {'save-alarm': ('alarm', 'alarm')}
                control, key = lookup[name]
                value = self.query_one('#' + control, Select).value
                if value not in ('on', 'off'):
                    raise ValueError(self.tr('choose-value'))
                req = {'action': 'settings', 'key': key, 'value': value == 'on'}
            if not isinstance(req.get('value'), (str, int, type(None))):
                raise ValueError(self.tr('choose-value'))
            await asyncio.to_thread(hardware_request, req)
            self.query_one('#status', Static).update(self.tr('success'))
            self.poll_hardware()
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
            self.query_one('#status', Static).update(self.tr('error') + ' ' + str(e))

    def action_profile(self, name):
        if name in ('powersave', 'normal', 'performance') and not self.busy:
            self.run_worker(self.switch_profile(name))

    async def switch_profile(self, name):
        self.busy = True
        self.status_key = 'switching'
        self.query_one('#status', Static).update(self.tr(self.status_key))
        governor = {'powersave': 'powersave', 'normal': 'schedutil', 'performance': 'performance'}[name]
        try:
            result = await asyncio.to_thread(subprocess.run, ['sudo', '-n', '/usr/local/bin/ps5-power', governor], capture_output=True, text=True, timeout=12)
            self.status_key = 'success' if result.returncode == 0 else 'error'
        except (OSError, subprocess.TimeoutExpired):
            self.status_key = 'error'
        finally:
            self.busy = False
        self.query_one('#status', Static).update(self.tr(self.status_key))
        self.refresh_metrics()


def main():
    PowerApp().run()


if __name__ == '__main__':
    main()
