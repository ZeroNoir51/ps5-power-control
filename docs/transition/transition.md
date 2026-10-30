# PS5 Power Control — transición del proyecto

Fecha de preparación: 30 de octubre de 2026 (America/Bogota). Documento de continuidad en español; aplicación y README en inglés por defecto.

## 1. Estado que recibe el siguiente desarrollador

- Repositorio: https://github.com/ZeroNoir51/ps5-power-control
- Rama de referencia: `main`.
- Commit empaquetado: `6f42b3a43ea3b949803e4b3a8e494a38f37d6cfd`.
- Versión vigente: **0.2**. No subirla automáticamente. El usuario primero pidió reiniciar a 0.1 y después autorizó expresamente 0.2.
- Producto: aplicación de terminal Python/Textual para PS5 con Linux, usable localmente o por SSH; controles de gobernador CPU/GPU y objetivo térmico del ventilador.
- Último cambio funcional: botones GPU y Fan, secciones CPU/GPU/Fan delimitadas y barra de frecuencia GPU.
- Este paquete es una copia verificable del código actual, documentación de transferencia y archivos históricos disponibles. No contiene un ejecutable compilado ni una instalación de PS5.
- No se modificó el comportamiento de la aplicación ni se publicó un nuevo commit para esta entrega.

Este documento combina código e historial Git recuperados el día de preparación, mensajes visibles del usuario y contexto recuperado de sesiones anteriores. Las pruebas de sesiones anteriores se identifican como reportadas; no se presentan como una nueva ejecución. No existe una transcripción íntegra de todas las conversaciones dentro de este paquete.

## 2. Alcance y reglas de producto

El objetivo es controlar perfiles y consultar métricas desde una terminal, sin depender de un escritorio gráfico. El entorno objetivo documentado es PS5 Linux / Ubuntu 26.04 con los drivers apropiados. El paquete declara Python >=3.10 y `textual>=0.80,<9`; la compatibilidad con cada combinación dentro de ese intervalo no ha sido comprobada.

Decisiones del usuario que deben mantenerse:

1. Barras compactas al estilo htop: uso **general** de CPU, sin filas por núcleo.
2. Mostrar memoria, temperatura y frecuencia; no confundir estos valores con consumo eléctrico en vatios.
3. Referencias de escala con margen visual del 5%; los colores solicitados fueron naranja al 90% y rojo por encima.
4. Inglés y español mediante archivos XML; inglés por defecto. La selección de idioma sí permanece como desplegable.
5. CPU con tres botones; GPU y Fan también con botones, no desplegables de perfiles.
6. Separar visualmente CPU, GPU y Fan y mantener sus datos en la sección correspondiente.
7. No reintroducir reloj GPU manual, GPU Restore, Fan Restore ni Thermal Guard sin una nueva solicitud.
8. Conservar versión 0.2 hasta nueva instrucción, créditos y avisos del README.
9. README en inglés: uso exclusivo para investigación, asistencia de Codex y exención de garantías/responsabilidad.

No está dentro del alcance actual: medición de vatios, indicadores de uso por core, confirmar giro/RPM sin sensor, modificar kernel/EFI/arranque, ni garantizar temperaturas seguras por software. El margen de escala del 5% no aumenta ninguna frecuencia del hardware.

## 3. Evolución del trabajo

### Base, instalación y primeras entregas

Se creó una TUI Python/Textual con perfiles CPU `powersave`, `normal` y `performance`, temperatura/frecuencia y gráficas. Las primeras entregas locales incluían sparklines; después se sustituyeron por barras compactas tipo htop. Se entregaron fuentes de los comandos de perfiles, instalador y script de compilación con PyInstaller.

El usuario reportó que faltaba `ensurepip`/soporte de venv, con Python 3.14. La solución implementada comprueba que `python3 -m venv` realmente cree un entorno con pip, permite al instalador instalar `pythonX.Y-venv` y `python3-pip`, y elimina únicamente una `.venv` local incompleta al recompilar. Comprobar solo `import ensurepip` no era suficiente en Debian/Ubuntu. Se documentó la corrección manual. No hay constancia aquí de una compilación final ejecutada en la PS5 después de cada revisión.

