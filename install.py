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
for filename in ['app.py','backend.py','i18n.py','solaar_write.py','execution.py','operations.py','backups.py','discovery.py','ratbag_dbus.py','mouse_models.py','mouse_editor.py','mouse_art.py','audio_pipeline.py','microphone_ui.py','diagnostics.py','devices.py','device_ui.py','keyboard_ui.py','simulation.py','drafts.py','reports.py','solaar_adapter.py','mchose_adapter.py','sdk_worker.py','openrgb_adapter.py','openrazer_adapter.py','rivalcfg_adapter.py','ckb_adapter.py','capability_backup.py','ace68_adapter.py','ace68_protocol.py']:
    target=destination/filename
    if (source/filename).resolve()!=target.resolve():shutil.copy2(source/filename,target)
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
