#!/usr/bin/env bash
# Install build prerequisites (when needed), build the TUI, and install profiles.
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(id -u)" -eq 0 ]]; then
  echo 'ERROR: Run ./install.sh as a regular user, not with sudo.' >&2
  exit 1
fi
command -v python3 >/dev/null || { echo 'ERROR: python3 is missing. Install python3 first.' >&2; exit 1; }
command -v sudo >/dev/null || { echo 'ERROR: sudo is required for system installation.' >&2; exit 1; }

pyver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
testdir="$(mktemp -d)"
trap 'rm -rf -- "$testdir"' EXIT
if ! python3 -m venv "$testdir/check" >/dev/null 2>&1 || ! "$testdir/check/bin/python" -m pip --version >/dev/null 2>&1; then
  echo "Python $pyver virtual environment support is missing."
  echo "Installing python${pyver}-venv and python3-pip with apt..."
  if ! command -v apt-get >/dev/null; then
    echo 'ERROR: apt-get is unavailable; install venv support manually.' >&2
    exit 1
  fi
  sudo apt-get update
  sudo apt-get install -y "python${pyver}-venv" python3-pip
fi
rm -rf -- "$testdir"
trap - EXIT

./build.sh
sudo -v
for name in ps5-power ps5-powersave ps5-normal ps5-performance; do
  sudo install -o root -g root -m 0755 "profiles/$name" "/usr/local/bin/$name"
done
sudo install -o root -g root -m 0755 bin/ps5-power-control /usr/local/bin/ps5-power-control

# Limit passwordless privilege to three exact root-owned commands/arguments.
user="$(id -un)"
if [[ ! "$user" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  echo 'ERROR: Username needs manual sudoers configuration.' >&2
  exit 1
fi
sudoers_tmp="$(mktemp)"
trap 'rm -f -- "$sudoers_tmp"' EXIT
cat > "$sudoers_tmp" <<RULES
# PS5 Power Control: allow only the three fixed governors.
$user ALL=(root) NOPASSWD: /usr/local/bin/ps5-power powersave, /usr/local/bin/ps5-power schedutil, /usr/local/bin/ps5-power performance
RULES
sudo visudo -cf "$sudoers_tmp"
sudo install -o root -g root -m 0440 "$sudoers_tmp" /etc/sudoers.d/ps5-power-control
sudo visudo -cf /etc/sudoers.d/ps5-power-control
printf '\nInstallation complete. Commands:\n  ps5-power-control\n  ps5-powersave\n  ps5-normal\n  ps5-performance\n'
