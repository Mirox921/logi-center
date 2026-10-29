#!/usr/bin/env python3
"""Exercise QML backup selection/results with the real services and memory I/O."""
# Allow direct execution without installing developer tools.
if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import scripts  # source-package bootstrap
from pathlib import Path
import os
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def exercise(app, root, bridge, finished):
    from PySide6.QtCore import QTimer, Qt
    from PySide6.QtTest import QTest
    import logi_center.core.services.capability_backup as service
    controller = bridge.backups
    mock = controller.transport
    folder = Path(os.environ.get('LOGI_CENTER_BACKUP_SCREENSHOTS', '/tmp/logi-qml-backup-review'))
    folder.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix='logi-backup-preview-')
    path = Path(temporary.name) / 'backup.json'
    root.setProperty('page', 'backups')
    root.requestActivate()
    # No real device or command may enter this smoke. The main runner patches
    # backend.run to fail and the facade uses its explicitly simulated transport.
    document = service.capture(mock.devices[0], lambda args: '{"dpi":1600,"debounce":8}')
    service.write(document, path)
    controller.inspectFile(path.as_uri())
    deadline = time.monotonic() + 15

    def visual(item, name):
        if item.objectName() == name: return item
        for child in item.childItems():
            found = visual(child, name)
            if found is not None: return found
        return None

    def wait_then(callback):
        if time.monotonic() > deadline:
            raise AssertionError('Backup smoke timed out: '+controller.message)
        if controller.busy:
            QTimer.singleShot(20, lambda: checked(lambda: wait_then(callback)))
        else: callback()

    def checked(callback):
        try: callback()
        except BaseException:
            import traceback
            traceback.print_exc()
            root.grabWindow().save(str(folder / 'failure.png'))
            def describe(item):
                if item.objectName().startswith('backup'):
                    print('Backup visual:', item.objectName(), item.width(), item.height(), item.isVisible())
                for child in item.childItems(): describe(child)
            describe(root.contentItem())
            temporary.cleanup()
            app.exit(10)

    def capture_series(name, then):
        cases = [('ru', 640), ('ru', 1000), ('en', 640), ('en', 1000)]
        def take(index=0):
            if index == len(cases):
                then(); return
            language, width = cases[index]
            bridge.setLanguage(language); root.resize(width, 820)
            def save():
                assert root.width() == width, 'Compositor did not apply the requested logical width'
                destination = folder / f'{name}-{language}-{width}.png'
                assert root.grabWindow().save(str(destination))
                take(index + 1)
            QTimer.singleShot(180, lambda: checked(save))
        take()

    def preview_ready():
        assert controller.canRestore and controller.fields.count == 2, controller.message
        assert not mock.writes
        target = visual(root.contentItem(), 'backupTarget')
        assert target is not None
        target.forceActiveFocus(); QTest.keyClick(root, Qt.Key.Key_Space)
        QTimer.singleShot(150, lambda: checked(close_target_popup))

    def close_target_popup():
        from PySide6.QtCore import QObject
        popup = root.findChild(QObject, 'backupTargetPopup')
        assert popup is not None and popup.property('visible')
        assert root.grabWindow().save(str(folder / 'targets-popup.png'))
        QTest.keyClick(root, Qt.Key.Key_Escape)
        assert not popup.property('visible')
        assert root.property('page') == 'backups'
        checkbox = visual(root.contentItem(), 'backup-field-mchose:debounce')
        assert checkbox is not None
        checkbox.forceActiveFocus(); QTest.keyClick(root, Qt.Key.Key_Space)
        assert controller.selectedCount == 1
        capture_series('preview', restore)

    def restore():
        button = visual(root.contentItem(), 'backupRestore')
        assert button is not None and button.property('enabled')
        button.forceActiveFocus(); QTest.keyClick(root, Qt.Key.Key_Space)
        wait_then(restored)

    def restored():
        assert mock.values == {'dpi':1600,'debounce':4}
        assert mock.writes == ['dpi']
        assert not controller.canRestore
        assert controller.fields._rows[0]['resultKey'] == 'Подтверждено чтением'
        assert list((Path(controller._temporary.name)/'before-restore').glob('*.json'))
        capture_series('result', partial_preview)

    def partial_preview():
        mock.writes.clear(); mock.fail_field='debounce'
        service.write(service.capture(mock.devices[0],lambda args:'{"dpi":2400,"debounce":8}'),path)
        controller.inspectFile(str(path)); wait_then(partial_restore)

    def partial_restore():
        assert controller.canRestore
        controller.restoreSelected(); wait_then(partial_done)

    def partial_done():
        assert mock.values == {'dpi':2400,'debounce':4}
        assert 'отключено' in controller.fields._rows[1]['resultKey']
        capture_series('partial', done)

    def done():
        temporary.cleanup()
        print('PASS: QML backup preview, keyboard field selection, selective restore, private snapshot, partial result and RU/EN; memory I/O only.')
        finished()

    QTimer.singleShot(200, lambda: checked(lambda: wait_then(preview_ready)))


def main():
    from unittest.mock import patch
    from logi_center.qml_ui.main import run
    os.environ['QT_QPA_PLATFORM'] = 'wayland' if '--wayland' in sys.argv else 'offscreen'
    os.environ['QT_QPA_PLATFORMTHEME'] = 'generic'
    os.environ['LOGI_CENTER_QML_BACKUP_SMOKE'] = '1'
    with patch('logi_center.adapters.external.backend.run', side_effect=AssertionError('Real CLI called from backup simulation')):
        return run(['qml-backup-smoke', '--simulate', '--smoke'])


if __name__ == '__main__':
    raise SystemExit(main())
