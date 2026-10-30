#!/usr/bin/env bash
# Install or update PS5 Power Control on Ubuntu/Debian or Fedora-based systems (Bazzite included).
# Run as a regular user; sudo is requested only for the system-wide steps.
set -euo pipefail
cd "$(dirname "$0")"

LIB_DIR=/usr/local/lib/ps5-power-control
BIN_DIR=/usr/local/bin
SERVICE=ps5-power-control-hardware.service
PROFILES=(ps5-power ps5-powersave ps5-normal ps5-performance)

die() { echo "ERROR: $*" >&2; exit 1; }
step() { printf '\n==> %s\n' "$*"; }

[[ "$(id -u)" -ne 0 ]] || die 'Run ./install.sh as a regular user, not with sudo. It asks for sudo when needed.'
command -v sudo >/dev/null || die 'sudo is required.'
command -v systemctl >/dev/null || die 'systemd is required for the hardware service.'
[[ -x /usr/bin/python3 ]] || die '/usr/bin/python3 is missing. Install the distribution python3 package first.'
/usr/bin/python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || die "Python 3.10 or newer is required (found $(/usr/bin/python3 -V))."
pyver="$(/usr/bin/python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

# Detect the distribution family; Bazzite reports ID=bazzite with ID_LIKE=fedora.
family=other
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  case " ${ID:-} ${ID_LIKE:-} " in
    *" ubuntu "*|*" debian "*) family=debian ;;
    *" fedora "*|*" rhel "*|*" centos "*) family=fedora ;;
  esac
fi
atomic=no
[[ -e /run/ostree-booted ]] && atomic=yes
echo "System: ${PRETTY_NAME:-unknown} | family: $family | image-based: $atomic | Python $pyver"

venv_works() {
  local dir status=1
  dir="$(mktemp -d)"
  if /usr/bin/python3 -m venv "$dir/venv" >/dev/null 2>&1 && "$dir/venv/bin/python" -m pip --version >/dev/null 2>&1; then
    status=0
  fi
  rm -rf -- "$dir"
  return "$status"
}

step 'Checking Python virtual environment support'
if ! venv_works; then
  case "$family" in
    debian)
      echo "Installing python${pyver}-venv and python3-pip with apt..."
      sudo apt-get update
      sudo apt-get install -y "python${pyver}-venv" python3-pip
      ;;
    fedora)
      if [[ "$atomic" == yes ]]; then
        die "Python venv support is missing. Run 'rpm-ostree install python3-pip', reboot, then run ./install.sh again."
      fi
      sudo dnf install -y python3-pip
      ;;
    *)
      die "Python $pyver cannot create a virtual environment with pip. Install your distribution's venv/pip package and retry."
      ;;
  esac
  venv_works || die 'Python virtual environments still do not work. See the errors above.'
fi
echo 'OK'

# A fresh, timestamped environment per install: a failed update never breaks the working one.
step "Installing the terminal app into $LIB_DIR"
sudo install -d -o root -g root -m 0755 "$LIB_DIR"
venv="$LIB_DIR/venv-$(date +%Y%m%d%H%M%S)"
build="$(sudo mktemp -d)"
cleanup() { sudo rm -rf -- "$build"; }
trap cleanup EXIT
sudo cp -r pyproject.toml src "$build/"
sudo /usr/bin/python3 -m venv "$venv"
if ! sudo "$venv/bin/python" -m pip install --quiet --no-cache-dir --disable-pip-version-check "$build"; then
  sudo rm -rf -- "$venv"
  die 'Installing Python dependencies failed. The PS5 needs internet access to PyPI during installation.'
fi
sudo ln -sfn "$venv/bin/ps5-power-control" "$BIN_DIR/ps5-power-control"
for old in "$LIB_DIR"/venv-*; do
  [[ "$old" == "$venv" ]] || sudo rm -rf -- "$old"
done

step 'Installing CPU profile commands'
for name in "${PROFILES[@]}"; do
  sudo install -o root -g root -m 0755 "profiles/$name" "$BIN_DIR/$name"
done

# Limit passwordless privilege to three exact root-owned commands/arguments.
step 'Adding the sudoers rule for the three CPU governors'
user="$(id -un)"
[[ "$user" =~ ^[a-z_][a-z0-9_-]*$ ]] || die "Username '$user' needs manual sudoers configuration."
sudoers_tmp="$(mktemp)"
cat > "$sudoers_tmp" <<RULES
# PS5 Power Control: allow only the three fixed governors.
$user ALL=(root) NOPASSWD: $BIN_DIR/ps5-power powersave, $BIN_DIR/ps5-power schedutil, $BIN_DIR/ps5-power performance
RULES
sudo visudo -cqf "$sudoers_tmp" || die 'Generated sudoers rule is invalid.'
sudo install -o root -g root -m 0440 "$sudoers_tmp" /etc/sudoers.d/ps5-power-control
rm -f -- "$sudoers_tmp"

# The privileged hardware service accepts fixed operations only from root and this user.
step "Installing $SERVICE"
sudo install -o root -g root -m 0755 hardware/ps5_control_service.py "$LIB_DIR/service.py"
unit_tmp="$(mktemp)"
cat > "$unit_tmp" <<UNIT
[Unit]
Description=PS5 Power Control hardware service

[Service]
Type=simple
ExecStart=/usr/bin/python3 $LIB_DIR/service.py --uid $(id -u)
Restart=on-failure
RestartSec=3
RuntimeDirectory=ps5-power-control
RuntimeDirectoryMode=0755
StateDirectory=ps5-power-control
StateDirectoryMode=0700
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=full

[Install]
WantedBy=multi-user.target
UNIT
sudo install -o root -g root -m 0644 "$unit_tmp" "/etc/systemd/system/$SERVICE"
rm -f -- "$unit_tmp"

# Fedora/Bazzite enforce SELinux: give the copied files their default labels.
if command -v restorecon >/dev/null; then
  sudo restorecon -R "$(readlink -f "$LIB_DIR")" "$(readlink -f "$BIN_DIR")" /etc/sudoers.d/ps5-power-control "/etc/systemd/system/$SERVICE" 2>/dev/null || true
fi

sudo systemctl daemon-reload
sudo systemctl enable --quiet "$SERVICE"
sudo systemctl restart "$SERVICE"

step 'Checking PS5 interfaces'
check() { if [[ -e "$1" ]]; then echo "  found    $2"; else echo "  missing  $2 ($1)"; fi; }
check /sys/devices/system/cpu/cpufreq/policy0 'CPU frequency scaling'
check /sys/class/devfreq/ps5-gpufreq 'GPU frequency driver (ps5-gpufreq)'
check /sys/bus/platform/devices/ps5-fan/target_temp 'Fan controller (ps5-fan)'
check /sys/class/misc/ps5_buzzer/beep 'Buzzer for the alarm (ps5_buzzer)'
if systemctl is-active --quiet "$SERVICE"; then
  echo "  running  $SERVICE"
else
  echo "  stopped  $SERVICE (see: journalctl -u $SERVICE -b)"
fi

cat <<DONE

Installation complete. Commands:
  ps5-power-control   terminal dashboard
  ps5-powersave       CPU governor: powersave
  ps5-normal          CPU governor: schedutil
  ps5-performance     CPU governor: performance
Missing interfaces only disable the matching controls.
DONE
