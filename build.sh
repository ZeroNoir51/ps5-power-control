#!/usr/bin/env bash
# Optional: build a standalone PyInstaller executable in bin/. Run as a regular user.
# ./install.sh does not need this; it installs the app into a virtual environment.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(id -u)" -eq 0 ]]; then
  echo 'ERROR: Run ./build.sh as a regular user (without sudo).' >&2
  exit 1
fi

command -v python3 >/dev/null || { echo 'ERROR: python3 is missing.' >&2; exit 1; }
pyver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

# On Debian/Ubuntu, ensurepip may be unavailable in the *system* Python even
# when python3 -m venv works. Test venv itself instead of importing ensurepip.
check_venv() {
  local testdir
  testdir="$(mktemp -d)"
  if python3 -m venv "$testdir/venv" >/dev/null 2>&1 && "$testdir/venv/bin/python" -m pip --version >/dev/null 2>&1; then
    rm -rf "$testdir"
    return 0
  fi
  rm -rf "$testdir"
  return 1
}

if ! check_venv; then
  echo "ERROR: Python $pyver cannot create a working virtual environment." >&2
  echo '  Ubuntu/Debian: sudo apt install python'"$pyver"'-venv python3-pip' >&2
  echo '  Fedora:        sudo dnf install python3-pip' >&2
  echo '  Bazzite:       rpm-ostree install python3-pip, then reboot' >&2
  exit 1
fi

# Replace only a broken local environment (never another directory).
if [[ -d .venv ]] && { [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; }; then
  echo 'Removing incomplete local .venv from a previous failed build.'
  rm -rf -- .venv
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -e . pyinstaller
.venv/bin/python -m PyInstaller --noconfirm --clean --onefile --name ps5-power-control --paths src --add-data "src/ps5_power_control/languages:languages" src/ps5_power_control/app.py
mkdir -p bin
install -m 0755 dist/ps5-power-control bin/ps5-power-control
echo "Executable: $PWD/bin/ps5-power-control"
