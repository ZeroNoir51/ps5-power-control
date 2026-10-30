import asyncio
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).parents[1] / 'src'))
try:
    from ps5_power_control import app
except ImportError:  # Textual is not installed; the UI tests are skipped.
    app = None

STATUS = {
    'state': {'alarm': False, 'threshold': 95}, 'fan': '80', 'error': None, 'alarm_active': False,
    'gpu': {'available': True, 'governors': ['simple_ondemand', 'performance'], 'governor': 'simple_ondemand',
            'current': 1600.0, 'target': 1600.0, 'min': 500.0, 'max': 2230.0, 'frequencies': [500, 2230]},
    'sensors': [{'chip': 'k10temp', 'label': 'Tctl', 'temp': 60.0}, {'chip': 'amdgpu', 'label': 'edge', 'temp': 55.0},
                {'chip': 'nvme', 'label': 'Composite', 'temp': 40.0}],
}


@unittest.skipIf(app is None, 'textual is not installed')
class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.requests = []
        def fake(request):
            self.requests.append(request)
            return STATUS if request['action'] == 'status' else {'ok': True}
        patches = [mock.patch.dict('os.environ', {'XDG_CONFIG_HOME': self.tmp.name}),
                   mock.patch.object(app, 'hardware_request', fake)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def run_app(self, scenario, size=(110, 50)):
        async def main():
            power = app.PowerApp()
            async with power.run_test(size=size) as pilot:
                await pilot.pause(0.5)
                await scenario(power, pilot)
        asyncio.run(main())

    def assert_meters_fit(self, power):
        for name in app.METERS:
            widget = power.query_one('#' + name, app.Meter)
            line = widget.render().plain
            self.assertIn(']', line, name)
            self.assertLessEqual(len(line), widget.content_size.width, name)

    def test_meters_fit_after_resize_and_language_change(self):
        async def scenario(power, pilot):
            self.assert_meters_fit(power)
            power.query_one('#language').value = 'es'
            await pilot.pause(0.2)
            await pilot.resize_terminal(60, 50)
            await pilot.pause(0.2)
            self.assertIn('Frecuencia GPU', power.query_one('#gpu-frequency', app.Meter).render().plain)
            self.assert_meters_fit(power)
        self.run_app(scenario)
        self.assertIn('"es"', (Path(self.tmp.name) / 'ps5-power-control/settings.json').read_text())

    def test_buttons_follow_available_hardware(self):
        async def scenario(power, pilot):
            self.assertFalse(power.query_one('#gpu-performance').disabled)
            self.assertTrue(power.query_one('#gpu-powersave').disabled)
            self.assertFalse(power.query_one('#fan-cool').disabled)
            await pilot.click('#fan-cool')
            await pilot.pause(0.2)
        self.run_app(scenario)
        self.assertIn({'action': 'fan', 'value': 65}, self.requests)

    def test_invalid_number_is_reported(self):
        async def scenario(power, pilot):
            power.query_one('#fan-target').value = 'abc'
            await pilot.click('#apply-target')
            await pilot.pause(0.2)
            self.assertIn(power.tr('enter-number'), str(power.query_one('#status').render()))
        self.run_app(scenario)
        self.assertFalse([r for r in self.requests if r['action'] == 'fan'])

    def test_service_unavailable_disables_hardware_buttons(self):
        def broken(request):
            raise OSError('No such file or directory')
        with mock.patch.object(app, 'hardware_request', broken):
            async def scenario(power, pilot):
                for name in app.HW_BUTTONS:
                    self.assertTrue(power.query_one('#' + name).disabled, name)
                self.assert_meters_fit(power)
            self.run_app(scenario)


if __name__ == '__main__': unittest.main()
