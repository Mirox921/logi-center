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
for filename in ['app.py','version.py','control_service.py','keyboard_layouts.py','g515_layout.py','g515_adapter.py','backend.py','i18n.py','solaar_write.py','execution.py','operations.py','backups.py','discovery.py','ratbag_dbus.py','mouse_models.py','macro_library.py','logitech_status.py','audio_pipeline.py','audio_status.py','diagnostics.py','devices.py','simulation.py','drafts.py','reports.py','solaar_adapter.py','mchose_adapter.py','k7_settings.py','sdk_worker.py','openrgb_adapter.py','openrazer_adapter.py','rivalcfg_adapter.py','ckb_adapter.py','capability_backup.py','ace68_adapter.py','ace68_protocol.py','ace68_bindings.py','ace68_advanced.py','eweadn_adapter.py','eweadn_protocol.py','device_status.py','device_service.py','device_presentation.py','battery_presentation.py','battery_service.py','device_artwork.py']:
    target=destination/filename
    if (source/filename).resolve()!=target.resolve():shutil.copy2(source/filename,target)
# Remove only obsolete bundled presentation modules during an upgrade.
# Preferences, drafts, device images and hardware backups live elsewhere.
for filename in ('audio_ui.py','dashboard.py','device_ui.py','keyboard_ui.py',
                 'microphone_ui.py','mouse_editor.py','peripheral_ui.py','mouse_art.py'):
    (destination/filename).unlink(missing_ok=True)
# Copy QML, native backups, fonts, diagrams and license manifests.
# No Qt import is required by installation.
qml_source=source/'qml_ui'
qml_target=destination/'qml_ui'
if qml_target.exists():shutil.rmtree(qml_target)
if qml_source.is_dir():shutil.copytree(qml_source,qml_target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for resource in ('assets/devices/exact/g502-top-wired-qt.svg','assets/devices/exact/g502-top-wireless-qt.svg','assets/devices/exact/g502_transparent_wired.svg','assets/devices/exact/g502_wireless.svg','assets/devices/exact/g502_hero_side_wired_fixed.svg','assets/devices/exact/g502_hero_side_wireless.svg','qml/G502ButtonPanel.qml','qml/GenericMouseButtons.qml','qml/MacroWindow.qml','assets/devices/exact/g502-hero-side.svg','assets/devices/exact/g502-hero-legacy.svg','qml/EweadnPanel.qml','assets/devices/exact/eweadn-s9.svg','assets/devices/exact/eweadn-s9-original.svg','qml/G515Panel.qml','qml/Ace68Panel.qml','qml/Ace68Keyboard.qml','qml/Ace68Assignments.qml','qml/Ace68Advanced.qml','qml/K7DockPanel.qml','qml/K7DpiPanel.qml','qml/K7ButtonPanel.qml','qml/K7PerformancePanel.qml','qml/NumberInput.qml','assets/diagrams/k7-dock.svg','assets/diagrams/k7-buttons.svg'):
    if not (qml_target/resource).is_file():raise FileNotFoundError('Missing QML dock resource: '+resource)
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
