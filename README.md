# PS5 Power Control v0.2

An SSH-friendly terminal dashboard for **PS5 Linux / Ubuntu 26.04**. It monitors CPU temperature, clock frequency, and the active CPU governor, with compact CPU, memory, temperature, and frequency meters. Three buttons and shortcuts select the CPU governor. **English is the default language** for the application, installation scripts, and documentation.

## Disclaimer

**Version: 0.2**

PS5 Power Control was programmed with the assistance of OpenAI Codex.

This software is provided "as is", without warranty of any kind, express or implied. Use it entirely at your own risk. To the fullest extent permitted by applicable law, the authors, maintainers, and contributors accept no responsibility or liability for any damage, data loss, hardware failure, system instability, or other loss arising from installing, using, modifying, or being unable to use this software.

## Project layout

```text
ps5-power-control/
├── src/ps5_power_control/app.py  # Textual TUI source
├── profiles/                     # Source for all CPU governor commands
│   ├── ps5-power
│   ├── ps5-powersave
│   ├── ps5-normal
│   └── ps5-performance
├── bin/                          # Generated standalone executable
├── build.sh                      # Build with PyInstaller
├── install.sh                    # One-step install, including dependencies
├── pyproject.toml
├── .gitignore
└── README.md
```

## One-step installation on the PS5

Extract the ZIP into `~/proyectos/ps5-power-control`, then run **as your normal user**:

```bash
cd ~/proyectos/ps5-power-control
chmod +x build.sh install.sh
./install.sh
```

The installer checks whether `python3 -m venv` can actually create an environment with pip. If Ubuntu reports that `ensurepip` is unavailable, it automatically runs `sudo apt-get update` and installs the matching `pythonX.Y-venv` package plus `python3-pip`. For example, with Python 3.14 it installs `python3.14-venv`. You may be prompted for your sudo password. The installer then builds a PyInstaller executable, installs the four profiles and TUI to `/usr/local/bin`, and adds a restricted sudoers rule for changing governors.

**The PS5 must have access to Ubuntu package repositories and PyPI during the first build.** If apt cannot locate `python3.14-venv`, check `python3 --version`, `apt-cache policy python3.14-venv`, and the enabled Ubuntu repositories. The script prints the underlying apt error instead of claiming success.

### Fix `ensurepip is not available` manually

```bash
python3 --version
sudo apt update
sudo apt install -y python3.14-venv python3-pip
cd ~/proyectos/ps5-power-control
./install.sh
```

Replace `3.14` with the Python version reported by `python3 --version` if needed. A failed virtual environment may leave `.venv` in the project directory; `build.sh` removes **only an incomplete project-local `.venv`** automatically. Do not run `sudo pip install` or install Python libraries into Ubuntu's system Python.

**Note:** `import ensurepip` in the system Python is *not* a reliable venv check on Debian/Ubuntu. Version 0.2 tests the actual `python3 -m venv` operation and pip availability in the created environment.

## Usage

```bash
ps5-power-control   # Launch TUI over SSH
ps5-powersave       # Set governor to powersave
ps5-normal          # Restore dynamic schedutil governor
ps5-performance     # Set governor to performance
```

In the TUI, click the buttons or press **1** (powersave), **2** (normal), **3** (performance), or **Q** (quit). Metrics update every second without clearing the terminal screen. The TUI uses `sudo -n` and shows permission errors rather than prompting inside the interface.

The program reads `/sys/devices/system/cpu/cpufreq/policy0` and looks for CPU temperature sensors named `k10temp`, `zenpower`, or `coretemp`, or relevant CPU thermal zones. If your PS5 exposes the CPU temperature under another hwmon name, sensor detection may need adjustment. The graphs are not measurements of power consumption in watts.

## Build only / Git

```bash
./build.sh
./bin/ps5-power-control
git init
git add .
git commit -m 'PS5 Power Control v0.2'
```

The standalone executable is generated locally for your PS5's Linux architecture and saved as `bin/ps5-power-control`; the ZIP includes the **source**, not a pre-built binary. `build.sh` does not use sudo or install system-wide commands.

## Security

Run `./install.sh` as a normal user. Review `install.sh` and `profiles/` before running. It installs root-owned scripts and allows the invoking user passwordless sudo for **only three exact arguments** to `/usr/local/bin/ps5-power`. It does not change the kernel, CPU frequency limits, EFI boot files, or boot configuration. Profile changes are not made persistent across reboot.

## Uninstall

```bash
sudo rm -f /usr/local/bin/ps5-power-control /usr/local/bin/ps5-power /usr/local/bin/ps5-powersave /usr/local/bin/ps5-normal /usr/local/bin/ps5-performance /etc/sudoers.d/ps5-power-control
```

## GPU and fan

PS5 Linux kernel interfaces are required: `ps5-gpufreq` (`CONFIG_PS5_GPUFREQ`), `ps5-fan`, `k10temp`, and `ps5_buzzer` for the alarm. Missing interfaces are reported by the application. The installer enables `ps5-power-control-hardware.service`, a privileged background service that continues monitoring after the TUI closes. Check it with `systemctl status ps5-power-control-hardware` and `journalctl -u ps5-power-control-hardware`. Its fixed socket API only accepts root and the user who installed it. Configuration is stored in `/var/lib/ps5-power-control/settings.json`.

The TUI displays all hwmon temperatures every 2 seconds. Fan presets are 85/80/72/65/50 °C and the manual target accepts 40–90 °C. Guard and alarm are opt-in. Guard changes the fan target to 50 °C at the chosen threshold (80–100 °C, default 95) and restores the previous target after the CPU cools by 10 °C. Alarm uses the console error beep once per event. Both depend on the `k10temp` sensor. A missing sensor, service failure, missing driver or failed write is reported; software monitoring is not a substitute for hardware thermal protection. Restore options reapply saved fan and GPU settings at service startup. Avoid running another fan controller concurrently.

GPU controls show governor, current/target frequency, range and available clocks. The governor is selected from those the driver offers; enter a listed MHz value or `auto` to remove the lock. The PS5 firmware may override clocks under some conditions. These features require testing on the target PS5 and have not been verified on hardware.

### Credits

GPU and fan behavior and kernel interfaces are based on [NotHavocc/ps5-hwcon-gui](https://github.com/NotHavocc/ps5-hwcon-gui) and its [ps5-hwcon-plugin](https://github.com/NotHavocc/ps5-hwcon-plugin). Kernel support is provided by the PS5 Linux patches. This project's service is an independent implementation.

To uninstall the hardware service, run `sudo systemctl disable --now ps5-power-control-hardware.service`, then remove `/etc/systemd/system/ps5-power-control-hardware.service` and `/usr/local/lib/ps5-power-control/`, and run `sudo systemctl daemon-reload`.
