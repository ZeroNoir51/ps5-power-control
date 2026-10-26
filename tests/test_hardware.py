import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('service', Path(__file__).parents[1] / 'hardware/ps5_control_service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)

class HardwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        service.FAN = root / 'fan'; service.FAN.write_text('80')
        service.GPU = root / 'gpu'; service.GPU.mkdir()
        service.HWMON = root / 'hwmon'; service.HWMON.mkdir()
        service.BEEP = root / 'beep'; service.BEEP.write_text('0')
        service.STATE = root / 'state/settings.json'
        hw = service.HWMON / 'hwmon0'; hw.mkdir(); (hw/'name').write_text('k10temp'); (hw/'temp1_input').write_text('50000')
        for name, value in {'available_governors':'simple_ondemand performance powersave userspace', 'available_frequencies':'500000000 1000000000', 'governor':'simple_ondemand','min_freq':'0','max_freq':'0','cur_freq':'500000000','target_freq':'1000000000'}.items():
            (service.GPU / name).write_text(value)
        self.temp = hw / 'temp1_input'
        self.c = service.Controller()

    def tearDown(self): self.tmp.cleanup()

    def test_old_restore_and_guard_settings_are_ignored(self):
        service.STATE.parent.mkdir(parents=True)
        service.STATE.write_text('{"gpu_restore":true,"gpu_governor":"performance","gpu_clock_set":true,"gpu_clock":1000,"fan_restore":true,"fan_target":65,"guard":true,"alarm":true,"threshold":95}')
        self.temp.write_text('97000')
        other = service.Controller()
        other.tick()
        self.assertEqual(service.read(service.FAN), '80')
        self.assertEqual(service.read(service.GPU / 'governor'), 'simple_ondemand')
        self.assertEqual(service.read(service.GPU / 'max_freq'), '0')
        self.assertEqual(service.read(service.BEEP), '2')
        self.assertEqual(other.state, {'alarm':True,'threshold':95})

    def test_alarm_rearm_and_missing_sensor(self):
        self.c.action({'action':'settings','key':'alarm','value':True})
        self.temp.write_text('95000'); self.c.tick(); self.assertEqual(service.read(service.BEEP), '2')
        service.BEEP.write_text('0'); self.c.tick(); self.assertEqual(service.read(service.BEEP), '0')
        self.temp.write_text('85000'); self.c.tick(); self.temp.write_text('95000'); self.c.tick()
        self.assertEqual(service.read(service.BEEP), '2')
        self.temp.unlink(); self.c.tick(); self.assertIn('unavailable', self.c.error)

    def test_gpu_governor_and_removed_commands(self):
        self.c.action({'action':'gpu_governor','value':'performance'})
        self.assertEqual(service.read(service.GPU/'governor'), 'performance')
        with self.assertRaises(ValueError): self.c.action({'action':'gpu_governor','value':'evil'})
        for req in [{'action':'gpu_clock','value':1000}, {'action':'settings','key':'gpu_restore','value':True}, {'action':'settings','key':'fan_restore','value':True}, {'action':'settings','key':'guard','value':True}]:
            with self.assertRaises(ValueError): self.c.action(req)
        self.assertEqual(service.read(service.GPU/'min_freq'), '0')
        self.assertEqual(service.read(service.GPU/'max_freq'), '0')

    def test_invalid_settings(self):
        for req in [{'action':'fan','value':39}, {'action':'settings','key':'threshold','value':101}, {'action':'settings','key':'guard','value':1}]:
            with self.assertRaises(ValueError): self.c.action(req)

if __name__ == '__main__': unittest.main()
