# Instalación de PS5 Power Control (Ubuntu y Bazzite)

Guía rápida en español. La referencia completa está en el [README](../README.md) (en inglés).

**Uso exclusivo para investigación, sin garantía.** Lee el aviso del README antes de instalar.

## Requisitos

- Ubuntu 24.04 o posterior, o Bazzite (también deberían funcionar otros sistemas basados en Debian o Fedora).
- Un kernel PS5 Linux. Los controles de GPU y ventilador necesitan `ps5-gpufreq`, `ps5-fan`, `k10temp` y `ps5_buzzer`.
- `python3` 3.10 o posterior, `sudo` y systemd.
- Internet durante la instalación, para descargar Textual desde PyPI.

## Instalar

Ejecuta el instalador como **usuario normal, sin `sudo`**. Pedirá la contraseña cuando la necesite. Los comandos son iguales en Ubuntu y en Bazzite.

```bash
git clone https://github.com/ZeroNoir51/ps5-power-control.git ~/ps5-power-control
```

```bash
cd ~/ps5-power-control && ./install.sh
```

Al terminar, el instalador muestra qué interfaces de la PS5 encontró. Si falta alguna, la app desactiva los botones correspondientes.

### Bazzite

No necesitas `rpm-ostree` ni reiniciar: `/usr/local`, `/etc` y `/var` admiten escritura. El instalador también restaura las etiquetas de SELinux. Solo si Python no puede crear entornos virtuales (algo raro en Bazzite), te pedirá ejecutar `rpm-ostree install python3-pip` y reiniciar.

### Ubuntu

Si falta el soporte de entornos virtuales (`ensurepip is not available`), el instalador instala `pythonX.Y-venv` y `python3-pip` con apt.

## Actualizar

```bash
cd ~/ps5-power-control && git pull --ff-only && ./install.sh
```

Necesitas un clon de Git: una carpeta extraída de un ZIP no tiene `.git` y `git pull` falla. Vuelve a ejecutar `./install.sh` también después de actualizar la distribución.

## Usar

```bash
ps5-power-control   # Panel (funciona por SSH)
ps5-powersave       # Gobernador CPU: powersave
ps5-normal          # Gobernador CPU: schedutil
ps5-performance     # Gobernador CPU: performance
```

En el panel, usa los botones o pulsa **1**, **2** y **3** para los perfiles de CPU, y **Q** para salir. El idioma se cambia en el desplegable.

## Desinstalar

```bash
cd ~/ps5-power-control && ./uninstall.sh
```

Con `--purge` también borra la configuración guardada. Desinstalar no restablece los gobernadores ni el objetivo del ventilador: mantienen su valor hasta reiniciar.

## Diagnóstico

```bash
systemctl status ps5-power-control-hardware
```

```bash
journalctl -u ps5-power-control-hardware -b
```

```bash
cat /sys/class/devfreq/ps5-gpufreq/available_governors /sys/bus/platform/devices/ps5-fan/target_temp
```