Existen ZIP anteriores denominados v0.2.2 y v0.1. Son antecedentes previos al estado actual; sus nombres no establecen la versión vigente. Se conservan en `historical/` para continuidad.

### Barras, idiomas y publicación

El usuario aclaró que quería el estilo de barras de htop, no la distribución de uso por núcleo. Se agregó uso agregado de CPU, memoria, temperatura, frecuencia y XML EN/ES. Se fijó versión 0.1 y se publicó el proyecto en GitHub tras solicitudes de acceso/reintentos.

Se retiró del README una sección de medidores compactos en el commit `9520858`; la solicitud visible «Qué es esto, remuévelo» no identifica por sí sola el elemento, pero el historial Git registra esa eliminación. Después se añadieron atribución a Codex y disclaimer en inglés.

### Expansión GPU/Fan y simplificación posterior

La referencia solicitada fue https://github.com/NotHavocc/ps5-hwcon-gui. Se implementó un servicio independiente y se reconocieron ese proyecto, su plugin y los parches de PS5 Linux en el README.

La primera ampliación incluyó gobernadores y relojes GPU, restauración al inicio, objetivos de ventilador, Thermal Guard y alarma. La simulación de esa etapa reportó pruebas de umbrales, histéresis de 10 °C, alarma, restauración y límites GPU. Esas pruebas describen una etapa histórica, no funcionalidades que deban volver a activarse.

El usuario autorizó cambiar a 0.2 y pidió añadir el uso exclusivo para investigación. Más tarde pidió retirar reloj GPU manual, los controles Restore de GPU/Fan y Select/Guard. El commit `8fa3599` eliminó esas funciones, también de la API del servicio; las claves antiguas de configuración se ignoran. Se mantuvieron objetivo manual de ventilador, gobernadores GPU y alarma opcional.

Finalmente se sustituyeron los desplegables GPU/Fan por botones, se añadieron bordes entre secciones y una barra de frecuencia GPU. El último cambio está en `6f42b3a`.

### Incidente de actualización Git

El usuario ejecutó `git pull --ff-only` en un directorio extraído de ZIP y recibió `fatal: not a git repository`. Una copia ZIP no incluye `.git`; reinstalar desde esa carpeta tampoco descarga cambios nuevos. Se indicó usar un clon independiente, `~/proyectos/ps5-power-control-git`, actualizarlo e instalar desde allí. El texto enviado también comenzaba con `d` en vez de `cd`.

Durante esta entrega se encontró otra copia local antigua sin `.git`; por ello se recuperaron los 16 archivos del commit actual desde GitHub, sin sobrescribir aquella copia ni usarla como fuente vigente.

## 4. Funcionalidad actual y comportamiento exacto

### CPU y memoria

- Botones/atajos: `1` Powersave → `powersave`; `2` Normal → `schedutil`; `3` Performance → `performance`; `Q` sale.
- Los scripts validan disponibilidad y permisos en todas las políticas `policy*` antes de escribir. La TUI muestra frecuencia/gobernador desde `policy0`.
- Uso agregado calculado con diferencias de `/proc/stat`.
- Memoria usada = `MemTotal - MemAvailable` de `/proc/meminfo`, presentada en GiB. La referencia es la memoria visible para Linux, no un total comercial fijo de VRAM/RAM.
- Temperatura: busca zonas térmicas y sensores CPU compatibles (`k10temp`, `zenpower`, `coretemp`).
- Métricas CPU/memoria: cada segundo.
- Frecuencia CPU: referencia de código 3.5 GHz y escala 3.675 GHz. Es una referencia de visualización; no se revalidó en esta entrega como especificación para todos los modelos PS5.
- Temperatura: referencia `PS5_TEMP_MAX_C` si válida; en otro caso `temp*_crit` de hwmon compatible; fallback 100 °C. Escala de la barra = referencia ×1.05.
- Uso CPU: escala 100%, sin margen adicional. Memoria y frecuencia sí llevan margen.

