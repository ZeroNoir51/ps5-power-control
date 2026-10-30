# PS5 Power Control

**Version 0.2** · Terminal dashboard for **PS5 Linux** on **Ubuntu** and **Bazzite**

Tested on PS5 hardware running Ubuntu and Bazzite.

PS5 Power Control is a terminal app that works locally or over SSH. It shows compact htop-style meters and lets you change CPU and GPU governors and the fan target temperature from the keyboard or mouse.

> **This project is intended for research purposes only.** Read the [disclaimer](#disclaimer) before installing.

Spanish installation guide: [docs/INSTALL.es.md](docs/INSTALL.es.md).

## Features

- **CPU:** overall usage, memory used, temperature and frequency meters, plus three governor buttons: Power save (`powersave`), Normal (`schedutil`) and Performance (`performance`).
- **GPU:** frequency meter, current governor, target frequency and allowed range, and buttons for the governors the driver offers.
- **Fan:** target temperature presets (85/80/72/65/50 °C), a manual target from 40 to 90 °C, and an optional alarm that beeps once when the CPU reaches a threshold from 80 to 100 °C.
- **Sensors:** GPU sensors appear in the GPU section, and other sensors (for example an NVMe SSD) appear under *Other sensors*.
- English and Spanish interface, chosen from a drop-down and remembered between sessions.

The meters show temperature, frequency and memory. They do not measure power in watts, and the fan target is a temperature, not RPM or a PWM percentage. The 5% margin on the meter scales only affects the display and never raises a hardware clock.

## Requirements

| | |
| --- | --- |
| Distribution | Ubuntu 24.04 or newer (other Debian-based systems should work), or Bazzite (other Fedora-based systems should work) |
| Kernel | A PS5 Linux kernel. GPU and fan controls need `ps5-gpufreq`, `ps5-fan`, `k10temp` and `ps5_buzzer` |
| Software | `/usr/bin/python3` 3.10 or newer, `sudo` and systemd |
| Network | Internet access to PyPI during installation, to download [Textual](https://textual.textualize.io/) |

If an interface is missing, the installer reports it and the app disables the matching controls.

## Installation

Run the installer **as your normal user, without `sudo`**. It asks for your password when it needs it. The same commands work on Ubuntu and Bazzite.

```bash
git clone https://github.com/ZeroNoir51/ps5-power-control.git ~/ps5-power-control
```

```bash
cd ~/ps5-power-control && ./install.sh
```

The installer does the following:

1. Detects the distribution and checks that Python can create virtual environments. On Ubuntu it installs `pythonX.Y-venv` and `python3-pip` with apt if needed.
2. Installs the app and its Python dependencies into a private virtual environment under `/usr/local/lib/ps5-power-control/`, and links `ps5-power-control` into `/usr/local/bin`. It never touches the system Python.
3. Installs the CPU profile commands and a sudoers rule limited to three exact commands.
4. Installs and starts the `ps5-power-control-hardware` systemd service, which controls the GPU and fan.
5. Prints which PS5 interfaces it found.

### Bazzite notes

Bazzite is image-based, but `/usr/local`, `/etc` and `/var` are writable, so you do not need `rpm-ostree` or a reboot. The installer also restores SELinux labels on the files it copies. If Python cannot create virtual environments (unusual on Bazzite), the installer asks you to run `rpm-ostree install python3-pip` and reboot.

### Updating

```bash
cd ~/ps5-power-control && git pull --ff-only && ./install.sh
```

Each install builds a new virtual environment and removes the old one only after the new one works. Run `./install.sh` again after a distribution upgrade that changes the Python version.

**Updating needs a Git clone.** A folder extracted from a ZIP has no `.git` directory, so `git pull` fails with `fatal: not a git repository`. Clone the repository as shown above instead.

## Usage

```bash
ps5-power-control   # Open the dashboard (works over SSH)
ps5-powersave       # CPU governor: powersave
ps5-normal          # CPU governor: schedutil
ps5-performance     # CPU governor: performance
```

In the dashboard, click the buttons or press **1**, **2** or **3** for the CPU profiles and **Q** to quit. CPU meters refresh every second and hardware status every 2 seconds. A CPU governor applies until the next change or reboot. The app does not save it.

## Uninstall

```bash
cd ~/ps5-power-control && ./uninstall.sh
```

Add `--purge` to also delete saved settings (`/var/lib/ps5-power-control` and `~/.config/ps5-power-control`). Uninstalling does not reset governors or the fan target. They keep their current values until you reboot or change them.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `ensurepip is not available` / venv errors on Ubuntu | `python3 --version`, then `sudo apt install python3.X-venv python3-pip` with your version, and run `./install.sh` again |
| *Hardware service unavailable* | `systemctl status ps5-power-control-hardware` and `journalctl -u ps5-power-control-hardware -b` |
| GPU buttons disabled | `cat /sys/class/devfreq/ps5-gpufreq/available_governors`. The kernel driver may be missing |
| Fan buttons disabled | `cat /sys/bus/platform/devices/ps5-fan/target_temp` |
| *Profile failed* | Confirm that `/etc/sudoers.d/ps5-power-control` exists and that you installed as the same user |
| No CPU temperature | The app looks for `k10temp`, `zenpower` or `coretemp` sensors. Set `PS5_TEMP_MAX_C` to override the temperature scale |

Do not run another fan controller at the same time. The fan driver does not report RPM, so the app shows the target it read back, not proof that the fan is spinning.

## How it works

| Part | Location | Role |
| --- | --- | --- |
| Dashboard | `src/ps5_power_control/` | Textual app. Text lives in `languages/en.xml` and `languages/es.xml` |
| CPU profiles | `profiles/` → `/usr/local/bin/` | `ps5-power` validates every `cpufreq` policy before writing a governor |
| Hardware service | `hardware/ps5_control_service.py` → `/usr/local/lib/ps5-power-control/service.py` | Root service for the GPU governor, fan target and alarm |
| Installers | `install.sh`, `uninstall.sh` | System installation and removal |
| Standalone build | `build.sh` → `bin/` | Optional PyInstaller executable. The installer does not need it |
| Tests | `tests/` | `python3 -m unittest discover -s tests -v` |

**Security.** The dashboard runs as your user. CPU changes go through `sudo -n` and a sudoers rule that allows only `ps5-power powersave|schedutil|performance`. The hardware service listens on `/run/ps5-power-control/control.sock`, accepts connections only from root and the installing user (checked with `SO_PEERCRED`), and offers only four fixed operations: `status`, `fan`, `gpu_governor` and `settings`. It cannot run arbitrary commands. The service saves only the alarm state and threshold, in `/var/lib/ps5-power-control/settings.json`. It never saves the GPU governor or the fan target. Nothing changes the kernel, the boot configuration or CPU frequency limits.

Review `install.sh`, `profiles/` and `hardware/` before installing.

## Credits

GPU and fan behavior and kernel interfaces are based on [NotHavocc/ps5-hwcon-gui](https://github.com/NotHavocc/ps5-hwcon-gui) and its [ps5-hwcon-plugin](https://github.com/NotHavocc/ps5-hwcon-plugin). Kernel support comes from the PS5 Linux patches. This project's service is an independent implementation.

## Disclaimer

**This project is intended for research purposes only.**

PS5 Power Control was programmed with the assistance of OpenAI Codex.

This software is provided "as is", without warranty of any kind, express or implied. Use it entirely at your own risk. To the fullest extent permitted by applicable law, the authors, maintainers, and contributors accept no responsibility or liability for any damage, data loss, hardware failure, system instability, or other loss arising from installing, using, modifying, or being unable to use this software.

Firmware may override clocks. Software cannot guarantee safe temperatures.
