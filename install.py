#!/usr/bin/env python3
"""Install Logi Center for the current user, without administrator privileges."""
from pathlib import Path
import os, shlex, shutil, sys

source=Path(__file__).resolve().parent
data_root=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
destination=data_root/'logi-center'
bin_dir=Path.home()/'.local/bin'
apps_dir=data_root/'applications'
icon_dir=data_root/'icons/hicolor/scalable/apps'
for folder in [destination,bin_dir,apps_dir,icon_dir]:folder.mkdir(parents=True,exist_ok=True)
# Stage the same package/resources used by wheel and Arch builds.
package_source=source/'src/logi_center'
package_target=destination/'logi_center'
if source.resolve()==destination.resolve():
    raise SystemExit('Install from a checkout, not from the runtime directory.')
if package_target.exists():shutil.rmtree(package_target)
shutil.copytree(package_source,package_target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copytree(source/'assets',package_target/'assets',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
shutil.copy2(source/'app.py',destination/'app.py')
# Remove only known obsolete application files; never touch private preferences.
for filename in ['ace68_adapter.py', 'ace68_advanced.py', 'ace68_bindings.py', 'ace68_protocol.py', 'audio_pipeline.py', 'audio_status.py', 'audio_ui.py', 'backend.py', 'backups.py', 'battery_presentation.py', 'battery_service.py', 'capability_backup.py', 'ckb_adapter.py', 'control_service.py', 'dashboard.py', 'device_artwork.py', 'device_presentation.py', 'device_service.py', 'device_status.py', 'device_ui.py', 'devices.py', 'diagnostics.py', 'discovery.py', 'drafts.py', 'eweadn_adapter.py', 'eweadn_protocol.py', 'execution.py', 'g515_adapter.py', 'g515_layout.py', 'i18n.py', 'k7_settings.py', 'keyboard_layouts.py', 'keyboard_ui.py', 'logitech_status.py', 'macro_library.py', 'mchose_adapter.py', 'microphone_ui.py', 'mouse_art.py', 'mouse_editor.py', 'mouse_models.py', 'openrazer_adapter.py', 'openrgb_adapter.py', 'operations.py', 'peripheral_ui.py', 'ratbag_dbus.py', 'reports.py', 'rivalcfg_adapter.py', 'sdk_worker.py', 'simulation.py', 'solaar_adapter.py', 'solaar_write.py', 'version.py']:
    (destination/filename).unlink(missing_ok=True)
legacy_qml=destination/'qml_ui'
if legacy_qml.exists():shutil.rmtree(legacy_qml)
icon_source=source/'packaging/icons/logi-center.svg'
if icon_source.is_file():shutil.copy2(icon_source,icon_dir/'logi-center.svg')
launcher=bin_dir/'logi-center'
launcher.write_text('#!/bin/sh\nexec /usr/bin/python '+shlex.quote(str(destination/'app.py'))+' "$@"\n')
launcher.chmod(0o755)
# Desktop Exec uses its own quoting rules, not shell escaping.
exec_path=str(launcher).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
(apps_dir/'logi-center.desktop').write_text(
    '[Desktop Entry]\nType=Application\nName=Logi Center\n'
    'Comment=Linux peripheral settings through supported backends\nComment[ru]=Настройка периферии Linux\n'
    f'Exec="{exec_path}"\nIcon=logi-center\nTerminal=false\nCategories=Settings;HardwareSettings;\nStartupNotify=true\n')
print('Installed:',destination)
print('Launch:',launcher)