### GPU

- Interfaz esperada: `/sys/class/devfreq/ps5-gpufreq`.
- Botones para `simple_ondemand`, `performance`, `powersave`, `userspace`, limitados a lo anunciado por `available_governors`.
- Estado: gobernador, frecuencia actual/objetivo, mínimo/máximo. El servicio convierte Hz a MHz; la barra muestra GHz.
- Escala: mayor valor positivo de `available_frequencies` más 5%; si falta, referencia 2230 MHz más 5% = 2341.5 MHz.
- Sensores `amdgpu` en la sección GPU. Gobernadores no disponibles se deshabilitan.
- No hay selección manual de reloj ni restauración de ajustes GPU al iniciar. Un límite escrito por una versión anterior no se borra automáticamente por actualizar la aplicación.
- El firmware puede modificar el comportamiento de frecuencias; falta validación física.

### Fan, sensores y alarma

| Preset | Objetivo |
| --- | ---: |
| Quiet | 85 °C |
| Default | 80 °C |
| Balanced | 72 °C |
| Cool | 65 °C |
| Max Cooling | 50 °C |

El objetivo manual admite enteros 40–90 °C. Es una temperatura objetivo, no RPM, porcentaje PWM ni interruptor de encendido. La escritura en `/sys/bus/platform/devices/ps5-fan/target_temp` se verifica mediante lectura posterior.

Alarma ON/OFF: usa la máxima temperatura de los sensores `k10temp`; umbral entero de 80–100 °C, por defecto 95. Al alcanzar el umbral escribe `2` en `/sys/class/misc/ps5_buzzer/beep` una vez, y se rearma al enfriarse al menos 10 °C o desactivarse. Si falla la escritura no se marca como emitida. No cambia el objetivo del ventilador. Alarma inicialmente desactivada.

El servicio y la consulta de hardware trabajan cada 2 segundos. La alarma puede continuar al cerrar la TUI porque el servicio es independiente. Solo se persisten `alarm` y `threshold`; **no** gobernador GPU ni objetivo Fan.

`k10temp` se omite de la lista secundaria porque la temperatura CPU ya tiene su sección; `amdgpu` va a GPU y los demás sensores, incluidos SSD si existen, se muestran en «Other sensors» fuera de Fan. No se inventan sensores ausentes.

### Colores: detalle para continuidad

Las barras generales implementan verde por debajo del 90% de la referencia, naranja exactamente al 90% y rojo por encima. El naranja puede resultar muy breve con valores continuos. Los sensores adicionales usan otra regla: naranja desde el 90% del umbral de alarma y rojo al alcanzar el umbral. Esta diferencia existe en el código actual; no fue corregida al empaquetar. El umbral de alarma tampoco equivale necesariamente a `temp*_crit` ni al límite de la barra CPU.

### Idiomas y organización visual

Los textos se cargan de `languages/en.xml` y `languages/es.xml`; PyInstaller incluye ambos. La preferencia se guarda en `$XDG_CONFIG_HOME/ps5-power-control/settings.json`, o `~/.config/ps5-power-control/settings.json`. Idioma inválido vuelve a inglés.

Tres contenedores con borde separan CPU, GPU y Fan. Las filas de botones permiten desplazamiento horizontal en terminales estrechas. Algunos errores del servicio son mensajes técnicos en inglés; no asumir traducción completa de cada excepción.

## 5. Arquitectura, archivos y privilegios

| Archivo | Responsabilidad |
| --- | --- |
| `src/ps5_power_control/app.py` | TUI, métricas, barras, idioma, acciones y cliente del socket |
| `src/ps5_power_control/__init__.py` | Versión del paquete |
| `src/ps5_power_control/languages/{en,es}.xml` | Textos de interfaz |
| `hardware/ps5_control_service.py` | Control GPU/Fan y monitor de alarma |
| `profiles/ps5-power` | Valida/escribe gobernadores CPU |
| `profiles/ps5-{powersave,normal,performance}` | Comandos de perfiles |
| `build.sh` | venv, dependencias, PyInstaller, binario local |
| `install.sh` | Compila, instala comandos, sudoers y servicio systemd |
| `tests/test_hardware.py` | Cuatro pruebas unitarias con sysfs simulado |
| `pyproject.toml` | Dependencias, versión, entrypoint y XML como datos |
| `README.md`, `bin/README.md`, `.gitignore` | Uso, avisos, explicación del binario y exclusiones |

