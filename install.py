#!/usr/bin/env python3
"""Install Logi Center for the current user, without administrator privileges."""
from pathlib import Path
import os, shlex, shutil, sys

source=Path(__file__).resolve().parent
data_root=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
destination=data_root/'logi-center'
bin_dir=Path.home()/'.local/bin'
apps_dir=data_root/'applications'
for folder in [destination,bin_dir,apps_dir]:folder.mkdir(parents=True,exist_ok=True)
for filename in ['app.py','backend.py','i18n.py','solaar_write.py']:
    target=destination/filename
    if (source/filename).resolve()!=target.resolve():shutil.copy2(source/filename,target)
launcher=bin_dir/'logi-center'
launcher.write_text('#!/bin/sh\nexec /usr/bin/python '+shlex.quote(str(destination/'app.py'))+' "$@"\n')
launcher.chmod(0o755)
# Desktop Exec uses its own quoting rules, not shell escaping.
exec_path=str(launcher).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
(apps_dir/'logi-center.desktop').write_text(
    '[Desktop Entry]\nType=Application\nName=Logi Center\n'
    'Comment=Logitech device settings in one place\nComment[ru]=Единый центр управления Logitech\n'
    f'Exec="{exec_path}"\nIcon=input-gaming\nTerminal=false\nCategories=Settings;HardwareSettings;\nStartupNotify=true\n')
print('Installed:',destination)
print('Launch:',launcher)
