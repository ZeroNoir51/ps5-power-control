#!/usr/bin/env bash
# Remove PS5 Power Control. Pass --purge to also delete saved settings.
set -euo pipefail

SERVICE=ps5-power-control-hardware.service

[[ "$(id -u)" -ne 0 ]] || { echo 'ERROR: Run ./uninstall.sh as a regular user, not with sudo.' >&2; exit 1; }
case "${1:-}" in
  '') purge=no ;;
  --purge) purge=yes ;;
  *) echo 'Usage: ./uninstall.sh [--purge]' >&2; exit 2 ;;
esac

if [[ -e "/etc/systemd/system/$SERVICE" ]]; then
  sudo systemctl disable --now "$SERVICE" || true
  sudo rm -f -- "/etc/systemd/system/$SERVICE"
  sudo systemctl daemon-reload
fi
sudo rm -f -- /usr/local/bin/ps5-power-control /usr/local/bin/ps5-power /usr/local/bin/ps5-powersave \
  /usr/local/bin/ps5-normal /usr/local/bin/ps5-performance /etc/sudoers.d/ps5-power-control
sudo rm -rf -- /usr/local/lib/ps5-power-control

if [[ "$purge" == yes ]]; then
  sudo rm -rf -- /var/lib/ps5-power-control
  rm -rf -- "${XDG_CONFIG_HOME:-$HOME/.config}/ps5-power-control"
fi

echo 'PS5 Power Control removed.'
echo 'CPU/GPU governors and the fan target keep their current values until you reboot or change them.'
[[ "$purge" == yes ]] || echo 'Settings were kept; run ./uninstall.sh --purge to delete them too.'