CPU: la TUI llama a comandos root-owned mediante `sudo -n`. La regla sudoers permite solo tres argumentos exactos de `/usr/local/bin/ps5-power`.

GPU/Fan: servicio root `/usr/local/lib/ps5-power-control/service.py`, unidad `ps5-power-control-hardware.service`, socket `/run/ps5-power-control/control.sock`. Protocolo JSON delimitado por salto de línea, operaciones `status`, `fan`, `gpu_governor`, `settings`. Aunque el socket tiene modo 0666, el servidor comprueba UID mediante `SO_PEERCRED` y acepta únicamente root o el usuario instalador. No es una API de ejecución arbitraria de comandos.

Estado del servicio en `/var/lib/ps5-power-control/settings.json`; escritura a temporal y reemplazo atómico. Un bloqueo evita dos instancias compitiendo por el socket. La instalación genera la unidad systemd dinámicamente; no falta un archivo de unidad en el paquete.

## 6. Qué funcionó y qué evidencia existe

| Comprobación | Evidencia / alcance |
| --- | --- |
| Estado actual GitHub | `main` apunta a `6f42b3a`; 16 blobs descargados y verificados byte a byte mediante hash Git |
| Pruebas del servicio | Ejecutadas de nuevo en esta entrega: 4/4 pasan, usando archivos temporales, sin hardware PS5 |
| Alarma | Prueba actual de disparo único, rearme y error por sensor ausente |
| Eliminaciones | Pruebas actuales rechazan comandos retirados e ignoran configuración antigua Restore/Guard |
| Validación de valores | Pruebas actuales rechazan objetivo Fan y umbral fuera de rango y gobernador inválido |
| Sintaxis y XML | Validación estática de Python, shell y XML realizada para este paquete; ver informe |
| UI con botones, separación, GPU, ES y resize | Pruebas simuladas reportadas en la sesión del último cambio; no hay suite persistida de UI en el repositorio |
| Restore/Guard y límites GPU antiguos | Simulación reportada de la etapa anterior, posteriormente retirada |
| PS5 física | Datos reales aportados por el usuario, descritos abajo; no validación integral GPU/Fan/UI |
| Ejecutable PyInstaller | Script disponible; no binario compilado ni compilación realizada en esta entrega |

En este entorno no está instalado Textual; no se repitieron las pruebas interactivas de la TUI. No se ejecutó `install.sh`, no se escribieron sensores reales ni se instaló el servicio en este equipo.

El usuario proporcionó: kernel `7.3.0-rc6-ps5hdmi120-rearm`, objetivo de ventilador `80`, controlador asociado `/sys/bus/platform/drivers/ps5-fan`, mensaje del kernel `FanServo: A-Eiger Micron`, y ninguna salida en sensores de velocidad. Esto respalda presencia del controlador y lectura del objetivo. **No demuestra giro, RPM ni eficacia térmica.** La interfaz no debe presentar «fan activo» como hecho basándose solo en esas lecturas.

## 7. Cómo retomar, instalar y diagnosticar

Para continuar con historial Git, usar un clon nuevo (no inicializar otra historia en una carpeta ZIP):

```bash
mkdir -p ~/proyectos
cd ~/proyectos
git clone https://github.com/ZeroNoir51/ps5-power-control.git ps5-power-control-git
cd ps5-power-control-git
git log -1 --oneline
./install.sh
ps5-power-control
```

Si ya existe ese clon:

```bash
cd ~/proyectos/ps5-power-control-git
git status --short
git pull --ff-only
./install.sh
```

No descartar cambios locales para forzar un pull. Para instalar esta instantánea sin Git, extraer el ZIP y entrar en `ps5-power-control-transition-0.2/ps5-power-control`; ejecutar `chmod +x build.sh install.sh` si el extractor perdió permisos, y después `./install.sh` como usuario normal. No ejecutar el instalador con sudo; pedirá elevación donde corresponde.

La compilación necesita repositorios Ubuntu/PyPI. `./build.sh` genera `bin/ps5-power-control` y no instala en el sistema. Si falla venv, instalar el paquete correspondiente a `python3 --version`; en el caso reportado fue `python3.14-venv` más `python3-pip`.

Diagnóstico de lectura:

```bash
systemctl status ps5-power-control-hardware.service
journalctl -u ps5-power-control-hardware.service -b
cat /sys/bus/platform/devices/ps5-fan/target_temp
cat /sys/class/devfreq/ps5-gpufreq/available_governors
cat /sys/class/devfreq/ps5-gpufreq/cur_freq
python3 -m unittest discover -s tests -v
```

Los archivos de sysfs pueden no existir si faltan drivers. El README incluye desinstalación de comandos/sudoers y, por separado, del servicio. Desinstalar no debe interpretarse como restaurar límites GPU históricos ni borrar toda configuración automáticamente.

## 8. Pendientes y límites conocidos

1. Validar en PS5 real el arranque de servicio, lectura/escritura de gobernador GPU, objetivos Fan y comportamiento de alarma. No provocar sobrecalentamiento para probarla; las pruebas sintéticas ya cubren los umbrales lógicos.
2. Registrar una prueba real de instalación/compilación y comportamiento de la TUI por SSH. Confirmar driver/sensores concretos y tamaño de terminal.
3. Si el usuario quiere una confirmación de ventilación, buscar telemetría real del controlador; sin ella solo informar objetivo leído/control disponible y RPM no disponibles.
4. Revisar la diferencia de colores entre barras y sensores si se desea uniformidad. No alterar silenciosamente el criterio aprobado.
5. El README tiene un árbol de archivos anterior a la ampliación hardware y ejemplos `git init` orientados a la primera creación; para continuar este repositorio usar clone/pull según este documento.
6. La unidad generada tiene `After=multi-user.target` y `WantedBy=multi-user.target`; conviene revisar su orden de arranque en el sistema real. No se afirma aquí haber reproducido un ciclo de systemd.
7. No hay suite persistida para todo el flujo UI ni validación de cada versión de Textual admitida. La prueba de archivos simulados tampoco valida permisos reales, protocolo de socket o controladores físicos por completo.
8. No aparece archivo LICENSE en el árbol actual. Los créditos y disclaimer no sustituyen una licencia; no se añadió ni se atribuyó una licencia inexistente.
9. Mantener cambios futuros pequeños, probar lo afectado, conservar XML en ambos idiomas y no cambiar versión sin autorización.

## 9. Contenido del paquete y trazabilidad

- `transition.md`: este documento.
- `ps5-power-control/`: los 16 archivos del commit vigente, con modos ejecutables restaurados y sin cambios funcionales.
- `evidence/source-tree.json`: árbol Git, identificadores y hashes de origen.
- `evidence/commits.json` y `evidence/git-history.md`: historial recuperado del repositorio.
- `evidence/validation.txt`: resultado de comprobaciones de esta entrega.
- `historical/`: los tres ZIP locales anteriores, solo referencia; no instalar por encima de la copia vigente.
- `MANIFEST.sha256`: integridad de los archivos empaquetados, excepto el propio manifiesto.

No se incluyen `.git`, entornos virtuales, cachés, credenciales ni un binario precompilado. Las imágenes de conversación no son fuente vigente del proyecto y no forman parte del paquete. El ZIP sirve como instantánea; para trabajar con commits hay que clonar GitHub.

Fuentes principales: árbol y commits de https://github.com/ZeroNoir51/ps5-power-control/tree/6f42b3a43ea3b949803e4b3a8e494a38f37d6cfd, README y código incluidos; solicitudes y salida de diagnóstico del usuario; contexto recuperado de pruebas anteriores, con las limitaciones señaladas.
